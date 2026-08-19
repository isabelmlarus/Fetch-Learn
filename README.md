# Fetch-Learn

This repository is for pulling additional ORFeome annotations and learning how to use GitHub.

**Code lives on GitHub. Excel inputs and outputs live on Dropbox. Scoring runs on Stanford Sherlock.**

Dropbox is **not** mounted on Sherlock. You clone the code from GitHub, then **upload** the Excel through Sherlock OnDemand Files.

| Place | What belongs there |
| --- | --- |
| [GitHub](https://github.com/isabelmlarus/Fetch-Learn) | Python scripts, Sherlock job files, this README |
| Dropbox `Fetch-Learn/data/` | `Input_260818.xlsx` and the annotated output Excel |
| Sherlock `$SCRATCH/Fetch-Learn` | A copy of the code plus the Excel, used only to compute |

## GitHub in one page

- **Working copy:** the files on your Mac (this Dropbox folder).
- **Commit:** a snapshot of code you choose to save.
- **Remote (`origin`):** GitHub, at `https://github.com/isabelmlarus/Fetch-Learn`.
- **Push:** send commits from your Mac to GitHub.
- **`.gitignore`:** tells git to skip Dropbox data (`data/inputs`, `data/outputs`, Excel files) so sequences never go to GitHub.

## What the script does

[`src/fetch_catgranule.py`](src/fetch_catgranule.py) reads the Excel, takes the **amino acid** column `Protein_sequence`, and **recomputes** a catGRANULE 2.0 sequence-only Random Forest LLPS score for every row. It writes a **new** Excel with one added column named `catGRANULE2`.

It does **not**:

- look up UniProt IDs
- use `src/catG2_scores_human_proteome.csv.zip` or any published score table
- use DNA (`dna_sequence`) or AlphaFold PDBs

Invalid or empty sequences are left blank in `catGRANULE2`. Trailing `*` stop signs are stripped before scoring. Progress is saved to a checkpoint CSV so a Sherlock time limit can be resumed.

Software: [catGRANULE 2.0](https://github.com/tartaglialabIIT/catGRANULE2.0) / [Zenodo 19691228](https://zenodo.org/records/19691228).

## Run on Sherlock (OnDemand)

Use the **OnDemand website terminal**, not SSH from your Mac. Full copy-paste steps: [`sherlock/ONDEMAND.md`](sherlock/ONDEMAND.md).

Short version:

1. In the OnDemand terminal, clone the GitHub repo into scratch (this is the code; it does not include the Excel):

   ```bash
   cd $SCRATCH
   git clone https://github.com/isabelmlarus/Fetch-Learn.git
   mkdir -p $SCRATCH/Fetch-Learn/data/inputs $SCRATCH/Fetch-Learn/data/outputs
   ```

2. In OnDemand **Files**, upload Dropbox file  
   `Fetch-Learn/data/inputs/Input_260818.xlsx`  
   into Sherlock `$SCRATCH/Fetch-Learn/data/inputs/`.

3. Back in the OnDemand terminal, build the environment on a **dev node** (do not pip-install on the login node):

   ```bash
   cd $SCRATCH/Fetch-Learn
   sh_dev -c 4 -t 1:00:00
   bash sherlock/setup_env.sh
   exit
   ```

4. Submit jobs from the OnDemand terminal (login node is OK for `sbatch`):

   ```bash
   cd $SCRATCH/Fetch-Learn
   sbatch sherlock/smoke.sbatch
   squeue -u $USER
   sbatch sherlock/run_catgranule.sbatch
   ```

5. When the full job finishes, download  
   `$SCRATCH/Fetch-Learn/data/outputs/Input_260818_catGRANULE2.xlsx`  
   with OnDemand **Files** into your Mac Dropbox folder `Fetch-Learn/data/outputs/`.

Setup uses Python **3.9 or 3.10** because the published models need `scikit-learn==1.1.1`.

## Public annotation lookups

[`src/annotations/`](src/annotations/) downloads caches into Dropbox `data/cache/` (gitignored) and joins them onto the Excel. This does **not** need Sherlock unless you later compute DeepCoil, ESpritz, or TANGO.

```bash
# From the Mac Dropbox copy of this repo (needs pandas + curl)
python3 src/annotations/download.py
python3 src/annotations/join_annotations.py \
  --input data/inputs/Input_260818.xlsx \
  --output data/outputs/Input_260818_annotations.xlsx
```

| Source | What is joined | Notes |
| --- | --- | --- |
| Gene4PD | `Gene4PD_tier`, `Gene4PD_known_PD_causing` | Live site blocks downloads; uses Zhao et al. 2021 Table 1 (124 PAGs). |
| HAGR | GenAge human, CellAge, CellAge signatures, LongevityMap; GenAge models via OrthoDB | https://genomics.senescence.info/download.html |
| PhaSePred | SaPS/PdPS 8- and 10-feature models plus PLAAC, PScore, IDR, hydropathy, DeepCoil, LCR, FCR, Phos, DeepPhase | Copied **only** when `Protein_sequence` matches the UniProt canonical sequence. Other species are limited to OrthoDB orthologs. |
| CD-CODE v2.3 | `CDCODE_in_database`, `CDCODE_condensates` | Public dump; human UniProt match plus OrthoDB orthologs in the dump. |
| OrthoDB | Ortholog sheet / `*_orthologs.csv` | Only species that actually appear in PhaSePred or CD-CODE. |

Sequence mismatches are listed in `*_phasepred_mismatches.fasta`. PhosphoSitePlus cannot be recomputed from sequence. DeepCoil and ESpritz for those rows need Sherlock installs later (`src/annotations/compute_missing.py`).

**TANGO** (licensed amyloid predictor): the Sherlock binary should be `vendor/tango/tango_x86_64_release`. `git pull` on Sherlock first, then `sbatch sherlock/run_tango.sbatch`. Do not commit the binary. **Zyggregator** is skipped. **DeepCoil** for sequence mismatches: `bash sherlock/setup_deepcoil.sh` (Python 3.7/3.8 venv) then `sbatch sherlock/run_deepcoil.sbatch`. **ESpritz** is skipped.

## Citation

Monti, Fiorentino, et al. catGRANULE 2.0: accurate predictions of liquid-liquid phase separating proteins at single amino acid resolution. *Genome Biology* (2025).
