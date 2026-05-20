#!/usr/bin/env python3
"""Market regime diagnostics built from daily equity curves."""

from __future__ import annotations

from typing import Any


REGIME_LABEL_ORDER = (
    "主升浪",
    "快速拉升",
    "可交易震荡上行",
    "修复反弹",
    "普通震荡",
    "高波动乱震",
    "脉冲回落",
    "普通回调",
    "大幅回调",
    "阴跌",
    "过渡",
)

OPPORTUNITY_REGIME_LABELS = frozenset({"主升浪", "可交易震荡上行", "修复反弹", "快速拉升"})
DAMAGE_REGIME_LABELS = frozenset({"普通震荡", "高波动乱震", "脉冲回落", "普通回调", "大幅回调", "阴跌"})

REGIME_LABEL_IDS = {label: float(index + 1) for index, label in enumerate(REGIME_LABEL_ORDER)}
REGIME_ID_LABELS = {int(value): label for label, value in REGIME_LABEL_IDS.items()}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _std(values: list[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    return (sum((value - mean) ** 2 for value in values) / len(values)) ** 0.5


def compound_return_pct(returns: list[float]) -> float:
    growth = 1.0
    for value in returns:
        growth *= max(1e-9, 1.0 + float(value))
    return (growth - 1.0) * 100.0


def regime_label_from_id(value: Any) -> str:
    try:
        return REGIME_ID_LABELS.get(int(round(float(value))), "")
    except (TypeError, ValueError):
        return ""


def _window_features(returns: list[float]) -> dict[str, float]:
    if not returns:
        return {
            "move": 0.0,
            "efficiency": 0.0,
            "realized_vol": 0.0,
            "max_drawdown": 0.0,
            "peak_giveback": 0.0,
            "one_day_positive_share": 0.0,
            "one_day_negative_share": 0.0,
            "path_abs": 0.0,
        }
    price = 1.0
    path = [price]
    for value in returns:
        price *= max(1e-9, 1.0 + float(value))
        path.append(price)
    move = path[-1] - 1.0
    path_abs = sum(abs(float(value)) for value in returns)
    positive_sum = sum(max(float(value), 0.0) for value in returns)
    negative_sum = sum(max(-float(value), 0.0) for value in returns)
    peak = path[0]
    max_drawdown = 0.0
    for value in path:
        peak = max(peak, value)
        if peak > 1e-9:
            max_drawdown = max(max_drawdown, (peak - value) / peak)
    peak_value = max(path)
    peak_giveback = (peak_value - path[-1]) / peak_value if peak_value > 1e-9 else 0.0
    return {
        "move": move,
        "efficiency": abs(move) / path_abs if path_abs > 1e-9 else 0.0,
        "realized_vol": _std([float(value) for value in returns]),
        "max_drawdown": max_drawdown,
        "peak_giveback": peak_giveback,
        "one_day_positive_share": (
            max((max(float(value), 0.0) for value in returns), default=0.0) / positive_sum
            if positive_sum > 1e-9 else 0.0
        ),
        "one_day_negative_share": (
            max((max(-float(value), 0.0) for value in returns), default=0.0) / negative_sum
            if negative_sum > 1e-9 else 0.0
        ),
        "path_abs": path_abs,
    }


def daily_regime_rows_from_result(
    result: dict[str, Any],
    *,
    before_date: str = "",
    on_or_after_date: str = "",
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    curve = result.get("daily_equity_curve", [])
    market_history: list[float] = []
    for idx in range(1, len(curve)):
        prev_point = curve[idx - 1]
        point = curve[idx]
        day = str(point.get("date", "")).strip()
        prev_close = _safe_float(prev_point.get("market_close"))
        current_close = _safe_float(point.get("market_close"))
        prev_equity = _safe_float(prev_point.get("equity"))
        current_equity = _safe_float(point.get("equity"))
        if not day or prev_close <= 1e-9 or prev_equity <= 1e-9:
            continue
        market_return = current_close / prev_close - 1.0
        market_history.append(market_return)
        if before_date and day >= before_date:
            continue
        if on_or_after_date and day < on_or_after_date:
            continue
        features_7 = _window_features(market_history[-7:])
        features_14 = _window_features(market_history[-14:])
        features_28 = _window_features(market_history[-28:])
        fear_greed_value = point.get("fear_greed_value")
        flow_imbalance = _safe_float(point.get("flow_imbalance"))
        rows.append(
            {
                "date": day,
                "strategy_return": current_equity / prev_equity - 1.0,
                "market_return": market_return,
                "trend_move_7": features_7["move"],
                "trend_move": features_14["move"],
                "trend_move_14": features_14["move"],
                "trend_move_28": features_28["move"],
                "realized_vol": features_14["realized_vol"],
                "direction_efficiency_14": features_14["efficiency"],
                "max_drawdown_14": features_14["max_drawdown"],
                "peak_giveback_14": features_14["peak_giveback"],
                "one_day_positive_share_14": features_14["one_day_positive_share"],
                "one_day_negative_share_14": features_14["one_day_negative_share"],
                "path_abs_14": features_14["path_abs"],
                "adx": _safe_float(point.get("adx")),
                "chop": _safe_float(point.get("chop")),
                "atr_ratio": _safe_float(point.get("atr_ratio")),
                "flow_imbalance": flow_imbalance,
                "fear_greed_value": None if fear_greed_value in (None, "") else _safe_float(fear_greed_value),
            }
        )
    return rows


def market_regime_label(row: dict[str, Any]) -> str:
    move_7 = _safe_float(row.get("trend_move_7"))
    move_14 = _safe_float(row.get("trend_move_14", row.get("trend_move")))
    move_28 = _safe_float(row.get("trend_move_28"))
    efficiency = _safe_float(row.get("direction_efficiency_14"))
    realized_vol = _safe_float(row.get("realized_vol"))
    max_drawdown = _safe_float(row.get("max_drawdown_14"))
    peak_giveback = _safe_float(row.get("peak_giveback_14"))
    one_day_positive_share = _safe_float(row.get("one_day_positive_share_14"))
    adx = _safe_float(row.get("adx"))
    chop = _safe_float(row.get("chop"))
    atr_ratio = _safe_float(row.get("atr_ratio"))
    path_abs = _safe_float(row.get("path_abs_14"))
    high_vol = realized_vol >= 0.035 or atr_ratio >= 0.025
    clean_up = move_14 >= 0.05 and adx >= 18.0 and chop < 58.0

    if move_7 <= -0.08 or move_14 <= -0.10:
        return "大幅回调"
    if move_14 <= -0.03:
        if move_28 <= -0.06 and efficiency >= 0.22:
            return "阴跌"
        return "普通回调"

    if move_14 >= 0.03 and peak_giveback > max(0.025, move_14 * 0.65):
        return "脉冲回落"

    if move_7 >= 0.06 and (one_day_positive_share >= 0.50 or high_vol):
        return "快速拉升"

    if (move_14 >= 0.08 or move_28 >= 0.14) and adx >= 22.0 and chop < 58.0 and efficiency >= 0.28:
        return "主升浪"

    if move_14 >= 0.03 and move_28 < 0.0 and efficiency >= 0.22:
        return "修复反弹"

    if 0.03 <= move_14 <= 0.08 and not clean_up:
        if (
            efficiency >= 0.25
            and max_drawdown <= max(0.025, move_14 * 0.75)
            and peak_giveback <= max(0.025, move_14 * 0.65)
            and one_day_positive_share < 0.65
        ):
            return "可交易震荡上行"
        if high_vol or efficiency < 0.20 or one_day_positive_share >= 0.65:
            return "高波动乱震"

    if abs(move_14) < 0.03:
        if high_vol or path_abs >= 0.16 or (chop >= 61.8 and efficiency < 0.20):
            return "高波动乱震"
        return "普通震荡"

    if move_14 > 0.08:
        if efficiency < 0.25 or high_vol:
            return "快速拉升"
        return "主升浪" if adx >= 18.0 and chop < 61.8 else "快速拉升"

    return "过渡"


def _labeled_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    labeled: list[dict[str, Any]] = []
    for row in rows:
        payload = dict(row)
        payload["regime_label"] = market_regime_label(row)
        labeled.append(payload)
    return labeled


def _segment_counts(labeled_rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {label: 0 for label in REGIME_LABEL_ORDER}
    previous_label = ""
    for row in labeled_rows:
        label = str(row.get("regime_label", "")).strip()
        if not label:
            continue
        if label != previous_label:
            counts[label] = counts.get(label, 0) + 1
            previous_label = label
    return counts


def regime_bucket_payload(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    labeled_rows = _labeled_rows(rows)
    segment_counts = _segment_counts(labeled_rows)
    payload: dict[str, dict[str, float]] = {}
    for label in REGIME_LABEL_ORDER:
        bucket_rows = [row for row in labeled_rows if row.get("regime_label") == label]
        strategy_return_pct = compound_return_pct([_safe_float(row.get("strategy_return")) for row in bucket_rows])
        market_return_pct = compound_return_pct([_safe_float(row.get("market_return")) for row in bucket_rows])
        payload[label] = {
            "label_id": REGIME_LABEL_IDS[label],
            "days": float(len(bucket_rows)),
            "segments": float(segment_counts.get(label, 0)),
            "market_return_pct": market_return_pct,
            "strategy_return_pct": strategy_return_pct,
            "gap_pct": strategy_return_pct - market_return_pct,
        }
    return payload


def _select_opportunity_weakness(payload: dict[str, dict[str, float]]) -> tuple[str, dict[str, float]]:
    candidates = [
        (label, bucket)
        for label, bucket in payload.items()
        if label in OPPORTUNITY_REGIME_LABELS
        and bucket["days"] >= 2.0
        and bucket["market_return_pct"] >= 1.0
        and bucket["gap_pct"] < 0.0
    ]
    if not candidates:
        return "", {}
    return min(candidates, key=lambda item: (item[1]["gap_pct"], -item[1]["market_return_pct"]))


def _select_damage_bucket(payload: dict[str, dict[str, float]]) -> tuple[str, dict[str, float]]:
    candidates = [
        (label, bucket)
        for label, bucket in payload.items()
        if label in DAMAGE_REGIME_LABELS
        and bucket["days"] >= 2.0
        and bucket["strategy_return_pct"] < 0.0
    ]
    if not candidates:
        return "", {}
    return min(candidates, key=lambda item: item[1]["strategy_return_pct"])


def regime_diagnostic_payload(rows: list[dict[str, Any]]) -> dict[str, Any]:
    buckets = regime_bucket_payload(rows)
    opportunity_label, opportunity_bucket = _select_opportunity_weakness(buckets)
    damage_label, damage_bucket = _select_damage_bucket(buckets)
    return {
        "buckets": buckets,
        "opportunity_weakness_label": opportunity_label,
        "opportunity_weakness": opportunity_bucket,
        "damage_label": damage_label,
        "damage": damage_bucket,
    }


def _bucket_text(label: str, bucket: dict[str, float]) -> str:
    return (
        f"{label} n={bucket['days']:.0f}/段={bucket['segments']:.0f} "
        f"盘面={bucket['market_return_pct']:.1f}% "
        f"策略={bucket['strategy_return_pct']:.1f}% "
        f"差={bucket['gap_pct']:.1f}%"
    )


def _compact_bucket_list(payload: dict[str, Any], *, max_items: int = 7) -> str:
    buckets = payload.get("buckets", {})
    lines: list[str] = []
    for label in REGIME_LABEL_ORDER:
        bucket = buckets.get(label, {})
        if _safe_float(bucket.get("days")) <= 0.0:
            continue
        lines.append(_bucket_text(label, bucket))
        if len(lines) >= max_items:
            break
    return " | ".join(lines) if lines else "无可用标签"


def _shortfall_text(prefix: str, payload: dict[str, Any]) -> str:
    label = str(payload.get("opportunity_weakness_label", "")).strip()
    if not label:
        return f"{prefix}机会短板=无明显"
    return f"{prefix}机会短板=" + _bucket_text(label, payload["opportunity_weakness"])


def _damage_text(prefix: str, payload: dict[str, Any]) -> str:
    label = str(payload.get("damage_label", "")).strip()
    if not label:
        return f"{prefix}错误参与=无明显"
    return f"{prefix}错误参与=" + _bucket_text(label, payload["damage"])


def regime_summary_lines(train_rows: list[dict[str, Any]], validation_rows: list[dict[str, Any]]) -> list[str]:
    train_payload = regime_diagnostic_payload(train_rows)
    validation_payload = regime_diagnostic_payload(validation_rows)
    return [
        "行情标签表现（诊断，不进主评分；train/val 给 planner，test 只人工看）:",
        "train: " + _compact_bucket_list(train_payload),
        "val: " + _compact_bucket_list(validation_payload),
        _shortfall_text("train", train_payload) + " | " + _shortfall_text("val", validation_payload),
        _damage_text("train", train_payload) + " | " + _damage_text("val", validation_payload),
    ]


def regime_prompt_text(train_rows: list[dict[str, Any]], validation_rows: list[dict[str, Any]]) -> str:
    train_payload = regime_diagnostic_payload(train_rows)
    validation_payload = regime_diagnostic_payload(validation_rows)
    return (
        "行情标签诊断（只解释，不进评分/gate）: "
        + _shortfall_text("train", train_payload)
        + "；"
        + _shortfall_text("val", validation_payload)
        + "；"
        + _damage_text("train", train_payload)
        + "；"
        + _damage_text("val", validation_payload)
    )


def regime_metric_payload(rows: list[dict[str, Any]], *, prefix: str) -> dict[str, float]:
    payload = regime_diagnostic_payload(rows)
    opportunity_label = str(payload.get("opportunity_weakness_label", "")).strip()
    opportunity_bucket = payload.get("opportunity_weakness") or {}
    damage_label = str(payload.get("damage_label", "")).strip()
    damage_bucket = payload.get("damage") or {}
    return {
        f"{prefix}regime_opportunity_weakness_label_id": REGIME_LABEL_IDS.get(opportunity_label, 0.0),
        f"{prefix}regime_opportunity_weakness_days": _safe_float(opportunity_bucket.get("days")),
        f"{prefix}regime_opportunity_weakness_market_return_pct": _safe_float(opportunity_bucket.get("market_return_pct")),
        f"{prefix}regime_opportunity_weakness_strategy_return_pct": _safe_float(opportunity_bucket.get("strategy_return_pct")),
        f"{prefix}regime_opportunity_weakness_gap_pct": _safe_float(opportunity_bucket.get("gap_pct")),
        f"{prefix}regime_damage_label_id": REGIME_LABEL_IDS.get(damage_label, 0.0),
        f"{prefix}regime_damage_days": _safe_float(damage_bucket.get("days")),
        f"{prefix}regime_damage_market_return_pct": _safe_float(damage_bucket.get("market_return_pct")),
        f"{prefix}regime_damage_strategy_return_pct": _safe_float(damage_bucket.get("strategy_return_pct")),
        f"{prefix}regime_damage_gap_pct": _safe_float(damage_bucket.get("gap_pct")),
    }
