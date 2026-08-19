#!/bin/bash
# Install DeepCoil 2.0 into its own Sherlock venv.
# DeepCoil needs Python 3.7 or 3.8 (not the 3.9/3.10 catGRANULE env).
# Run once on a compute node: sh_dev -c 4 -t 2:00:00 && bash sherlock/setup_deepcoil.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_DIR="${DEEPCOIL_VENV:-${SCRATCH:-$HOME}/fetch-learn-deepcoil-venv}"

module purge || true
loaded=""
for ver in python/3.8.8 python/3.8.6 python/3.8 python/3.7.13 python/3.7; do
  if module load "$ver" 2>/dev/null; then
    loaded="$ver"
    break
  fi
done
if [[ -z "$loaded" ]]; then
  echo "DeepCoil needs Python 3.7 or 3.8. Available python modules:" >&2
  module avail python 2>&1 || true
  exit 1
fi
echo "Using module: ${loaded} ($(python3 --version))"

python3 -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"
python -m pip install --upgrade pip
python -m pip install 'deepcoil==2.0.2' openpyxl
python - <<'PY'
from deepcoil import DeepCoil
print("Import OK. First prediction will download SeqVec weights (~1 GB) into the user cache.")
PY
echo "DeepCoil venv: ${VENV_DIR}"
echo "Activate with: source ${VENV_DIR}/bin/activate"
