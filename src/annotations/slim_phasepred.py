"""Shrink PhaSePred JSON to protein-level fields (no residue arrays)."""

from __future__ import annotations

import gc
import json
from pathlib import Path


def _num(value):
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_gene(names: object) -> str | None:
    text = str(names or "").strip()
    if not text or text.lower() == "nan":
        return None
    return text.split()[0]


def slim_record(uniprot: str, rec: dict) -> dict:
    phase = rec.get("PhaSePred") or {}
    plaac = rec.get("PLAAC") or {}
    pscore = rec.get("PScore") or {}
    catg = rec.get("catGRANULE") or {}
    espritz = rec.get("ESpritz-DisProt") or {}
    hydro = rec.get("Hydropathy") or {}
    coil = rec.get("DeepCoil") or {}
    seg = rec.get("SEG") or {}
    charged = rec.get("Charged residue") or {}
    phos = rec.get("Phos") or {}
    deep = rec.get("DeepPhase") or {}
    return {
        "uniprot": str(uniprot).split("-")[0].upper(),
        "entry_name": rec.get("Entry name"),
        "gene": _first_gene(rec.get("Gene names")),
        "gene_names": rec.get("Gene names"),
        "organism": rec.get("Organism"),
        "sequence": str(rec.get("Sequence") or "").replace(" ", "").replace("*", "").upper(),
        "SaPS8": _num(phase.get("SaPS-8fea")),
        "PdPS8": _num(phase.get("PdPS-8fea")),
        "SaPS10": _num(phase.get("SaPS-10fea")),
        "PdPS10": _num(phase.get("PdPS-10fea")),
        "SaPS8_rnk": _num(phase.get("SaPS-8fea_rnk")),
        "PdPS8_rnk": _num(phase.get("PdPS-8fea_rnk")),
        "SaPS10_rnk": _num(phase.get("SaPS-10fea_rnk")),
        "PdPS10_rnk": _num(phase.get("PdPS-10fea_rnk")),
        "PLAAC_NLLR": _num(plaac.get("NLLR")),
        "PScore": _num(pscore.get("single")),
        "catGRANULE": _num(catg.get("single")),
        "IDR_fraction": _num(espritz.get("single")),
        "Hydropathy": _num(hydro.get("single")),
        "DeepCoil": _num(coil.get("single")),
        "LCR_fraction": _num(seg.get("single")),
        "FCR": _num(charged.get("FCR")),
        "Phos_rnk": _num(phos.get("rnk")) if isinstance(phos, dict) else None,
        "DeepPhase": _num(deep.get("single")) if isinstance(deep, dict) else None,
    }


def slim_species_dir(species_dir: Path, dest: Path, delete_full_json: bool = True) -> Path:
    json_files = [p for p in species_dir.glob("*.json") if p.is_file()]
    if dest.exists() and dest.stat().st_size > 0:
        print(f"exists slim {dest} ({dest.stat().st_size} bytes)", flush=True)
        return dest
    if not json_files:
        raise FileNotFoundError(f"No PhaSePred JSON in {species_dir}")
    slim: dict[str, dict] = {}
    for path in json_files:
        print(f"slim {path} ({path.stat().st_size} bytes)", flush=True)
        raw = json.loads(path.read_text())
        if not isinstance(raw, dict):
            raise TypeError(f"{path} is not a UniProt-keyed object")
        for uid, rec in raw.items():
            if isinstance(rec, dict):
                slim[str(uid).split("-")[0].upper()] = slim_record(uid, rec)
        del raw
        gc.collect()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(slim, separators=(",", ":")))
    print(f"wrote {dest} ({dest.stat().st_size} bytes, {len(slim)} proteins)", flush=True)
    if delete_full_json:
        for path in json_files:
            path.unlink()
            print(f"deleted bulky {path.name}", flush=True)
    return dest


def slim_all(cache: Path, delete_full_json: bool = True) -> list[Path]:
    root = cache / "phasepred"
    written = []
    if not root.exists():
        return written
    for species_dir in sorted(p for p in root.iterdir() if p.is_dir() and p.name != "slim"):
        dest = root / "slim" / f"{species_dir.name}.json"
        if list(species_dir.glob("*.json")) or dest.exists():
            written.append(slim_species_dir(species_dir, dest, delete_full_json=delete_full_json))
    return written
