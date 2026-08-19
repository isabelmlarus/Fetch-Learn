#!/bin/bash
# Install DeepCoil 2.0 into its own env with Python 3.8.
# Sherlock has no python/3.7 or python/3.8 module, so this bootstraps
# micromamba + Python 3.8 in $SCRATCH (do not use catGRANULE's 3.9 env).
# Micromamba envs have bin/python but often no bin/activate — call python directly.
# Run on a compute node: sh_dev -c 4 -t 2:00:00
set -euo pipefail

VENV_DIR="${DEEPCOIL_VENV:-${SCRATCH:-$HOME}/fetch-learn-deepcoil-venv}"
MAMBA_ROOT="${MAMBA_ROOT_PREFIX:-${SCRATCH:-$HOME}/micromamba}"
MICROMAMBA="${MAMBA_ROOT}/bin/micromamba"
PY="${VENV_DIR}/bin/python"

mkdir -p "$MAMBA_ROOT/bin"

if [[ ! -x "$MICROMAMBA" ]]; then
  echo "Downloading micromamba into ${MAMBA_ROOT}"
  curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj -C "$MAMBA_ROOT" bin/micromamba
fi

if [[ ! -x "$PY" ]]; then
  echo "Creating Python 3.8 env at ${VENV_DIR}"
  "$MICROMAMBA" create -y -p "$VENV_DIR" -c conda-forge python=3.8 pip
fi

if [[ ! -x "$PY" ]]; then
  echo "Python still missing after micromamba create. Prefix contents:" >&2
  ls -la "$VENV_DIR" >&2 || true
  ls -la "${VENV_DIR}/bin" >&2 || true
  exit 1
fi

echo "Using $($PY --version) at ${PY}"
"$PY" -m pip install --upgrade pip
"$PY" -m pip install 'deepcoil==2.0.2' openpyxl
"$PY" - <<'PY'
import sys
print("Python", sys.version)
from deepcoil import DeepCoil
print("DeepCoil import OK. First prediction downloads SeqVec weights (~1 GB).")
PY
echo
echo "DeepCoil python: ${PY}"
echo "Then submit: sbatch sherlock/run_deepcoil.sbatch"
