#!/bin/bash
#SBATCH --job-name=deepcoil
#SBATCH --partition=normal
#SBATCH --time=36:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --mail-type=END,FAIL
#SBATCH --output=logs/deepcoil-%j.out
#SBATCH --error=logs/deepcoil-%j.err

# Unattended: install DeepCoil if needed, then score sequence mismatches.
# Submit from the login node (no sh_dev): sbatch sherlock/run_deepcoil.sbatch

set -euo pipefail
REPO_DIR="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
VENV_DIR="${DEEPCOIL_VENV:-${SCRATCH:-$HOME}/fetch-learn-deepcoil-venv}"
PY="${VENV_DIR}/bin/python"
INPUT="${INPUT_XLSX:-${REPO_DIR}/data/outputs/Input_260818_annotations.xlsx}"
OUTPUT="${OUTPUT_XLSX:-${REPO_DIR}/data/outputs/Input_260818_deepcoil.xlsx}"

cd "$REPO_DIR"
mkdir -p logs data/outputs

if [[ ! -f "$INPUT" ]]; then
  echo "Missing input Excel: $INPUT" >&2
  echo "Upload Dropbox data/outputs/Input_260818_annotations.xlsx to that path first." >&2
  exit 1
fi

need_setup=1
if [[ -x "$PY" ]] && "$PY" -c 'from deepcoil import DeepCoil' 2>/dev/null; then
  need_setup=0
fi
if [[ "$need_setup" -eq 1 ]]; then
  echo "DeepCoil not installed yet; running setup on this compute node."
  bash sherlock/setup_deepcoil.sh
fi

if [[ ! -x "$PY" ]]; then
  echo "DeepCoil python missing at ${PY} after setup." >&2
  exit 1
fi

export PYTHONUNBUFFERED=True
"$PY" -u src/annotations/run_deepcoil.py \
  --input "$INPUT" \
  --output "$OUTPUT" \
  --n-cpu "${SLURM_CPUS_PER_TASK:-8}"
