"""Download public annotation caches into data/cache (Dropbox / Sherlock only)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import zipfile
from pathlib import Path

from urls import (
    CDCODE_RELEASE,
    HAGR,
    PHASEPRED_BASE,
    PHASEPRED_SPECIES,
    USER_AGENT,
    cache_dir,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        print(f"exists {dest} ({dest.stat().st_size} bytes)", flush=True)
        return dest
    tmp = dest.with_suffix(dest.suffix + ".partial")
    print(f"GET {url}", flush=True)
    cmd = [
        "curl",
        "-fL",
        "--retry",
        "3",
        "--retry-delay",
        "2",
        "-A",
        USER_AGENT,
        "-o",
        str(tmp),
        url,
    ]
    subprocess.run(cmd, check=True)
    tmp.replace(dest)
    print(f"wrote {dest} ({dest.stat().st_size} bytes)", flush=True)
    return dest


def unzip(zip_path: Path, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            target = out_dir / Path(info.filename).name
            target.write_bytes(zf.read(info))
            written.append(target)
            print(f"unzipped {target.name} ({target.stat().st_size} bytes)", flush=True)
    return written


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument(
        "--phasepred",
        action="store_true",
        default=True,
        help="Download all PhaSePred species zips (default: on).",
    )
    parser.add_argument("--no-phasepred", action="store_true")
    parser.add_argument("--phasepred-human-only", action="store_true")
    parser.add_argument("--skip-cdcode", action="store_true")
    parser.add_argument("--skip-hagr", action="store_true")
    args = parser.parse_args()
    cache = cache_dir(args.repo_root)

    if not args.skip_hagr:
        for name, url in HAGR.items():
            zpath = download(url, cache / "hagr" / Path(url).name)
            unzip(zpath, cache / "hagr" / name)

    if not args.skip_cdcode:
        zpath = download(CDCODE_RELEASE, cache / "cdcode" / "cdcode_v2.3.zip")
        unzip(zpath, cache / "cdcode" / "v2.3")

    species = {}
    if args.phasepred_human_only:
        species = {"human": PHASEPRED_SPECIES["human"]}
    elif args.phasepred and not args.no_phasepred:
        species = PHASEPRED_SPECIES
    for key, filename in species.items():
        url = PHASEPRED_BASE + filename
        try:
            zpath = download(url, cache / "phasepred" / filename)
            unzip(zpath, cache / "phasepred" / key)
        except subprocess.CalledProcessError as exc:
            print(f"skip {filename}: curl failed ({exc.returncode})", flush=True)

    summary = {
        "hagr": sorted(p.name for p in (cache / "hagr").rglob("*") if p.is_file()),
        "cdcode": sorted(p.name for p in (cache / "cdcode").rglob("*") if p.is_file()),
        "phasepred": sorted(
            str(p.relative_to(cache / "phasepred"))
            for p in (cache / "phasepred").rglob("*")
            if p.is_file()
        ),
    }
    (cache / "download_manifest.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: len(v) for k, v in summary.items()}, indent=2), flush=True)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))
    main()
