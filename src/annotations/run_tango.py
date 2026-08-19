"""Run licensed TANGO on protein sequences (binary is not on GitHub).

TANGO does not read FASTA. It takes a batch text file of at most 1000 sequences:
  Name Cter Nter pH Temp Ionic Sequence
and writes Name.out plus a batch .out with per-sequence averages.

Default executable on Sherlock:
  $SCRATCH/Fetch-Learn/vendor/tango/tango_x86_64_release
"""

from __future__ import annotations

import argparse
import math
import re
import subprocess
import tempfile
from pathlib import Path

import pandas as pd

AA = set("ACDEFGHIKLMNPQRSTVWY")
BATCH_SIZE = 1000  # TANGO hard limit
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


def parse_batch_out(path: Path) -> dict[str, float]:
    """Best-effort parse of TANGO's batch .out (average aggregation per sequence)."""
    scores: dict[str, float] = {}
    if not path.exists():
        return scores
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = re.split(r"[,\s]+", line)
        if len(parts) < 2:
            continue
        name = parts[0]
        nums = []
        for token in parts[1:]:
            try:
                nums.append(float(token))
            except ValueError:
                continue
        if not nums:
            continue
        # Prefer a column literally named aggregation if present; else last number.
        scores[name] = nums[-1]
    return scores


def run_batch(binary: Path, rows: list[tuple[str, str]], tmp: Path, batch_i: int, args) -> dict[str, float]:
    inp = tmp / f"b{batch_i:03d}.txt"
    lines = [
        f"{name} {args.ct} {args.nt} {args.ph} {args.te} {args.io} {seq}"
        for name, seq in rows
    ]
    inp.write_text("\n".join(lines) + "\n")
    # TANGO interactively asks whether to write residue-level files; answer No.
    proc = subprocess.run(
        [str(binary), inp.name],
        cwd=tmp,
        input="N\n",
        capture_output=True,
        text=True,
        check=False,
    )
    log = tmp / f"b{batch_i:03d}.log"
    log.write_text(proc.stdout + "\n" + proc.stderr)
    if proc.returncode != 0:
        raise SystemExit(
            f"TANGO batch {batch_i} exited {proc.returncode}.\n"
            f"stdout/stderr:\n{log.read_text()[-4000:]}\n"
            "Confirm the binary is executable: chmod +x vendor/tango/tango_x86_64_release"
        )
    out_file = tmp / f"b{batch_i:03d}.out"
    scores = parse_batch_out(out_file)
    if not scores:
        # Some builds write next to the binary or use the sequence names as files.
        for path in tmp.glob("*.out"):
            scores.update(parse_batch_out(path))
    return scores


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--tango-bin", required=True)
    parser.add_argument("--sequence-column", default="Protein_sequence")
    parser.add_argument("--id-column", default="VidalID")
    parser.add_argument("--ct", default="N", help="C-terminus: N=free, Y=amidated")
    parser.add_argument("--nt", default="N", help="N-terminus: N=free, A=acetylated, S=succinylated")
    parser.add_argument("--ph", default="7.4")
    parser.add_argument("--te", default="298", help="Temperature in Kelvin")
    parser.add_argument("--io", default="0.05", help="Ionic strength in M")
    args = parser.parse_args()

    binary = Path(args.tango_bin).expanduser().resolve()
    if not binary.exists():
        raise SystemExit(
            f"TANGO executable not found: {binary}\n"
            "Expected $SCRATCH/Fetch-Learn/vendor/tango/tango_x86_64_release"
        )
    if not binary.stat().st_mode & 0o111:
        binary.chmod(binary.stat().st_mode | 0o755)

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

    scores: dict[str, float] = {}
    n_batch = max(1, math.ceil(len(jobs) / BATCH_SIZE))
    print(f"TANGO {len(jobs)} sequences in {n_batch} batches of <={BATCH_SIZE}", flush=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for b in range(n_batch):
            chunk = jobs[b * BATCH_SIZE : (b + 1) * BATCH_SIZE]
            print(f"batch {b + 1}/{n_batch} ({len(chunk)} seqs)", flush=True)
            scores.update(run_batch(binary, [(n, s) for _, n, s in chunk], tmp_path, b, args))

    df["TANGO_aggregation"] = None
    name_by_idx = {idx: name for idx, name, _ in jobs}
    for idx, name in name_by_idx.items():
        if name in scores:
            df.at[idx, "TANGO_aggregation"] = scores[name]
    n_scored = df["TANGO_aggregation"].notna().sum()
    print(f"Parsed TANGO scores for {n_scored}/{len(jobs)} sequences", flush=True)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(output, index=False)
    print(f"Wrote {output}", flush=True)


if __name__ == "__main__":
    main()
