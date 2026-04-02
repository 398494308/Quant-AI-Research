#!/usr/bin/env python3
"""激进版双向 BTC 合约策略自动研究循环。"""
import importlib
import json
import logging
import os
import pprint
import re
import shutil
import sys
import time
import traceback
from datetime import UTC, datetime, timedelta
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SRC_DIR = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

import backtest_macd_aggressive as backtest_module
import strategy_macd_aggressive as strategy_module
from openai_strategy_client import (
    StrategyGenerationTransientError,
    describe_client_config,
    generate_json_object,
)

BASE_DIR = REPO_ROOT
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID", "")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID", "")
DISCORD_CHANNEL_NAME = os.getenv("DISCORD_CHANNEL_NAME", "quant-highrisk")
STRATEGY_FILE = BASE_DIR / "src/strategy_macd_aggressive.py"
BACKUP_FILE = BASE_DIR / "backups/strategy_macd_aggressive_backup.py"
BACKTEST_FILE = BASE_DIR / "src/backtest_macd_aggressive.py"
BACKTEST_BACKUP_FILE = BASE_DIR / "backups/backtest_macd_aggressive_backup.py"
PROGRAM_FILE = BASE_DIR / "docs/program_macd_aggressive.md"
LOG_FILE = str(BASE_DIR / "logs/macd_aggressive_research.log")
MEMORY_FILE = BASE_DIR / "state/optimizer_memory_macd_aggressive.json"
HEARTBEAT_FILE = BASE_DIR / "state/research_macd_aggressive_heartbeat.json"
LOOP_INTERVAL_SECONDS = int(os.getenv("MACD_LOOP_INTERVAL_SECONDS", "600"))
PROVIDER_RECOVERY_WAIT_SECONDS = int(os.getenv("MACD_PROVIDER_RECOVERY_WAIT_SECONDS", "120"))
FAILURE_COOLDOWN_SECONDS = int(os.getenv("MACD_FAILURE_COOLDOWN_SECONDS", "60"))
MAX_PARAM_CHANGES_PER_ITERATION = int(os.getenv("MACD_MAX_PARAM_CHANGES", "6"))
MAX_PARAM_RELATIVE_STEP = float(os.getenv("MACD_MAX_PARAM_RELATIVE_STEP", "0.15"))
MAX_DUPLICATE_REPLAN_ATTEMPTS = int(os.getenv("MACD_DUPLICATE_REPLAN_ATTEMPTS", "2"))
PLATEAU_PASS_STREAK_TO_EXPAND = int(os.getenv("MACD_PLATEAU_PASS_STREAK_TO_EXPAND", "6"))
BOOSTED_PARAM_CHANGES_PER_ITERATION = int(os.getenv("MACD_BOOSTED_PARAM_CHANGES", "8"))
BOOSTED_PARAM_RELATIVE_STEP = float(os.getenv("MACD_BOOSTED_PARAM_RELATIVE_STEP", "0.22"))
AGGRESSIVE_DRAWDOWN_SOFT_CAP = float(os.getenv("MACD_DRAWDOWN_SOFT_CAP", "55.0"))
AGGRESSIVE_DRAWDOWN_HARD_CAP = float(os.getenv("MACD_DRAWDOWN_HARD_CAP", "65.0"))
AGGRESSIVE_MIN_VALIDATION_SCORE = float(os.getenv("MACD_MIN_VALIDATION_SCORE", "0.0"))
AGGRESSIVE_MAX_OVERFIT_GAP = float(os.getenv("MACD_MAX_OVERFIT_GAP", "25.0"))
AGGRESSIVE_MIN_LEVERAGE = int(os.getenv("MACD_MIN_LEVERAGE", "14"))
AGGRESSIVE_MIN_TP1_PNL_PCT = float(os.getenv("MACD_MIN_TP1_PNL_PCT", "42.0"))
AGGRESSIVE_MIN_SHADOW_TEST_SCORE = float(os.getenv("MACD_MIN_SHADOW_TEST_SCORE", "0.0"))
AGGRESSIVE_MAX_VAL_SHADOW_GAP = float(os.getenv("MACD_MAX_VAL_SHADOW_GAP", "28.0"))
AGGRESSIVE_MAX_SHADOW_REGRESSION = float(os.getenv("MACD_MAX_SHADOW_REGRESSION", "6.0"))
AGGRESSIVE_MIN_SHADOW_TEST_TRADES = int(os.getenv("MACD_MIN_SHADOW_TEST_TRADES", "8"))
EVAL_START_DATE = os.getenv("MACD_EVAL_START_DATE", "2025-10-01")
EVAL_END_DATE = os.getenv("MACD_EVAL_END_DATE", "2026-03-31")
EVAL_CHUNK_DAYS = int(os.getenv("MACD_EVAL_CHUNK_DAYS", "20"))
TRAIN_CHUNK_COUNT = int(os.getenv("MACD_TRAIN_CHUNK_COUNT", "5"))
VAL_CHUNK_COUNT = int(os.getenv("MACD_VAL_CHUNK_COUNT", "2"))
TEST_CHUNK_COUNT = int(os.getenv("MACD_TEST_CHUNK_COUNT", "2"))
CORE_STRATEGY_PARAM_KEYS = (
    "macd_fast",
    "macd_slow",
    "macd_signal",
    "hourly_adx_min",
    "breakout_lookback",
    "breakdown_lookback",
)
CORE_EXIT_PARAM_KEYS = (
    "leverage",
    "position_fraction",
    "stop_atr_mult",
    "stop_max_loss_pct",
    "tp1_pnl_pct",
    "trailing_activation_pct",
)
INTRADAY_FILE = str(BASE_DIR / "data/price/BTCUSDT_futures_15m_20240601_20260401.csv")
HOURLY_FILE = str(BASE_DIR / "data/price/BTCUSDT_futures_1h_20240601_20260401.csv")


