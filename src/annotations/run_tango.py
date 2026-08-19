"""Run TANGO (licensed binary, not on GitHub) on protein sequences.

Put the Linux 64-bit TANGO folder on Sherlock at:
  $SCRATCH/Fetch-Learn/vendor/tango/
and point --tango-bin at the executable inside it.
"""

from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path

import pandas as pd

AA = set("ACDEFGHIKLMNPQRSTVWY")


def clean_seq(value: object) -> str | None:
    text = str(value or "").strip().upper().replace(" ", "").replace("*", "")
    if not text or any(ch not in AA for ch in text):
        return None
    return text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--tango-bin", required=True, help="Path to the TANGO executable")
    parser.add_argument("--sequence-column", default="Protein_sequence")
    parser.add_argument("--id-column", default="VidalID")
    args = parser.parse_args()

    binary = Path(args.tango_bin).expanduser().resolve()
    if not binary.exists():
        raise SystemExit(
            f"TANGO executable not found: {binary}\n"
            "Download Linux 64-bit from your academic license page and upload it to "
            "$SCRATCH/Fetch-Learn/vendor/tango/ via OnDemand Files. Do not commit it to GitHub."
        )

    df = pd.read_excel(args.input)
    with tempfile.TemporaryDirectory() as tmp:
        fasta = Path(tmp) / "seq.fasta"
        lines = []
        keep = []
        for idx, row in df.iterrows():
            seq = clean_seq(row[args.sequence_column])
            if not seq:
                continue
            ident = str(row.get(args.id_column, idx)).replace(" ", "_")
            lines.append(f">{ident}\n{seq}\n")
            keep.append(idx)
        fasta.write_text("".join(lines))
        # TANGO CLI flags vary by build; this follows the common FASTA batch form.
        proc = subprocess.run(
            [str(binary), str(fasta)],
            cwd=tmp,
            capture_output=True,
            text=True,
            check=False,
        )
        log = Path(args.output).with_suffix(".tango.log")
        log.write_text(proc.stdout + "\n" + proc.stderr)
        if proc.returncode != 0:
            raise SystemExit(
                f"TANGO exited {proc.returncode}. See {log} and adjust --tango-bin / flags "
                "after you inspect the Linux 64-bit README in vendor/tango."
            )
        print(proc.stdout)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    print(f"TANGO finished. Raw log: {log}")


if __name__ == "__main__":
    main()
