#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime

from runtime_common import (
    CN_TZ,
    LOCAL_REPORT_ENV_PATH,
    REPO_ROOT,
    SECRETS_ENV_PATH,
    format_age,
    get_mode_spec,
    load_env,
    load_pinned_metadata,
    read_bot_status,
    resolve_runtime_paths,
    send_discord,
)


DEFAULT_HEARTBEAT_THRESHOLD_MINUTES = 15


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monitor demo freqtrade health and notify Discord")
    parser.add_argument("--sync-now", action="store_true", help="同步当前 demo 健康状态并按状态变化播报")
    parser.add_argument("--notify-start-failure", default="", help="显式发送 demo 启动失败播报")
    parser.add_argument(
        "--heartbeat-threshold-minutes",
        type=int,
        default=DEFAULT_HEARTBEAT_THRESHOLD_MINUTES,
    )
    return parser.parse_args()


def _read_state(path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_state(path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _current_health_code(now: datetime, status, *, threshold_minutes: int) -> str:
    if not status.running:
        return "stopped"
    if status.heartbeat_at is None:
        return "stale"
    heartbeat_seconds = (now - status.heartbeat_at).total_seconds()
    return "healthy" if heartbeat_seconds <= threshold_minutes * 60 else "stale"


def _build_context_line(status, now: datetime) -> str:
    parts = [f"状态 {'RUNNING' if status.running else 'STOPPED'}"]
    if status.running:
        parts.append(f"pid {status.pid or '-'}")
        parts.append(f"hb {format_age(status.heartbeat_at, now)}")
    elif status.last_log_at is not None:
        parts.append(f"lastlog {format_age(status.last_log_at, now)}")
    return " | ".join(parts)


def _build_strategy_line() -> str:
    metadata = load_pinned_metadata("demo")
    if not metadata:
        return "策略 未固定"
    return (
        f"策略 {metadata.get('code_hash_short') or '-'}"
        f" | {metadata.get('source_name') or '-'}"
    )


def _build_environment_line() -> str:
    spec = get_mode_spec("demo")
    return f"环境 {spec.label} | repo {REPO_ROOT.name}"


def _send_message(message: str) -> None:
    env = load_env([SECRETS_ENV_PATH, LOCAL_REPORT_ENV_PATH])
    send_discord(message, env)


def _build_event_message(now: datetime, title: str, detail: str, status) -> str:
    lines = [
        f"【OKX Demo 事件】{now.strftime('%Y-%m-%d %H:%M CST')}",
        f"事件 {title}",
        _build_context_line(status, now),
        _build_strategy_line(),
        _build_environment_line(),
    ]
    if detail.strip():
        lines.append(f"详情 {detail.strip()}")
    return "\n".join(lines)


def sync_status(threshold_minutes: int) -> int:
    paths = resolve_runtime_paths("demo")
    now = datetime.now(CN_TZ)
    status = read_bot_status(paths)
    current_code = _current_health_code(now, status, threshold_minutes=threshold_minutes)
    previous_state = _read_state(paths.monitor_state_path)
    previous_code = str(previous_state.get("health_code") or "")

    event_title = ""
    detail = ""
    if previous_code != current_code:
        if current_code == "healthy":
            event_title = "demo 启动成功" if not previous_code else "demo 已恢复健康"
        elif current_code == "stale":
            event_title = "heartbeat 超阈值"
            detail = f"阈值 {threshold_minutes}m"
        elif current_code == "stopped" and previous_code in {"healthy", "stale"}:
            event_title = "demo 进程停止"

    _write_state(
        paths.monitor_state_path,
        {
            "checked_at": now.isoformat(),
            "health_code": current_code,
            "pid": status.pid,
            "heartbeat_at": status.heartbeat_at.isoformat() if status.heartbeat_at else "",
            "last_log_at": status.last_log_at.isoformat() if status.last_log_at else "",
        },
    )

    if event_title:
        _send_message(_build_event_message(now, event_title, detail, status))
    return 0


def notify_start_failure(detail: str) -> int:
    now = datetime.now(CN_TZ)
    paths = resolve_runtime_paths("demo")
    status = read_bot_status(paths)
    _send_message(_build_event_message(now, "demo 启动失败", detail, status))
    return 0


def main() -> int:
    args = parse_args()
    if args.notify_start_failure.strip():
        return notify_start_failure(args.notify_start_failure.strip())
    return sync_status(args.heartbeat_threshold_minutes)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"demo monitor failed: {exc}", file=sys.stderr)
        raise