def _generate_windows():
    start_dt = datetime.strptime(EVAL_START_DATE, "%Y-%m-%d")
    end_dt = datetime.strptime(EVAL_END_DATE, "%Y-%m-%d")
    total_days = (end_dt - start_dt).days + 1
    if total_days <= 0:
        raise ValueError(f"invalid evaluation range: {EVAL_START_DATE}..{EVAL_END_DATE}")
    if EVAL_CHUNK_DAYS < 5:
        raise ValueError(f"EVAL_CHUNK_DAYS too small: {EVAL_CHUNK_DAYS}")

    full_chunks, remainder = divmod(total_days, EVAL_CHUNK_DAYS)
    if full_chunks == 0:
        chunk_lengths = [total_days]
    elif remainder == 0:
        chunk_lengths = [EVAL_CHUNK_DAYS] * full_chunks
    else:
        chunk_lengths = [remainder + EVAL_CHUNK_DAYS] + [EVAL_CHUNK_DAYS] * (full_chunks - 1)

    required_chunks = TRAIN_CHUNK_COUNT + VAL_CHUNK_COUNT + TEST_CHUNK_COUNT
    if len(chunk_lengths) < required_chunks:
        raise ValueError(
            f"not enough chunks for split: have={len(chunk_lengths)}, need={required_chunks}"
        )

    boundaries = []
    cursor = start_dt
    for chunk_len in chunk_lengths:
        chunk_end = cursor + timedelta(days=chunk_len - 1)
        boundaries.append((cursor, chunk_end))
        cursor = chunk_end + timedelta(days=1)

    windows = []
    for idx, (chunk_start, chunk_end) in enumerate(boundaries):
        if idx < TRAIN_CHUNK_COUNT:
            group = "train"
            label = f"训练块{idx + 1}"
        elif idx < TRAIN_CHUNK_COUNT + VAL_CHUNK_COUNT:
            group = "val"
            label = f"验证块{idx - TRAIN_CHUNK_COUNT + 1}"
        else:
            group = "test"
            label = f"影测块{idx - TRAIN_CHUNK_COUNT - VAL_CHUNK_COUNT + 1}"
        windows.append(
            (
                group,
                f"{label}-{chunk_start.strftime('%Y-%m-%d')}~{chunk_end.strftime('%Y-%m-%d')}",
                chunk_start.strftime("%Y-%m-%d"),
                chunk_end.strftime("%Y-%m-%d"),
            )
        )
    return windows


WINDOWS = _generate_windows()
best_score = -999999.0
best_shadow_test_avg = -999999.0
iteration = 0
plateau_pass_streak = 0
strategy = strategy_module.strategy
backtest_macd_aggressive = backtest_module.backtest_macd_aggressive
latest_eval_summary = ""
latest_public_eval_summary = ""
last_params_snapshot = None
last_exit_snapshot = None
_resolved_discord_channel_id = CHANNEL_ID

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


