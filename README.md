# Fetch-Learn

This repository is for pulling additional ORFeome annotations and learning how to use GitHub.

**Code lives on GitHub. Excel inputs and outputs live on Dropbox. Scoring runs on Stanford Sherlock.**

| Place | What belongs there |
| --- | --- |
| [GitHub](https://github.com/isabelmlarus/Fetch-Learn) | Python scripts, Sherlock job files, this README |
| Dropbox `Fetch-Learn/data/` | `Input_260818.xlsx` and the annotated output Excel |
| Sherlock `$SCRATCH/Fetch-Learn` | A copy of the code plus the Excel, used only to compute |

GitHub is a history of the *code*. Dropbox is the working copy of *data*. Sherlock is the computer that is fast enough for ~15,000 sequences.

## GitHub in one page

- **Working copy:** the files on your Mac (this Dropbox folder).
- **Commit:** a snapshot of code you choose to save.
- **Remote (`origin`):** GitHub, at `https://github.com/isabelmlarus/Fetch-Learn`.
- **Push:** send commits from your Mac to GitHub.
- **`.gitignore`:** tells git to skip Dropbox data (`data/inputs`, `data/outputs`, Excel files) so sequences never go to GitHub.

You do not need Cursor’s GitHub plugin for this. `git` in the terminal is enough.

## What the script does

[`src/fetch_catgranule.py`](src/fetch_catgranule.py) reads the Excel, takes the **amino acid** column `Protein_sequence`, and **recomputes** a catGRANULE 2.0 sequence-only Random Forest LLPS score for every row. It writes a **new** Excel with one added column named `catGRANULE2`.

It does **not**:

- look up UniProt IDs
- use `src/catG2_scores_human_proteome.csv.zip` or any published score table
- use DNA (`dna_sequence`) or AlphaFold PDBs

Invalid or empty sequences are left blank in `catGRANULE2`. Trailing `*` stop signs are stripped before scoring. Progress is saved to a checkpoint CSV so a Sherlock time limit can be resumed.

Software: [catGRANULE 2.0](https://github.com/tartaglialabIIT/catGRANULE2.0) / [Zenodo 19691228](https://zenodo.org/records/19691228).

## Dropbox layout

```
Fetch-Learn/
  src/fetch_catgranule.py      # on GitHub
  sherlock/                    # on GitHub
  data/inputs/Input_260818.xlsx          # Dropbox only
  data/outputs/Input_260818_catGRANULE2.xlsx  # Dropbox only, after the job
```

## Run on Sherlock

Sherlock login is password + Duo, so submit from Terminal.app:

```bash
# on your Mac, from this folder
bash sherlock/sync_to_sherlock.sh
```

Then in the SSH session the script prints:

1. `sh_dev -c 4 -t 1:00:00` and `bash sherlock/setup_env.sh` (once)
2. `sbatch sherlock/smoke.sbatch` (10 sequences)
3. `sbatch sherlock/run_catgranule.sbatch` (all ~15,482 sequences)

Copy the result back to Dropbox:

```bash
scp "$USER@login.sherlock.stanford.edu:\$SCRATCH/Fetch-Learn/data/outputs/Input_260818_catGRANULE2.xlsx" \
  data/outputs/
```

Setup uses Python **3.9 or 3.10** because the published models need `scikit-learn==1.1.1`.

## Citation

Monti, Fiorentino, et al. catGRANULE 2.0: accurate predictions of liquid-liquid phase separating proteins at single amino acid resolution. *Genome Biology* (2025).
