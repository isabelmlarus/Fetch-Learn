#!/bin/bash
# Short Sherlock job: score 10 sequences to confirm the environment works.
#   sbatch sherlock/smoke.sbatch
#
#SBATCH --job-name=catGRANULE2-smoke
#SBATCH --partition=normal
#SBATCH --time=00:30:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --output=logs/catGRANULE2-smoke-%j.out
#SBATCH --error=logs/catGRANULE2-smoke-%j.err

set -euo pipefail

REPO_DIR="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
VENV_DIR="${FETCH_LEARN_VENV:-${SCRATCH:-$HOME}/fetch-learn-venv}"
INPUT="${INPUT_XLSX:-${REPO_DIR}/data/inputs/Input_260818.xlsx}"
OUTPUT="${OUTPUT_XLSX:-${REPO_DIR}/data/outputs/Input_260818_catGRANULE2_smoke.xlsx}"

cd "$REPO_DIR"
mkdir -p logs data/outputs

module purge || true
for ver in python/3.9.0 python/3.10.13 python/3.10.6 python/3.9.6 python/3.10 python/3.9; do
  if module load "$ver" 2>/dev/null; then
    break
  fi
done

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"
export PYTHONUNBUFFERED=True
export OMP_NUM_THREADS=1

python -u src/fetch_catgranule.py \
  --input "$INPUT" \
  --output "$OUTPUT" \
  --sequence-column Protein_sequence \
  --catgranule-dir "${REPO_DIR}/vendor/catGRANULE2.0" \
  --batch-size 10 \
  --limit 10
