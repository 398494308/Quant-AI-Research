#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  echo "usage: bash manage.sh {start|stop|restart|status|log} {demo|dry-run|live}"
  exit 1
}

ACTION="${1:-}"
MODE="${2:-demo}"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-${REPO_ROOT}/.venv/bin/python}"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="${PYTHON_BIN_FALLBACK:-python3}"
fi

if [[ -z "${ACTION}" ]]; then
  usage
fi

case "${MODE}" in
  dry-run|dryrun)
    MODE_LABEL="dry-run"
    RUNTIME_DIR="${SCRIPT_DIR}/runtime/dryrun"
    PID_FILE="${RUNTIME_DIR}/freqtrade.pid"
    LOG_FILE="${RUNTIME_DIR}/freqtrade.log"
    STDOUT_FILE="${RUNTIME_DIR}/freqtrade.stdout.log"
    CONFIG_PATH="${RUNTIME_DIR}/config.runtime.json"
    START_SCRIPT="${SCRIPT_DIR}/start_dry_run.sh"
    BUILD_MODE="dry-run"
    ;;
  demo)
    MODE_LABEL="demo"
    RUNTIME_DIR="${SCRIPT_DIR}/runtime/demo"
    PID_FILE="${RUNTIME_DIR}/freqtrade.pid"
    LOG_FILE="${RUNTIME_DIR}/freqtrade.log"
    STDOUT_FILE="${RUNTIME_DIR}/freqtrade.stdout.log"
    CONFIG_PATH="${RUNTIME_DIR}/config.runtime.json"
    START_SCRIPT="${SCRIPT_DIR}/start_demo.sh"
    BUILD_MODE="demo"
    ;;
  live)
    MODE_LABEL="live"
    RUNTIME_DIR="${SCRIPT_DIR}/runtime/live"
    PID_FILE="${RUNTIME_DIR}/freqtrade.pid"
    LOG_FILE="${RUNTIME_DIR}/freqtrade.log"
    STDOUT_FILE="${RUNTIME_DIR}/freqtrade.stdout.log"
    CONFIG_PATH="${RUNTIME_DIR}/config.runtime.json"
    START_SCRIPT="${SCRIPT_DIR}/start_live.sh"
    BUILD_MODE="live"
    ;;
  *)
    echo "unknown mode: ${MODE}"
    usage
    ;;
esac

mkdir -p "${RUNTIME_DIR}"

notify_demo_state() {
  if [[ "${MODE_LABEL}" != "demo" ]]; then
    return 0
  fi
  "${PYTHON_BIN}" "${SCRIPT_DIR}/demo_monitor.py" --sync-now >>"${STDOUT_FILE}" 2>&1 || true
}

notify_demo_start_failure() {
  local detail="${1:-demo failed to start}"
  if [[ "${MODE_LABEL}" != "demo" ]]; then
    return 0
  fi
  "${PYTHON_BIN}" "${SCRIPT_DIR}/demo_monitor.py" --notify-start-failure "${detail}" >>"${STDOUT_FILE}" 2>&1 || true
}

latest_failure_detail() {
  local detail=""
  if [[ -f "${STDOUT_FILE}" ]]; then
    detail="$(tail -n 5 "${STDOUT_FILE}" | tail -n 1 | tr -d '\r' || true)"
  fi
  if [[ -z "${detail}" && -f "${LOG_FILE}" ]]; then
    detail="$(tail -n 5 "${LOG_FILE}" | tail -n 1 | tr -d '\r' || true)"
  fi
  if [[ -z "${detail}" ]]; then
    detail="${MODE_LABEL} start exited before pid became healthy"
  fi
  printf '%s' "${detail}"
}

pid_is_alive() {
  local pid="${1:-}"
  [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null
}

find_running_pids() {
  local pid
  local cmd
  while read -r pid; do
    [[ -n "${pid}" ]] || continue
    cmd="$(ps -p "${pid}" -o args= 2>/dev/null || true)"
    [[ "${cmd}" == *"freqtrade trade"* ]] || continue
    [[ "${cmd}" == *"${CONFIG_PATH}"* ]] || continue
    echo "${pid}"
  done < <(pgrep -f -- "${CONFIG_PATH}" 2>/dev/null || true)
}

current_pid() {
  local pid
  if [[ -f "${PID_FILE}" ]]; then
    pid="$(cat "${PID_FILE}")"
    if pid_is_alive "${pid}"; then
      echo "${pid}"
      return 0
    fi
    rm -f "${PID_FILE}"
  fi

  pid="$(find_running_pids | head -n 1 || true)"
  if [[ -n "${pid}" ]]; then
    echo "${pid}" > "${PID_FILE}"
    echo "${pid}"
    return 0
  fi

  return 1
}

start_bot() {
  local build_output=""
  local pid
  if pid="$(current_pid)"; then
    echo "${MODE_LABEL} already running: pid ${pid}"
    exit 0
  fi

  if ! build_output="$("${PYTHON_BIN}" "${SCRIPT_DIR}/build_runtime_config.py" --mode "${BUILD_MODE}" 2>&1 >/dev/null)"; then
    [[ -n "${build_output}" ]] && printf '%s\n' "${build_output}" >>"${STDOUT_FILE}"
    notify_demo_start_failure "${build_output:-${MODE_LABEL} runtime config build failed}"
    echo "${MODE_LABEL} failed to build runtime config"
    exit 1
  fi
  setsid nohup bash "${START_SCRIPT}" >>"${STDOUT_FILE}" 2>&1 </dev/null &
  pid=$!
  echo "${pid}" > "${PID_FILE}"
  sleep 2
  if pid_is_alive "${pid}"; then
    echo "${MODE_LABEL} started: pid ${pid}"
    notify_demo_state
  else
    echo "${MODE_LABEL} failed to start"
    rm -f "${PID_FILE}"
    notify_demo_start_failure "$(latest_failure_detail)"
    exit 1
  fi
}

stop_bot() {
  local pid
  if pid="$(current_pid)"; then
    kill -INT "${pid}" 2>/dev/null || true
    for _ in {1..10}; do
      if ! pid_is_alive "${pid}"; then
        break
      fi
      sleep 1
    done
    if pid_is_alive "${pid}"; then
      kill -TERM "${pid}" 2>/dev/null || true
      for _ in {1..5}; do
        if ! pid_is_alive "${pid}"; then
          break
        fi
        sleep 1
      done
    fi
    if pid_is_alive "${pid}"; then
      echo "${MODE_LABEL} did not stop cleanly: pid ${pid}"
      exit 1
    fi
    rm -f "${PID_FILE}"
    echo "${MODE_LABEL} stopped"
    notify_demo_state
  else
    echo "${MODE_LABEL} not running"
  fi
}

status_bot() {
  local pid
  if pid="$(current_pid)"; then
    echo "${MODE_LABEL} running: pid ${pid}"
    ps -fp "${pid}"
  else
    echo "${MODE_LABEL} not running"
  fi
}

log_bot() {
  touch "${LOG_FILE}"
  tail -f "${LOG_FILE}"
}

case "${ACTION}" in
  start)
    start_bot
    ;;
  stop)
    stop_bot
    ;;
  restart)
    stop_bot
    start_bot
    ;;
  status)
    status_bot
    ;;
  log)
    log_bot
    ;;
  *)
    usage
    ;;
esac
