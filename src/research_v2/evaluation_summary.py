#!/usr/bin/env python3
"""评估汇总组装辅助。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from research_v2 import evaluation as mod


def _equal_segment_score(report: mod.TrendScoreReport) -> float:
    return mod._equal_segment_score(report)


def _capture_score_from_report(report: mod.TrendScoreReport) -> float:
    return mod._capture_score_from_report(report)


def _weak_label(left_label: str, left_score: float, right_label: str, right_score: float) -> str:
    if abs(float(left_score) - float(right_score)) < 1e-12:
        return "balanced"
    return left_label if float(left_score) < float(right_score) else right_label


def _balance_warning(gap: float, scoring: mod.ScoringConfig) -> str:
    if gap >= float(scoring.capture_balance_gap_full):
        return "严重偏科"
    if gap > float(scoring.capture_balance_gap_tolerance):
        return "偏科"
    return "正常"


def _hit_segment_count(report: mod.TrendScoreReport) -> int:
    return sum(1 for detail in report.segment_details if detail.score >= mod.HIT_SCORE_THRESHOLD)


def _timestamp_to_beijing_date(timestamp_ms: int | None) -> str:
    if timestamp_ms is None:
        return ""
    try:
        timestamp = int(timestamp_ms)
    except (TypeError, ValueError):
        return ""
    dt = datetime.fromtimestamp(timestamp / 1000.0, tz=UTC) + timedelta(hours=8)
    return dt.date().isoformat()


def _validation_start_timestamp(validation_source: dict[str, Any]) -> int | None:
    start_timestamp, _ = mod._result_period_timestamps(validation_source)
    if start_timestamp is not None:
        return start_timestamp
    validation_points = mod._result_trend_capture_points(validation_source)
    if validation_points:
        return int(validation_points[0]["timestamp"])
    return None


def _selection_train_trend_points(
    selection_source: dict[str, Any],
    validation_source: dict[str, Any],
    *,
    selection_points: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    validation_start = _validation_start_timestamp(validation_source)
    if validation_start is None:
        return []
    if selection_points is None:
        selection_points = mod._normalize_trend_points(mod._result_trend_capture_points(selection_source))
    return [
        point
        for point in selection_points
        if int(point.get("timestamp", 0)) < validation_start
    ]


def _selection_train_daily_returns(
    selection_source: dict[str, Any],
    validation_source: dict[str, Any],
) -> list[float]:
    validation_start_date = _timestamp_to_beijing_date(_validation_start_timestamp(validation_source))
    if not validation_start_date:
        return []
    returns: list[float] = []
    for point in selection_source.get("daily_return_points", []):
        day = str(point.get("date", "")).strip()
        if day and day < validation_start_date:
            returns.append(float(point.get("return", 0.0)))
    return returns


def _market_daily_returns_from_equity_curve(
    result: dict[str, Any],
    *,
    before_date: str = "",
    on_or_after_date: str = "",
) -> list[float]:
    returns: list[float] = []
    curve = result.get("daily_equity_curve", [])
    for idx in range(1, len(curve)):
        point = curve[idx]
        day = str(point.get("date", "")).strip()
        if not day:
            continue
        if before_date and day >= before_date:
            continue
        if on_or_after_date and day < on_or_after_date:
            continue
        prev_close = float(curve[idx - 1].get("market_close", 0.0) or 0.0)
        current_close = float(point.get("market_close", 0.0) or 0.0)
        if prev_close <= 1e-9:
            continue
        returns.append(current_close / prev_close - 1.0)
    return returns


def _daily_regime_rows(
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
        prev_close = float(prev_point.get("market_close", 0.0) or 0.0)
        current_close = float(point.get("market_close", 0.0) or 0.0)
        prev_equity = float(prev_point.get("equity", 0.0) or 0.0)
        current_equity = float(point.get("equity", 0.0) or 0.0)
        if not day or prev_close <= 1e-9 or prev_equity <= 1e-9:
            continue
        market_return = current_close / prev_close - 1.0
        market_history.append(market_return)
        if before_date and day >= before_date:
            continue
        if on_or_after_date and day < on_or_after_date:
            continue
        lookback = market_history[-14:]
        lookback_growth = 1.0
        for value in lookback:
            lookback_growth *= max(1e-9, 1.0 + value)
        trend_move = lookback_growth - 1.0
        realized_vol = mod._std(lookback)
        fear_greed_value = point.get("fear_greed_value")
        flow_imbalance = float(point.get("flow_imbalance", 0.0) or 0.0)
        rows.append(
            {
                "date": day,
                "strategy_return": current_equity / prev_equity - 1.0,
                "market_return": market_return,
                "trend_move": trend_move,
                "realized_vol": realized_vol,
                "adx": float(point.get("adx", 0.0) or 0.0),
                "chop": float(point.get("chop", 0.0) or 0.0),
                "atr_ratio": float(point.get("atr_ratio", 0.0) or 0.0),
                "flow_imbalance": flow_imbalance,
                "fear_greed_value": None if fear_greed_value in (None, "") else float(fear_greed_value),
            }
        )
    return rows


def _compound_return_pct(returns: list[float]) -> float:
    growth = 1.0
    for value in returns:
        growth *= max(1e-9, 1.0 + float(value))
    return (growth - 1.0) * 100.0


def _bucket_line(label: str, rows: list[dict[str, Any]]) -> str:
    if not rows:
        return f"{label}: n=0 ret=0.0%"
    return f"{label}: n={len(rows)} ret={_compound_return_pct([row['strategy_return'] for row in rows]):.1f}%"


def _regime_scorecard_lines(train_rows: list[dict[str, Any]], validation_rows: list[dict[str, Any]]) -> list[str]:
    rows = train_rows + validation_rows
    if not rows:
        return ["regime scorecard: 当前结果缺少 daily_equity_curve，无法生成 regime 诊断"]

    def trend_bucket(row: dict[str, Any]) -> str:
        move = float(row.get("trend_move", 0.0))
        adx = float(row.get("adx", 0.0))
        chop = float(row.get("chop", 0.0))
        if move >= 0.05 and adx >= 18.0 and chop < 58.0:
            return "trend_up"
        if move <= -0.05 and adx >= 18.0 and chop < 58.0:
            return "trend_down"
        return "chop"

    def vol_bucket(row: dict[str, Any]) -> str:
        realized_vol = float(row.get("realized_vol", 0.0))
        if realized_vol >= 0.05:
            return "high_vol"
        if realized_vol <= 0.02:
            return "low_vol"
        return "normal_vol"

    def sentiment_bucket(row: dict[str, Any]) -> str:
        value = row.get("fear_greed_value")
        if value is None:
            return "sent_unknown"
        if float(value) <= 35.0:
            return "fear"
        if float(value) >= 70.0:
            return "greed"
        return "neutral_sent"

    def flow_bucket(row: dict[str, Any]) -> str:
        flow = float(row.get("flow_imbalance", 0.0))
        market = float(row.get("market_return", 0.0))
        if abs(flow) < 0.005 or abs(market) < 0.003:
            return "flow_neutral"
        return "flow_with_trend" if flow * market > 0 else "flow_against_trend"

    groups = (
        ("趋势环境", ("trend_up", "trend_down", "chop"), trend_bucket),
        ("波动环境", ("low_vol", "normal_vol", "high_vol"), vol_bucket),
        ("情绪环境", ("fear", "neutral_sent", "greed", "sent_unknown"), sentiment_bucket),
        ("流量方向", ("flow_with_trend", "flow_against_trend", "flow_neutral"), flow_bucket),
    )
    lines: list[str] = []
    for title, labels, classifier in groups:
        parts = [
            _bucket_line(label, [row for row in rows if classifier(row) == label])
            for label in labels
        ]
        lines.append(f"{title}: " + " | ".join(parts))
    return lines


def summarize_evaluation_impl(
    results: list[dict[str, Any]],
    gates: mod.GateConfig,
    selection_period_result: dict[str, Any] | None = None,
    validation_continuous_result: dict[str, Any] | None = None,
    scoring: mod.ScoringConfig | None = None,
    **_kwargs: Any,
) -> mod.EvaluationReport:
    scoring = scoring or mod.ScoringConfig()
    if selection_period_result is None:
        selection_period_result = _kwargs.get("full_period_result")
    eval_results = mod._window_payloads(results, "eval")
    validation_results = mod._window_payloads(results, "validation")
    validation_source = validation_continuous_result
    if validation_source is None and len(validation_results) == 1:
        validation_source = validation_results[0]["result"]
    validation_source = validation_source or {}
    selection_source = selection_period_result or {}

    eval_returns = [float(item["result"].get("return", 0.0)) for item in eval_results]
    validation_returns = [float(item["result"].get("return", 0.0)) for item in validation_results]
    eval_avg_return = mod._mean(eval_returns)
    eval_median_return = mod.median(eval_returns) if eval_returns else 0.0
    eval_p25_return = mod._quantile(eval_returns, 0.25)
    eval_worst_return = min(eval_returns) if eval_returns else 0.0
    validation_avg_return = mod._mean(validation_returns)
    validation_worst_return = min(validation_returns) if validation_returns else 0.0

    worst_drawdown = max((float(item["result"].get("max_drawdown", 0.0)) for item in results), default=0.0)
    avg_fee_drag = mod._mean([float(item["result"].get("fee_drag_pct", 0.0)) for item in results])
    eval_funding_coverage = mod._mean([float(item["result"].get("funding_coverage_ratio", 0.0)) for item in eval_results])
    validation_funding_coverage = float(validation_source.get("funding_coverage_ratio", 0.0))
    selection_funding_coverage = float(selection_source.get("funding_coverage_ratio", 0.0))
    liquidations = sum(int(item["result"].get("liquidations", 0)) for item in results)
    total_trades = sum(int(item["result"].get("trades", 0)) for item in results)
    eval_trades = sum(int(item["result"].get("trades", 0)) for item in eval_results)
    validation_trades = int(
        validation_source.get(
            "trades",
            validation_results[0]["result"].get("trades", 0) if validation_results else 0,
        )
    )

    eval_daily_path = mod._collect_daily_path(results, "eval")
    validation_daily_path = mod._collect_daily_path(results, "validation")
    eval_path = mod._collect_trend_path(results, "eval")
    validation_path = mod._collect_trend_path(results, "validation")
    selection_points = mod._normalize_trend_points(mod._result_trend_capture_points(selection_source))
    selection_train_points = _selection_train_trend_points(
        selection_source,
        validation_source,
        selection_points=selection_points,
    )
    train_capture_source = "selection切分连续train" if selection_train_points else "rolling拼接回退"
    train_score_points = selection_train_points or eval_path.points
    selection_train_daily_returns = _selection_train_daily_returns(selection_source, validation_source)
    train_daily_return_source = "selection切分连续train" if selection_train_daily_returns else "rolling拼接回退"
    train_daily_returns = selection_train_daily_returns or eval_daily_path.returns
    eval_sharpe_ratio = mod._annualized_sharpe(train_daily_returns)
    validation_sharpe_ratio = mod._annualized_sharpe(validation_daily_path.returns)

    development_window_reports = [
        mod._trend_report_from_result(item["result"])
        for item in eval_results
    ]
    development_window_scores = [
        mod._robust_block_report(
            [
                value
                for _, value in mod._result_daily_return_points(item["result"], item["window"].label)
            ],
            scoring,
        ).robust_score
        for item in eval_results
    ]
    development_mean_score = mod._mean(development_window_scores)
    development_median_score = mod.median(development_window_scores) if development_window_scores else 0.0
    development_score_std = mod._std(development_window_scores)
    profitable_window_ratio = mod._safe_ratio(
        sum(1 for score in development_window_scores if score > 0.0),
        len(development_window_scores),
        default=0.0,
    )
    development_mean_trend_score = mod._mean([report.trend_score for report in development_window_reports])
    development_mean_return_score = mod._mean([report.return_score for report in development_window_reports])
    development_mean_hit_rate = mod._mean([report.hit_rate for report in development_window_reports])
    development_mean_segment_count = mod._mean([float(report.segment_count) for report in development_window_reports])

    train_continuous_trend_report = mod._trend_score_report(train_score_points)
    validation_trend_report = (
        mod._trend_score_report(validation_path.points)
        if validation_path.points
        else mod._trend_report_from_result(validation_source)
    )
    selection_trend_report = mod._trend_score_report(selection_points)

    train_capture_equal_score = _equal_segment_score(train_continuous_trend_report)
    validation_capture_equal_score = _equal_segment_score(validation_trend_report)
    train_capture_weighted_score = train_continuous_trend_report.trend_score
    validation_capture_weighted_score = validation_trend_report.trend_score
    train_capture_score = _capture_score_from_report(train_continuous_trend_report)
    validation_capture_score = _capture_score_from_report(validation_trend_report)
    capture_score = (
        mod.TRAIN_VAL_SCORE_WEIGHT * train_capture_score
        + mod.TRAIN_VAL_SCORE_WEIGHT * validation_capture_score
    )
    capture_core_payload = mod._capture_core_score(
        train_capture_score,
        validation_capture_score,
        selection_trend_report.bull_score,
        selection_trend_report.bear_score,
        scoring,
    )
    capture_core_score = capture_core_payload["capture_core_score"]
    train_timed_return_score = mod._annualized_return_score(train_daily_returns)
    validation_timed_return_score = mod._annualized_return_score(validation_daily_path.returns)
    timed_return_score = (
        mod.TRAIN_VAL_SCORE_WEIGHT * train_timed_return_score
        + mod.TRAIN_VAL_SCORE_WEIGHT * validation_timed_return_score
    )
    validation_start_date = _timestamp_to_beijing_date(_validation_start_timestamp(validation_source))
    train_market_daily_returns = _market_daily_returns_from_equity_curve(
        selection_source,
        before_date=validation_start_date,
    )
    validation_market_daily_returns = _market_daily_returns_from_equity_curve(validation_source)
    train_robust_block_report = mod._robust_block_report(train_daily_returns, scoring)
    validation_robust_block_report = mod._robust_block_report(validation_daily_path.returns, scoring)
    train_benchmark_block_report = mod._robust_block_report(train_market_daily_returns, scoring)
    validation_benchmark_block_report = mod._robust_block_report(validation_market_daily_returns, scoring)
    validation_long_trades, validation_short_trades = mod._trade_side_counts(validation_source)
    selection_long_trades, selection_short_trades = mod._trade_side_counts(selection_source)
    validation_long_entries, validation_short_entries = mod._entry_side_counts(validation_source)
    selection_long_entries, selection_short_entries = mod._entry_side_counts(selection_source)
    validation_closed_trades = int(validation_source.get("trades", validation_long_trades + validation_short_trades))
    selection_closed_trades = int(selection_source.get("trades", selection_long_trades + selection_short_trades))
    train_closed_trades = max(0, selection_closed_trades - validation_closed_trades)
    validation_entry_trades = validation_long_entries + validation_short_entries
    selection_entry_trades = selection_long_entries + selection_short_entries
    train_entry_trades = max(0, selection_entry_trades - validation_entry_trades)
    selection_start_ts, _selection_end_ts = mod._result_period_timestamps(selection_source)
    validation_start_ts, validation_end_ts = mod._result_period_timestamps(validation_source)
    train_months = mod._period_months_from_timestamps(selection_start_ts, validation_start_ts)
    validation_months = mod._period_months_from_timestamps(validation_start_ts, validation_end_ts)
    train_monthly_entries = mod._monthly_trade_rate(train_entry_trades, train_months)
    validation_monthly_entries = mod._monthly_trade_rate(validation_entry_trades, validation_months)
    train_activity_multiplier = mod._activity_multiplier_from_monthly_entries(train_monthly_entries, scoring)
    validation_activity_multiplier = mod._activity_multiplier_from_monthly_entries(validation_monthly_entries, scoring)
    activity_multiplier = (
        mod.TRAIN_VAL_SCORE_WEIGHT * train_activity_multiplier
        + mod.TRAIN_VAL_SCORE_WEIGHT * validation_activity_multiplier
    )
    train_activity_adjusted_robust_block_score = (
        min(train_robust_block_report.robust_score, 0.0)
        + max(train_robust_block_report.robust_score, 0.0) * train_activity_multiplier
    )
    validation_activity_adjusted_robust_block_score = (
        min(validation_robust_block_report.robust_score, 0.0)
        + max(validation_robust_block_report.robust_score, 0.0) * validation_activity_multiplier
    )
    raw_robust_time_score = (
        mod.TRAIN_VAL_SCORE_WEIGHT * train_robust_block_report.robust_score
        + mod.TRAIN_VAL_SCORE_WEIGHT * validation_robust_block_report.robust_score
    )
    robust_time_score = (
        mod.TRAIN_VAL_SCORE_WEIGHT * train_activity_adjusted_robust_block_score
        + mod.TRAIN_VAL_SCORE_WEIGHT * validation_activity_adjusted_robust_block_score
    )
    buy_hold_robust_score = (
        mod.TRAIN_VAL_SCORE_WEIGHT * train_benchmark_block_report.robust_score
        + mod.TRAIN_VAL_SCORE_WEIGHT * validation_benchmark_block_report.robust_score
    )
    benchmark_hurdle = max(0.0, buy_hold_robust_score) * max(0.0, float(scoring.benchmark_hurdle_weight))
    main_score = robust_time_score - benchmark_hurdle
    train_drawdown_risk_report = mod._drawdown_risk_side_report(train_daily_returns, scoring)
    validation_drawdown_risk_report = mod._drawdown_risk_side_report(validation_daily_path.returns, scoring)
    train_drawdown_risk_score = train_drawdown_risk_report.risk_score
    validation_drawdown_risk_score = validation_drawdown_risk_report.risk_score
    drawdown_risk_score = (
        mod.TRAIN_VAL_SCORE_WEIGHT * train_drawdown_risk_score
        + mod.TRAIN_VAL_SCORE_WEIGHT * validation_drawdown_risk_score
    )
    drawdown_penalty_score = mod._promotion_drawdown_penalty(drawdown_risk_score, scoring)
    train_turn_protection_score = train_continuous_trend_report.turn_protection_score
    validation_turn_protection_score = validation_trend_report.turn_protection_score
    turn_protection_score = (
        mod.TRAIN_VAL_SCORE_WEIGHT * train_turn_protection_score
        + mod.TRAIN_VAL_SCORE_WEIGHT * validation_turn_protection_score
    )
    quality_score = train_activity_adjusted_robust_block_score
    raw_validation_score = mod._period_score(validation_trend_report)
    validation_block_report = mod._validation_block_report(
        validation_source,
        block_count=gates.validation_block_count,
        fallback_score=raw_validation_score,
    )
    capture_drop = train_capture_score - validation_capture_score
    promotion_gap = train_robust_block_report.robust_score - validation_robust_block_report.robust_score
    overfit_report = mod._overfit_risk_report(selection_trend_report, capture_drop)
    robustness_penalty_payload = mod._robustness_penalty_payload(
        train_window_scores=list(train_robust_block_report.block_scores),
        validation_block_scores=list(validation_robust_block_report.block_scores),
        train_ulcer_pct=train_drawdown_risk_report.blended_ulcer_pct,
        validation_ulcer_pct=validation_drawdown_risk_report.blended_ulcer_pct,
        scoring=scoring,
    )
    robustness_penalty_score = robustness_penalty_payload["robustness_penalty_score"]
    selection_entry_timestamps = mod._trade_entry_timestamps(selection_source)
    validation_entry_timestamps = mod._trade_entry_timestamps(validation_source)
    train_max_trade_idle_days = (
        mod._max_trade_idle_days_from_timestamps(
            selection_entry_timestamps,
            start_timestamp=selection_start_ts,
            end_timestamp=validation_start_ts,
        )
        if "trades_detail" in selection_source
        else 0.0
    )
    validation_max_trade_idle_days = (
        mod._max_trade_idle_days_from_timestamps(
            validation_entry_timestamps,
            start_timestamp=validation_start_ts,
            end_timestamp=validation_end_ts,
        )
        if "trades_detail" in validation_source
        else 0.0
    )
    train_trade_idle_shortfall = mod._trade_idle_shortfall(
        train_max_trade_idle_days,
        scoring.max_trade_idle_days,
    )
    validation_trade_idle_shortfall = mod._trade_idle_shortfall(
        validation_max_trade_idle_days,
        scoring.max_trade_idle_days,
    )
    trade_idle_shortfall = (
        mod.TRAIN_VAL_SCORE_WEIGHT * train_trade_idle_shortfall
        + mod.TRAIN_VAL_SCORE_WEIGHT * validation_trade_idle_shortfall
    )
    _trend_participation_penalty, train_trend_participation_shortfall, validation_trend_participation_shortfall = (
        mod._trend_participation_penalty(
            train_continuous_trend_report.hit_rate,
            validation_trend_report.hit_rate,
            scoring,
        )
    )
    trade_idle_penalty = scoring.trade_idle_penalty_weight * trade_idle_shortfall
    trend_participation_penalty = 0.0
    promotion_score = main_score - drawdown_penalty_score - robustness_penalty_score - trade_idle_penalty
    promotion_main_contribution = main_score
    promotion_penalty_total = drawdown_penalty_score + robustness_penalty_score + trade_idle_penalty
    eval_funnel_counts = mod._aggregate_funnel_counts(results, "eval")
    validation_funnel_counts = mod._result_funnel_counts(validation_source)
    selection_funnel_counts = mod._result_funnel_counts(selection_source)
    low_activity_payload = mod._low_activity_signal_payload(
        validation_counts=validation_funnel_counts,
        selection_counts=selection_funnel_counts,
        validation_closed_trades=validation_closed_trades,
        selection_closed_trades=selection_closed_trades,
        min_validation_closed_trades=gates.min_validation_closed_trades,
    )
    validation_weakest_axis = mod._validation_weakest_axis(validation_trend_report, validation_block_report)
    selection_total_return = float(selection_source.get("return", 0.0))
    selection_max_drawdown = float(selection_source.get("max_drawdown", 0.0))
    selection_fee_drag_pct = float(selection_source.get("fee_drag_pct", 0.0))
    selection_sharpe_ratio = mod._annualized_sharpe([float(value) for value in selection_source.get("daily_returns", [])])

    gate_reasons: list[str] = []
    if liquidations > 0:
        gate_reasons.append(f"出现爆仓({liquidations})")
    if avg_fee_drag > gates.max_fee_drag_pct:
        gate_reasons.append(f"手续费拖累过高({avg_fee_drag:.2f}%)")
    if overfit_report.hard_fail:
        gate_reasons.append(
            "train+val过拟合集中度严重"
            f"({'; '.join(overfit_report.hard_reasons)})"
        )

    gate_passed = not gate_reasons
    gate_reason = "通过" if gate_passed else "；".join(gate_reasons)
    weak_period_label = _weak_label("train", train_capture_score, "val", validation_capture_score)
    weak_side_label = _weak_label(
        "bull",
        selection_trend_report.bull_score,
        "bear",
        selection_trend_report.bear_score,
    )
    period_balance_warning = _balance_warning(capture_core_payload["train_validation_capture_gap"], scoring)
    side_balance_warning = _balance_warning(capture_core_payload["bull_bear_capture_gap"], scoring)
    train_regime_rows = _daily_regime_rows(selection_source, before_date=validation_start_date)
    validation_regime_rows = _daily_regime_rows(validation_source)
    regime_scorecard_lines = _regime_scorecard_lines(train_regime_rows, validation_regime_rows)

    weakest_signals = mod._aggregate_signal_stats(results, "eval")
    weakest_signal_paths = mod._aggregate_signal_stats(results, "eval", stats_key="signal_path_stats")
    summary_lines = [
        "研究评估摘要（15m 为唯一事实源，1h/4h 只是由 15m 聚合的确认层；成交量只读展示总量，方向确认主要看 OKX K 线方向流量代理）",
        (
            "train walk-forward robust分(均值/中位/std/盈利窗比): "
            f"{development_mean_score:.2f} / {development_median_score:.2f} / "
            f"{development_score_std:.2f} / {profitable_window_ratio:.0%}"
        ),
        (
            "v26稳健时间块分(train/val原始 -> 活跃度调整 / 合成) / buy&hold稳健分 / 基准扣分 / 主分: "
            f"{train_robust_block_report.robust_score:.2f} / "
            f"{validation_robust_block_report.robust_score:.2f} / "
            f"{train_activity_adjusted_robust_block_score:.2f} / "
            f"{validation_activity_adjusted_robust_block_score:.2f} / "
            f"{robust_time_score:.2f} / {buy_hold_robust_score:.2f} / "
            f"{benchmark_hurdle:.2f} / {main_score:.2f}"
        ),
        (
            "v26时间块明细(train均值/中位/P25/最差/n | val均值/中位/P25/最差/n): "
            f"{train_robust_block_report.mean_score:.2f}/"
            f"{train_robust_block_report.median_score:.2f}/"
            f"{train_robust_block_report.p25_score:.2f}/"
            f"{train_robust_block_report.min_score:.2f}/"
            f"{train_robust_block_report.block_count} | "
            f"{validation_robust_block_report.mean_score:.2f}/"
            f"{validation_robust_block_report.median_score:.2f}/"
            f"{validation_robust_block_report.p25_score:.2f}/"
            f"{validation_robust_block_report.min_score:.2f}/"
            f"{validation_robust_block_report.block_count}"
        ),
        "regime scorecard（诊断，不进主评分）:",
        *regime_scorecard_lines,
        (
            "capture诊断(train/val clean混合分 / 平均抓取 / capture_core，不进主评分): "
            f"{train_capture_score:.2f} / {validation_capture_score:.2f} / "
            f"{capture_score:.2f} / {capture_core_score:.2f}"
        ),
        (
            "capture balance(period/side): "
            f"period={capture_core_payload['period_capture_score']:.2f}, "
            f"side={capture_core_payload['side_capture_score']:.2f}, "
            f"side_mult={capture_core_payload['side_capture_multiplier']:.2f}, "
            f"gap={capture_core_payload['train_validation_capture_gap']:.2f}/"
            f"{capture_core_payload['bull_bear_capture_gap']:.2f}, "
            f"weak={weak_period_label}/{weak_side_label}, "
            f"warning={period_balance_warning}/{side_balance_warning}"
        ),
        (
            "train/val段等权抓取 / 原权重抓取: "
            f"{train_capture_equal_score:.2f}/{validation_capture_equal_score:.2f} / "
            f"{train_capture_weighted_score:.2f}/{validation_capture_weighted_score:.2f}"
        ),
        (
            "train/val趋势段(总/多/空/命中): "
            f"{train_continuous_trend_report.segment_count}/"
            f"{train_continuous_trend_report.bull_segment_count}/"
            f"{train_continuous_trend_report.bear_segment_count}/"
            f"{_hit_segment_count(train_continuous_trend_report)} | "
            f"{validation_trend_report.segment_count}/"
            f"{validation_trend_report.bull_segment_count}/"
            f"{validation_trend_report.bear_segment_count}/"
            f"{_hit_segment_count(validation_trend_report)}"
        ),
        f"主评分数据源: v26时间块={train_daily_return_source}；capture仅诊断={train_capture_source}",
        (
            "train/val按日收益年化分 / v26主分 / 固定窗口回撤风险分 / 回撤罚分 / 晋级分: "
            f"{train_timed_return_score:.2f} / {validation_timed_return_score:.2f} / "
            f"{main_score:.2f} / "
            f"{drawdown_risk_score:.2f} / {drawdown_penalty_score:.2f} / {promotion_score:.2f}"
        ),
        (
            "交易量倍率(月频train/val -> 倍率train/val/合成): "
            f"{train_monthly_entries:.2f} / {validation_monthly_entries:.2f} -> "
            f"{train_activity_multiplier:.2f} / {validation_activity_multiplier:.2f} / "
            f"{activity_multiplier:.2f}"
        ),
        (
            "最长无新开仓天数(train/val/上限) / 空窗短缺率 / 空窗惩罚: "
            f"{train_max_trade_idle_days:.1f} / {validation_max_trade_idle_days:.1f} / "
            f"{scoring.max_trade_idle_days:.1f} | "
            f"{train_trade_idle_shortfall:.2f} / {validation_trade_idle_shortfall:.2f} / "
            f"{trade_idle_penalty:.2f}"
        ),
        (
            "趋势机会覆盖短缺率(train/val，诊断不扣分) / 空窗惩罚: "
            f"{train_trend_participation_shortfall:.2f} / {validation_trend_participation_shortfall:.2f} / "
            f"{trade_idle_penalty:.2f}"
        ),
        f"train/val月非加仓开仓频率: {train_monthly_entries:.2f} / {validation_monthly_entries:.2f}",
        (
            "train/val回撤风险分(窗口数): "
            f"{train_drawdown_risk_score:.2f}({train_drawdown_risk_report.window_count}) / "
            f"{validation_drawdown_risk_score:.2f}({validation_drawdown_risk_report.window_count})"
        ),
        (
            "回撤罚分公式(base / knee / excess): "
            f"{scoring.promotion_drawdown_base_weight:.2f} / "
            f"{scoring.promotion_drawdown_knee:.2f} / "
            f"{scoring.promotion_drawdown_excess_weight:.2f}"
        ),
        (
            "train/val窗口 Ulcer 中位 / P75: "
            f"{train_drawdown_risk_report.median_ulcer_pct:.2f}/{train_drawdown_risk_report.tail_ulcer_pct:.2f} / "
            f"{validation_drawdown_risk_report.median_ulcer_pct:.2f}/{validation_drawdown_risk_report.tail_ulcer_pct:.2f}"
        ),
        f"val到来 / 陪跑 / 掉头: {validation_trend_report.arrival_score:.2f} / {validation_trend_report.escort_score:.2f} / {validation_trend_report.turn_score:.2f}",
        (
            "train/val掉头保护分(事件数): "
            f"{train_turn_protection_score:.2f}({train_continuous_trend_report.turn_protection_event_count}) / "
            f"{validation_turn_protection_score:.2f}({validation_trend_report.turn_protection_event_count})"
        ),
        f"val多头 / 空头捕获: {validation_trend_report.bull_score:.2f} / {validation_trend_report.bear_score:.2f}",
        f"val趋势段 / 命中率: {validation_trend_report.segment_count} / {validation_trend_report.hit_rate:.0%}",
        f"val连续综合分 / 收益分: {raw_validation_score:.2f} / {validation_trend_report.return_score:.2f}",
        f"val多 / 空平仓数: {validation_long_trades} / {validation_short_trades}",
        f"val多 / 空非加仓开仓数: {validation_long_entries} / {validation_short_entries}",
        mod._format_funnel_line("train滚动漏斗(long)", eval_funnel_counts["long"]),
        mod._format_funnel_line("train滚动漏斗(short)", eval_funnel_counts["short"]),
        mod._format_funnel_line("val连续漏斗(long)", validation_funnel_counts["long"]),
        mod._format_funnel_line("val连续漏斗(short)", validation_funnel_counts["short"]),
        f"val短板: {validation_weakest_axis}",
        (
            "val趋势分块诊断(均值/std/最差/尾块/负分块，不做硬gate): "
            f"{validation_block_report.mean_score:.2f} / "
            f"{validation_block_report.std_score:.2f} / "
            f"{validation_block_report.min_score:.2f} / "
            f"{validation_block_report.tail_score:.2f} / "
            f"{validation_block_report.fail_count}"
            + (
                f" (分块数={validation_block_report.used_block_count})"
                if validation_block_report.used_block_count > 0 else " (未启用)"
            )
        ),
        (
            "鲁棒性软惩罚(center/spread/envelope/ulcer/raw/cap后): "
            f"{robustness_penalty_payload['score_center_penalty_score']:.2f} / "
            f"{robustness_penalty_payload['score_spread_penalty_score']:.2f} / "
            f"{robustness_penalty_payload['score_envelope_penalty_score']:.2f} / "
            f"{robustness_penalty_payload['ulcer_ratio_penalty_score']:.2f} / "
            f"{robustness_penalty_payload['robustness_penalty_score_raw']:.2f} / "
            f"{robustness_penalty_score:.2f}"
        ),
        (
            "鲁棒性分布诊断(train中位/IQR/std, val中位/std, 中位差IQR倍数/波动比/包络溢出IQR倍数/Ulcer比): "
            f"{robustness_penalty_payload['robustness_train_score_median']:.2f} / "
            f"{robustness_penalty_payload['robustness_train_score_iqr']:.2f} / "
            f"{robustness_penalty_payload['robustness_train_score_std']:.2f} | "
            f"{robustness_penalty_payload['robustness_validation_score_median']:.2f} / "
            f"{robustness_penalty_payload['robustness_validation_score_std']:.2f} | "
            f"{robustness_penalty_payload['robustness_score_center_gap_units']:.2f} / "
            f"{robustness_penalty_payload['robustness_score_spread_ratio']:.2f} / "
            f"{robustness_penalty_payload['robustness_score_envelope_overflow_units']:.2f} / "
            f"{robustness_penalty_payload['robustness_ulcer_ratio']:.2f}"
        ),
        (
            "train+val集中度诊断: "
            f"{overfit_report.risk_level}({overfit_report.risk_score:.0f})，"
            f"单段正向贡献={overfit_report.top1_positive_share:.0%}，"
            f"同向链贡献={overfit_report.max_chain_positive_share:.0%}，"
            f"覆盖率={overfit_report.coverage_ratio:.0%}，"
            f"多空落差={overfit_report.bull_bear_gap:.2f}，"
            f"处置={mod.overfit_reference_action(overfit_report.risk_score, overfit_report.hard_fail)}"
        ),
        f"train+val连续趋势捕获分 / 收益分: {selection_trend_report.trend_score:.2f} / {selection_trend_report.return_score:.2f}",
        f"train+val连续到来 / 陪跑 / 掉头: {selection_trend_report.arrival_score:.2f} / {selection_trend_report.escort_score:.2f} / {selection_trend_report.turn_score:.2f}",
        f"train+val连续多头 / 空头捕获: {selection_trend_report.bull_score:.2f} / {selection_trend_report.bear_score:.2f}",
        f"train+val期间收益 / 路径收益: {selection_total_return:.2f}% / {selection_trend_report.path_return_pct:.2f}%",
        f"Sharpe(train / val / train+val): {eval_sharpe_ratio:.2f} / {validation_sharpe_ratio:.2f} / {selection_sharpe_ratio:.2f}",
        f"train窗口收益均值 / 中位 / P25 / 最差: {eval_avg_return:.2f}% / {eval_median_return:.2f}% / {eval_p25_return:.2f}% / {eval_worst_return:.2f}%",
        f"val窗口收益均值 / 最差: {validation_avg_return:.2f}% / {validation_worst_return:.2f}%",
        f"train/val稳健时间块落差: {promotion_gap:.2f}",
        f"train 4h唯一路径点 / 重叠点 / 被覆盖点: {eval_path.unique_points} / {eval_path.overlap_points} / {eval_path.dropped_points}",
        f"funding覆盖(train均值 / val / train+val): {eval_funding_coverage:.0%} / {validation_funding_coverage:.0%} / {selection_funding_coverage:.0%}",
        f"最大回撤 / 手续费拖累: {worst_drawdown:.2f}% / {avg_fee_drag:.2f}%",
        (
            "train+val非加仓开仓 / train非加仓开仓 / val非加仓开仓 / "
            f"平仓(train+val/train/val) / 爆仓: {selection_entry_trades} / "
            f"{train_entry_trades} / {validation_entry_trades} / "
            f"{selection_closed_trades}/{train_closed_trades}/{validation_closed_trades} / {liquidations}"
        ),
        f"质量分(train活跃度调整时间块分) / 晋级分: {quality_score:.2f} / {promotion_score:.2f}",
        f"Gate: {gate_reason}",
        "",
        "窗口明细:",
        *mod._build_window_lines(results, include_validation=True),
    ]
    if low_activity_payload["lines"]:
        summary_lines.extend(["", *low_activity_payload["lines"]])
    if weakest_signals:
        summary_lines.extend(["", "拖累较大的执行标签:", *weakest_signals])
    if weakest_signal_paths:
        summary_lines.extend(["", "拖累较大的路径标签:", *weakest_signal_paths])

    prompt_lines = [
        "当前诊断（必须先读）:",
        (
            f"- 当前基底: 质量分(train活跃度调整时间块分)={quality_score:.2f}，晋级分={promotion_score:.2f}，"
            f"v26主分={main_score:.2f}，时间块稳健分原始(train/val)="
            f"{train_robust_block_report.robust_score:.2f}/{validation_robust_block_report.robust_score:.2f}，"
            f"活跃度调整后={train_activity_adjusted_robust_block_score:.2f}/"
            f"{validation_activity_adjusted_robust_block_score:.2f}，"
            f"buy&hold基准扣分={benchmark_hurdle:.2f}，capture诊断={capture_score:.2f}/{capture_core_score:.2f}，"
            f"回撤风险分={drawdown_risk_score:.2f}，回撤罚分={drawdown_penalty_score:.2f}，"
            f"鲁棒性软惩罚={robustness_penalty_score:.2f}，"
            f"gate={gate_reason}"
        ),
        f"- 当前主短板: {validation_weakest_axis}",
        f"- 当前 gate 主失败项: {gate_reason}",
        (
            f"- val 现状: 趋势段/命中率={validation_trend_report.segment_count}/"
            f"{validation_trend_report.hit_rate:.0%}，"
            f"多头/空头捕获={validation_trend_report.bull_score:.2f}/"
            f"{validation_trend_report.bear_score:.2f}，"
            f"多/空平仓数={validation_long_trades}/{validation_short_trades}"
        ),
        (
            "- val 漏斗堵点: "
            + mod._funnel_choke_point_text("long", validation_funnel_counts["long"])
            + "；"
            + mod._funnel_choke_point_text("short", validation_funnel_counts["short"])
        ),
        (
            f"- train walk-forward robust状态: 均值/中位/std/盈利窗比="
            f"{development_mean_score:.2f}/{development_median_score:.2f}/"
            f"{development_score_std:.2f}/{profitable_window_ratio:.0%}"
        ),
        "- regime scorecard（诊断，不进主评分）: " + " | ".join(regime_scorecard_lines),
        (
            f"- promotion breakdown: v26主分={main_score:.2f} "
            f"(原始稳健时间块={raw_robust_time_score:.2f}, 活跃度调整后={robust_time_score:.2f}, "
            f"buy&hold稳健={buy_hold_robust_score:.2f}, "
            f"基准扣分={benchmark_hurdle:.2f})，"
            f"回撤扣分={drawdown_penalty_score:.2f}，鲁棒性扣分={robustness_penalty_score:.2f}，"
            f"空窗扣分={trade_idle_penalty:.2f}，最终promotion={promotion_score:.2f}"
        ),
        (
            f"- activity diagnostic: train/val非加仓开仓={train_entry_trades}/{validation_entry_trades}，"
            f"月频={train_monthly_entries:.2f}/{validation_monthly_entries:.2f}，"
            f"倍率={train_activity_multiplier:.2f}/{validation_activity_multiplier:.2f}，"
            f"最长无新开仓={train_max_trade_idle_days:.1f}/{validation_max_trade_idle_days:.1f}天，"
            f"趋势机会覆盖短缺={train_trend_participation_shortfall:.2f}/"
            f"{validation_trend_participation_shortfall:.2f}"
        ),
        (
            f"- risk diagnostic: train/val固定窗口回撤风险={train_drawdown_risk_score:.2f}/"
            f"{validation_drawdown_risk_score:.2f}，回撤扣分={drawdown_penalty_score:.2f}，"
            f"鲁棒性软惩罚={robustness_penalty_score:.2f}"
        ),
        (
            f"- 当前评分组成: train/val稳健时间块原始={train_robust_block_report.robust_score:.2f}/"
            f"{validation_robust_block_report.robust_score:.2f}，"
            f"活跃度调整后={train_activity_adjusted_robust_block_score:.2f}/"
            f"{validation_activity_adjusted_robust_block_score:.2f}，"
            f"块数={train_robust_block_report.block_count}/{validation_robust_block_report.block_count}，"
            f"capture仅诊断={train_capture_score:.2f}/{validation_capture_score:.2f}，"
            f"趋势段(train总/多/空/命中)="
            f"{train_continuous_trend_report.segment_count}/"
            f"{train_continuous_trend_report.bull_segment_count}/"
            f"{train_continuous_trend_report.bear_segment_count}/"
            f"{_hit_segment_count(train_continuous_trend_report)}，"
            f"趋势段(val总/多/空/命中)="
            f"{validation_trend_report.segment_count}/"
            f"{validation_trend_report.bull_segment_count}/"
            f"{validation_trend_report.bear_segment_count}/"
            f"{_hit_segment_count(validation_trend_report)}，"
            f"train/val 按日收益年化分={train_timed_return_score:.2f}/{validation_timed_return_score:.2f}，"
            f"train/val 非加仓开仓={train_entry_trades}/{validation_entry_trades}，"
            f"月频={train_monthly_entries:.2f}/{validation_monthly_entries:.2f}，"
            f"交易量倍率={train_activity_multiplier:.2f}/{validation_activity_multiplier:.2f}，"
            f"最长无新开仓={train_max_trade_idle_days:.1f}/{validation_max_trade_idle_days:.1f}天，"
            f"趋势机会覆盖短缺={train_trend_participation_shortfall:.2f}/{validation_trend_participation_shortfall:.2f}，"
            f"空窗惩罚={trade_idle_penalty:.2f}，"
            f"train/val 固定窗口回撤风险分={train_drawdown_risk_score:.2f}/{validation_drawdown_risk_score:.2f}，"
            f"回撤罚分={drawdown_penalty_score:.2f}，鲁棒性软惩罚={robustness_penalty_score:.2f}"
        ),
        (
            f"- 鲁棒性分布: train分数中位/IQR={robustness_penalty_payload['robustness_train_score_median']:.2f}/"
            f"{robustness_penalty_payload['robustness_train_score_iqr']:.2f}，"
            f"val分数中位/std={robustness_penalty_payload['robustness_validation_score_median']:.2f}/"
            f"{robustness_penalty_payload['robustness_validation_score_std']:.2f}，"
            f"中位差IQR倍数={robustness_penalty_payload['robustness_score_center_gap_units']:.2f}，"
            f"波动比={robustness_penalty_payload['robustness_score_spread_ratio']:.2f}，"
            f"包络溢出IQR倍数={robustness_penalty_payload['robustness_score_envelope_overflow_units']:.2f}，"
            f"Ulcer比={robustness_penalty_payload['robustness_ulcer_ratio']:.2f}"
        ),
        (
            f"- train+val 状态: 趋势分/收益分={selection_trend_report.trend_score:.2f}/"
            f"{selection_trend_report.return_score:.2f}，"
            f"多头/空头捕获={selection_trend_report.bull_score:.2f}/"
            f"{selection_trend_report.bear_score:.2f}，"
            f"期间收益={selection_total_return:.2f}%"
        ),
        (
            f"- 风险与成本: 最大回撤={worst_drawdown:.2f}%，"
            f"窗口 Ulcer(train/val blended)="
            f"{train_drawdown_risk_report.blended_ulcer_pct:.2f}/{validation_drawdown_risk_report.blended_ulcer_pct:.2f}%，"
            f"手续费拖累={avg_fee_drag:.2f}%，"
            f"train/val稳健时间块落差={promotion_gap:.2f}"
        ),
        (
            f"- 集中度诊断: {overfit_report.risk_level}({overfit_report.risk_score:.0f})，"
            f"覆盖率={overfit_report.coverage_ratio:.0%}，"
            f"多空落差={overfit_report.bull_bear_gap:.2f}，"
            f"处置={mod.overfit_reference_action(overfit_report.risk_score, overfit_report.hard_fail)}"
        ),
    ]
    if low_activity_payload["prompt_line"]:
        prompt_lines.append(low_activity_payload["prompt_line"])
    if weakest_signals:
        prompt_lines.append("train拖累执行标签: " + " | ".join(weakest_signals))
    if weakest_signal_paths:
        prompt_lines.append("train拖累路径标签: " + " | ".join(weakest_signal_paths))

    metrics = {
        "development_mean_score": development_mean_score,
        "development_median_score": development_median_score,
        "development_score_std": development_score_std,
        "development_profitable_window_ratio": profitable_window_ratio,
        "development_window_count": float(len(development_window_scores)),
        "development_mean_trend_capture_score": development_mean_trend_score,
        "eval_avg_return": eval_avg_return,
        "eval_median_return": eval_median_return,
        "eval_p25_return": eval_p25_return,
        "eval_worst_return": eval_worst_return,
        "validation_avg_return": validation_avg_return,
        "validation_worst_return": validation_worst_return,
        "development_funding_coverage_ratio": eval_funding_coverage,
        "validation_funding_coverage_ratio": validation_funding_coverage,
        "selection_funding_coverage_ratio": selection_funding_coverage,
        "worst_drawdown": worst_drawdown,
        "avg_fee_drag": avg_fee_drag,
        "liquidations": float(liquidations),
        "total_trades": float(total_trades),
        "eval_trades": float(eval_trades),
        "validation_trades": float(validation_trades),
        "eval_unique_trend_points": float(eval_path.unique_points),
        "eval_overlap_trend_points": float(eval_path.overlap_points),
        "eval_overlap_trend_points_dropped": float(eval_path.dropped_points),
        "validation_unique_trend_points": float(validation_path.unique_points),
        "validation_overlap_trend_points": float(validation_path.overlap_points),
        "validation_overlap_trend_points_dropped": float(validation_path.dropped_points),
        "validation_score": raw_validation_score,
        "train_capture_score": train_capture_score,
        "validation_capture_score": validation_capture_score,
        "train_capture_equal_score": train_capture_equal_score,
        "validation_capture_equal_score": validation_capture_equal_score,
        "train_capture_weighted_score": train_capture_weighted_score,
        "validation_capture_weighted_score": validation_capture_weighted_score,
        "capture_score": capture_score,
        "period_capture_score": capture_core_payload["period_capture_score"],
        "side_capture_score": capture_core_payload["side_capture_score"],
        "side_capture_multiplier": capture_core_payload["side_capture_multiplier"],
        "capture_core_score": capture_core_score,
        "train_validation_capture_gap": capture_core_payload["train_validation_capture_gap"],
        "bull_bear_capture_gap": capture_core_payload["bull_bear_capture_gap"],
        "period_capture_weak_weight": capture_core_payload["period_capture_weak_weight"],
        "side_capture_weak_weight": capture_core_payload["side_capture_weak_weight"],
        "train_timed_return_score": train_timed_return_score,
        "validation_timed_return_score": validation_timed_return_score,
        "timed_return_score": timed_return_score,
        "train_drawdown_risk_score": train_drawdown_risk_score,
        "validation_drawdown_risk_score": validation_drawdown_risk_score,
        "drawdown_risk_score": drawdown_risk_score,
        "drawdown_penalty_score": drawdown_penalty_score,
        "train_window_ulcer_median_pct": train_drawdown_risk_report.median_ulcer_pct,
        "train_window_ulcer_p75_pct": train_drawdown_risk_report.tail_ulcer_pct,
        "train_window_ulcer_blended_pct": train_drawdown_risk_report.blended_ulcer_pct,
        "train_drawdown_window_count": float(train_drawdown_risk_report.window_count),
        "validation_window_ulcer_median_pct": validation_drawdown_risk_report.median_ulcer_pct,
        "validation_window_ulcer_p75_pct": validation_drawdown_risk_report.tail_ulcer_pct,
        "validation_window_ulcer_blended_pct": validation_drawdown_risk_report.blended_ulcer_pct,
        "validation_drawdown_window_count": float(validation_drawdown_risk_report.window_count),
        "train_turn_protection_score": train_turn_protection_score,
        "validation_turn_protection_score": validation_turn_protection_score,
        "turn_protection_score": turn_protection_score,
        "train_turn_protection_event_count": float(train_continuous_trend_report.turn_protection_event_count),
        "validation_turn_protection_event_count": float(validation_trend_report.turn_protection_event_count),
        "train_capture_source_selection_split": 1.0 if selection_train_points else 0.0,
        "train_return_source_selection_split": 1.0 if selection_train_daily_returns else 0.0,
        "eval_trend_capture_score": development_mean_trend_score,
        "eval_return_score": development_mean_return_score,
        "eval_segment_hit_rate": development_mean_hit_rate,
        "eval_major_segment_count": development_mean_segment_count,
        "validation_trend_capture_score": validation_trend_report.trend_score,
        "selection_trend_capture_score": selection_trend_report.trend_score,
        "combined_trend_capture_score": selection_trend_report.trend_score,
        "full_period_trend_capture_score": selection_trend_report.trend_score,
        "validation_return_score": validation_trend_report.return_score,
        "selection_return_score": selection_trend_report.return_score,
        "combined_return_score": selection_trend_report.return_score,
        "full_period_return_score": selection_trend_report.return_score,
        "validation_arrival_capture_score": validation_trend_report.arrival_score,
        "validation_escort_capture_score": validation_trend_report.escort_score,
        "validation_turn_adaptation_score": validation_trend_report.turn_score,
        "selection_arrival_capture_score": selection_trend_report.arrival_score,
        "selection_escort_capture_score": selection_trend_report.escort_score,
        "selection_turn_adaptation_score": selection_trend_report.turn_score,
        "selection_turn_protection_score": selection_trend_report.turn_protection_score,
        "arrival_capture_score": selection_trend_report.arrival_score,
        "escort_capture_score": selection_trend_report.escort_score,
        "turn_adaptation_score": selection_trend_report.turn_score,
        "selection_turn_protection_event_count": float(selection_trend_report.turn_protection_event_count),
        "validation_bull_capture_score": validation_trend_report.bull_score,
        "validation_bear_capture_score": validation_trend_report.bear_score,
        "selection_bull_capture_score": selection_trend_report.bull_score,
        "selection_bear_capture_score": selection_trend_report.bear_score,
        "bull_capture_score": selection_trend_report.bull_score,
        "bear_capture_score": selection_trend_report.bear_score,
        "validation_segment_hit_rate": validation_trend_report.hit_rate,
        "train_segment_hit_rate": train_continuous_trend_report.hit_rate,
        "selection_segment_hit_rate": selection_trend_report.hit_rate,
        "segment_hit_rate": selection_trend_report.hit_rate,
        "full_period_segment_hit_rate": selection_trend_report.hit_rate,
        "train_major_segment_count": float(train_continuous_trend_report.segment_count),
        "train_bull_segment_count": float(train_continuous_trend_report.bull_segment_count),
        "train_bear_segment_count": float(train_continuous_trend_report.bear_segment_count),
        "train_hit_segment_count": float(_hit_segment_count(train_continuous_trend_report)),
        "validation_hit_segment_count": float(_hit_segment_count(validation_trend_report)),
        "validation_major_segment_count": float(validation_trend_report.segment_count),
        "selection_major_segment_count": float(selection_trend_report.segment_count),
        "major_segment_count": float(selection_trend_report.segment_count),
        "full_period_major_segment_count": float(selection_trend_report.segment_count),
        "validation_bull_segment_count": float(validation_trend_report.bull_segment_count),
        "validation_bear_segment_count": float(validation_trend_report.bear_segment_count),
        "validation_long_closed_trades": float(validation_long_trades),
        "validation_short_closed_trades": float(validation_short_trades),
        "train_closed_trades": float(train_closed_trades),
        "validation_long_entries": float(validation_long_entries),
        "validation_short_entries": float(validation_short_entries),
        "selection_long_entries": float(selection_long_entries),
        "selection_short_entries": float(selection_short_entries),
        "train_entry_trades": float(train_entry_trades),
        "validation_entry_trades": float(validation_entry_trades),
        "selection_entry_trades": float(selection_entry_trades),
        "train_activity_multiplier": train_activity_multiplier,
        "validation_activity_multiplier": validation_activity_multiplier,
        "activity_multiplier": activity_multiplier,
        "train_max_trade_idle_days": train_max_trade_idle_days,
        "validation_max_trade_idle_days": validation_max_trade_idle_days,
        "train_trade_idle_shortfall": train_trade_idle_shortfall,
        "validation_trade_idle_shortfall": validation_trade_idle_shortfall,
        "trade_idle_shortfall": trade_idle_shortfall,
        "trade_idle_penalty": trade_idle_penalty,
        "train_trend_participation_shortfall": train_trend_participation_shortfall,
        "validation_trend_participation_shortfall": validation_trend_participation_shortfall,
        "trend_participation_penalty": trend_participation_penalty,
        "selection_long_closed_trades": float(selection_long_trades),
        "selection_short_closed_trades": float(selection_short_trades),
        "validation_closed_trades": float(validation_closed_trades),
        "selection_closed_trades": float(selection_closed_trades),
        "validation_path_return_pct": validation_trend_report.path_return_pct,
        "validation_total_return_pct": float(validation_source.get("return", validation_avg_return)),
        "selection_path_return_pct": selection_trend_report.path_return_pct,
        "selection_total_return_pct": selection_total_return,
        "selection_max_drawdown": selection_max_drawdown,
        "selection_fee_drag_pct": selection_fee_drag_pct,
        "eval_sharpe_ratio": eval_sharpe_ratio,
        "validation_sharpe_ratio": validation_sharpe_ratio,
        "selection_sharpe_ratio": selection_sharpe_ratio,
        "train_monthly_entries": train_monthly_entries,
        "validation_monthly_entries": validation_monthly_entries,
        "combined_path_return_pct": selection_trend_report.path_return_pct,
        "full_period_return_pct": selection_total_return,
        "capture_drop": capture_drop,
        "dev_validation_gap": promotion_gap,
        "promotion_gap": promotion_gap,
        "validation_block_score_mean": validation_block_report.mean_score,
        "validation_block_score_std": validation_block_report.std_score,
        "validation_block_score_min": validation_block_report.min_score,
        "validation_block_tail_score": validation_block_report.tail_score,
        "validation_block_fail_count": float(validation_block_report.fail_count),
        "validation_block_count_used": float(validation_block_report.used_block_count),
        "train_robust_block_score": train_robust_block_report.robust_score,
        "validation_robust_block_score": validation_robust_block_report.robust_score,
        "train_activity_adjusted_robust_block_score": train_activity_adjusted_robust_block_score,
        "validation_activity_adjusted_robust_block_score": validation_activity_adjusted_robust_block_score,
        "raw_robust_time_score": raw_robust_time_score,
        "robust_time_score": robust_time_score,
        "buy_hold_robust_score": buy_hold_robust_score,
        "benchmark_hurdle_score": benchmark_hurdle,
        "main_score": main_score,
        "train_robust_block_mean_score": train_robust_block_report.mean_score,
        "train_robust_block_median_score": train_robust_block_report.median_score,
        "train_robust_block_p25_score": train_robust_block_report.p25_score,
        "train_robust_block_min_score": train_robust_block_report.min_score,
        "train_robust_block_count": float(train_robust_block_report.block_count),
        "validation_robust_block_mean_score": validation_robust_block_report.mean_score,
        "validation_robust_block_median_score": validation_robust_block_report.median_score,
        "validation_robust_block_p25_score": validation_robust_block_report.p25_score,
        "validation_robust_block_min_score": validation_robust_block_report.min_score,
        "validation_robust_block_count": float(validation_robust_block_report.block_count),
        "train_buy_hold_robust_block_score": train_benchmark_block_report.robust_score,
        "validation_buy_hold_robust_block_score": validation_benchmark_block_report.robust_score,
        "robustness_train_score_median": robustness_penalty_payload["robustness_train_score_median"],
        "robustness_train_score_iqr": robustness_penalty_payload["robustness_train_score_iqr"],
        "robustness_train_score_std": robustness_penalty_payload["robustness_train_score_std"],
        "robustness_validation_score_median": robustness_penalty_payload["robustness_validation_score_median"],
        "robustness_validation_score_std": robustness_penalty_payload["robustness_validation_score_std"],
        "robustness_score_center_gap_units": robustness_penalty_payload["robustness_score_center_gap_units"],
        "robustness_score_spread_ratio": robustness_penalty_payload["robustness_score_spread_ratio"],
        "robustness_score_envelope_overflow_units": robustness_penalty_payload["robustness_score_envelope_overflow_units"],
        "robustness_ulcer_ratio": robustness_penalty_payload["robustness_ulcer_ratio"],
        "score_center_penalty_score": robustness_penalty_payload["score_center_penalty_score"],
        "score_spread_penalty_score": robustness_penalty_payload["score_spread_penalty_score"],
        "score_envelope_penalty_score": robustness_penalty_payload["score_envelope_penalty_score"],
        "ulcer_ratio_penalty_score": robustness_penalty_payload["ulcer_ratio_penalty_score"],
        "robustness_penalty_score_raw": robustness_penalty_payload["robustness_penalty_score_raw"],
        "robustness_penalty_score": robustness_penalty_score,
        "overfit_risk_score": overfit_report.risk_score,
        "overfit_top1_positive_share": overfit_report.top1_positive_share,
        "overfit_chain_positive_share": overfit_report.max_chain_positive_share,
        "overfit_duration_coverage_ratio": overfit_report.duration_coverage_ratio,
        "overfit_volatility_coverage_ratio": overfit_report.volatility_coverage_ratio,
        "overfit_coverage_ratio": overfit_report.coverage_ratio,
        "overfit_bull_bear_gap": overfit_report.bull_bear_gap,
        "overfit_weak_side_capture_score": overfit_report.weak_side_capture_score,
        "overfit_capture_drop_abs": overfit_report.capture_drop_abs,
        "overfit_hard_fail": 1.0 if overfit_report.hard_fail else 0.0,
        "low_activity_signal_count": float(low_activity_payload["count"]),
        "quality_score": quality_score,
        "promotion_main_contribution": promotion_main_contribution,
        "promotion_penalty_total": promotion_penalty_total,
        "promotion_score": promotion_score,
    }
    mod._append_funnel_metrics(metrics, "eval", eval_funnel_counts)
    mod._append_funnel_metrics(metrics, "validation", validation_funnel_counts)
    mod._append_funnel_metrics(metrics, "selection", selection_funnel_counts)
    return mod.EvaluationReport(
        metrics=metrics,
        gate_passed=gate_passed,
        gate_reason=gate_reason,
        summary_text="\n".join(summary_lines),
        prompt_summary_text="\n".join(prompt_lines),
        artifacts={
            "validation_result": validation_source,
            "selection_period_result": selection_source,
        },
    )
