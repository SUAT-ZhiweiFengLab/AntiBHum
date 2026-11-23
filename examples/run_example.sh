#!/usr/bin/env bash
# Run the bundled scFv and VHH inputs using the installed binary distribution.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON="${PYTHON:-python}"

"${PYTHON}" -c "from antibhum import _core; print('Compiled core:', _core.__file__)"

# --vhh routes single-domain input through the existing compiled core.
echo "== HL: scFv humanization =="
"${PYTHON}" "${ROOT_DIR}/run_humanize_v5.py" \
  --scfv "${SCRIPT_DIR}/HL.fasta" \
  --output "${SCRIPT_DIR}/output/HL"

echo "== VHH: single-domain humanization =="
"${PYTHON}" "${ROOT_DIR}/run_humanize_v5.py" \
  --vhh "${SCRIPT_DIR}/VHH.fasta" \
  --output "${SCRIPT_DIR}/output/VHH"

echo "Results: ${SCRIPT_DIR}/output/HL and ${SCRIPT_DIR}/output/VHH"
