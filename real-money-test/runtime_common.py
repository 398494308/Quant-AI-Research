#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo


CN_TZ = ZoneInfo("Asia/Shanghai")
UTC_TZ = ZoneInfo("UTC")
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SECRETS_ENV_PATH = REPO_ROOT / "config" / "secrets.env"
LOCAL_REPORT_ENV_PATH = SCRIPT_DIR / "report.env"
DISCORD_API_BASE = "https://discord.com/api/v10"
LOG_TIMESTAMP_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d{3}")


@dataclass(frozen=True)
class ModeSpec:
    mode: str
    label: str
    runtime_subdir: str
    user_data_subdir: str
    db_name: str
    bot_name: str
    strategy_name: str
    is_exchange_mode: bool
    is_demo: bool = False


@dataclass(frozen=True)
class RuntimePaths:
    mode: str
    runtime_dir: Path
    user_data_dir: Path
    config_path: Path
    pid_file: Path
    db_path: Path
    log_path: Path
    stdout_path: Path
    snapshot_path: Path
    monitor_state_path: Path


@dataclass
class BotStatus:
    running: bool
    pid: str = ""
    heartbeat_at: datetime | None = None
    last_log_at: datetime | None = None


MODE_SPECS: dict[str, ModeSpec] = {
    "dry-run": ModeSpec(
        mode="dry-run",
        label="Dry Run",
        runtime_subdir="dryrun",
        user_data_subdir="dryrun",
        db_name="tradesv3.dryrun.sqlite",
        bot_name="macd-aggressive-dryrun",
        strategy_name="MacdAggressiveStrategy",
        is_exchange_mode=False,
    ),
    "demo": ModeSpec(
        mode="demo",
        label="OKX Demo",
        runtime_subdir="demo",
        user_data_subdir="demo",
        db_name="tradesv3.demo.sqlite",
        bot_name="macd-aggressive-demo",
        strategy_name="MacdAggressivePinnedStrategy",
        is_exchange_mode=True,
        is_demo=True,
    ),
    "live": ModeSpec(
        mode="live",
        label="Live",
        runtime_subdir="live",
        user_data_subdir="live",
        db_name="tradesv3.live.sqlite",
        bot_name="macd-aggressive-live",
        strategy_name="MacdAggressiveStrategy",
        is_exchange_mode=True,
    ),
}

MODE_ALIASES = {
    "dry-run": "dry-run",
    "dryrun": "dry-run",
    "demo": "demo",
    "live": "live",
}


def normalize_mode(mode: str | None, *, default: str = "demo") -> str:
    raw = str(mode or default).strip().lower()
    if not raw:
        raw = default
    if raw not in MODE_ALIASES:
        valid = ", ".join(sorted(MODE_SPECS))
        raise ValueError(f"unknown mode: {mode}. expected one of: {valid}")
    return MODE_ALIASES[raw]


def get_mode_spec(mode: str | None) -> ModeSpec:
    return MODE_SPECS[normalize_mode(mode)]


def resolve_runtime_paths(mode: str | None) -> RuntimePaths:
    spec = get_mode_spec(mode)
    runtime_dir = SCRIPT_DIR / "runtime" / spec.runtime_subdir
    user_data_dir = SCRIPT_DIR / "user_data" / spec.user_data_subdir
    return RuntimePaths(
        mode=spec.mode,
        runtime_dir=runtime_dir,
        user_data_dir=user_data_dir,
        config_path=runtime_dir / "config.runtime.json",
        pid_file=runtime_dir / "freqtrade.pid",
        db_path=runtime_dir / spec.db_name,
        log_path=runtime_dir / "freqtrade.log",
        stdout_path=runtime_dir / "freqtrade.stdout.log",
        snapshot_path=runtime_dir / "daily-report-snapshots.json",
        monitor_state_path=runtime_dir / "demo-monitor-state.json",
    )


def pinned_strategy_dir(mode: str = "demo") -> Path:
    return SCRIPT_DIR / "pinned" / normalize_mode(mode)


def pinned_strategy_path(mode: str = "demo") -> Path:
    return pinned_strategy_dir(mode) / "strategy_macd_aggressive.py"


def pinned_metadata_path(mode: str = "demo") -> Path:
    return pinned_strategy_dir(mode) / "metadata.json"


def load_env(paths: Iterable[Path]) -> dict[str, str]:
    env: dict[str, str] = {}
    for path in paths:
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip()
    return env


def tail_lines(path: Path, limit: int = 200) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8", errors="ignore").splitlines()[-limit:]


def parse_log_timestamp(line: str) -> datetime | None:
    match = LOG_TIMESTAMP_RE.match(line)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S").replace(tzinfo=CN_TZ)
    except ValueError:
        return None


def pid_is_alive(pid: str) -> bool:
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except Exception:
        return False


def find_running_pid(paths: RuntimePaths) -> str:
    if paths.pid_file.exists():
        pid = paths.pid_file.read_text(encoding="utf-8").strip()
        if pid_is_alive(pid):
            return pid
    try:
        result = subprocess.run(
            ["ps", "-eo", "pid=,args="],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return ""
    for line in result.stdout.splitlines():
        if "freqtrade trade" not in line or str(paths.config_path) not in line:
            continue
        parts = line.strip().split(maxsplit=1)
        if parts:
            return parts[0]
    return ""


def read_bot_status(paths: RuntimePaths) -> BotStatus:
    pid = find_running_pid(paths)
    heartbeat_at = None
    last_log_at = None
    for line in reversed(tail_lines(paths.log_path, limit=400)):
        ts = parse_log_timestamp(line)
        if ts and last_log_at is None:
            last_log_at = ts
        if "Bot heartbeat." in line and ts:
            heartbeat_at = ts
            break
    return BotStatus(running=bool(pid), pid=pid, heartbeat_at=heartbeat_at, last_log_at=last_log_at)


def format_age(ts: datetime | None, now: datetime) -> str:
    if ts is None:
        return "-"
    delta = now - ts
    seconds = max(0, int(delta.total_seconds()))
    if seconds < 60:
        return f"{seconds}s"
    minutes, _ = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h{minutes:02d}m"


def resolve_discord_channel_id(env: dict[str, str]) -> str:
    import requests

    if env.get("DISCORD_CHANNEL_ID"):
        return env["DISCORD_CHANNEL_ID"]
    token = env.get("DISCORD_BOT_TOKEN", "")
    guild_id = env.get("DISCORD_GUILD_ID", "")
    channel_name = env.get("DISCORD_CHANNEL_NAME", "quant-highrisk")
    if not token or not guild_id or not channel_name:
        return ""
    response = requests.get(
        f"{DISCORD_API_BASE}/guilds/{guild_id}/channels",
        headers={"Authorization": f"Bot {token}"},
        timeout=15,
    )
    response.raise_for_status()
    for channel in response.json():
        if channel.get("type") == 0 and channel.get("name") == channel_name:
            return channel.get("id", "")
    return ""


def send_discord(message: str, env: dict[str, str]) -> None:
    import requests

    token = env.get("DISCORD_BOT_TOKEN", "")
    channel_id = resolve_discord_channel_id(env)
    if not token or not channel_id:
        raise RuntimeError("missing DISCORD_BOT_TOKEN or channel id")
    response = requests.post(
        f"{DISCORD_API_BASE}/channels/{channel_id}/messages",
        headers={"Authorization": f"Bot {token}"},
        json={"content": message},
        timeout=15,
    )
    response.raise_for_status()


def load_pinned_metadata(mode: str = "demo") -> dict[str, object]:
    path = pinned_metadata_path(mode)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}
