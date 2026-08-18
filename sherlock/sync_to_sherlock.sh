#!/bin/bash
# Copy this project to Sherlock, then print the remaining login/Duo steps.
# Run in Terminal.app so you can enter your SUNet password and Duo:
#   bash sherlock/sync_to_sherlock.sh
#
# Optional:
#   SUNET=your_sunetid bash sherlock/sync_to_sherlock.sh
set -euo pipefail

SUNET="${SUNET:-$USER}"
HOST="${SHERLOCK_HOST:-login.sherlock.stanford.edu}"
LOCAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
INPUT_LOCAL="${LOCAL_DIR}/data/inputs/Input_260818.xlsx"
if [[ ! -f "$INPUT_LOCAL" ]]; then
  echo "Missing input Excel at ${INPUT_LOCAL}" >&2
  exit 1
fi

echo "Using SSH ${SUNET}@${HOST}"
echo "Remote directory: \$SCRATCH/Fetch-Learn (expanded on Sherlock)"

ssh -t "${SUNET}@${HOST}" 'mkdir -p $SCRATCH/Fetch-Learn/data/inputs $SCRATCH/Fetch-Learn/data/outputs $SCRATCH/Fetch-Learn/logs $SCRATCH/Fetch-Learn/src $SCRATCH/Fetch-Learn/sherlock'

rsync -av --exclude '.git' \
  "${LOCAL_DIR}/src/" "${SUNET}@${HOST}:"'$SCRATCH/Fetch-Learn/src/'
rsync -av "${LOCAL_DIR}/sherlock/" "${SUNET}@${HOST}:"'$SCRATCH/Fetch-Learn/sherlock/'
rsync -av "${LOCAL_DIR}/requirements.txt" "${LOCAL_DIR}/README.md" "${LOCAL_DIR}/.gitignore" \
  "${SUNET}@${HOST}:"'$SCRATCH/Fetch-Learn/'
rsync -av "${INPUT_LOCAL}" "${SUNET}@${HOST}:"'$SCRATCH/Fetch-Learn/data/inputs/'

echo
echo "Next, in Terminal:"
echo "  ssh ${SUNET}@${HOST}"
echo "  cd \$SCRATCH/Fetch-Learn"
echo "  sh_dev -c 4 -t 1:00:00"
echo "  bash sherlock/setup_env.sh"
echo "  exit"
echo "  cd \$SCRATCH/Fetch-Learn"
echo "  sbatch sherlock/smoke.sbatch"
echo "  sbatch sherlock/run_catgranule.sbatch"
echo
echo "After the full job finishes, copy the result back to Dropbox:"
echo "  mkdir -p ${LOCAL_DIR}/data/outputs"
echo "  scp ${SUNET}@${HOST}:\$SCRATCH/Fetch-Learn/data/outputs/Input_260818_catGRANULE2.xlsx ${LOCAL_DIR}/data/outputs/"
