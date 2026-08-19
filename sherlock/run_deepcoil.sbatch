#!/bin/bash
#SBATCH --job-name=deepcoil
#SBATCH --partition=normal
#SBATCH --time=24:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --output=logs/deepcoil-%j.out
#SBATCH --error=logs/deepcoil-%j.err

set -euo pipefail
REPO_DIR="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
VENV_DIR="${DEEPCOIL_VENV:-${SCRATCH:-$HOME}/fetch-learn-deepcoil-venv}"
PY="${VENV_DIR}/bin/python"
INPUT="${INPUT_XLSX:-${REPO_DIR}/data/outputs/Input_260818_annotations.xlsx}"
OUTPUT="${OUTPUT_XLSX:-${REPO_DIR}/data/outputs/Input_260818_deepcoil.xlsx}"

cd "$REPO_DIR"
mkdir -p logs data/outputs
if [[ ! -x "$PY" ]]; then
  echo "DeepCoil python missing at ${PY}." >&2
  echo "On a compute node run: bash sherlock/setup_deepcoil.sh" >&2
  exit 1
fi
export PYTHONUNBUFFERED=True
"$PY" -u src/annotations/run_deepcoil.py \
  --input "$INPUT" \
  --output "$OUTPUT" \
  --n-cpu "${SLURM_CPUS_PER_TASK:-8}"
