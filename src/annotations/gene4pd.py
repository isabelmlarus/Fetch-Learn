"""Gene4PD Parkinson associations.

Primary evidence layers come from the Gene4PD website downloads (rare genes,
rare variants, GWAS SNPs, CNVs, DE genes, methylation). Drop those .txt files
into data/cache/gene4pd/. The published 124-PAG Table 1 is kept as Gene4PD_PAG_tier.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

# High confidence (score >= 20). '#' in the paper = known PD-causing gene.
HIGH_CONFIDENCE = {
    "PRKN": True,
    "PINK1": True,
    "LRRK2": True,
    "SNCA": True,
    "GBA": True,
    "PARK7": True,
    "GCH1": False,
    "PLA2G6": True,
    "ATP13A2": True,
    "VPS35": True,
    "DNAJC13": True,
    "FBXO7": True,
    "POLG": True,
    "TMEM230": True,
    "SYNJ1": True,
    "GIGYF2": True,
    "VPS13C": True,
    "LRP10": True,
    "RAB39B": False,
    "CHCHD2": False,
    "MAPT": False,
    "TH": False,
    "EIF4G1": True,
    "ASNA1": False,
    "DNAJC6": True,
}

STRONG = {
    "TNR", "PODXL", "CSMD1", "HTRA2", "GPRIN3", "PPM1K", "TARDBP", "SLC6A3",
    "ATP10B", "PTEN", "MMRN1", "VAPB", "L2HGDH", "SPP1", "SCN3A", "NAP1L5",
    "ITPR1", "PZP", "UQCRC1", "DCTN1", "ABCG2", "ATOH1", "CCSER1", "FAM13A",
    "FAM13A-AS1", "GRID2", "HERC3", "HERC5", "HERC6", "PIGY", "PKD2", "PYURF",
    "SMARCAD1", "TIGD2", "ANKRD30A", "DIS3", "MNS1", "PTRHD1",
}

SUGGESTIVE = {
    "RIC3", "SLC18A2", "COL6A5", "ATP1A3", "CD36", "CP", "GRN", "PSEN1",
    "SMPD1", "FAM83A", "KIF21A", "PTPRH", "COMT", "SPG7", "MCCC1", "PLIN4",
    "TNK2", "UCHL1", "APOE", "OGN", "WDR45", "TBC1D24", "TWNK", "BST1",
    "CAPS2", "CEL", "SVOPL", "ATG4C", "CABIN1", "COL15A1", "DARS", "DNAH8",
    "ELOA2", "FAM71A", "FAM90A1", "FER1L6", "GH2", "GPATCH2L", "GRAMD1C",
    "IFI35", "KALRN", "KCNK16", "LIPI", "LPA", "MAP3K6", "MS4A5", "NUS1",
    "OR8B3", "PCDHA9", "PRB3", "PRMT3", "PRSS48", "PTCHD3", "RFPL2",
    "SCARF2", "SPPL2C", "TMEM134", "UHRF1BP1L", "USP20", "ZNF516", "ZNF543",
}

LAYERS = {
    "Gene4PD_rare_gene": ("rare gene", "rare_gene", "raregenes"),
    "Gene4PD_rare_variant": ("rare variant", "rare_variant", "rarevariants"),
    "Gene4PD_GWAS_SNP": ("snp", "gwas"),
    "Gene4PD_CNV": ("cnv", "copy"),
    "Gene4PD_methylation": ("methyl", "dmg"),
    "Gene4PD_DE": ("expression", "deg", "transcript"),
}


def pag_lookup(gene_symbol: str) -> dict:
    symbol = str(gene_symbol or "").strip().upper()
    if symbol in HIGH_CONFIDENCE:
        return {
            "Gene4PD_PAG_tier": "high_confidence",
            "Gene4PD_known_PD_causing": HIGH_CONFIDENCE[symbol],
        }
    if symbol in STRONG:
        return {"Gene4PD_PAG_tier": "strong", "Gene4PD_known_PD_causing": symbol == "HTRA2"}
    if symbol in SUGGESTIVE:
        return {
            "Gene4PD_PAG_tier": "suggestive",
            "Gene4PD_known_PD_causing": symbol == "UCHL1",
        }
    return {"Gene4PD_PAG_tier": None, "Gene4PD_known_PD_causing": None}


def _read_table(path: Path) -> pd.DataFrame:
    for sep in ["\t", ",", ";", "|"]:
        try:
            frame = pd.read_csv(path, sep=sep)
        except Exception:  # noqa: BLE001
            continue
        if frame.shape[1] > 1:
            return frame
    return pd.read_csv(path, sep="\t", engine="python")


def _symbols_from_table(frame: pd.DataFrame) -> set[str]:
    lowered = {str(c).strip().lower(): c for c in frame.columns}
    for key in (
        "gene symbol", "genesymbol", "gene", "symbol", "hgnc", "gene_name",
        "genename", "gene.symbol",
    ):
        if key in lowered:
            col = lowered[key]
            return {
                str(v).strip().upper()
                for v in frame[col].dropna()
                if str(v).strip() and str(v).strip().upper() not in {"NAN", "NONE", "GENE"}
            }
    # Fall back to the first column if it looks like gene IDs.
    first = frame.columns[0]
    return {
        str(v).strip().upper()
        for v in frame[first].dropna()
        if str(v).strip() and " " not in str(v).strip() and str(v).strip().upper() not in {"NAN"}
    }


def load_download_layers(cache: Path) -> dict[str, set[str]]:
    folder = cache / "gene4pd"
    layers = {name: set() for name in LAYERS}
    if not folder.exists():
        print("No data/cache/gene4pd/ yet; Gene4PD download layers will be empty.", flush=True)
        return layers
    files = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in {".txt", ".tsv", ".csv"}]
    if not files:
        print(f"{folder} has no .txt/.tsv/.csv files.", flush=True)
        return layers
    for path in files:
        hay = path.name.lower().replace("-", " ").replace("_", " ")
        assigned = None
        for col, needles in LAYERS.items():
            if any(n in hay for n in needles):
                assigned = col
                break
        if assigned is None:
            print(f"skip unrecognized Gene4PD file {path.name}", flush=True)
            continue
        try:
            table = _read_table(path)
            symbols = _symbols_from_table(table)
        except Exception as exc:  # noqa: BLE001
            print(f"skip {path.name}: {exc}", flush=True)
            continue
        layers[assigned] |= symbols
        print(f"Gene4PD {assigned}: {len(symbols)} symbols from {path.name}", flush=True)
    return layers


def annotate(symbols: pd.Series, cache: Path) -> pd.DataFrame:
    layers = load_download_layers(cache)
    rows = []
    for symbol in symbols:
        row = pag_lookup(symbol)
        key = str(symbol or "").strip().upper()
        for col, genes in layers.items():
            row[col] = key in genes
        rows.append(row)
    return pd.DataFrame(rows, index=symbols.index)
