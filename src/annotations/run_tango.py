"""Run licensed TANGO 2.3.1 (tango_x86_64_release).

This binary does **not** take the sequence file as a CLI argument. It prints:

  Type the name of the file with the peptide names, conditions and sequence...
  Do you want a prediction per residue?. If yes type Y. Default, N

and writes ``*_aggregation.txt`` (not ``.out``). Answers are sent on stdin.
Work files are kept under data/outputs/tango_work/ so a failed parse can be inspected.
"""

from __future__ import annotations

import argparse
import math
import re
import shutil
import subprocess
from pathlib import Path

import pandas as pd

AA = set("ACDEFGHIKLMNPQRSTVWY")
BATCH_SIZE = 1000
NAME_MAX = 24


def clean_seq(value: object) -> str | None:
    text = str(value or "").strip().upper().replace(" ", "").replace("*", "")
    if not text or any(ch not in AA for ch in text):
        return None
    return text


def tango_name(raw: object, idx: int) -> str:
    text = re.sub(r"[^A-Za-z0-9_]+", "", str(raw if raw is not None else idx))
    if not text:
        text = f"r{idx}"
    return text[:NAME_MAX]


def parse_aggregation_file(path: Path) -> dict[str, float]:
    """Parse TANGO *_aggregation.txt (summary table or per-residue)."""
    scores: dict[str, float] = {}
    text = path.read_text(errors="replace")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return scores

    residue_re = re.compile(r"^\s*\d+\s*,\s*[A-Z]\s*,")
    residue_vals: list[float] = []
    for line in lines:
        if residue_re.match(line):
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 6:
                try:
                    residue_vals.append(float(parts[5]))
                except ValueError:
                    continue
    if residue_vals:
        key = path.stem.replace("_aggregation", "")
        scores[key] = sum(residue_vals) / len(residue_vals)
        return scores

    agg_idx = None
    saw_header = False
    for line in lines:
        parts = re.split(r"[\t,;]+", line) if ("," in line or "\t" in line) else line.split()
        joined = " ".join(parts).lower()
        if not saw_header and ("aggreg" in joined or "name" in joined):
            saw_header = True
            header = [p.strip().lower() for p in parts]
            for i, col in enumerate(header):
                if "total" in col and "aggreg" in col:
                    agg_idx = i
                elif agg_idx is None and "aggreg" in col and "hel" not in col:
                    agg_idx = i
            continue
        if len(parts) < 2:
            continue
        name = parts[0].strip()
        nums = []
        for token in parts[1:]:
            try:
                nums.append(float(token))
            except ValueError:
                continue
        if not nums:
            continue
        if agg_idx is not None and agg_idx < len(parts):
            try:
                scores[name] = float(parts[agg_idx])
                continue
            except ValueError:
                pass
        scores[name] = nums[-1]
    return scores


def run_batch(
    binary: Path,
    rows: list[tuple[str, str]],
    work: Path,
    batch_i: int,
    args,
) -> dict[str, float]:
    inp = work / f"b{batch_i:03d}.txt"
    lines = [
        f"{name} {args.ct} {args.nt} {args.ph} {args.te} {args.io} {seq}"
        for name, seq in rows
    ]
    inp.write_text("\n".join(lines) + "\n")
    before = {p.name for p in work.iterdir()}

    # Filename first, then residue-level (N), then "no pH/temp scan" (0).
    answers = f"{inp.name}\nN\n0\n"
    proc = subprocess.run(
        [str(binary)],
        cwd=work,
        input=answers,
        capture_output=True,
        text=True,
        check=False,
    )
    log = work / f"b{batch_i:03d}.log"
    log.write_text(proc.stdout + "\n--- stderr ---\n" + proc.stderr)

    created = [p for p in work.iterdir() if p.name not in before]
    scores: dict[str, float] = {}
    for path in created:
        if path.suffix.lower() in {".txt", ".out"} and "aggreg" in path.name.lower():
            scores.update(parse_aggregation_file(path))
        elif path.suffix.lower() == ".out":
            scores.update(parse_aggregation_file(path))

    if not scores:
        for path in work.glob("*aggregation*"):
            scores.update(parse_aggregation_file(path))

    if batch_i == 0 and not scores:
        listing = "\n".join(f"  {p.name} ({p.stat().st_size} bytes)" for p in sorted(work.iterdir()))
        raise SystemExit(
            "TANGO batch 0 produced no aggregation files.\n"
            f"exit={proc.returncode}\n"
            f"work dir {work}:\n{listing}\n\n"
            f"log:\n{log.read_text()[-6000:]}\n"
            "The binary asks for the input filename on stdin; it does not take it as a CLI arg."
        )
    print(
        f"  batch {batch_i}: exit={proc.returncode} new_files={len(created)} scores={len(scores)}",
        flush=True,
    )
    return scores


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--tango-bin", required=True)
    parser.add_argument("--work-dir", default=None)
    parser.add_argument("--sequence-column", default="Protein_sequence")
    parser.add_argument("--id-column", default="VidalID")
    parser.add_argument("--limit", type=int, default=None, help="Score only the first N sequences (smoke test).")
    parser.add_argument("--ct", default="N")
    parser.add_argument("--nt", default="N")
    parser.add_argument("--ph", default="7.4")
    parser.add_argument("--te", default="298")
    parser.add_argument("--io", default="0.05")
    args = parser.parse_args()

    binary = Path(args.tango_bin).expanduser().resolve()
    if not binary.exists():
        raise SystemExit(f"TANGO executable not found: {binary}")
    if not binary.stat().st_mode & 0o111:
        binary.chmod(binary.stat().st_mode | 0o755)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    work = Path(args.work_dir) if args.work_dir else output.parent / "tango_work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    local_bin = work / binary.name
    shutil.copy2(binary, local_bin)
    local_bin.chmod(0o755)

    df = pd.read_excel(args.input)
    jobs: list[tuple[int, str, str]] = []
    used_names: set[str] = set()
    for idx, row in df.iterrows():
        seq = clean_seq(row.get(args.sequence_column))
        if not seq:
            continue
        name = tango_name(row.get(args.id_column, idx), int(idx) if isinstance(idx, int) else 0)
        if name in used_names:
            name = tango_name(f"{name}{idx}", int(idx) if isinstance(idx, int) else 0)
        used_names.add(name)
        jobs.append((idx, name, seq))
        if args.limit is not None and len(jobs) >= args.limit:
            break

    scores: dict[str, float] = {}
    n_batch = max(1, math.ceil(len(jobs) / BATCH_SIZE))
    print(f"TANGO {len(jobs)} sequences in {n_batch} batches; work={work}", flush=True)
    for b in range(n_batch):
        chunk = jobs[b * BATCH_SIZE : (b + 1) * BATCH_SIZE]
        print(f"batch {b + 1}/{n_batch} ({len(chunk)} seqs)", flush=True)
        scores.update(run_batch(local_bin, [(n, s) for _, n, s in chunk], work, b, args))

    df["TANGO_aggregation"] = None
    name_by_idx = {idx: name for idx, name, _ in jobs}
    for idx, name in name_by_idx.items():
        if name in scores:
            df.at[idx, "TANGO_aggregation"] = scores[name]
    n_scored = int(df["TANGO_aggregation"].notna().sum())
    print(f"Parsed TANGO scores for {n_scored}/{len(jobs)} sequences", flush=True)
    if n_scored == 0:
        raise SystemExit(f"No scores parsed. Inspect {work} (logs and *_aggregation.txt).")

    df.to_excel(output, index=False)
    print(f"Wrote {output}", flush=True)


if __name__ == "__main__":
    main()
