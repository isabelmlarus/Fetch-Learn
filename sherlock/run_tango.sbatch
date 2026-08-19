#!/bin/bash
#SBATCH --job-name=tango
#SBATCH --partition=normal
#SBATCH --time=48:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=16G
#SBATCH --output=logs/tango-%j.out
#SBATCH --error=logs/tango-%j.err

set -euo pipefail
REPO_DIR="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
VENV_DIR="${FETCH_LEARN_VENV:-${SCRATCH:-$HOME}/fetch-learn-venv}"
TANGO_BIN="${TANGO_BIN:-${REPO_DIR}/vendor/tango/tango_x86_64_release}"
INPUT="${INPUT_XLSX:-${REPO_DIR}/data/inputs/Input_260818.xlsx}"
OUTPUT="${OUTPUT_XLSX:-${REPO_DIR}/data/outputs/Input_260818_tango.xlsx}"

cd "$REPO_DIR"
mkdir -p logs data/outputs
if [[ ! -x "$TANGO_BIN" ]]; then
  if [[ -f "$TANGO_BIN" ]]; then
    chmod +x "$TANGO_BIN"
  else
    echo "TANGO binary not found at $TANGO_BIN" >&2
    ls -la "${REPO_DIR}/vendor/tango" >&2 || true
    exit 1
  fi
fi
module purge || true
for ver in python/3.9.0 python/3.10.13 python/3.10 python/3.9; do
  if module load "$ver" 2>/dev/null; then
    break
  fi
done
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"
export PYTHONUNBUFFERED=True
python -u src/annotations/run_tango.py \
  --input "$INPUT" \
  --output "$OUTPUT" \
  --tango-bin "$TANGO_BIN"
