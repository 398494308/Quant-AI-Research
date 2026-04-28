#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
RUNTIME_DIR="${SCRIPT_DIR}/runtime/dryrun"
USER_DATA_DIR="${SCRIPT_DIR}/user_data/dryrun"
PYTHON_BIN="${PYTHON_BIN:-${REPO_ROOT}/.venv/bin/python}"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="${PYTHON_BIN_FALLBACK:-python3}"
fi

FREQTRADE_BIN="${FREQTRADE_BIN:-${REPO_ROOT}/.venv/bin/freqtrade}"
if [[ ! -x "${FREQTRADE_BIN}" ]]; then
  FREQTRADE_BIN="$(command -v freqtrade || true)"
fi
if [[ -z "${FREQTRADE_BIN}" ]]; then
  echo "freqtrade binary not found. Set FREQTRADE_BIN or install freqtrade."
  exit 1
fi

mkdir -p "${RUNTIME_DIR}" "${USER_DATA_DIR}/data"
"${PYTHON_BIN}" "${SCRIPT_DIR}/build_runtime_config.py" --mode dry-run >/dev/null

exec "${FREQTRADE_BIN}" trade \
  --config "${RUNTIME_DIR}/config.runtime.json" \
  --strategy-path "${SCRIPT_DIR}/strategies" \
  --strategy MacdAggressiveStrategy \
  --user-data-dir "${USER_DATA_DIR}" \
  --logfile "${RUNTIME_DIR}/freqtrade.log"
