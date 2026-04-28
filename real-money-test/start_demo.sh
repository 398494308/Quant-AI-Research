#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
RUNTIME_DIR="${SCRIPT_DIR}/runtime/demo"
USER_DATA_DIR="${SCRIPT_DIR}/user_data/demo"
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

PINNED_STRATEGY_PATH="${SCRIPT_DIR}/pinned/demo/strategy_macd_aggressive.py"
if [[ ! -f "${PINNED_STRATEGY_PATH}" ]]; then
  echo "demo pinned strategy missing: ${PINNED_STRATEGY_PATH}"
  echo "run: ${PYTHON_BIN} ${SCRIPT_DIR}/pin_strategy.py --source ${REPO_ROOT}/backups/strategy_macd_aggressive_v2_champion.py"
  exit 1
fi

mkdir -p "${RUNTIME_DIR}" "${USER_DATA_DIR}/data"
"${PYTHON_BIN}" "${SCRIPT_DIR}/build_runtime_config.py" --mode demo >/dev/null

exec "${FREQTRADE_BIN}" trade \
  --config "${RUNTIME_DIR}/config.runtime.json" \
  --strategy-path "${SCRIPT_DIR}/strategies" \
  --strategy MacdAggressivePinnedStrategy \
  --user-data-dir "${USER_DATA_DIR}" \
  --logfile "${RUNTIME_DIR}/freqtrade.log"
