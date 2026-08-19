#!/bin/bash
# Install DeepCoil 2.0 into its own env with Python 3.8.
# Sherlock has no python/3.7 or python/3.8 module, so this bootstraps
# micromamba + Python 3.8 in $SCRATCH (do not use catGRANULE's 3.9 env).
# Run on a compute node: sh_dev -c 4 -t 2:00:00
set -euo pipefail

VENV_DIR="${DEEPCOIL_VENV:-${SCRATCH:-$HOME}/fetch-learn-deepcoil-venv}"
MAMBA_ROOT="${MAMBA_ROOT_PREFIX:-${SCRATCH:-$HOME}/micromamba}"
MICROMAMBA="${MAMBA_ROOT}/bin/micromamba"

mkdir -p "$MAMBA_ROOT/bin"

if [[ ! -x "$MICROMAMBA" ]]; then
  echo "Downloading micromamba into ${MAMBA_ROOT}"
  curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj -C "$MAMBA_ROOT" bin/micromamba
fi

echo "Creating Python 3.8 env at ${VENV_DIR}"
"$MICROMAMBA" create -y -p "$VENV_DIR" -c conda-forge python=3.8 pip
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"
python -m pip install --upgrade pip
python -m pip install 'deepcoil==2.0.2' openpyxl
python - <<'PY'
import sys
print("Python", sys.version)
from deepcoil import DeepCoil
print("DeepCoil import OK. First prediction downloads SeqVec weights (~1 GB).")
PY
echo
echo "DeepCoil env: ${VENV_DIR}"
echo "Activate with: source ${VENV_DIR}/bin/activate"
echo "Then submit: sbatch sherlock/run_deepcoil.sbatch"
