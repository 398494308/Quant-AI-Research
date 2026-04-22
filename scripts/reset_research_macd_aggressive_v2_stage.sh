#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ARCHIVE_ROOT="${REPO_ROOT}/backups/research_macd_aggressive_v2_stage_resets"

JOURNAL_FILE="${REPO_ROOT}/state/research_macd_aggressive_v2_journal.jsonl"
JOURNAL_COMPACT_FILE="${REPO_ROOT}/state/research_macd_aggressive_v2_journal.compact.json"
MEMORY_DIR="${REPO_ROOT}/state/research_macd_aggressive_v2_memory"
SESSION_STATE_FILE="${REPO_ROOT}/state/research_macd_aggressive_v2_session.json"
AGENT_WORKSPACE_DIR="${REPO_ROOT}/state/research_macd_aggressive_v2_agent_workspace"
HEARTBEAT_FILE="${REPO_ROOT}/state/research_macd_aggressive_v2_heartbeat.json"
BEST_STATE_FILE="${REPO_ROOT}/state/research_macd_aggressive_v2_best.json"
STOP_FILE="${REPO_ROOT}/state/research_macd_aggressive_v2.stop"
PID_FILE="${REPO_ROOT}/state/research_macd_aggressive_v2.pid"
LOCK_FILE="${REPO_ROOT}/state/research_macd_aggressive_v2.lock"
CANDIDATE_BACKUP_FILE="${REPO_ROOT}/backups/strategy_macd_aggressive_v2_candidate.py"

mkdir -p "${ARCHIVE_ROOT}" "${REPO_ROOT}/state" "${REPO_ROOT}/backups"

bash "${SCRIPT_DIR}/manage_research_macd_aggressive_v2.sh" stop >/dev/null 2>&1 || true

timestamp="$(date '+%Y%m%d_%H%M%S')"
archive_dir="${ARCHIVE_ROOT}/${timestamp}"
mkdir -p "${archive_dir}"

move_if_exists() {
  local path="$1"
  if [[ -e "${path}" ]]; then
    mv "${path}" "${archive_dir}/"
  fi
}

move_if_exists "${JOURNAL_FILE}"
move_if_exists "${JOURNAL_COMPACT_FILE}"
move_if_exists "${SESSION_STATE_FILE}"
move_if_exists "${AGENT_WORKSPACE_DIR}"
move_if_exists "${HEARTBEAT_FILE}"
move_if_exists "${CANDIDATE_BACKUP_FILE}"
move_if_exists "${MEMORY_DIR}/prompt"
move_if_exists "${MEMORY_DIR}/wiki"
move_if_exists "${MEMORY_DIR}/summaries"

rm -f "${STOP_FILE}" "${PID_FILE}" "${LOCK_FILE}"

if [[ -f "${BEST_STATE_FILE}" ]]; then
  python3 - <<'PY' "${BEST_STATE_FILE}"
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

path = Path(sys.argv[1])
payload = json.loads(path.read_text())
now = datetime.now(UTC).isoformat()
payload["updated_at"] = now
payload["reference_stage_started_at"] = now
payload["reference_stage_iteration"] = 0
path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
PY
fi

mkdir -p "${MEMORY_DIR}/raw/rounds" "${MEMORY_DIR}/prompt" "${MEMORY_DIR}/wiki" "${MEMORY_DIR}/summaries"

echo "stage front reset complete: ${archive_dir}"
