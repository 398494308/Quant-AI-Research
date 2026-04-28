#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MODE="${1:-demo}"
PYTHON_BIN="${PYTHON_BIN:-${REPO_ROOT}/.venv/bin/python}"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="${PYTHON_BIN_FALLBACK:-python3}"
fi

case "${MODE}" in
  dry-run|dryrun)
    RUNTIME_DIR="${SCRIPT_DIR}/runtime/dryrun"
    ;;
  demo)
    RUNTIME_DIR="${SCRIPT_DIR}/runtime/demo"
    ;;
  live)
    RUNTIME_DIR="${SCRIPT_DIR}/runtime/live"
    ;;
  *)
    echo "usage: bash run_daily_report.sh {demo|dry-run|live}"
    exit 1
    ;;
esac

mkdir -p "${RUNTIME_DIR}"

cd "${SCRIPT_DIR}/.."
"${PYTHON_BIN}" "${SCRIPT_DIR}/daily_report.py" "${MODE}" >>"${RUNTIME_DIR}/daily-report.log" 2>&1
