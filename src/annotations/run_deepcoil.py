"""Score sequence-mismatch proteins with DeepCoil 2.0 (PhaSePred used SeqVec DeepCoil).

ESpritz is skipped. PhosphoSitePlus cannot be recomputed from sequence.
"""

from __future__ import annotations

import argparse
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
    parser.add_argument("--input", required=True, help="Annotated Excel with PhaSePred_match")
    parser.add_argument("--output", required=True)
    parser.add_argument("--sequence-column", default="Protein_sequence")
    parser.add_argument("--id-column", default="UniprotID")
    parser.add_argument("--only-mismatches", action="store_true", default=True)
    parser.add_argument("--n-cpu", type=int, default=8)
    args = parser.parse_args()

    try:
        from deepcoil import DeepCoil
        from deepcoil.utils import sharpen_preds
    except ImportError as exc:
        raise SystemExit(
            "DeepCoil is not installed in this Python.\n"
            "On Sherlock, use the 3.7/3.8 venv from sherlock/setup_deepcoil.sh "
            f"(not the catGRANULE 3.9 env). Original error: {exc}"
        ) from exc

    df = pd.read_excel(args.input)
    inp = {}
    for idx, row in df.iterrows():
        if args.only_mismatches and str(row.get("PhaSePred_match") or "") != "sequence_mismatch":
            continue
        seq = clean_seq(row.get(args.sequence_column))
        if not seq:
            continue
        ident = f"{row.get(args.id_column, idx)}_{idx}"
        inp[ident] = seq

    print(f"DeepCoil on {len(inp)} sequences", flush=True)
    dc = DeepCoil(use_gpu=False, n_cpu=args.n_cpu)
    results = dc.predict(inp) if inp else {}

    df["DeepCoil_computed"] = None
    df["DeepCoil_max"] = None
    for ident, pred in results.items():
        idx = int(ident.rsplit("_", 1)[-1])
        cc = pred.get("cc") if isinstance(pred, dict) else pred
        if cc is None:
            continue
        vals = list(cc)
        try:
            sharp = sharpen_preds(pred)
            if isinstance(sharp, dict) and sharp.get("cc") is not None:
                vals = list(sharp["cc"])
            elif hasattr(sharp, "__len__"):
                vals = list(sharp)
        except Exception:
            pass
        mx = float(max(vals))
        df.at[idx, "DeepCoil_max"] = mx
        df.at[idx, "DeepCoil_computed"] = mx >= 0.82

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(output, index=False)
    print(f"Wrote {output}", flush=True)


if __name__ == "__main__":
    main()
