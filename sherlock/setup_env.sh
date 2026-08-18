#!/bin/bash
# Create the Sherlock Python env and clone catGRANULE 2.0 (v1.0.0).
# Run once on a compute node (sh_dev), not on a login node.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CAT_DIR="${REPO_DIR}/vendor/catGRANULE2.0"
VENV_DIR="${FETCH_LEARN_VENV:-${SCRATCH:-$HOME}/fetch-learn-venv}"

echo "Repo: ${REPO_DIR}"
echo "catGRANULE clone: ${CAT_DIR}"
echo "venv: ${VENV_DIR}"

module purge || true
loaded=""
for ver in python/3.9.0 python/3.10.13 python/3.10.6 python/3.9.6 python/3.10 python/3.9; do
  if module load "$ver" 2>/dev/null; then
    loaded="$ver"
    break
  fi
done
if [[ -z "$loaded" ]]; then
  echo "Need Python 3.9 or 3.10 so scikit-learn==1.1.1 can load the published models." >&2
  echo "Available python modules:" >&2
  module avail python 2>&1 || true
  exit 1
fi
echo "Using module: ${loaded} ($(python3 --version))"

if [[ ! -d "${CAT_DIR}/.git" ]]; then
  mkdir -p "$(dirname "$CAT_DIR")"
  git clone --branch v1.0.0 --depth 1 https://github.com/tartaglialabIIT/catGRANULE2.0.git "$CAT_DIR"
fi

if [[ -d "${CAT_DIR}/ChemicalPhysicalScales_Py_dictionary" && ! -e "${CAT_DIR}/src/ChemicalPhysicalScales_Py_dictionary" ]]; then
  ln -sfn "${CAT_DIR}/ChemicalPhysicalScales_Py_dictionary" "${CAT_DIR}/src/ChemicalPhysicalScales_Py_dictionary"
fi

python3 -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r "${REPO_DIR}/requirements.txt"

mkdir -p "${REPO_DIR}/data/inputs" "${REPO_DIR}/data/outputs" "${REPO_DIR}/logs"
echo "Setup finished. Activate with: source ${VENV_DIR}/bin/activate"
