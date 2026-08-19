#!/bin/bash
#SBATCH --job-name=annot-join
#SBATCH --partition=normal
#SBATCH --time=06:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --output=logs/annot-join-%j.out
#SBATCH --error=logs/annot-join-%j.err

# Optional: run the Dropbox join on Sherlock if the Mac is short on RAM.
# Upload data/cache (or re-run src/annotations/download.py) first.

set -euo pipefail
REPO_DIR="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
VENV_DIR="${FETCH_LEARN_VENV:-${SCRATCH:-$HOME}/fetch-learn-venv}"
INPUT="${INPUT_XLSX:-${REPO_DIR}/data/inputs/Input_260818.xlsx}"
OUTPUT="${OUTPUT_XLSX:-${REPO_DIR}/data/outputs/Input_260818_annotations.xlsx}"

cd "$REPO_DIR"
mkdir -p logs data/outputs data/cache
module purge || true
for ver in python/3.9.0 python/3.10.13 python/3.10 python/3.9; do
  if module load "$ver" 2>/dev/null; then
    break
  fi
done
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"
export PYTHONUNBUFFERED=True
python -u src/annotations/join_annotations.py --input "$INPUT" --output "$OUTPUT"
