# Sherlock OnDemand instructions

Use this if you are already in a **Sherlock OnDemand terminal** in the browser. You do not need SSH from your Mac.

Dropbox is not on Sherlock. GitHub has the **code**. You must **upload** the Excel separately.

Your input file on the Mac:

`/Users/isabellarus/Library/CloudStorage/Dropbox/Fetch-Learn/data/inputs/Input_260818.xlsx`

---

## 1. Clone the code from GitHub

Paste this in the OnDemand terminal:

```bash
cd $SCRATCH
git clone https://github.com/isabelmlarus/Fetch-Learn.git
mkdir -p $SCRATCH/Fetch-Learn/data/inputs $SCRATCH/Fetch-Learn/data/outputs $SCRATCH/Fetch-Learn/logs
ls $SCRATCH/Fetch-Learn
```

You should see `src`, `sherlock`, `README.md`, and `requirements.txt`. You will **not** see the Excel yet. That is expected: Excel is not on GitHub.

If `Fetch-Learn` already exists from an earlier try:

```bash
cd $SCRATCH/Fetch-Learn
git pull
```

---

## 2. Upload the Excel (OnDemand Files, not the terminal)

1. In the OnDemand site, open **Files** (leave the terminal tab open).
2. Click **Go To** (or the path bar) and enter: `$SCRATCH/Fetch-Learn/data/inputs`
3. Click **Upload**.
4. Choose `Input_260818.xlsx` from your Mac Dropbox `Fetch-Learn/data/inputs/` folder.

Check in the terminal:

```bash
ls -lh $SCRATCH/Fetch-Learn/data/inputs/Input_260818.xlsx
```

It should be about 12 MB.

---

## 3. One-time environment setup (dev node)

Do **not** run `pip install` on the OnDemand login terminal. Request a short dev session:

```bash
cd $SCRATCH/Fetch-Learn
sh_dev -c 4 -t 1:00:00
bash sherlock/setup_env.sh
exit
```

`setup_env.sh` clones catGRANULE 2.0 into `vendor/` (on Sherlock only) and creates a Python 3.9/3.10 virtualenv. That can take several minutes.

---

## 4. Smoke test, then the full job

Still in the OnDemand terminal (login node is fine for `sbatch`):

```bash
cd $SCRATCH/Fetch-Learn
sbatch sherlock/smoke.sbatch
squeue -u $USER
```

Watch the smoke log:

```bash
ls -lt logs | head
tail -f logs/catGRANULE2-smoke-*.out
```

If the smoke job wrote `data/outputs/Input_260818_catGRANULE2_smoke.xlsx`, submit everyone:

```bash
cd $SCRATCH/Fetch-Learn
sbatch sherlock/run_catgranule.sbatch
squeue -u $USER
```

The full run is ~15,482 sequences and may take many hours. It checkpoints, so you can resubmit the same `sbatch` if time runs out.

---

## 5. Download the result back to Dropbox

When `squeue -u $USER` no longer shows `catGRANULE2`:

```bash
ls -lh $SCRATCH/Fetch-Learn/data/outputs/Input_260818_catGRANULE2.xlsx
```

In OnDemand **Files**, go to `$SCRATCH/Fetch-Learn/data/outputs/`, download `Input_260818_catGRANULE2.xlsx`, and save it into:

`/Users/isabellarus/Library/CloudStorage/Dropbox/Fetch-Learn/data/outputs/`

That file should have the original columns plus **`catGRANULE2`**.

---

## If the job ran ~1 hour and wrote no Excel (`KeyError` / missing scale columns)

Git tag `v1.0.0` is missing ~29 JSON files (including `charge.json`). Update the code and catGRANULE clone, then resubmit:

```bash
cd $SCRATCH/Fetch-Learn
git pull
sh_dev -c 4 -t 1:00:00
bash sherlock/setup_env.sh
exit
cd $SCRATCH/Fetch-Learn
sbatch sherlock/smoke.sbatch
```

Setup should print `Scale JSON files: 82` (or more). If it is still ~53, stop and paste that line.

## If something fails

- `git clone` asks for a password: the repo is public; use the HTTPS URL above, not SSH.
- `Input_260818.xlsx` missing: the upload step was skipped or went to a different folder. Re-run `ls` in step 2.
- `module load python` fails in setup: paste the `module avail python` output and we will pick a 3.9 or 3.10 module.
- Smoke job in `squeue` with reason `QOSMax...` or `(Priority)`: it is waiting, not dead. Wait and `squeue -u $USER` again.

---

## TANGO (Linux 64-bit binary)

The file name `tango_x86_64_release` is correct. **Do not submit the old sbatch until you `git pull`** — TANGO does not take FASTA; the wrapper now writes TANGO's batch format (max 1000 sequences per file, N-terminus/C-terminus free, pH 7.4, 298 K, ionic 0.05).

OnDemand terminal:

```bash
cd $SCRATCH/Fetch-Learn
git pull
chmod +x vendor/tango/tango_x86_64_release
# smoke test: 3 sequences. Should print scores=3, not scores=0.
export TANGO_LIMIT=3
sbatch sherlock/run_tango.sbatch
# if the smoke Excel has TANGO_aggregation filled, run everyone:
unset TANGO_LIMIT
sbatch sherlock/run_tango.sbatch
```

Output: `$SCRATCH/Fetch-Learn/data/outputs/Input_260818_tango.xlsx` with column `TANGO_aggregation`.

## DeepCoil (sequence mismatches only)

Needs **Python 3.7** (micromamba; Sherlock has no 3.7 module). Use a **16G** dev node so the install is not OOM-killed:

```bash
cd $SCRATCH/Fetch-Learn
git pull
sh_dev -c 4 --mem=16G -t 2:00:00
bash sherlock/setup_deepcoil.sh
exit
# upload data/outputs/Input_260818_annotations.xlsx into $SCRATCH/Fetch-Learn/data/outputs/ if it is not already there
sbatch sherlock/run_deepcoil.sbatch
```

## Gene4PD website downloads

Copy the six `.txt` files into Dropbox:

`Fetch-Learn/data/cache/gene4pd/`

Keep the original names (Rare genes, Rare variants, Associated SNPs, CNVs, Differential expression, Differential DNA methylation). Then re-run `join_annotations.py` on the Mac.

## Annotation join on Sherlock (optional)

Lookups normally run on the Mac. If you instead download caches on Sherlock:

```bash
cd $SCRATCH/Fetch-Learn
git pull
sh_dev -c 4 -t 2:00:00
source $SCRATCH/fetch-learn-venv/bin/activate
python src/annotations/download.py
python src/annotations/join_annotations.py \
  --input data/inputs/Input_260818.xlsx \
  --output data/outputs/Input_260818_annotations.xlsx
exit
```

Or `sbatch sherlock/run_annotations.sbatch` after `download.py` has filled `data/cache/`.
