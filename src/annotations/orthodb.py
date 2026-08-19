"""Map UniProt accessions to OrthoDB groups via UniProt's ID mapping API."""

from __future__ import annotations

import json
import time
import urllib.parse
from pathlib import Path

from urls import (
    UNIPROT_IDMAPPING_RUN,
    UNIPROT_IDMAPPING_STATUS,
    USER_AGENT,
)

BATCH = 10000


def _curl(url: str, post_data: str | None = None) -> bytes:
    import subprocess

    cmd = ["curl", "-sS", "-L", "--max-time", "600", "-A", USER_AGENT]
    if post_data is not None:
        cmd += ["-X", "POST", "--data", post_data, url]
    else:
        cmd += [url]
    return subprocess.check_output(cmd)


def _curl_json(url: str, post_data: str | None = None) -> dict:
    raw = _curl(url, post_data)
    if not raw.strip():
        return {}
    return json.loads(raw.decode())


def _wait_job(job: str) -> None:
    for _ in range(180):
        status = _curl_json(UNIPROT_IDMAPPING_STATUS.format(job=job))
        if status.get("jobStatus") == "RUNNING":
            time.sleep(2)
            continue
        return
    raise TimeoutError(f"UniProt ID mapping job {job} did not finish")


def _stream_pairs(job: str) -> list[tuple[str, str]]:
    raw = _curl(f"https://rest.uniprot.org/idmapping/stream/{job}?format=tsv").decode()
    pairs = []
    lines = raw.splitlines()
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        src = parts[0].split("-")[0].strip().upper()
        dest = parts[1].strip()
        if src and dest:
            pairs.append((src, dest))
    return pairs


def map_ids(
    identifiers: list[str],
    *,
    source: str,
    dest: str,
    cache_path: Path,
) -> dict[str, str]:
    wanted = sorted({str(a).split("-")[0].strip().upper() for a in identifiers if str(a).strip()})
    wanted = [w for w in wanted if w not in {"NAN", "NONE", "NA"}]
    mapping: dict[str, str] = {}
    if cache_path.exists():
        mapping = json.loads(cache_path.read_text())
        print(f"ID-map cache {len(mapping)} from {cache_path}", flush=True)
    missing = [a for a in wanted if a not in mapping]
    if not missing:
        return mapping
    print(f"Mapping {len(missing)} {source}->{dest} ids ({len(wanted)} total)", flush=True)
    for i in range(0, len(missing), BATCH):
        chunk = missing[i : i + BATCH]
        payload = urllib.parse.urlencode({"from": source, "to": dest, "ids": ",".join(chunk)})
        job = _curl_json(UNIPROT_IDMAPPING_RUN, payload).get("jobId")
        if not job:
            raise RuntimeError(f"UniProt ID mapping did not return a job for batch {i}")
        print(f"  job {job} ({len(chunk)} ids)", flush=True)
        _wait_job(job)
        pairs = _stream_pairs(job)
        for src, target in pairs:
            mapping[src] = target
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(mapping, indent=0, sort_keys=True))
        print(f"  cache now {len(mapping)} mappings", flush=True)
    return mapping


def map_uniprot_to_orthodb(accessions: list[str], cache_path: Path) -> dict[str, str]:
    return map_ids(accessions, source="UniProtKB_AC-ID", dest="OrthoDB", cache_path=cache_path)


def map_entrez_to_uniprot(entrez_ids: list[str], cache_path: Path) -> dict[str, str]:
    return map_ids(
        [str(i) for i in entrez_ids],
        source="GeneID",
        dest="UniProtKB",
        cache_path=cache_path,
    )
