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
INPUT="${INPUT_XLSX:-${REPO_DIR}/data/outputs/Input_260818_annotations.xlsx}"
OUTPUT="${OUTPUT_XLSX:-${REPO_DIR}/data/outputs/Input_260818_deepcoil.xlsx}"

cd "$REPO_DIR"
mkdir -p logs data/outputs
module purge || true
for ver in python/3.8.8 python/3.8.6 python/3.8 python/3.7; do
  if module load "$ver" 2>/dev/null; then
    break
  fi
done
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"
export PYTHONUNBUFFERED=True
python -u src/annotations/run_deepcoil.py \
  --input "$INPUT" \
  --output "$OUTPUT" \
  --n-cpu "${SLURM_CPUS_PER_TASK:-8}"
