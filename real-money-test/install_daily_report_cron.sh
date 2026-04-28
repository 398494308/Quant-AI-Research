#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROJECT_SLUG="$(basename "${REPO_ROOT}")"
ACTION="${1:-install}"
MODE_RAW="${2:-demo}"
TASK="${3:-report}"
PYTHON_BIN="${PYTHON_BIN:-${REPO_ROOT}/.venv/bin/python}"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="${PYTHON_BIN_FALLBACK:-python3}"
fi

case "${MODE_RAW}" in
  dry-run|dryrun)
    MODE="dry-run"
    ;;
  demo|live)
    MODE="${MODE_RAW}"
    ;;
  *)
    echo "unknown mode: ${MODE_RAW}"
    echo "usage: bash install_daily_report_cron.sh {install|remove} {demo|dry-run|live} {report|monitor}"
    exit 1
    ;;
esac

case "${TASK}" in
  report)
    CRON_EXPR="0 8 * * *"
    CRON_CMD="cd ${REPO_ROOT} && bash ${SCRIPT_DIR}/run_daily_report.sh ${MODE}"
    ;;
  monitor)
    if [[ "${MODE}" != "demo" ]]; then
      echo "monitor cron only supports demo mode"
      exit 1
    fi
    CRON_EXPR="*/5 * * * *"
    CRON_CMD="cd ${REPO_ROOT} && ${PYTHON_BIN} ${SCRIPT_DIR}/demo_monitor.py --sync-now"
    ;;
  *)
    echo "unknown task: ${TASK}"
    echo "usage: bash install_daily_report_cron.sh {install|remove} {demo|dry-run|live} {report|monitor}"
    exit 1
    ;;
esac

MARKER_KEY="${PROJECT_SLUG}-${MODE//-}-${TASK}"
BEGIN_MARKER="# BEGIN ${MARKER_KEY}"
END_MARKER="# END ${MARKER_KEY}"

existing_crontab="$(crontab -l 2>/dev/null || true)"
filtered_crontab="$(
  printf '%s\n' "${existing_crontab}" | awk -v begin="${BEGIN_MARKER}" -v end="${END_MARKER}" '
    $0 == begin { skip = 1; next }
    $0 == end { skip = 0; next }
    !skip { print }
  '
)"

if [[ "${ACTION}" == "remove" ]]; then
  printf '%s\n' "${filtered_crontab}" | crontab -
  echo "removed ${MODE} ${TASK} cron"
  exit 0
fi

if [[ "${ACTION}" != "install" ]]; then
  echo "unknown action: ${ACTION}"
  echo "usage: bash install_daily_report_cron.sh {install|remove} {demo|dry-run|live} {report|monitor}"
  exit 1
fi

new_block="$(cat <<EOF
${BEGIN_MARKER}
CRON_TZ=Asia/Shanghai
${CRON_EXPR} ${CRON_CMD}
${END_MARKER}
EOF
)"

{
  if [[ -n "${filtered_crontab}" ]]; then
    printf '%s\n' "${filtered_crontab}"
  fi
  printf '%s\n' "${new_block}"
} | crontab -

echo "installed ${MODE} ${TASK} cron"
