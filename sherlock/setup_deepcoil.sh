#!/bin/bash
# Install DeepCoil 2.0 into a Python 3.8 micromamba env on Sherlock.
# DeepCoil pins allennlp 0.9.0, which tries to compile ancient preshed/cymem.
# Use conda-forge binaries plus setuptools 59 so pip does not hit modern distutils.
# Run on a compute node: sh_dev -c 4 -t 2:00:00
set -euo pipefail

VENV_DIR="${DEEPCOIL_VENV:-${SCRATCH:-$HOME}/fetch-learn-deepcoil-venv}"
MAMBA_ROOT="${MAMBA_ROOT_PREFIX:-${SCRATCH:-$HOME}/micromamba}"
MICROMAMBA="${MAMBA_ROOT}/bin/micromamba"
PY="${VENV_DIR}/bin/python"

mkdir -p "$MAMBA_ROOT/bin"
module load gcc 2>/dev/null || module load gcc/12 2>/dev/null || true

if [[ ! -x "$MICROMAMBA" ]]; then
  echo "Downloading micromamba into ${MAMBA_ROOT}"
  curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj -C "$MAMBA_ROOT" bin/micromamba
fi

if [[ ! -x "$PY" ]]; then
  echo "Creating Python 3.8 env at ${VENV_DIR}"
  "$MICROMAMBA" create -y -p "$VENV_DIR" -c conda-forge python=3.8 pip
fi

echo "Installing compiled DeepCoil dependencies from conda-forge"
"$MICROMAMBA" install -y -p "$VENV_DIR" -c conda-forge \
  'setuptools=59.8.0' \
  wheel \
  'pandas=1.3.0' \
  'biopython=1.79' \
  openpyxl \
  'tensorflow>=2.3,<2.12' \
  'pytorch>=1.4,<2.0' \
  'spacy>=2.1,<2.4' \
  'preshed>=2.0.1,<2.1' \
  cymem \
  cython \
  h5py \
  tqdm \
  'overrides=3.1.0' \
  'seaborn>=0.12,<0.13'

if [[ ! -x "$PY" ]]; then
  echo "Python missing at ${PY}" >&2
  ls -la "${VENV_DIR}/bin" >&2 || true
  exit 1
fi

export SETUPTOOLS_USE_DISTUTILS=stdlib
echo "Using $($PY --version) at ${PY}"
"$PY" -m pip install --upgrade 'pip<24.1' 'setuptools==59.8.0' wheel
# Isolation would download a new setuptools and break distutils again.
"$PY" -m pip install --no-build-isolation 'allennlp==0.9.0'
"$PY" -m pip install --no-build-isolation 'deepcoil==2.0.2'
"$PY" - <<'PY'
import sys
print("Python", sys.version)
from deepcoil import DeepCoil
print("DeepCoil import OK. First prediction downloads SeqVec weights (~1 GB).")
PY
echo
echo "DeepCoil python: ${PY}"
echo "Then submit: sbatch sherlock/run_deepcoil.sbatch"
