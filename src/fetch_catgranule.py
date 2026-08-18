"""Compute catGRANULE 2.0 sequence-only LLPS scores from amino acid sequences.

Every score is recalculated from the exact protein sequence. This script never
looks up published UniProt or proteome-wide tables.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

STANDARD_AA = set("ACDEFGHIKLMNPQRSTVWY")
PREFERRED_SEQUENCE_COLUMNS = (
    "Protein_sequence",
    "protein_sequence",
    "protein sequence",
    "AA_sequence",
    "amino_acid_sequence",
    "AminoAcidSequence",
    "sequence",
    "Sequence",
    "seq",
    "SEQ",
)
DNA_LIKE_COLUMNS = {"dna_sequence", "DNA_sequence", "nucleotide_sequence", "cds"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add a catGRANULE2 column by scoring each amino acid sequence."
    )
    parser.add_argument("--input", required=True, help="Input Excel file (.xlsx)")
    parser.add_argument("--output", required=True, help="Output Excel file (.xlsx)")
    parser.add_argument(
        "--sequence-column",
        default=None,
        help="Column with amino acid sequences. Default: auto-detect, preferring Protein_sequence.",
    )
    parser.add_argument(
        "--sheet",
        default=0,
        help="Excel sheet name or index. Default: first sheet.",
    )
    parser.add_argument(
        "--catgranule-dir",
        default="vendor/catGRANULE2.0",
        help="Path to a clone of tartaglialabIIT/catGRANULE2.0 (tag v1.0.0).",
    )
    parser.add_argument(
        "--checkpoint",
        default=None,
        help="CSV used to resume after a Sherlock walltime kill. Default: output path with .checkpoint.csv",
    )
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Score only the first N valid sequences (smoke tests).",
    )
    parser.add_argument(
        "--column-name",
        default="catGRANULE2",
        help="Output column header. Default: catGRANULE2",
    )
    return parser.parse_args()


def detect_sequence_column(columns: Iterable[str]) -> str:
    lowered = {str(c).strip().lower(): str(c) for c in columns}
    for name in PREFERRED_SEQUENCE_COLUMNS:
        if name.lower() in lowered:
            candidate = lowered[name.lower()]
            if candidate.lower() in {x.lower() for x in DNA_LIKE_COLUMNS}:
                continue
            return candidate
    raise SystemExit(
        "Could not find an amino acid sequence column. "
        f"Columns were: {list(columns)}. Pass --sequence-column."
    )


def clean_sequence(value: object) -> Optional[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip().upper().replace(" ", "").replace("\n", "")
    text = text.replace("*", "")
    if not text:
        return None
    if not all(letter in STANDARD_AA for letter in text):
        return None
    return text


def load_checkpoint(path: Path) -> dict[int, float]:
    if not path.exists():
        return {}
    frame = pd.read_csv(path)
    scored = {}
    for _, row in frame.iterrows():
        if pd.notna(row.get("catGRANULE2")):
            scored[int(row["row_index"])] = float(row["catGRANULE2"])
    return scored


def save_checkpoint(path: Path, scores: dict[int, float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(
        {"row_index": list(scores.keys()), "catGRANULE2": list(scores.values())}
    ).sort_values("row_index")
    frame.to_csv(path, index=False)


def import_catgranule(catgranule_dir: Path):
    catgranule_dir = catgranule_dir.resolve()
    if not catgranule_dir.exists():
        raise SystemExit(
            f"catGRANULE directory not found: {catgranule_dir}\n"
            "On Sherlock run: bash sherlock/setup_env.sh"
        )
    src_scales = catgranule_dir / "src" / "ChemicalPhysicalScales_Py_dictionary"
    root_scales = catgranule_dir / "ChemicalPhysicalScales_Py_dictionary"
    json_count = len(list(src_scales.glob("*.json"))) if src_scales.exists() else 0
    if root_scales.exists() and (not src_scales.exists() or src_scales.is_symlink() or json_count < 82):
        import shutil

        if src_scales.is_symlink():
            src_scales.unlink()
        elif src_scales.exists():
            shutil.rmtree(src_scales)
        shutil.copytree(root_scales, src_scales)

    os.chdir(catgranule_dir)
    if str(catgranule_dir) not in sys.path:
        sys.path.insert(0, str(catgranule_dir))

    import matplotlib

    matplotlib.use("Agg")
    from catgranuleFunctions import get_physical_chemical_properties, predict
    from compute_profiles_and_predictions import correct_order_columns

    present = {path.stem for path in Path("src/ChemicalPhysicalScales_Py_dictionary").glob("*.json")}
    missing = [name for name in list(correct_order_columns[:82]) if name not in present]
    if missing:
        raise SystemExit(
            "catGRANULE scale files are incomplete (git tag v1.0.0 is missing files). "
            f"Missing {len(missing)}, e.g. {missing[:5]}. "
            "On Sherlock: cd $SCRATCH/Fetch-Learn && git pull && bash sherlock/setup_env.sh"
        )
    print(f"Found {len(present)} scale JSON files.", flush=True)

    return get_physical_chemical_properties, predict, correct_order_columns


def ensure_scale_columns(pc_df, correct_order_columns):
    needed = list(correct_order_columns[:82])
    missing = [name for name in needed if name not in pc_df.columns]
    if missing:
        raise SystemExit(
            "catGRANULE scale files are incomplete. Missing "
            f"{len(missing)} columns, including {missing[:5]}. "
            "On Sherlock run: cd $SCRATCH/Fetch-Learn && git pull && bash sherlock/setup_env.sh"
        )
    return pc_df[needed]


def score_sequences(
    sequences: list[str],
    ids: list[str],
    catgranule_dir: Path,
    get_physical_chemical_properties,
    predict,
    correct_order_columns,
) -> list[float]:
    # Relative paths: catGRANULE's predict() hardcodes ./src/TRAINED_MODELS/
    scales_dir = "./src/ChemicalPhysicalScales_Py_dictionary"
    classifiers_dir = "./src/TRAINED_MODELS/"
    json_files = list(Path(scales_dir).glob("*.json"))
    print(f"Using {len(json_files)} scale JSON files from {Path(scales_dir).resolve()}", flush=True)
    pc_df = get_physical_chemical_properties(sequences, ids, scales_dir)
    pc_df.columns = [Path(str(col)).stem for col in pc_df.columns]
    pc_df = ensure_scale_columns(pc_df, correct_order_columns)
    predictions = predict(pc_df, classifiers_dir, only_pc=True)
    return [float(x) for x in predictions["RandomForest"]]


def main() -> None:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    catgranule_dir = Path(args.catgranule_dir).expanduser()
    if not catgranule_dir.is_absolute():
        catgranule_dir = (Path.cwd() / catgranule_dir).resolve()
    checkpoint_path = (
        Path(args.checkpoint).expanduser().resolve()
        if args.checkpoint
        else output_path.with_suffix(".checkpoint.csv")
    )

    sheet = args.sheet
    try:
        sheet = int(sheet)
    except (TypeError, ValueError):
        pass

    print(f"Reading {input_path}", flush=True)
    df = pd.read_excel(input_path, sheet_name=sheet)
    sequence_column = args.sequence_column or detect_sequence_column(df.columns)
    if sequence_column not in df.columns:
        raise SystemExit(f"Column {sequence_column!r} is not in the Excel file.")
    if sequence_column.lower() in {x.lower() for x in DNA_LIKE_COLUMNS}:
        raise SystemExit(
            f"{sequence_column!r} looks like DNA. Use the amino acid column, e.g. Protein_sequence."
        )
    print(f"Using amino acid column: {sequence_column}", flush=True)
    print(f"Rows: {len(df)}", flush=True)

    (
        get_physical_chemical_properties,
        predict,
        correct_order_columns,
    ) = import_catgranule(catgranule_dir)

    already = load_checkpoint(checkpoint_path)
    work: list[tuple[int, str]] = []
    skipped = 0
    for idx, value in df[sequence_column].items():
        if idx in already:
            continue
        cleaned = clean_sequence(value)
        if cleaned is None:
            skipped += 1
            continue
        work.append((idx, cleaned))
        if args.limit is not None and len(already) + len(work) >= args.limit:
            break

    print(
        f"Already scored: {len(already)}; to score now: {len(work)}; invalid/empty skipped: {skipped}",
        flush=True,
    )

    for start in range(0, len(work), args.batch_size):
        batch = work[start : start + args.batch_size]
        indexes = [item[0] for item in batch]
        sequences = [item[1] for item in batch]
        ids = [f"row_{i}" for i in indexes]
        print(
            f"Scoring batch {start // args.batch_size + 1} "
            f"({len(sequences)} sequences, rows {indexes[0]}-{indexes[-1]})",
            flush=True,
        )
        scores = score_sequences(
            sequences,
            ids,
            catgranule_dir,
            get_physical_chemical_properties,
            predict,
            correct_order_columns,
        )
        for idx, score in zip(indexes, scores):
            already[idx] = score
        save_checkpoint(checkpoint_path, already)

    df[args.column_name] = pd.NA
    for idx, score in already.items():
        if idx in df.index:
            df.at[idx, args.column_name] = score

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(output_path, index=False)
    print(f"Wrote {output_path} with column {args.column_name}", flush=True)


if __name__ == "__main__":
    main()
