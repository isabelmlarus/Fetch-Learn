"""Public download URLs for annotation caches (stored under data/cache, not GitHub)."""

from pathlib import Path

HAGR = {
    "genage_human": "https://genomics.senescence.info/genes/human_genes.zip",
    "genage_models": "https://genomics.senescence.info/genes/models_genes.zip",
    "cellage": "https://genomics.senescence.info/cells/cellAge.zip",
    "cellage_signatures": "https://genomics.senescence.info/cells/cellSignatures.zip",
    "longevitymap": "https://genomics.senescence.info/longevity/longevity_genes.zip",
}

# Exact zip names from http://predict.phasep.pro/download/
PHASEPRED_SPECIES = {
    "human": "human_reviewed.zip",
    "mouse": "mouse_reviewed.zip",
    "rat": "rat_reviewed.zip",
    "arabidopsis": "mouse-ear-cress_reviewed.zip",
    "zebrafish": "zebrafish_reviewed.zip",
    "chicken": "chicken_reviewed.zip",
    "bovine": "bovine_reviewed.zip",
    "dicty": "slime-mold_reviewed.zip",
    "dog": "dog_reviewed.zip",
    "pig": "pig_reviewed.zip",
    "subtilis": "bacillus-subtilis_reviewed.zip",
    "elegans": "caenorhabditis-elegans_reviewed.zip",
    "rice": "rice_reviewed.zip",
    "xenopus": "xenopus-laevis_reviewed.zip",
    "fly": "fruit-fly_reviewed.zip",
    "yeast": "yeast_reviewed.zip",
    "ecoli": "Escherichia-coli_reviewed.zip",
    "pombe": "schizosaccharomyces-pombe_reviewed.zip",
}

PHASEPRED_BASE = "http://predict.phasep.pro/static/phasepred/database/"

# Latest public dump linked from https://cd-code.org/release (v2.3, 16 June 2026)
CDCODE_RELEASE = "https://owncloud.mpi-cbg.de/index.php/s/OuBpmU7S8cbXuNb/download"

# NCBI taxonomy IDs for PhaSePred species. Orthologs are limited to these plus
# whatever other species actually appear in the CD-CODE dump.
PHASEPRED_TAXIDS = {
    "human": 9606,
    "mouse": 10090,
    "rat": 10116,
    "arabidopsis": 3702,
    "zebrafish": 7955,
    "chicken": 9031,
    "bovine": 9913,
    "dicty": 44689,
    "dog": 9615,
    "pig": 9823,
    "subtilis": 224308,
    "elegans": 6239,
    "rice": 39947,
    "xenopus": 8355,
    "fly": 7227,
    "yeast": 559292,
    "ecoli": 83333,
    "pombe": 284812,
}

UNIPROT_IDMAPPING_RUN = "https://rest.uniprot.org/idmapping/run"
UNIPROT_IDMAPPING_STATUS = "https://rest.uniprot.org/idmapping/status/{job}"
UNIPROT_IDMAPPING_RESULTS = "https://rest.uniprot.org/idmapping/results/{job}"

USER_AGENT = "Fetch-Learn/1.0 (academic; https://github.com/isabelmlarus/Fetch-Learn)"


def cache_dir(repo_root: Path) -> Path:
    path = repo_root / "data" / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path
