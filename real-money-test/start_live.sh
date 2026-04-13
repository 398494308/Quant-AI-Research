#!/usr/bin/env bash
set -euo pipefail

if [[ "${I_UNDERSTAND_LIVE_RISK:-}" != "YES" ]]; then
  echo "Refusing to start live trading. Export I_UNDERSTAND_LIVE_RISK=YES first."
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
RUNTIME_DIR="${SCRIPT_DIR}/runtime/live"
USER_DATA_DIR="${SCRIPT_DIR}/user_data/live"

FREQTRADE_BIN="${FREQTRADE_BIN:-$(command -v freqtrade || true)}"
if [[ -z "${FREQTRADE_BIN}" ]]; then
  echo "freqtrade binary not found. Set FREQTRADE_BIN or install freqtrade."
  exit 1
fi

mkdir -p "${RUNTIME_DIR}" "${USER_DATA_DIR}/data"
python3 "${SCRIPT_DIR}/build_runtime_config.py" --mode live >/dev/null

exec "${FREQTRADE_BIN}" trade \
  --config "${RUNTIME_DIR}/config.runtime.json" \
  --strategy-path "${SCRIPT_DIR}/strategies" \
  --strategy MacdAggressiveStrategy \
  --user-data-dir "${USER_DATA_DIR}" \
  --logfile "${RUNTIME_DIR}/freqtrade.log"
