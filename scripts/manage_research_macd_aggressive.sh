#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

PID_FILE="${REPO_ROOT}/state/research_macd_aggressive.pid"
LOCK_FILE="${REPO_ROOT}/state/research_macd_aggressive.lock"
OUT_FILE="${REPO_ROOT}/logs/macd_aggressive_research.out"
BASE_ENV="${REPO_ROOT}/../test1/freqtrade.service.env"
LOCAL_ENV="${REPO_ROOT}/config/research.env"
RUNNER="${REPO_ROOT}/scripts/run_research_macd_aggressive.sh"

mkdir -p "${REPO_ROOT}/logs" "${REPO_ROOT}/state"

is_running() {
  if [[ -f "${PID_FILE}" ]]; then
    local pid
    pid="$(cat "${PID_FILE}")"
    if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
      return 0
    fi
  fi
  return 1
}

list_running_pids() {
  pgrep -f "python3 -u scripts/research_macd_aggressive.py|python3 scripts/research_macd_aggressive.py" || true
}

cmd_start() {
  if is_running; then
    echo "already running: pid=$(cat "${PID_FILE}")"
    exit 0
  fi
  local existing_pids
  existing_pids="$(list_running_pids | xargs echo)"
  if [[ -n "${existing_pids}" ]]; then
    echo "existing unmanaged process detected: ${existing_pids}" >&2
    echo "run '$0 stop' first" >&2
    exit 1
  fi
  if [[ ! -f "${BASE_ENV}" ]]; then
    echo "missing env file: ${BASE_ENV}" >&2
    exit 1
  fi
  if [[ ! -f "${LOCAL_ENV}" ]]; then
    echo "missing env file: ${LOCAL_ENV}" >&2
    exit 1
  fi

  local pid
  pid="$(bash -lc "cd '${REPO_ROOT}' && exec setsid nohup '${RUNNER}' > /dev/null 2>&1 < /dev/null & printf '%s\n' \$!")"
  sleep 1
  if kill -0 "${pid}" 2>/dev/null; then
    echo "${pid}" > "${PID_FILE}"
    echo "started: pid=${pid}"
    exit 0
  fi
  echo "failed to start, check ${OUT_FILE}" >&2
  exit 1
}

cmd_stop() {
  if ! is_running; then
    local stray_pids
    stray_pids="$(list_running_pids | xargs echo)"
    if [[ -z "${stray_pids}" ]]; then
      rm -f "${PID_FILE}"
      echo "not running"
      exit 0
    fi
    for pid in ${stray_pids}; do
      kill "${pid}" 2>/dev/null || true
    done
    rm -f "${PID_FILE}"
    echo "stopped stray pids: ${stray_pids}"
    exit 0
  fi
  local pid
  pid="$(cat "${PID_FILE}")"
  kill "${pid}" 2>/dev/null || true
  for _ in {1..20}; do
    if ! kill -0 "${pid}" 2>/dev/null; then
      rm -f "${PID_FILE}"
      echo "stopped: pid=${pid}"
      exit 0
    fi
    sleep 1
  done
  kill -9 "${pid}" 2>/dev/null || true
  rm -f "${PID_FILE}"
  echo "killed: pid=${pid}"
}

cmd_status() {
  if is_running; then
    echo "running: pid=$(cat "${PID_FILE}")"
  else
    local stray_pids
    stray_pids="$(list_running_pids | xargs echo)"
    if [[ -n "${stray_pids}" ]]; then
      echo "running without pidfile: ${stray_pids}"
      exit 0
    fi
    echo "not running"
    exit 1
  fi
}

case "${1:-status}" in
  start)
    cmd_start
    ;;
  stop)
    cmd_stop
    ;;
  restart)
    bash "$0" stop || true
    bash "$0" start
    ;;
  status)
    cmd_status
    ;;
  *)
    echo "usage: $0 {start|stop|restart|status}" >&2
    exit 1
    ;;
esac
