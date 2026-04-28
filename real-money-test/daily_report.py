#!/usr/bin/env python3
from __future__ import annotations

import json
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests

from runtime_common import (
    CN_TZ,
    LOCAL_REPORT_ENV_PATH,
    SECRETS_ENV_PATH,
    UTC_TZ,
    BotStatus,
    format_age,
    get_mode_spec,
    load_env,
    load_pinned_metadata,
    read_bot_status,
    resolve_runtime_paths,
    send_discord,
)

try:  # pragma: no cover - 线上依赖 .venv 提供
    import ccxt
except ImportError:  # pragma: no cover
    ccxt = None


REPORT_MODE = "demo"


@dataclass
class AccountSnapshot:
    equity: float | None
    available_balance: float | None
    source_label: str
    degraded_reason: str = ""


def read_runtime_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return {}
    return json.loads(config_path.read_text(encoding="utf-8"))


def open_db(db_path: Path) -> sqlite3.Connection | None:
    if not db_path.exists():
        return None
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def read_summary(now: datetime, db_path: Path) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "total_trades": 0,
        "open_trades": 0,
        "closed_trades": 0,
        "closed_pnl_abs": 0.0,
        "open_realized_pnl_abs": 0.0,
        "unrealized_pnl_abs": 0.0,
        "day_closed_trades": 0,
        "day_wins": 0,
        "day_pnl_abs": 0.0,
        "open_positions": [],
        "recent_closes": [],
    }
    conn = open_db(db_path)
    if conn is None:
        return summary

    now_utc = now.astimezone(UTC_TZ)
    cutoff = (now_utc - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
          COUNT(*) AS total_trades,
          SUM(CASE WHEN is_open = 1 THEN 1 ELSE 0 END) AS open_trades,
          SUM(CASE WHEN is_open = 0 THEN 1 ELSE 0 END) AS closed_trades,
          SUM(CASE WHEN is_open = 0 THEN COALESCE(close_profit_abs, 0) ELSE 0 END) AS closed_pnl_abs,
          SUM(CASE WHEN is_open = 1 THEN COALESCE(realized_profit, 0) ELSE 0 END) AS open_realized_pnl_abs
        FROM trades
        """
    )
    row = cur.fetchone()
    if row is not None:
        summary["total_trades"] = row["total_trades"] or 0
        summary["open_trades"] = row["open_trades"] or 0
        summary["closed_trades"] = row["closed_trades"] or 0
        summary["closed_pnl_abs"] = float(row["closed_pnl_abs"] or 0.0)
        summary["open_realized_pnl_abs"] = float(row["open_realized_pnl_abs"] or 0.0)

    cur.execute(
        """
        SELECT
          COUNT(*) AS day_closed_trades,
          SUM(CASE WHEN COALESCE(close_profit_abs, 0) > 0 THEN 1 ELSE 0 END) AS day_wins,
          SUM(COALESCE(close_profit_abs, 0)) AS day_pnl_abs
        FROM trades
        WHERE is_open = 0
          AND close_date IS NOT NULL
          AND close_date >= ?
        """,
        (cutoff,),
    )
    row = cur.fetchone()
    if row is not None:
        summary["day_closed_trades"] = row["day_closed_trades"] or 0
        summary["day_wins"] = row["day_wins"] or 0
        summary["day_pnl_abs"] = float(row["day_pnl_abs"] or 0.0)

    cur.execute(
        """
        SELECT
          pair,
          is_short,
          leverage,
          open_rate,
          stake_amount,
          amount,
          contract_size,
          open_date,
          enter_tag,
          realized_profit
        FROM trades
        WHERE is_open = 1
        ORDER BY open_date ASC
        """
    )
    summary["open_positions"] = [dict(row) for row in cur.fetchall()]

    cur.execute(
        """
        SELECT pair, is_short, close_date, close_profit_abs, exit_reason
        FROM trades
        WHERE is_open = 0
        ORDER BY close_date DESC
        LIMIT 3
        """
    )
    summary["recent_closes"] = [dict(row) for row in cur.fetchall()]

    prices = fetch_current_prices(summary["open_positions"])
    unrealized_pnl_abs = 0.0
    for pos in summary["open_positions"]:
        current_rate = prices.get(pos["pair"])
        pos["current_rate"] = current_rate
        pos["unrealized_pnl_abs"] = calc_unrealized_pnl_abs(pos, current_rate)
        unrealized_pnl_abs += float(pos["unrealized_pnl_abs"] or 0.0)
    summary["unrealized_pnl_abs"] = unrealized_pnl_abs
    conn.close()
    return summary


def format_side(is_short: int | bool | None) -> str:
    return "SHORT" if is_short else "LONG"


def pair_to_okx_inst_id(pair: str) -> str:
    base, quote_part = pair.split("/", 1)
    quote = quote_part.split(":", 1)[0]
    settle = quote_part.split(":", 1)[1] if ":" in quote_part else quote
    if quote == settle:
        return f"{base}-{quote}-SWAP"
    return f"{base}-{quote}-{settle}"


def fetch_current_prices(positions: list[dict[str, Any]]) -> dict[str, float]:
    prices: dict[str, float] = {}
    for pos in positions:
        pair = str(pos.get("pair") or "")
        if not pair or pair in prices:
            continue
        inst_id = pair_to_okx_inst_id(pair)
        try:
            response = requests.get(
                f"https://www.okx.com/api/v5/market/ticker?instId={inst_id}",
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
            data = payload.get("data") or []
            if not data:
                continue
            last = data[0].get("last")
            if last is None:
                continue
            prices[pair] = float(last)
        except Exception:
            continue
    return prices


def calc_unrealized_pnl_abs(position: dict[str, Any], current_rate: float | None) -> float:
    if current_rate is None:
        return 0.0
    amount = float(position.get("amount") or 0.0)
    open_rate = float(position.get("open_rate") or 0.0)
    if amount <= 0 or open_rate <= 0:
        return 0.0
    direction = -1.0 if position.get("is_short") else 1.0
    return direction * (current_rate - open_rate) * amount


def format_pct(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:+.2f}%"


def format_abs(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:+.2f}U"


def format_plain(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2f}U"


def load_snapshots(snapshot_path: Path) -> list[dict[str, Any]]:
    if not snapshot_path.exists():
        return []
    try:
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    return payload if isinstance(payload, list) else []


def save_snapshots(snapshot_path: Path, snapshots: list[dict[str, Any]]) -> None:
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(json.dumps(snapshots, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def previous_snapshot_for_date(snapshots: list[dict[str, Any]], report_date: str) -> dict[str, Any] | None:
    for snapshot in reversed(snapshots):
        if snapshot.get("date") != report_date:
            return snapshot
    return None


def baseline_snapshot(snapshots: list[dict[str, Any]]) -> dict[str, Any] | None:
    for snapshot in snapshots:
        if snapshot.get("equity") is not None:
            return snapshot
    return None


def upsert_snapshot(snapshots: list[dict[str, Any]], snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    updated = [item for item in snapshots if item.get("date") != snapshot.get("date")]
    updated.append(snapshot)
    updated.sort(key=lambda item: item.get("date", ""))
    return updated[-60:]


def format_positions(positions: list[dict[str, Any]]) -> str:
    if not positions:
        return "空仓"
    rendered: list[str] = []
    for pos in positions[:2]:
        current_rate = pos.get("current_rate")
        unrealized_pnl_abs = float(pos.get("unrealized_pnl_abs") or 0.0)
        pnl_pct = None
        stake_amount = float(pos.get("stake_amount") or 0.0)
        if stake_amount > 0:
            pnl_pct = unrealized_pnl_abs / stake_amount * 100.0
        enter_tag = str(pos.get("enter_tag") or "").strip()
        rendered.append(
            (
                f"{pos['pair']} {format_side(pos.get('is_short'))} "
                f"x{int(pos.get('leverage') or 0)} "
                f"uPnL={format_abs(unrealized_pnl_abs)} "
                f"({format_pct(pnl_pct)})"
                + (f" tag={enter_tag}" if enter_tag else "")
                + (f" now={float(current_rate):.2f}" if current_rate else "")
            )
        )
    if len(positions) > 2:
        rendered.append(f"...其余 {len(positions) - 2} 笔")
    return " | ".join(rendered)


def format_recent_closes(closes: list[dict[str, Any]]) -> str:
    if not closes:
        return "无"
    rendered = []
    for item in closes:
        close_date = str(item.get("close_date") or "")[:16]
        rendered.append(
            (
                f"{close_date} {item['pair']} {format_side(item.get('is_short'))} "
                f"{float(item.get('close_profit_abs') or 0):+.2f} "
                f"{item.get('exit_reason') or '-'}"
            )
        )
    return " | ".join(rendered)


def _balance_value(payload: dict[str, Any], section: str, currency: str) -> float | None:
    section_payload = payload.get(section) or {}
    if isinstance(section_payload, dict):
        raw_value = section_payload.get(currency)
        if raw_value is None:
            return None
        try:
            return float(raw_value)
        except Exception:
            return None
    return None


def _account_credentials(mode: str, env: dict[str, str]) -> tuple[dict[str, str], str]:
    if mode == "demo":
        prefix = "OKX_DEMO"
    elif mode == "live":
        prefix = "OKX"
    else:
        return {}, ""
    creds = {
        "apiKey": env.get(f"{prefix}_API_KEY", ""),
        "secret": env.get(f"{prefix}_API_SECRET", ""),
        "password": env.get(f"{prefix}_API_PASSWORD", ""),
    }
    return creds, prefix


def fetch_okx_account_snapshot(mode: str, runtime_config: dict[str, Any], env: dict[str, str]) -> AccountSnapshot:
    if mode not in {"demo", "live"}:
        return AccountSnapshot(None, None, "local_estimate", "dry-run mode")
    if ccxt is None:
        return AccountSnapshot(None, None, "local_estimate", "ccxt unavailable")

    creds, prefix = _account_credentials(mode, env)
    if not all(creds.values()):
        return AccountSnapshot(None, None, "local_estimate", f"missing {prefix}_* credentials")

    params = {
        **creds,
        "sandbox": mode == "demo",
        "enableRateLimit": True,
        "options": {"defaultType": "swap"},
    }
    exchange = ccxt.okx(params)
    try:
        balance = exchange.fetch_balance({"type": "swap"})
        quote = str(runtime_config.get("stake_currency") or "USDT")
        equity = _balance_value(balance, "total", quote)
        available_balance = _balance_value(balance, "free", quote)
        if equity is None and available_balance is not None:
            used = _balance_value(balance, "used", quote)
            if used is not None:
                equity = available_balance + used
        if equity is None and available_balance is None:
            return AccountSnapshot(None, None, "local_estimate", "balance payload missing stake currency")
        return AccountSnapshot(equity, available_balance, "exchange_api")
    except Exception as exc:
        return AccountSnapshot(None, None, "local_estimate", str(exc))
    finally:
        try:
            exchange.close()
        except Exception:
            pass


def estimate_account_snapshot(runtime_config: dict[str, Any], summary: dict[str, Any]) -> AccountSnapshot:
    initial_capital = float(runtime_config.get("dry_run_wallet") or 0.0)
    total_realized = float(summary["closed_pnl_abs"]) + float(summary["open_realized_pnl_abs"])
    equity = initial_capital + total_realized + float(summary["unrealized_pnl_abs"])
    return AccountSnapshot(equity, None, "local_estimate", "account api unavailable")


def build_message(
    now: datetime,
    mode: str,
    status: BotStatus,
    runtime_config: dict[str, Any],
    summary: dict[str, Any],
    env: dict[str, str],
    snapshot_path: Path,
) -> str:
    spec = get_mode_spec(mode)
    total_realized = float(summary["closed_pnl_abs"]) + float(summary["open_realized_pnl_abs"])
    account_snapshot = fetch_okx_account_snapshot(mode, runtime_config, env)
    if account_snapshot.equity is None:
        estimated_snapshot = estimate_account_snapshot(runtime_config, summary)
        account_snapshot = AccountSnapshot(
            equity=estimated_snapshot.equity,
            available_balance=estimated_snapshot.available_balance,
            source_label=estimated_snapshot.source_label,
            degraded_reason=account_snapshot.degraded_reason or estimated_snapshot.degraded_reason,
        )

    snapshots = load_snapshots(snapshot_path)
    report_date = now.strftime("%Y-%m-%d")
    previous_snapshot = previous_snapshot_for_date(snapshots, report_date)
    baseline = baseline_snapshot(snapshots)

    day_delta_abs = None
    day_delta_pct = None
    if previous_snapshot is not None and account_snapshot.equity is not None:
        previous_equity = float(previous_snapshot.get("equity") or 0.0)
        day_delta_abs = account_snapshot.equity - previous_equity
        if previous_equity > 0:
            day_delta_pct = day_delta_abs / previous_equity * 100.0

    cumulative_pct = None
    if mode == "dry-run":
        initial_capital = float(runtime_config.get("dry_run_wallet") or 0.0)
        if initial_capital > 0 and account_snapshot.equity is not None:
            cumulative_pct = (account_snapshot.equity / initial_capital - 1.0) * 100.0
    elif baseline is not None and account_snapshot.equity is not None:
        baseline_equity = float(baseline.get("equity") or 0.0)
        if baseline_equity > 0:
            cumulative_pct = (account_snapshot.equity / baseline_equity - 1.0) * 100.0

    snapshot = {
        "date": report_date,
        "reported_at": now.isoformat(),
        "equity": account_snapshot.equity,
        "available_balance": account_snapshot.available_balance,
        "total_trades": summary["total_trades"],
        "open_trades": summary["open_trades"],
        "closed_trades": summary["closed_trades"],
        "total_realized": total_realized,
        "unrealized_pnl_abs": summary["unrealized_pnl_abs"],
        "account_source": account_snapshot.source_label,
    }
    save_snapshots(snapshot_path, upsert_snapshot(snapshots, snapshot))

    pairlist = runtime_config.get("exchange", {}).get("pair_whitelist", [])
    pair_text = ", ".join(pairlist) if pairlist else "-"
    position_usage = f"{summary['open_trades']}/{runtime_config.get('max_open_trades', '-')}"
    heartbeat_age = format_age(status.heartbeat_at, now)
    day_closed_trades = int(summary["day_closed_trades"] or 0)
    day_wins = int(summary["day_wins"] or 0)
    win_rate = (day_wins / day_closed_trades * 100.0) if day_closed_trades > 0 else None
    pinned_metadata = load_pinned_metadata(mode) if mode == "demo" else {}

    lines = [f"【{spec.label}】{now.strftime('%Y-%m-%d %H:%M CST')}"]
    lines.append(
        (
            f"状态 {'RUNNING' if status.running else 'STOPPED'}"
            + (f" | hb {heartbeat_age}" if status.running else "")
            + (f" | lastlog {format_age(status.last_log_at, now)}" if status.last_log_at else "")
        )
    )
    if mode == "demo":
        if pinned_metadata:
            lines.append(
                f"策略 {pinned_metadata.get('code_hash_short') or '-'}"
                f" | {pinned_metadata.get('source_name') or '-'}"
            )
        else:
            lines.append("策略 未固定")
    account_line = (
        f"账户 权益 {format_plain(account_snapshot.equity)}"
        f" | 可用 {format_plain(account_snapshot.available_balance)}"
        f" | 昨日 {format_abs(day_delta_abs)} ({format_pct(day_delta_pct)})"
        f" | 累计 {format_pct(cumulative_pct)}"
    )
    if account_snapshot.degraded_reason:
        account_line += f" | degraded={account_snapshot.degraded_reason}"
    lines.append(account_line)
    lines.append(
        f"交易 总{summary['total_trades']} | 24h平仓 {day_closed_trades} | 24h胜率 {format_pct(win_rate)}"
        f" | 已实现 {format_abs(total_realized)} | 未实现 {format_abs(summary['unrealized_pnl_abs'])}"
    )
    lines.append(f"持仓 {position_usage} | {format_positions(summary['open_positions'])}")
    lines.append(f"环境 {spec.label} | {pair_text} {runtime_config.get('timeframe', '-')}")
    lines.append(f"最近 {format_recent_closes(summary['recent_closes'])}")
    return "\n".join(lines)


def main() -> int:
    mode = REPORT_MODE
    if len(sys.argv) > 1 and sys.argv[1] in ("dry-run", "dryrun", "demo", "live"):
        mode = sys.argv[1]

    paths = resolve_runtime_paths(mode)
    env = load_env([SECRETS_ENV_PATH, LOCAL_REPORT_ENV_PATH])
    now = datetime.now(CN_TZ)
    runtime_config = read_runtime_config(paths.config_path)
    status = read_bot_status(paths)
    summary = read_summary(now, paths.db_path)
    message = build_message(now, mode, status, runtime_config, summary, env, paths.snapshot_path)
    send_discord(message, env)
    print(message)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"daily report failed: {exc}", file=sys.stderr)
        raise
