"""Sequence-mismatch features that PhaSePred cannot be copied for.

PhosphoSitePlus is experimental and cannot be recomputed from sequence.
DeepCoil and ESpritz need binaries/models on Sherlock; this script only writes
the FASTA of mismatches until those tools are installed under vendor/.
"""

from __future__ import annotations

import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fasta", required=True, help="FASTA written by join_annotations.py")
    parser.add_argument("--deepcoil-dir", default="vendor/deepcoil")
    parser.add_argument("--espritz-dir", default="vendor/espritz")
    args = parser.parse_args()
    fasta = Path(args.fasta)
    if not fasta.exists():
        raise SystemExit(f"No mismatch FASTA at {fasta}")
    n = sum(1 for line in fasta.read_text().splitlines() if line.startswith(">"))
    missing = []
    if not Path(args.deepcoil_dir).exists():
        missing.append(
            "DeepCoil: clone/install into vendor/deepcoil on Sherlock "
            "(pip package deepcoil; needs TensorFlow). Then re-run this script."
        )
    if not Path(args.espritz_dir).exists():
        missing.append(
            "ESpritz: unpack the local DisProt 5% FPR binary into vendor/espritz "
            "(see http://protein.bio.unipd.it/espritz/). Then re-run this script."
        )
    print(f"{n} mismatch sequences in {fasta}")
    if missing:
        raise SystemExit("\n".join(missing))


if __name__ == "__main__":
    main()
