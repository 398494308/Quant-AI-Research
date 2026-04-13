#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${1:-dry-run}"

case "${MODE}" in
  dry-run|dryrun)
    RUNTIME_DIR="${SCRIPT_DIR}/runtime/dryrun"
    ;;
  live)
    RUNTIME_DIR="${SCRIPT_DIR}/runtime/live"
    ;;
  *)
    echo "usage: bash run_daily_report.sh {dry-run|live}"
    exit 1
    ;;
esac

mkdir -p "${RUNTIME_DIR}"

cd "${SCRIPT_DIR}/.."
python3 "${SCRIPT_DIR}/daily_report.py" "${MODE}" >>"${RUNTIME_DIR}/daily-report.log" 2>&1
