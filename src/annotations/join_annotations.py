"""Join public annotations onto the ORFeome Excel.

Lookups only (no TANGO / Zyggregator / DeepCoil / ESpritz compute). PhaSePred
scores are copied only when the Excel protein sequence matches the UniProt
canonical sequence in PhaSePred. Orthologs are other-species PhaSePred and
CD-CODE proteins that share an OrthoDB group with a query UniProt, limited to
species those databases actually annotate.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

from gene4pd import lookup as gene4pd_lookup
from orthodb import map_entrez_to_uniprot, map_uniprot_to_orthodb
from slim_phasepred import slim_all
from urls import cache_dir

AA = set("ACDEFGHIKLMNPQRSTVWY")
REPO_ROOT = Path(__file__).resolve().parents[2]
PHASEPRED_PREFIX = "PhaSePred_"


def clean_seq(value: object) -> str:
    text = str(value or "").strip().upper().replace(" ", "").replace("*", "")
    return "".join(ch for ch in text if ch in AA)


def first_existing(frame: pd.DataFrame, names: list[str]) -> str | None:
    lowered = {str(c).strip().lower(): c for c in frame.columns}
    for name in names:
        if name.lower() in lowered:
            return lowered[name.lower()]
    return None


def load_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if path.suffix.lower() == ".tsv":
        return pd.read_csv(path, sep="\t")
    # CellAge signatures is semicolon-separated despite a .csv suffix.
    sample = path.read_text(errors="replace")[:400]
    if sample.count(";") > sample.count(",") and sample.count(";") > sample.count("\t"):
        return pd.read_csv(path, sep=";")
    return pd.read_csv(path)


def collect_files(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return [
        p
        for p in folder.rglob("*")
        if p.is_file()
        and p.suffix.lower() in {".txt", ".tsv", ".csv", ".tab"}
        and "release" not in p.name.lower()
    ]


def split_symbols(value: object) -> set[str]:
    text = str(value or "").replace("|", ",").replace(";", ",").replace("/", ",")
    out = set()
    for part in text.split(","):
        token = part.strip().upper()
        if token and token not in {"NAN", "NONE", "NA"}:
            out.add(token)
    return out


def annotate_gene4pd(symbols: pd.Series) -> pd.DataFrame:
    return pd.DataFrame([gene4pd_lookup(v) for v in symbols], index=symbols.index)


def annotate_hagr(df: pd.DataFrame, symbol_col: str, uid_col: str, cache: Path) -> pd.DataFrame:
    human_sym: set[str] = set()
    human_up: set[str] = set()
    cellage: set[str] = set()
    signatures: set[str] = set()
    longevity: set[str] = set()
    model_entrez: list[str] = []

    for path in collect_files(cache / "hagr" / "genage_human"):
        table = load_table(path)
        if "symbol" in table.columns:
            human_sym |= {s for v in table["symbol"] for s in split_symbols(v)}
        if "uniprot" in table.columns:
            human_up |= {str(v).strip().upper() for v in table["uniprot"].dropna()}

    for path in collect_files(cache / "hagr" / "genage_models"):
        table = load_table(path)
        col = first_existing(table, ["entrez gene id", "entrez"])
        if col:
            model_entrez.extend(str(int(v)) if isinstance(v, float) and v == int(v) else str(v) for v in table[col].dropna())

    for path in collect_files(cache / "hagr" / "cellage"):
        table = load_table(path)
        col = first_existing(table, ["Gene symbol", "gene_symbol", "symbol"])
        if col:
            cellage |= {s for v in table[col] for s in split_symbols(v)}

    for path in collect_files(cache / "hagr" / "cellage_signatures"):
        table = load_table(path)
        col = first_existing(table, ["gene_symbol", "symbol"])
        if col:
            signatures |= {s for v in table[col] for s in split_symbols(v)}

    for path in collect_files(cache / "hagr" / "longevitymap"):
        table = load_table(path)
        col = first_existing(table, ["Gene(s)", "gene", "genes", "symbol"])
        if col:
            longevity |= {s for v in table[col] for s in split_symbols(v)}

    symbols = df[symbol_col].astype(str).str.strip().str.upper()
    entry_names = df[uid_col].astype(str).str.strip().str.upper()
    out = pd.DataFrame(index=df.index)
    out["HAGR_GenAge_human"] = symbols.isin(human_sym) | entry_names.isin(human_up)
    out["HAGR_CellAge"] = symbols.isin(cellage)
    out["HAGR_CellAge_signature"] = symbols.isin(signatures)
    out["HAGR_LongevityMap"] = symbols.isin(longevity)

    model_ogs: set[str] = set()
    if model_entrez:
        entrez_to_up = map_entrez_to_uniprot(model_entrez, cache / "orthodb" / "entrez_to_uniprot.json")
        model_uniprot = list(entrez_to_up.values())
        up_to_og = map_uniprot_to_orthodb(model_uniprot, cache / "orthodb" / "uniprot_to_orthodb.json")
        model_ogs = {up_to_og[u] for u in model_uniprot if u in up_to_og}
        query_ogs = map_uniprot_to_orthodb(
            df[uid_col].astype(str).tolist(), cache / "orthodb" / "uniprot_to_orthodb.json"
        )
        out["HAGR_GenAge_models_ortholog"] = [
            query_ogs.get(str(u).split("-")[0].strip().upper()) in model_ogs for u in df[uid_col]
        ]
    else:
        out["HAGR_GenAge_models_ortholog"] = False
    return out


def load_phasepred_slim(cache: Path) -> dict[str, dict[str, dict]]:
    slim_all(cache, delete_full_json=True)
    by_species: dict[str, dict[str, dict]] = {}
    slim_dir = cache / "phasepred" / "slim"
    if not slim_dir.exists():
        return by_species
    for path in sorted(slim_dir.glob("*.json")):
        by_species[path.stem] = json.loads(path.read_text())
        print(f"loaded PhaSePred {path.stem}: {len(by_species[path.stem])} proteins", flush=True)
    return by_species


def phasepred_columns(rec: dict | None, match: str) -> dict:
    keys = [
        "SaPS8",
        "PdPS8",
        "SaPS10",
        "PdPS10",
        "SaPS8_rnk",
        "PdPS8_rnk",
        "SaPS10_rnk",
        "PdPS10_rnk",
        "PLAAC_NLLR",
        "PScore",
        "catGRANULE",
        "IDR_fraction",
        "Hydropathy",
        "DeepCoil",
        "LCR_fraction",
        "FCR",
        "Phos_rnk",
        "DeepPhase",
    ]
    out = {PHASEPRED_PREFIX + "match": match}
    use = rec if rec and match == "canonical" else None
    for key in keys:
        out[PHASEPRED_PREFIX + key] = None if use is None else use.get(key)
    out["PhaSePred_needs_DeepCoil"] = match == "sequence_mismatch"
    out["PhaSePred_needs_ESpritz"] = match == "sequence_mismatch"
    out["PhaSePred_PhosphoSitePlus"] = (
        "lookup_only_canonical" if match == "canonical" else "not_computable_from_sequence"
    )
    return out


def annotate_phasepred(uniprot: pd.Series, sequences: pd.Series, human: dict[str, dict]) -> pd.DataFrame:
    rows = []
    for uid, seq in zip(uniprot, sequences):
        key = str(uid or "").split("-")[0].strip().upper()
        rec = human.get(key)
        if rec is None:
            rows.append(phasepred_columns(None, "not_found"))
            continue
        excel_seq = clean_seq(seq)
        db_seq = str(rec.get("sequence") or "")
        match = "canonical" if excel_seq and db_seq and excel_seq == db_seq else "sequence_mismatch"
        rows.append(phasepred_columns(rec, match))
    return pd.DataFrame(rows, index=uniprot.index)


def load_cdcode(cache: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    folder = cache / "cdcode" / "v2.3"
    proteins = pd.read_csv(folder / "protein_202606151649.csv")
    relations = pd.read_csv(folder / "protein2cdcode_v2.3.tsv", sep="\t")
    return proteins, relations


def annotate_cdcode(uniprot: pd.Series, relations: pd.DataFrame) -> pd.DataFrame:
    by_uid: dict[str, set[str]] = defaultdict(set)
    for uid, name in zip(relations["uniprotkb_ac"], relations["condensate_name"]):
        key = str(uid).split("-")[0].strip().upper()
        if key and key not in {"NAN", "NONE"}:
            by_uid[key].add(str(name).strip())
    rows = []
    for uid in uniprot:
        key = str(uid or "").split("-")[0].strip().upper()
        names = {n for n in by_uid.get(key, set()) if n and n.lower() != "nan"}
        rows.append(
            {
                "CDCODE_in_database": bool(names),
                "CDCODE_condensates": "; ".join(sorted(names)) if names else None,
            }
        )
    return pd.DataFrame(rows, index=uniprot.index)


def build_orthologs(
    df: pd.DataFrame,
    uid_col: str,
    symbol_col: str,
    phasepred: dict[str, dict[str, dict]],
    cd_proteins: pd.DataFrame,
    cd_relations: pd.DataFrame,
    cache: Path,
) -> pd.DataFrame:
    query_ids = [str(u).split("-")[0].strip().upper() for u in df[uid_col]]
    phase_ids = [uid for species, recs in phasepred.items() if species != "human" for uid in recs]
    cd_ids = [
        str(u).split("-")[0].strip().upper()
        for u, tax in zip(cd_proteins["uniprot_id"], cd_proteins["species_taxon_id"])
        if str(tax) != "9606"
    ]
    og_map = map_uniprot_to_orthodb(query_ids + phase_ids + cd_ids, cache / "orthodb" / "uniprot_to_orthodb.json")

    query_by_og: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for uid, gene in zip(df[uid_col], df[symbol_col]):
        key = str(uid).split("-")[0].strip().upper()
        og = og_map.get(key)
        if og:
            query_by_og[og].append((key, str(gene)))

    cd_by_uid = {
        str(row["uniprot_id"]).split("-")[0].strip().upper(): row
        for _, row in cd_proteins.drop_duplicates("uniprot_id").iterrows()
    }
    cd_names: dict[str, set[str]] = defaultdict(set)
    for uid, name in zip(cd_relations["uniprotkb_ac"], cd_relations["condensate_name"]):
        cd_names[str(uid).split("-")[0].strip().upper()].add(str(name).strip())

    rows = []
    for species, recs in phasepred.items():
        if species == "human":
            continue
        for uid, rec in recs.items():
            og = og_map.get(uid)
            if not og or og not in query_by_og:
                continue
            o_gene = rec.get("gene")
            for q_uid, q_gene in query_by_og[og]:
                if q_uid == uid:
                    continue
                rows.append(
                    {
                        "query_uniprot": q_uid,
                        "query_gene": q_gene,
                        "orthodb_group": og,
                        "ortholog_uniprot": uid,
                        "ortholog_gene": o_gene,
                        "ortholog_organism": rec.get("organism"),
                        "ortholog_source": f"PhaSePred:{species}",
                        "symbol_match": bool(o_gene) and str(o_gene).upper() == str(q_gene).upper(),
                        "CDCODE_condensates": None,
                        **{PHASEPRED_PREFIX + k: rec.get(k) for k in (
                            "SaPS8", "PdPS8", "SaPS10", "PdPS10", "PLAAC_NLLR",
                            "PScore", "catGRANULE", "IDR_fraction", "Hydropathy",
                            "DeepCoil", "LCR_fraction", "FCR",
                        )},
                    }
                )

    for uid, rec in cd_by_uid.items():
        tax = rec.get("species_taxon_id")
        if str(tax) == "9606":
            continue
        og = og_map.get(uid)
        if not og or og not in query_by_og:
            continue
        condensates = "; ".join(sorted(n for n in cd_names.get(uid, set()) if n and n.lower() != "nan"))
        o_gene = rec.get("gene_name")
        for q_uid, q_gene in query_by_og[og]:
            if q_uid == uid:
                continue
            rows.append(
                {
                    "query_uniprot": q_uid,
                    "query_gene": q_gene,
                    "orthodb_group": og,
                    "ortholog_uniprot": uid,
                    "ortholog_gene": o_gene,
                    "ortholog_organism": rec.get("species_name"),
                    "ortholog_source": "CD-CODE",
                    "symbol_match": bool(o_gene) and str(o_gene).upper() == str(q_gene).upper(),
                    "CDCODE_condensates": condensates or None,
                }
            )
    if not rows:
        return pd.DataFrame(rows)
    # UniProt's OrthoDB xref is the broad Eukaryota group and can include paralogs.
    # Prefer same gene symbol; cap the rest so the Excel sheet stays usable.
    frame = pd.DataFrame(rows)
    frame["symbol_match"] = frame["symbol_match"].astype(bool)
    frame = frame.sort_values(
        ["query_uniprot", "ortholog_source", "symbol_match"],
        ascending=[True, True, False],
    )
    frame = frame.groupby(["query_uniprot", "ortholog_source"], sort=False, group_keys=False).head(25)
    return frame.reset_index(drop=True)


def write_mismatch_fasta(df: pd.DataFrame, uid_col: str, seq_col: str, match_col: str, dest: Path) -> int:
    lines = []
    n = 0
    for _, row in df.iterrows():
        if row.get(match_col) != "sequence_mismatch":
            continue
        seq = clean_seq(row[seq_col])
        if not seq:
            continue
        ident = str(row[uid_col]).split("-")[0]
        lines.append(f">{ident}\n{seq}\n")
        n += 1
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("".join(lines))
    return n


def main() -> None:
    parser = argparse.ArgumentParser(description="Join public annotations onto the input Excel.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()

    cache = cache_dir(args.repo_root)
    df = pd.read_excel(args.input)
    symbol_col = first_existing(df, ["GeneSymbol", "gene_symbol", "gene"])
    uid_col = first_existing(df, ["UniprotID", "UniProtID", "uniprot"])
    seq_col = first_existing(df, ["Protein_sequence", "sequence"])
    if not symbol_col or not uid_col or not seq_col:
        raise SystemExit(f"Need gene, UniProt, and protein sequence columns. Have: {list(df.columns)}")

    print(f"Rows {len(df)}; gene={symbol_col} uniprot={uid_col} seq={seq_col}", flush=True)
    phasepred = load_phasepred_slim(cache)
    human = phasepred.get("human") or {}
    cd_proteins, cd_relations = load_cdcode(cache)

    parts = [
        annotate_gene4pd(df[symbol_col]),
        annotate_hagr(df, symbol_col, uid_col, cache),
        annotate_phasepred(df[uid_col], df[seq_col], human),
        annotate_cdcode(df[uid_col], cd_relations),
    ]
    out = pd.concat([df] + parts, axis=1)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fasta_path = output.with_name(output.stem + "_phasepred_mismatches.fasta")
    n_mismatch = write_mismatch_fasta(out, uid_col, seq_col, "PhaSePred_match", fasta_path)
    print(f"Sequence mismatches needing DeepCoil/ESpritz: {n_mismatch} -> {fasta_path}", flush=True)

    orth = build_orthologs(df, uid_col, symbol_col, phasepred, cd_proteins, cd_relations, cache)
    orth_csv = output.with_name(output.stem + "_orthologs.csv")
    symbol_csv = output.with_name(output.stem + "_orthologs_symbol_match.csv")
    symbol_orth = pd.DataFrame()
    if not orth.empty:
        orth.to_csv(orth_csv, index=False)
        symbol_orth = orth[orth["symbol_match"] == True]
        if not symbol_orth.empty:
            symbol_orth.to_csv(symbol_csv, index=False)
        counts = orth.groupby(["query_uniprot", "ortholog_source"]).size().unstack(fill_value=0)
        counts = counts.add_prefix("n_orthologs_")
        out["_uid"] = out[uid_col].astype(str).str.split("-").str[0].str.strip().str.upper()
        out = out.merge(counts, how="left", left_on="_uid", right_index=True)
        out = out.drop(columns=["_uid"])

    with pd.ExcelWriter(output) as writer:
        out.to_excel(writer, sheet_name="human", index=False)
        if not symbol_orth.empty and len(symbol_orth) <= 250_000:
            symbol_orth.to_excel(writer, sheet_name="orthologs_symbol_match", index=False)
    print(
        f"Wrote {output} (human {len(out)} rows, orthologs {len(orth)} rows, "
        f"symbol-match {len(symbol_orth)} rows)",
        flush=True,
    )


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))
    main()