def _resolve_discord_channel_id():
    global _resolved_discord_channel_id
    if _resolved_discord_channel_id:
        return _resolved_discord_channel_id
    if not DISCORD_TOKEN or not DISCORD_GUILD_ID:
        return ""
    try:
        headers = {"Authorization": f"Bot {DISCORD_TOKEN}"}
        resp = requests.get(
            f"https://discord.com/api/v10/guilds/{DISCORD_GUILD_ID}/channels",
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        channels = resp.json()
        for channel in channels:
            if channel.get("type") == 0 and channel.get("name") == DISCORD_CHANNEL_NAME:
                _resolved_discord_channel_id = channel.get("id", "")
                return _resolved_discord_channel_id
    except Exception:
        return ""
    return ""


def send_discord(msg):
    if not DISCORD_TOKEN:
        return
    channel_id = _resolve_discord_channel_id()
    if not channel_id:
        return
    try:
        headers = {"Authorization": f"Bot {DISCORD_TOKEN}"}
        response = requests.post(
            f"https://discord.com/api/v10/channels/{channel_id}/messages",
            headers=headers,
            json={"content": msg},
            timeout=10,
        )
        response.raise_for_status()
    except Exception:
        logging.exception("Discord 发送失败")


def log_info(message):
    print(message)
    logging.info(message)


def log_exception(message):
    print(message)
    logging.error("%s\n%s", message, traceback.format_exc())


def write_heartbeat(status, **extra):
    HEARTBEAT_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": status,
        "pid": os.getpid(),
        "iteration": iteration,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    payload.update(extra)
    tmp_path = HEARTBEAT_FILE.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    tmp_path.replace(HEARTBEAT_FILE)


def heartbeat_for_log(status, message="", **extra):
    payload = {}
    if message:
        payload["message"] = message
    payload.update(extra)
    write_heartbeat(status, **payload)


def reload_strategy():
    global strategy, backtest_macd_aggressive
    importlib.reload(backtest_module)
    importlib.reload(strategy_module)
    strategy = strategy_module.strategy
    backtest_macd_aggressive = backtest_module.backtest_macd_aggressive


def run_all_tests():
    results = []
    for group, name, start_date, end_date in WINDOWS:
        result = backtest_macd_aggressive(
            strategy_func=strategy,
            intraday_file=INTRADAY_FILE,
            hourly_file=HOURLY_FILE,
            start_date=start_date,
            end_date=end_date,
            strategy_params=strategy_module.PARAMS,
            exit_params=backtest_module.EXIT_PARAMS,
        )
        results.append({"group": group, "name": name, "window": f"{start_date}~{end_date}", "result": result})
    return results


def _score_summary(results):
    train_returns = [item["result"]["return"] for item in results if item["group"] == "train"]
    val_returns = [item["result"]["return"] for item in results if item["group"] == "val"]
    test_returns = [item["result"]["return"] for item in results if item["group"] == "test"]
    train_avg = sum(train_returns) / len(train_returns) if train_returns else 0.0
    val_avg = sum(val_returns) / len(val_returns) if val_returns else 0.0
    test_avg = sum(test_returns) / len(test_returns) if test_returns else 0.0
    train_std = (
        sum((r - train_avg) ** 2 for r in train_returns) / len(train_returns)
    ) ** 0.5 if len(train_returns) > 1 else 0.0
    val_std = (
        sum((r - val_avg) ** 2 for r in val_returns) / len(val_returns)
    ) ** 0.5 if len(val_returns) > 1 else 0.0
    test_std = (
        sum((r - test_avg) ** 2 for r in test_returns) / len(test_returns)
    ) ** 0.5 if len(test_returns) > 1 else 0.0
    worst_val_return = min(val_returns) if val_returns else 0.0
    worst_test_return = min(test_returns) if test_returns else 0.0

    worst_drawdown = max((item["result"]["max_drawdown"] for item in results), default=0.0)
    avg_fee_drag = sum(item["result"].get("fee_drag_pct", 0.0) for item in results) / len(results) if results else 0.0
    liquidations = sum(item["result"].get("liquidations", 0) for item in results)
    total_trades = sum(item["result"]["trades"] for item in results)
    train_trades = sum(item["result"]["trades"] for item in results if item["group"] == "train")
    val_trades = sum(item["result"]["trades"] for item in results if item["group"] == "val")
    test_trades = sum(item["result"]["trades"] for item in results if item["group"] == "test")

    overfit_penalty = max(0.0, train_avg - val_avg) * 0.9
    validation_stability_penalty = val_std * 0.18
    validation_tail_penalty = max(0.0, -worst_val_return) * 0.35
    train_instability_penalty = max(0.0, train_std - max(10.0, val_std + 6.0)) * 0.05

    selection_score = (
        train_avg * 0.35
        + val_avg * 0.65
        - overfit_penalty
        - validation_stability_penalty
        - validation_tail_penalty
        - train_instability_penalty
        - max(0.0, worst_drawdown - AGGRESSIVE_DRAWDOWN_SOFT_CAP) * 0.22
        - liquidations * 1.5
    )
    shadow_gap = val_avg - test_avg
    promotion_score = selection_score - max(0.0, shadow_gap) * 0.15 - max(0.0, -test_avg) * 0.10
    return {
        "train_avg": train_avg,
        "val_avg": val_avg,
        "test_avg": test_avg,
        "train_std": train_std,
        "val_std": val_std,
        "test_std": test_std,
        "worst_val_return": worst_val_return,
        "worst_test_return": worst_test_return,
        "worst_drawdown": worst_drawdown,
        "avg_fee_drag": avg_fee_drag,
        "liquidations": liquidations,
        "total_trades": total_trades,
        "train_trades": train_trades,
        "val_trades": val_trades,
        "test_trades": test_trades,
        "selection_score": selection_score,
        "promotion_score": promotion_score,
        "shadow_gap": shadow_gap,
    }


def build_summary_message(title, results, metrics, include_shadow_test=True):
    total_trades = metrics["total_trades"]
    worst_drawdown = metrics["worst_drawdown"]
    pyramid_adds = sum(item["result"].get("pyramid_add_count", 0) for item in results)
    avg_fee_drag = metrics["avg_fee_drag"]
    lines = [
        f"**{title}**",
        f"",
        f"📊 综合评分",
        f"训练: {metrics['train_avg']:.2f}",
        f"验证: {metrics['val_avg']:.2f}",
        f"选优分: {metrics['selection_score']:.2f}",
    ]
    if include_shadow_test:
        lines.extend(
            [
            f"影子测试: {metrics['test_avg']:.2f}",
            f"晋级分: {metrics['promotion_score']:.2f}",
            ]
        )
    else:
        lines.append("影子测试: 已隔离，不向优化模型暴露最新时间块结果")
    lines.extend(
        [
            f"",
            f"⚙️ 参数配置",
            f"杠杆: {backtest_module.EXIT_PARAMS['leverage']}x",
            f"并发: {backtest_module.EXIT_PARAMS['max_concurrent_positions']}",
            f"首止盈: {backtest_module.EXIT_PARAMS['tp1_pnl_pct']:.0f}%",
            f"",
            f"⚠️ 风险指标",
            f"最大回撤: {worst_drawdown:.1f}%",
            f"总交易: {total_trades}",
        ]
    )
    if include_shadow_test:
        lines.append(f"影测差值(验证-影测): {metrics['shadow_gap']:.2f}")
    lines.extend(
        [
            f"加仓次数: {pyramid_adds}",
            f"手续费: {avg_fee_drag:.2f}%",
            f"",
            f"📈 窗口明细",
        ]
    )
    for item in results:
        if item["group"] == "test" and not include_shadow_test:
            continue
        result = item["result"]
        group_label = {"train": "训", "val": "验", "test": "测"}.get(item["group"], item["group"])
        lines.append(
            f"{item['name']}({group_label})"
        )
        lines.append(
            f"  交易{result['trades']} | "
            f"收益{result['return']:.1f}% | "
            f"回撤{result['max_drawdown']:.1f}%"
        )
    return "\n".join(lines)


def _build_gate_reason(metrics, base_gate_passed, shadow_gate_passed, shadow_regression_passed):
    if base_gate_passed and shadow_gate_passed and shadow_regression_passed:
        return "通过"
    reasons = [
        f"trade={metrics['total_trades']}",
        f"dd={metrics['worst_drawdown']:.2f}",
        f"liq={metrics['liquidations']}",
        f"过拟={metrics['train_avg'] - metrics['val_avg']:.2f}",
        f"验证={metrics['val_avg']:.2f}",
        f"杠杆={backtest_module.EXIT_PARAMS.get('leverage', 0)}",
        f"TP1={backtest_module.EXIT_PARAMS.get('tp1_pnl_pct', 0)}",
    ]
    if not shadow_gate_passed:
        reasons.append("影测=未过")
    if not shadow_regression_passed:
        reasons.append("影测=退化")
    return ", ".join(reasons)


def _memory_summary():
    if not MEMORY_FILE.exists():
        return "暂无历史方向记忆。"
    try:
        payload = json.loads(MEMORY_FILE.read_text())
    except Exception:
        return "历史记忆读取失败。"
    lines = []
    for title, key in [("最近有效方向", "accepted"), ("最近无效方向", "rejected")]:
        items = []
        seen = set()
        for item in reversed(payload.get(key, [])):
            signature = item.get("direction_signature") or item.get("signature") or "|".join(item.get("changes", []))
            if signature in seen:
                continue
            seen.add(signature)
            items.append(item)
            if len(items) >= 4:
                break
        items.reverse()
        if not items:
            continue
        lines.append(title + ":")
        for item in items:
            lines.append(
                f"- overall={item['overall']:.4f}, gate={item['gate']}, changes={'; '.join(item['changes'])}"
            )
    return "\n".join(lines) if lines else "暂无历史方向记忆。"


def _change_signature(changes):
    if not changes:
        return "no_change"
    return "|".join(changes)


def _change_direction_signature(changes):
    if not changes:
        return "no_change"
    directions = []
    for item in changes:
        key, _, delta = item.partition(":")
        old_value, _, new_value = delta.partition("->")
        try:
            old_num = float(old_value)
            new_num = float(new_value)
            direction = "up" if new_num > old_num else "down" if new_num < old_num else "flat"
        except Exception:
            direction = "changed"
        directions.append(f"{key}:{direction}")
    return "|".join(sorted(directions))


def _describe_param_changes(old_strategy_params, new_strategy_params, old_exit_params, new_exit_params):
    changes = []
    for key, old_value in old_strategy_params.items():
        new_value = new_strategy_params.get(key)
        if old_value != new_value:
            changes.append(f"strategy.{key}:{old_value}->{new_value}")
    for key, old_value in old_exit_params.items():
        new_value = new_exit_params.get(key)
        if old_value != new_value:
            changes.append(f"exit.{key}:{old_value}->{new_value}")
    return changes


def _load_memory_payload():
    if not MEMORY_FILE.exists():
        return {"accepted": [], "rejected": []}
    try:
        payload = json.loads(MEMORY_FILE.read_text())
    except Exception:
        return {"accepted": [], "rejected": []}
    payload.setdefault("accepted", [])
    payload.setdefault("rejected", [])
    return payload


def _find_recent_duplicate_direction(changes):
    payload = _load_memory_payload()
    signature = _change_signature(changes)
    direction_signature = _change_direction_signature(changes)
    for bucket in ("accepted", "rejected"):
        for item in reversed(payload.get(bucket, [])[-16:]):
            if item.get("signature") == signature:
                return bucket, "exact", item
            if item.get("direction_signature") == direction_signature:
                return bucket, "direction", item
    return None


def _build_duplicate_guidance(changes, duplicate_match):
    if not changes:
        return (
            "上一版候选没有产生任何参数变化，和当前基底完全一样。"
            "这类候选没有重复探索的价值，请换一个新方向。"
        )
    if duplicate_match is None:
        return ""
    bucket, match_type, item = duplicate_match
    return (
        f"上一版候选命中了最近{bucket}样本的{match_type}重复方向，"
        f"历史 gate={item.get('gate', 'unknown')}。"
        "这个方向已经重复过了，可能没有重复探索的价值。"
        f"重复改动: {'; '.join(changes)}。"
        "请避开同方向改动，换一组不同的局部微调。"
    )


def _current_search_policy():
    boosted = plateau_pass_streak >= PLATEAU_PASS_STREAK_TO_EXPAND
    return {
        "mode": "boosted" if boosted else "default",
        "max_changes": BOOSTED_PARAM_CHANGES_PER_ITERATION if boosted else MAX_PARAM_CHANGES_PER_ITERATION,
        "relative_step": BOOSTED_PARAM_RELATIVE_STEP if boosted else MAX_PARAM_RELATIVE_STEP,
        "plateau_streak": plateau_pass_streak,
    }


def _numeric_step_cap(current_value, relative_step):
    magnitude = abs(float(current_value))
    if isinstance(current_value, int) and not isinstance(current_value, bool):
        return max(1.0, round(max(1.0, magnitude * relative_step)))
    if magnitude >= 1.0:
        return max(0.25, magnitude * relative_step)
    if magnitude >= 0.01:
        return max(0.02, magnitude * relative_step)
    return max(0.00005, magnitude * relative_step)


def _normalize_candidate_value(current_value, proposed_value, relative_step):
    if isinstance(current_value, bool):
        return bool(proposed_value)
    if isinstance(current_value, int) and not isinstance(current_value, bool):
        if not isinstance(proposed_value, (int, float)) or isinstance(proposed_value, bool):
            return current_value
        capped_step = _numeric_step_cap(current_value, relative_step)
        if current_value == 0:
            bounded = float(proposed_value)
        else:
            bounded = min(max(float(proposed_value), current_value - capped_step), current_value + capped_step)
        return int(round(bounded))
    if isinstance(current_value, float):
        if not isinstance(proposed_value, (int, float)) or isinstance(proposed_value, bool):
            return current_value
        capped_step = _numeric_step_cap(current_value, relative_step)
        if current_value == 0.0:
            bounded = float(proposed_value)
        else:
            bounded = min(max(float(proposed_value), current_value - capped_step), current_value + capped_step)
        return round(float(bounded), 10)
    if isinstance(current_value, str):
        return proposed_value if isinstance(proposed_value, str) else current_value
    return proposed_value


def _relative_change_score(old_value, new_value):
    if old_value == new_value:
        return 0.0
    if isinstance(old_value, bool):
        return 1.0
    if isinstance(old_value, (int, float)) and not isinstance(old_value, bool):
        baseline = abs(float(old_value))
        if baseline < 1e-9:
            return abs(float(new_value))
        return abs(float(new_value) - float(old_value)) / baseline
    return 1.0


def _apply_local_search_guardrails(current_params, proposed_params, label, max_changes, relative_step):
    bounded = dict(current_params)
    changed_entries = []

    for key, current_value in current_params.items():
        proposed_value = proposed_params.get(key, current_value)
        normalized_value = _normalize_candidate_value(current_value, proposed_value, relative_step)
        bounded[key] = normalized_value
        if normalized_value != current_value:
            changed_entries.append(
                (
                    key,
                    current_value,
                    normalized_value,
                    _relative_change_score(current_value, normalized_value),
                )
            )

    if len(changed_entries) <= max_changes:
        return bounded

    keep_keys = {
        key
        for key, _, _, _ in sorted(changed_entries, key=lambda item: item[3], reverse=True)[:max_changes]
    }
    trimmed = dict(current_params)
    for key in keep_keys:
        trimmed[key] = bounded[key]

    log_info(
        f"{label} 提案包含 {len(changed_entries)} 项改动，"
        f"已限制为 {max_changes} 项局部微调"
    )
    return trimmed


def _pick_core_params(source_params, allowed_keys):
    return {key: source_params[key] for key in allowed_keys if key in source_params}


def optimize_strategy():
    with open(STRATEGY_FILE, "r") as f:
        current_strategy_code = f.read()
    with open(BACKTEST_FILE, "r") as f:
        current_backtest_code = f.read()
    with open(PROGRAM_FILE, "r") as f:
        instructions = f.read()

    core_strategy_params = _pick_core_params(strategy_module.PARAMS, CORE_STRATEGY_PARAM_KEYS)
    core_exit_params = _pick_core_params(backtest_module.EXIT_PARAMS, CORE_EXIT_PARAM_KEYS)
    search_policy = _current_search_policy()
    if search_policy["mode"] == "boosted":
        log_info(
            "探索增强模式已启用: "
            f"连续 {search_policy['plateau_streak']} 轮通过但未刷新最优，"
            f"本轮允许最多 {search_policy['max_changes']} 项改动，"
            f"单键步长上限 {search_policy['relative_step'] * 100:.0f}%"
        )
    duplicate_guidance = ""
    for candidate_attempt in range(MAX_DUPLICATE_REPLAN_ATTEMPTS + 1):
        prompt = f"""你是激进版 BTC 双向趋势策略参数优化 AI。

{instructions}

当前允许调整的核心策略参数（只允许修改这些键，共 {len(core_strategy_params)} 个）：
{json.dumps(core_strategy_params, ensure_ascii=False, indent=2, sort_keys=True)}

当前允许调整的核心退出参数（只允许修改这些键，共 {len(core_exit_params)} 个）：
{json.dumps(core_exit_params, ensure_ascii=False, indent=2, sort_keys=True)}

最近一轮评估摘要：
{latest_public_eval_summary or latest_eval_summary}

历史方向记忆：
{_memory_summary()}

约束要求：
- 维持激进风格，优先高收益趋势跟随，不要把策略改成保守低波动版本。
- 允许高风险，但目标是把最差回撤压到 {AGGRESSIVE_DRAWDOWN_HARD_CAP:.0f}% 以内，并让验证窗口收益保持为正。
- 杠杆尽量维持在 {AGGRESSIVE_MIN_LEVERAGE}x 以上，首止盈尽量维持在 {AGGRESSIVE_MIN_TP1_PNL_PCT:.0f}% 以上。
- 本轮只允许修改上面列出的 {len(core_strategy_params) + len(core_exit_params)} 个核心参数，其余参数全部保持不变。
- 当前搜索模式: {search_policy['mode']}。
- 每轮只做局部微调，最多改动 {search_policy['max_changes']} 个键，单个数值通常不要偏离当前值的 {search_policy['relative_step'] * 100:.0f}% 以上。
- 如果最近方案大多是回撤过高，就优先收紧止损、缩短持有、降低加仓强度，而不是同时重写所有入场阈值。
{f"- 额外提醒：{duplicate_guidance}" if duplicate_guidance else ""}

请只输出一个完整 JSON 对象：
{{
  "strategy_params": {{...}},
  "exit_params": {{...}}
}}
"""
        payload = generate_json_object(
            prompt=prompt,
            system_prompt=(
                "你是激进版 BTC 双向趋势策略参数优化 AI。"
                "只输出纯JSON，不要markdown代码块，不要任何解释。"
                "必须输出完整的JSON，确保所有括号和引号闭合。"
                "格式：{\"strategy_params\": {...}, \"exit_params\": {...}}"
            ),
            max_output_tokens=1500,
        )

        guarded_strategy_params = _apply_local_search_guardrails(
            core_strategy_params,
            payload["strategy_params"],
            "strategy_params",
            search_policy["max_changes"],
            search_policy["relative_step"],
        )
        guarded_exit_params = _apply_local_search_guardrails(
            core_exit_params,
            payload["exit_params"],
            "exit_params",
            search_policy["max_changes"],
            search_policy["relative_step"],
        )
        new_strategy_params = dict(strategy_module.PARAMS)
        new_strategy_params.update(guarded_strategy_params)
        new_exit_params = dict(backtest_module.EXIT_PARAMS)
        new_exit_params.update(guarded_exit_params)
        changes = _describe_param_changes(
            strategy_module.PARAMS,
            new_strategy_params,
            backtest_module.EXIT_PARAMS,
            new_exit_params,
        )
        duplicate_match = _find_recent_duplicate_direction(changes)
        if changes and duplicate_match is None:
            merged_exit_params = dict(backtest_module.EXIT_PARAMS)
            merged_exit_params.update(new_exit_params)

            params_block = "# PARAMS_START\nPARAMS = " + pprint.pformat(new_strategy_params, sort_dicts=True) + "\n# PARAMS_END"
            exit_block = "# EXIT_PARAMS_START\nEXIT_PARAMS = " + pprint.pformat(merged_exit_params, sort_dicts=True) + "\n# EXIT_PARAMS_END"

            updated_strategy_code = re.sub(
                r"# PARAMS_START\n.*?\n# PARAMS_END",
                params_block,
                current_strategy_code,
                count=1,
                flags=re.S,
            )
            updated_backtest_code = re.sub(
                r"# EXIT_PARAMS_START\n.*?\n# EXIT_PARAMS_END",
                exit_block,
                current_backtest_code,
                count=1,
                flags=re.S,
            )

            compile(updated_strategy_code, STRATEGY_FILE, "exec")
            compile(updated_backtest_code, BACKTEST_FILE, "exec")
            with open(STRATEGY_FILE, "w") as f:
                f.write(updated_strategy_code)
            with open(BACKTEST_FILE, "w") as f:
                f.write(updated_backtest_code)
            return "updated"

        duplicate_guidance = _build_duplicate_guidance(changes, duplicate_match)
        if not duplicate_guidance:
            duplicate_guidance = "上一版候选与当前基底没有有效差异，请换一个新方向。"
        log_info(
            f"候选重规划 #{candidate_attempt + 1}: {duplicate_guidance}"
        )

    log_info("本轮跳过: AI 连续给出重复或无变化参数，未进入回测")
    return "duplicate_skipped"


def _append_memory(bucket, changes, overall, gate):
    memory = _load_memory_payload()
    signature = _change_signature(changes)
    direction_signature = _change_direction_signature(changes)
    entries = memory.setdefault(bucket, [])
    if any(item.get("signature") == signature for item in entries[-8:]):
        return
    entries.append(
        {
            "overall": overall,
            "gate": gate,
            "changes": changes,
            "signature": signature,
            "direction_signature": direction_signature,
        }
    )
    memory[bucket] = memory[bucket][-16:]
    MEMORY_FILE.write_text(json.dumps(memory, ensure_ascii=False, indent=2))


def initialize_best_score():
    global best_score, best_shadow_test_avg, latest_eval_summary, latest_public_eval_summary, last_params_snapshot, last_exit_snapshot
    reload_strategy()
    results = run_all_tests()
    metrics = _score_summary(results)
    best_score = metrics["promotion_score"]
    best_shadow_test_avg = metrics["test_avg"]
    latest_eval_summary = build_summary_message("基准", results, metrics, include_shadow_test=True)
    latest_public_eval_summary = build_summary_message("基准", results, metrics, include_shadow_test=False)
    last_params_snapshot = dict(strategy_module.PARAMS)
    last_exit_snapshot = dict(backtest_module.EXIT_PARAMS)
    log_info(
        "激进版初始基准: "
        f"promotion={metrics['promotion_score']:.4f}, "
        f"selection={metrics['selection_score']:.4f}, "
        f"train={metrics['train_avg']:.4f}, "
        f"val={metrics['val_avg']:.4f}, "
        f"test={metrics['test_avg']:.4f}, "
        f"fee_drag={metrics['avg_fee_drag']:.4f}"
    )
    heartbeat_for_log(
        "initialized",
        "initial baseline ready",
        promotion=metrics["promotion_score"],
        selection=metrics["selection_score"],
        train=metrics["train_avg"],
        val=metrics["val_avg"],
        test=metrics["test_avg"],
        fee_drag=metrics["avg_fee_drag"],
    )
    send_discord(latest_eval_summary)


def run_iteration(iteration_id, use_model_optimization=True):
    global best_score, best_shadow_test_avg, latest_eval_summary, latest_public_eval_summary, last_params_snapshot, last_exit_snapshot, plateau_pass_streak
    shutil.copy(STRATEGY_FILE, BACKUP_FILE)
    shutil.copy(BACKTEST_FILE, BACKTEST_BACKUP_FILE)

    try:
        if use_model_optimization:
            optimization_outcome = optimize_strategy()
            if optimization_outcome == "duplicate_skipped":
                reload_strategy()
                plateau_pass_streak = max(0, plateau_pass_streak - 1)
                heartbeat_for_log("iteration_skipped", f"iteration {iteration_id} duplicate candidate before backtest", iteration=iteration_id)
                return "duplicate_skipped"
        reload_strategy()
        results = run_all_tests()
        metrics = _score_summary(results)
    except StrategyGenerationTransientError as exc:
        shutil.copy(BACKUP_FILE, STRATEGY_FILE)
        shutil.copy(BACKTEST_BACKUP_FILE, BACKTEST_FILE)
        reload_strategy()
        log_info(
            f"⚠️ 激进版第 {iteration_id} 轮跳过: 供应商暂时不可用或响应过慢，"
            f"{PROVIDER_RECOVERY_WAIT_SECONDS} 秒后再试"
        )
        heartbeat_for_log(
            "provider_transient_failure",
            f"iteration {iteration_id} provider transient failure",
            iteration=iteration_id,
            cooldown_seconds=PROVIDER_RECOVERY_WAIT_SECONDS,
            error=str(exc).splitlines()[0],
        )
        return "provider_deferred"
    except Exception as exc:
        shutil.copy(BACKUP_FILE, STRATEGY_FILE)
        shutil.copy(BACKTEST_BACKUP_FILE, BACKTEST_FILE)
        reload_strategy()
        log_exception(f"❌ 激进版第 {iteration_id} 轮失败: {exc}")
        raise

    latest_eval_summary = build_summary_message("最近一轮", results, metrics, include_shadow_test=True)
    latest_public_eval_summary = build_summary_message("最近一轮", results, metrics, include_shadow_test=False)
    current_params_snapshot = dict(strategy_module.PARAMS)
    current_exit_snapshot = dict(backtest_module.EXIT_PARAMS)
    changes = _describe_param_changes(
        last_params_snapshot,
        current_params_snapshot,
        last_exit_snapshot,
        current_exit_snapshot,
    )

    if not changes:
        shutil.copy(BACKUP_FILE, STRATEGY_FILE)
        shutil.copy(BACKTEST_BACKUP_FILE, BACKTEST_FILE)
        reload_strategy()
        log_info(f"第 {iteration_id} 轮跳过: 本轮参数没有变化")
        heartbeat_for_log("iteration_skipped", f"iteration {iteration_id} no-op candidate", iteration=iteration_id)
        return "duplicate_skipped"

    duplicate_match = _find_recent_duplicate_direction(changes)
    if duplicate_match is not None:
        bucket, match_type, item = duplicate_match
        shutil.copy(BACKUP_FILE, STRATEGY_FILE)
        shutil.copy(BACKTEST_BACKUP_FILE, BACKTEST_FILE)
        reload_strategy()
        log_info(
            f"第 {iteration_id} 轮跳过: 命中最近{bucket}的{match_type}重复方向，"
            f"gate={item.get('gate', 'unknown')}"
        )
        heartbeat_for_log(
            "iteration_skipped",
            f"iteration {iteration_id} duplicate {match_type} direction",
            iteration=iteration_id,
            duplicate_bucket=bucket,
            duplicate_gate=item.get("gate", ""),
        )
        return "duplicate_skipped"

    base_gate_passed = (
        metrics["total_trades"] >= 30
        and metrics["train_trades"] >= 15
        and metrics["val_trades"] >= 8
        and metrics["worst_drawdown"] <= AGGRESSIVE_DRAWDOWN_HARD_CAP
        and metrics["liquidations"] <= 10
        and metrics["train_avg"] - metrics["val_avg"] <= AGGRESSIVE_MAX_OVERFIT_GAP
        and metrics["val_avg"] > AGGRESSIVE_MIN_VALIDATION_SCORE
        and backtest_module.EXIT_PARAMS.get('leverage', 0) >= AGGRESSIVE_MIN_LEVERAGE
        and backtest_module.EXIT_PARAMS.get('tp1_pnl_pct', 0) >= AGGRESSIVE_MIN_TP1_PNL_PCT
    )
    shadow_gate_passed = (
        metrics["test_trades"] >= AGGRESSIVE_MIN_SHADOW_TEST_TRADES
        and metrics["test_avg"] >= AGGRESSIVE_MIN_SHADOW_TEST_SCORE
        and metrics["shadow_gap"] <= AGGRESSIVE_MAX_VAL_SHADOW_GAP
    )
    shadow_regression_passed = metrics["test_avg"] >= (best_shadow_test_avg - AGGRESSIVE_MAX_SHADOW_REGRESSION)
    gate_passed = base_gate_passed and shadow_gate_passed and shadow_regression_passed
    gate_reason = _build_gate_reason(metrics, base_gate_passed, shadow_gate_passed, shadow_regression_passed)

    if gate_passed and metrics["promotion_score"] > best_score:
        best_score = metrics["promotion_score"]
        best_shadow_test_avg = metrics["test_avg"]
        plateau_pass_streak = 0
        last_params_snapshot = current_params_snapshot
        last_exit_snapshot = current_exit_snapshot
        _append_memory("accepted", changes, metrics["promotion_score"], gate_reason)
        msg = build_summary_message(f"🚀 新最优激进版策略 #{iteration_id}", results, metrics, include_shadow_test=True)
        log_info(msg)
        heartbeat_for_log(
            "new_best",
            f"iteration {iteration_id} accepted",
            promotion=metrics["promotion_score"],
            selection=metrics["selection_score"],
            test=metrics["test_avg"],
            gate=gate_reason,
        )
        send_discord(msg)
        return "accepted"

    _append_memory("rejected", changes, metrics["promotion_score"], gate_reason)
    plateau_pass_streak = plateau_pass_streak + 1 if gate_passed else 0
    shutil.copy(BACKUP_FILE, STRATEGY_FILE)
    shutil.copy(BACKTEST_BACKUP_FILE, BACKTEST_FILE)
    reload_strategy()
    log_info(f"第 {iteration_id} 轮未保留: {gate_reason}")
    heartbeat_for_log(
        "iteration_rejected",
        f"iteration {iteration_id} rejected",
        promotion=metrics["promotion_score"],
        selection=metrics["selection_score"],
        test=metrics["test_avg"],
        gate=gate_reason,
    )
    return "rejected"


def main():
    global iteration
    once = "--once" in sys.argv
    no_optimize = "--no-optimize" in sys.argv

    log_info("🚀 启动激进版 MACD 研究系统")
    log_info(f"日志文件: {LOG_FILE}")
    log_info(f"循环间隔: {LOOP_INTERVAL_SECONDS} 秒")
    log_info(f"模型调用配置: {describe_client_config()}")
    heartbeat_for_log("starting", "research process booting", loop_interval=LOOP_INTERVAL_SECONDS)
    while True:
        try:
            initialize_best_score()
            break
        except Exception as exc:
            cooldown_seconds = max(LOOP_INTERVAL_SECONDS, FAILURE_COOLDOWN_SECONDS)
            log_exception(f"❌ 激进版初始化失败: {exc}")
            heartbeat_for_log("init_failed", "initialization failed", error=str(exc), cooldown_seconds=cooldown_seconds)
            if once:
                return
            log_info(f"初始化失败，冷却 {cooldown_seconds} 秒后重试")
            time.sleep(cooldown_seconds)
    if once and no_optimize:
        log_info(latest_eval_summary)
        heartbeat_for_log("once_completed", "once mode completed without optimization")
        return

    while True:
        iteration += 1
        log_info(f"\n=== 激进版第 {iteration} 轮 ===")
        heartbeat_for_log("iteration_running", f"iteration {iteration} running", iteration=iteration)
        try:
            iteration_outcome = run_iteration(iteration, use_model_optimization=not no_optimize)
        except Exception:
            cooldown_seconds = max(LOOP_INTERVAL_SECONDS, FAILURE_COOLDOWN_SECONDS)
            log_info(f"本轮失败，冷却 {cooldown_seconds} 秒后重试")
            heartbeat_for_log("iteration_failed", f"iteration {iteration} failed", iteration=iteration, cooldown_seconds=cooldown_seconds)
            if once:
                break
            time.sleep(cooldown_seconds)
            continue

        if once:
            heartbeat_for_log("once_completed", f"once mode completed at iteration {iteration}", iteration=iteration)
            break
        if iteration_outcome == "provider_deferred":
            heartbeat_for_log(
                "provider_recovery_wait",
                f"iteration {iteration} waiting for provider recovery",
                iteration=iteration,
                sleep_seconds=PROVIDER_RECOVERY_WAIT_SECONDS,
            )
            time.sleep(PROVIDER_RECOVERY_WAIT_SECONDS)
            continue
        heartbeat_for_log("sleeping", f"iteration {iteration} sleeping", iteration=iteration, sleep_seconds=LOOP_INTERVAL_SECONDS)
        time.sleep(LOOP_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
