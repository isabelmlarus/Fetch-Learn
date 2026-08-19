#!/bin/bash
# DeepCoil 2.0 needs Python 3.7 so pip can use old manylinux wheels
# (preshed/allennlp 0.9). Python 3.8 forces a source build that fails, and
# conda-solving tensorflow+pytorch together gets OOM-killed on a small sh_dev.
# Run on a compute node with enough RAM, e.g.:
#   sh_dev -c 4 --mem=16G -t 2:00:00
set -euo pipefail

VENV_DIR="${DEEPCOIL_VENV:-${SCRATCH:-$HOME}/fetch-learn-deepcoil-venv}"
MAMBA_ROOT="${MAMBA_ROOT_PREFIX:-${SCRATCH:-$HOME}/micromamba}"
MICROMAMBA="${MAMBA_ROOT}/bin/micromamba"
PY="${VENV_DIR}/bin/python"

mkdir -p "$MAMBA_ROOT/bin"
module load gcc 2>/dev/null || true

if [[ ! -x "$MICROMAMBA" ]]; then
  echo "Downloading micromamba into ${MAMBA_ROOT}"
  curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj -C "$MAMBA_ROOT" bin/micromamba
fi

need_create=1
if [[ -x "$PY" ]] && "$PY" -c 'import sys; raise SystemExit(0 if sys.version_info[:2]==(3,7) else 1)' 2>/dev/null; then
  need_create=0
  echo "Reusing Python 3.7 env at ${VENV_DIR}"
fi
if [[ "$need_create" -eq 1 ]]; then
  echo "Creating a fresh Python 3.7 env (replacing any 3.8 prefix)"
  rm -rf "$VENV_DIR"
  "$MICROMAMBA" create -y -p "$VENV_DIR" -c conda-forge python=3.7 pip setuptools=59.8.0 wheel
fi

if [[ ! -x "$PY" ]]; then
  echo "Python missing at ${PY}" >&2
  ls -la "${VENV_DIR}/bin" >&2 || true
  exit 1
fi

export SETUPTOOLS_USE_DISTUTILS=stdlib
echo "Using $($PY --version) at ${PY}"
"$PY" -m pip install --upgrade 'pip<24.1' 'setuptools==59.8.0' wheel
"$PY" -m pip install 'deepcoil==2.0.2' openpyxl
"$PY" - <<'PY'
import sys
print("Python", sys.version)
from deepcoil import DeepCoil
print("DeepCoil import OK. First prediction downloads SeqVec weights (~1 GB).")
PY
echo
echo "DeepCoil python: ${PY}"
echo "Then: sbatch sherlock/run_deepcoil.sbatch"
