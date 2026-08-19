"""Gene4PD Parkinson associations from Zhao et al., Front. Neurosci. 2021 Table 1.

The live Gene4PD website (genemed.tech) returns 403 from automated downloads.
This is the published PAG list with evidence tiers.
"""

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
    "TNR",
    "PODXL",
    "CSMD1",
    "HTRA2",
    "GPRIN3",
    "PPM1K",
    "TARDBP",
    "SLC6A3",
    "ATP10B",
    "PTEN",
    "MMRN1",
    "VAPB",
    "L2HGDH",
    "SPP1",
    "SCN3A",
    "NAP1L5",
    "ITPR1",
    "PZP",
    "UQCRC1",
    "DCTN1",
    "ABCG2",
    "ATOH1",
    "CCSER1",
    "FAM13A",
    "FAM13A-AS1",
    "GRID2",
    "HERC3",
    "HERC5",
    "HERC6",
    "PIGY",
    "PKD2",
    "PYURF",
    "SMARCAD1",
    "TIGD2",
    "ANKRD30A",
    "DIS3",
    "MNS1",
    "PTRHD1",
}

SUGGESTIVE = {
    "RIC3",
    "SLC18A2",
    "COL6A5",
    "ATP1A3",
    "CD36",
    "CP",
    "GRN",
    "PSEN1",
    "SMPD1",
    "FAM83A",
    "KIF21A",
    "PTPRH",
    "COMT",
    "SPG7",
    "MCCC1",
    "PLIN4",
    "TNK2",
    "UCHL1",
    "APOE",
    "OGN",
    "WDR45",
    "TBC1D24",
    "TWNK",
    "BST1",
    "CAPS2",
    "CEL",
    "SVOPL",
    "ATG4C",
    "CABIN1",
    "COL15A1",
    "DARS",
    "DNAH8",
    "ELOA2",
    "FAM71A",
    "FAM90A1",
    "FER1L6",
    "GH2",
    "GPATCH2L",
    "GRAMD1C",
    "IFI35",
    "KALRN",
    "KCNK16",
    "LIPI",
    "LPA",
    "MAP3K6",
    "MS4A5",
    "NUS1",
    "OR8B3",
    "PCDHA9",
    "PRB3",
    "PRMT3",
    "PRSS48",
    "PTCHD3",
    "RFPL2",
    "SCARF2",
    "SPPL2C",
    "TMEM134",
    "UHRF1BP1L",
    "USP20",
    "ZNF516",
    "ZNF543",
}


def lookup(gene_symbol: str) -> dict:
    symbol = str(gene_symbol or "").strip().upper()
    if symbol in HIGH_CONFIDENCE:
        return {
            "Gene4PD_tier": "high_confidence",
            "Gene4PD_known_PD_causing": HIGH_CONFIDENCE[symbol],
        }
    if symbol in STRONG:
        return {"Gene4PD_tier": "strong", "Gene4PD_known_PD_causing": symbol == "HTRA2"}
    if symbol in SUGGESTIVE:
        return {
            "Gene4PD_tier": "suggestive",
            "Gene4PD_known_PD_causing": symbol == "UCHL1",
        }
    return {"Gene4PD_tier": pd_na(), "Gene4PD_known_PD_causing": pd_na()}


def pd_na():
    return None
