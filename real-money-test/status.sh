#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${1:-demo}"

case "${MODE}" in
  dry-run|dryrun)
    CONFIG_PATH="${SCRIPT_DIR}/runtime/dryrun/config.runtime.json"
    ;;
  demo)
    CONFIG_PATH="${SCRIPT_DIR}/runtime/demo/config.runtime.json"
    ;;
  live)
    CONFIG_PATH="${SCRIPT_DIR}/runtime/live/config.runtime.json"
    ;;
  *)
    echo "usage: bash status.sh {demo|dry-run|live}"
    exit 1
    ;;
esac

ps -eo pid=,args= | grep -F -- "${CONFIG_PATH}" | grep "[f]reqtrade trade" || true
