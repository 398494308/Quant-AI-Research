#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

LOCK_FILE="${REPO_ROOT}/state/research_macd_aggressive.lock"
PID_FILE="${REPO_ROOT}/state/research_macd_aggressive.pid"
OUT_FILE="${REPO_ROOT}/logs/macd_aggressive_research.out"
BASE_ENV="${REPO_ROOT}/../test1/freqtrade.service.env"
LOCAL_ENV="${REPO_ROOT}/config/research.env"

mkdir -p "${REPO_ROOT}/logs" "${REPO_ROOT}/state"

exec 9>"${LOCK_FILE}"
if ! flock -n 9; then
  echo "another research process is already running" >> "${OUT_FILE}"
  exit 1
fi

set -a
source "${BASE_ENV}"
source "${LOCAL_ENV}"
set +a

echo "$$" > "${PID_FILE}"
cd "${REPO_ROOT}"
exec python3 -u scripts/research_macd_aggressive.py >> "${OUT_FILE}" 2>&1
