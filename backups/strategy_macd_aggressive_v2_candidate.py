#!/usr/bin/env python3
"""结构化 long-only 基底：价格结构优先，flow/趋势质量辅助，MACD 后置确认。"""

SIDEWAYS_INTRADAY_CHOP_MIN = 60.0
SIDEWAYS_HOURLY_CHOP_MIN = 58.0
SIDEWAYS_HARD_INTRADAY_CHOP_MIN = 62.0
SIDEWAYS_HARD_HOURLY_CHOP_MIN = 60.0
SIDEWAYS_MIN_ATR_RATIO = 0.0020
SIDEWAYS_MIN_HOURLY_SPREAD_PCT = 0.0016
SIDEWAYS_MIN_FOURH_SPREAD_PCT = 0.0020
SIDEWAYS_MAX_HOURLY_ADX = 18.0
SIDEWAYS_MAX_FOURH_ADX = 16.0
LONG_PARTIAL_TAKE_PROFIT_PRICE_PCT = 0.05
LONG_PARTIAL_TAKE_PROFIT_CLOSE_FRACTION = 0.50
LONG_TRAILING_MULTIPLIER = 1.5
LONG_TRAILING_GIVEBACK_MULTIPLIER = 1.3
LONG_TRAILING_GIVEBACK_ATR_BUFFER = 0.5
SHORT_TAKE_PROFIT_TIGHTEN_MULT = 0.8
SHORT_TRAILING_GIVEBACK_MULTIPLIER = 1.25
SHORT_PROFIT_PROTECT_DISABLE_MULTIPLIER = 10.0
LONG_INITIAL_STOP_ATR_MULT = 7.2
SHORT_STOP_ATR_MULT = 3.0
SHORT_BREAKDOWN_FINAL_VETO_VOLUME_AVG_MULT = 1.3
SHORT_BREAKDOWN_FINAL_VETO_VOLUME_PREV_MULT = 1.2
SHORT_TREND_STOP_SIGNAL = "short_trend"
SHORT_HOURLY_BULL_EXIT_MIN_HOLD_BARS = 4
SHORT_FINAL_VETO_RELAXED_ADX_MIN = 20.0
SHORT_FINAL_VETO_RELAXED_ATR_MIN = SIDEWAYS_MIN_ATR_RATIO * 1.05
SIDEWAYS_RELEASE_RELAX = {
    "spread_floor_mult": 0.88,
    "slope_floor_mult": 0.90,
    "atr_ceiling_mult": 1.12,
    "chop_buffer": 2.5,
    "hard_sideways_atr_mult": 1.22,
    "hard_sideways_spread_mult": 1.18,
    "extreme_compression_atr_mult": 0.96,
    "extreme_compression_spread_mult": 0.94,
}


def _leveraged_pnl_pct_from_price_move(price_move_pct, leverage):
    return max(price_move_pct, 0.0) * max(float(leverage), 0.0) * 100.0


# ==================== Tunable Parameter Surface ====================

# PARAMS_START
PARAMS = {
    "breakdown_adx_min": 25.0,
    "breakdown_body_ratio_min": 0.39,
    "breakdown_buffer_pct": 0.0002,
    "breakdown_close_pos_max": 0.34,
    "breakdown_hist_max": 14.0,
    "breakdown_lookback": 22,
    "breakdown_rsi_max": 44.0,
    "breakdown_rsi_min": 21.0,
    "breakdown_volume_ratio_min": 1.08,
    "breakout_adx_min": 18.5,
    "breakout_body_ratio_min": 0.26,
    "breakout_buffer_pct": 0.00012,
    "breakout_close_pos_min": 0.56,
    "breakout_flow_imbalance_min": -0.01,
    "breakout_flow_score_min": 3,
    "breakout_flow_score_strong_min": 5,
    "breakout_hist_min": -2.0,
    "breakout_lookback": 20,
    "breakout_rsi_max": 73.0,
    "breakout_rsi_min": 46.0,
    "breakout_taker_buy_ratio_min": 0.495,
    "breakout_trade_count_ratio_min": 0.92,
    "breakout_volume_ratio_min": 0.98,
    "flow_lookback": 10,
    "fourh_adx_min": 11.0,
    "fourh_ema_fast": 10,
    "fourh_ema_slow": 34,
    "fourh_flow_confirmation_min": 0.0,
    "fourh_taker_buy_ratio_min": 0.485,
    "hourly_adx_min": 13.0,
    "hourly_ema_anchor": 85,
    "hourly_ema_fast": 12,
    "hourly_ema_slow": 50,
    "hourly_flow_confirmation_min": 0.0,
    "hourly_taker_buy_ratio_min": 0.49,
    "hourly_trade_count_ratio_min": 0.68,
    "intraday_adx_min": 11.5,
    "intraday_ema_fast": 10,
    "intraday_ema_slow": 24,
    "macd_fast": 8,
    "macd_signal": 6,
    "macd_slow": 20,
    "min_history": 260,
    "volume_lookback": 9,
}
# PARAMS_END


# EXIT_PARAMS_START
EXIT_PARAMS = {
    "break_even_activation_pct": 28.0,
    "break_even_buffer_pct": 0.35,
    "breakout_break_even_activation_pct": 55.5,
    "breakout_break_even_buffer_pct": 0.30,
    "breakout_max_hold_bars": 520,
    "breakout_stop_atr_mult": 1.8,
    "breakout_tp1_close_fraction": 0.0,
    "breakout_tp1_pnl_pct": 89.0,
    "breakout_trailing_activation_pct": 95.0,
    "breakout_trailing_giveback_pct": 3.0,
    "dynamic_hold_adx_strong_threshold": 19.0,
    "dynamic_hold_adx_threshold": 16.0,
    "dynamic_hold_extension_bars": 108,
    "dynamic_hold_max_bars": 360,
    "entry_delay_minutes": 1,
    "execution_use_1m": 1,
    "funding_fee_enabled": 1,
    "leverage": 20,
    "long_breakout_stop_atr_mult": 6.2,
    "long_pullback_break_even_buffer_pct": 0.28,
    "long_pullback_stop_atr_mult": 6.2,
    "long_pullback_trailing_giveback_pct": 5.8,
    "max_concurrent_positions": 1,
    "max_hold_bars": 360,
    "okx_maker_fee_rate": 0.0002,
    "okx_taker_fee_rate": 0.0005,
    "position_fraction": 0.10,
    "position_size_max": 0,
    "position_size_min": 0,
    "pyramid_adx_min": 10.0,
    "pyramid_enabled": 1,
    "pyramid_max_times": -1,
    "pyramid_size_ratio": 0.05,
    "pyramid_trigger_pnl": 5.0,
    "regime_close_below_hourly_fast": 0,
    "regime_exit_confirm_bars": 0,
    "regime_exit_enabled": 1,
    "regime_hist_floor": -110.0,
    "regime_price_confirm_buffer_pct": 0.010,
    "short_breakdown_break_even_activation_pct": 257.0,
    "short_breakdown_max_hold_bars": 96,
    "short_breakdown_stop_atr_mult": 1.955,
    "short_breakdown_tp1_close_fraction": 0.0,
    "short_breakdown_tp1_pnl_pct": 297.88,
    "short_breakdown_trailing_activation_pct": 999.0,
    "short_breakdown_trailing_giveback_pct": 6.25,
    "short_trend_break_even_activation_pct": 257.0,
    "short_trend_max_hold_bars": 96,
    "short_trend_stop_atr_mult": 1.7,
    "short_trend_tp1_close_fraction": 0.0,
    "short_trend_tp1_pnl_pct": 297.88,
    "short_trend_trailing_activation_pct": 32.0,
    "short_trend_trailing_giveback_pct": 6.25,
    "slippage_pct": 0.0003,
    "stop_atr_mult": 1.6,
    "stop_max_loss_pct": 57.5,
    "tp1_close_fraction": 0.0,
    "tp1_pnl_pct": 79.9,
    "take_profit": 0.030,
    "trading_fee_enabled": 1,
    "trailing_activation_pct": 13.8,
    "trailing_giveback_pct": 5.8,
}
# EXIT_PARAMS_END


ENTRY_SIGNAL_ALIASES = {
    "long_breakout": "long_pullback",
    "long_pullback": "long_pullback",
    "long_reaccel": "long_pullback",
    "long_relay": "long_pullback",
    "long_impulse": "long_pullback",
    "long_reversal_sniper": "long_pullback",
    "long_retest": "long_pullback",
    "short_breakdown": "short_breakdown",
    "short_trend": "short_trend",
    "short_bounce_fail": "short_breakdown",
    "short_reaccel": "short_breakdown",
    "short_impulse": "short_breakdown",
    "short_retest": "short_breakdown",
}
ENTRY_PATH_TAGS = {
    "long_breakout": "long_impulse",
    "long_pullback": "long_retest",
    "long_reaccel": "long_reaccel",
    "long_relay": "long_relay",
    "long_impulse": "long_impulse",
    "long_reversal_sniper": "long_reversal_sniper",
    "long_retest": "long_retest",
    "short_breakdown": "short_impulse",
    "short_trend": "short_impulse",
    "short_bounce_fail": "short_retest",
    "short_reaccel": "short_reaccel",
    "short_impulse": "short_impulse",
    "short_retest": "short_retest",
}

STRATEGY_FRAMEWORK_VERSION = "structured_factor_slots_v1"
FACTOR_SLOT_NAMES = (
    "regime_trend",
    "regime_sideways",
    "regime_volatility",
    "regime_external",
    "long_context",
    "long_breakout",
    "long_pullback",
    "long_reaccel",
    "long_flow",
    "long_veto",
    "long_extra_1",
    "long_extra_2",
    "short_context",
    "short_breakdown",
    "short_bounce_fail",
    "short_reaccel",
    "short_flow",
    "short_veto",
    "short_extra_1",
    "short_extra_2",
)

# FACTOR_SLOT_PARAMS_START
FACTOR_SLOT_PARAMS = {
    "regime_trend": {"enabled": 1, "weight": 0.30, "threshold": 0.00},
    "regime_sideways": {"enabled": 1, "weight": 0.20, "threshold": 0.00},
    "regime_volatility": {"enabled": 1, "weight": 0.20, "threshold": 0.00},
    "regime_external": {"enabled": 0, "weight": 0.10, "threshold": 0.00},
    "long_context": {"enabled": 1, "weight": 1.00, "threshold": 0.50},
    "long_breakout": {"enabled": 1, "weight": 0.95, "threshold": 0.30},
    "long_pullback": {"enabled": 1, "weight": 0.90, "threshold": 0.30},
    "long_reaccel": {"enabled": 1, "weight": 0.82, "threshold": 0.36},
    "long_flow": {"enabled": 1, "weight": 0.35, "threshold": 0.10},
    "long_veto": {"enabled": 1, "weight": 0.55, "threshold": 0.00},
    "long_extra_1": {"enabled": 1, "weight": 0.15, "threshold": 0.50},
    "long_extra_2": {"enabled": 0, "weight": 0.20, "threshold": 0.50},
    "short_context": {"enabled": 0, "weight": 0.00, "threshold": 0.00},
    "short_breakdown": {"enabled": 0, "weight": 0.00, "threshold": 0.00},
    "short_bounce_fail": {"enabled": 0, "weight": 0.00, "threshold": 0.00},
    "short_reaccel": {"enabled": 0, "weight": 0.00, "threshold": 0.00},
    "short_flow": {"enabled": 0, "weight": 0.00, "threshold": 0.00},
    "short_veto": {"enabled": 0, "weight": 0.00, "threshold": 0.00},
    "short_extra_1": {"enabled": 0, "weight": 0.00, "threshold": 0.00},
    "short_extra_2": {"enabled": 0, "weight": 0.00, "threshold": 0.00},
}
# FACTOR_SLOT_PARAMS_END


# ==================== Runtime Contracts And Diagnostics ====================

FUNNEL_SIDES = ("long", "short")
FUNNEL_STAGES = ("sideways_pass", "outer_context_pass", "path_pass", "final_veto_pass")
_FUNNEL_DIAGNOSTICS = {}
LONG_PULLBACK_HOLD_TAGS = {"long_retest", "long_reaccel", "long_relay"}
LONG_PYRAMID_TRIGGER_MULTIPLIER = 0.62
LONG_PYRAMID_STRONG_ADX_MIN = 25.0
LONG_PYRAMID_STRONG_TRIGGER_RELAX_MULTIPLIER = 0.8
LONG_REENTRY_COOLDOWN_BARS = 1
INTRADAY_BULL_EMA_PERIOD = 50
INTRADAY_BULL_ADX_MIN = 20.0
LONG_TIME_EXIT_MIN_HOLD_BARS = 48
LONG_TIME_EXIT_MAX_PRICE_MOVE_PCT = 0.02
LONG_EXIT_VOLUME_FILTER_LOOKBACK = 20
LONG_EXIT_VOLUME_FILTER_MIN_RATIO = 0.8
MACD_DIVERGENCE_LOOKBACK = 20
MACD_DIVERGENCE_PIVOT_SPAN = 2


def _empty_funnel_bucket():
    return {stage: 0 for stage in FUNNEL_STAGES}


def reset_funnel_diagnostics():
    global _FUNNEL_DIAGNOSTICS
    _FUNNEL_DIAGNOSTICS = {side: _empty_funnel_bucket() for side in FUNNEL_SIDES}


def _record_funnel_pass(side, stage):
    bucket = _FUNNEL_DIAGNOSTICS.get(side)
    if bucket is None:
        bucket = _empty_funnel_bucket()
        _FUNNEL_DIAGNOSTICS[side] = bucket
    bucket[stage] = int(bucket.get(stage, 0)) + 1


def get_funnel_diagnostics():
    return {
        side: {stage: int(bucket.get(stage, 0)) for stage in FUNNEL_STAGES}
        for side, bucket in _FUNNEL_DIAGNOSTICS.items()
    }


reset_funnel_diagnostics()


def normalize_entry_signal(signal, fallback_side=""):
    text = str(signal or "").strip()
    if text == SHORT_TREND_STOP_SIGNAL:
        return text
    normalized = ENTRY_SIGNAL_ALIASES.get(text, "")
    if normalized:
        return normalized
    side = str(fallback_side or "").strip().lower()
    if not text:
        if side == "long":
            return "long_pullback"
        if side == "short":
            return "short_breakdown"
        return ""
    if text.startswith("long_"):
        return "long_pullback"
    if text.startswith("short_"):
        return "short_breakdown"
    return text


def _exit_param_value_for_signal(signal, key):
    signal_text = str(signal or "").strip()
    exact_key = f"{signal_text}_{key}"
    if exact_key in EXIT_PARAMS:
        return EXIT_PARAMS[exact_key]
    if signal_text in {"long_breakout", "short_breakdown"}:
        breakout_key = f"breakout_{key}"
        if breakout_key in EXIT_PARAMS:
            return EXIT_PARAMS[breakout_key]
    elif signal_text in {"long_pullback", "short_bounce_fail"}:
        pullback_key = f"pullback_{key}"
        if pullback_key in EXIT_PARAMS:
            return EXIT_PARAMS[pullback_key]
    return EXIT_PARAMS[key]


# ==================== Short Exit Safety Layer ====================

def _short_stop_environment_confirmed(market_state):
    hourly = (market_state or {}).get("hourly", {})
    try:
        hourly_close = float(hourly.get("close", 0.0))
        hourly_ema_slow = float(hourly.get("ema_slow", 0.0))
    except (TypeError, ValueError, AttributeError):
        return False
    return hourly_close > 0.0 and hourly_ema_slow > 0.0 and hourly_close < hourly_ema_slow


def _resolved_short_entry_signal(market_state, short_path_key=""):
    if str(short_path_key or "").strip() == "short_trend":
        return "short_trend"
    return "short_breakdown"


def _short_trailing_exhaustion_active(position, market_state, current_close):
    entry_price = float((position or {}).get("entry_price", current_close))
    if entry_price <= 0.0 or current_close <= 0.0:
        return False
    entry_path_key = str(
        (position or {}).get("entry_path_tag")
        or (position or {}).get("entry_path_key")
        or (position or {}).get("entry_signal")
        or ""
    ).strip()
    try:
        if not _trend_followthrough_short(
            market_state,
            entry_price,
            current_close,
            entry_path_key=entry_path_key,
        ):
            return True
    except (KeyError, TypeError, ValueError):
        return False

    hourly = market_state["hourly"]
    prev_hourly = market_state.get("prev_hourly") or hourly
    metrics = _directional_trend_metrics(market_state, "short")
    atr_ratio = max(float(metrics["atr_ratio"]), 0.0)
    hourly_spread = max(float(metrics["hourly_spread"]), 0.0)
    hourly_slope = max(float(metrics["hourly_slope"]), 0.0)
    prev_hourly_spread = max(-float(prev_hourly.get("trend_spread_pct", 0.0)), 0.0)
    prev_hourly_slope = max(-float(prev_hourly.get("ema_slow_slope_pct", 0.0)), 0.0)
    hourly_adx = max(float(hourly.get("adx", 0.0)), 0.0)
    prev_hourly_adx = max(float(prev_hourly.get("adx", hourly_adx)), 0.0)
    adx_rollover = (
        hourly_adx <= max(float(EXIT_PARAMS.get("dynamic_hold_adx_strong_threshold", 26.0)) - 2.0, 20.0)
        and hourly_adx < prev_hourly_adx
    ) or hourly_adx <= max(float(EXIT_PARAMS.get("dynamic_hold_adx_threshold", 16.0)), 16.0)
    spread_converging = hourly_spread <= max(
        prev_hourly_spread * 0.90,
        atr_ratio * 0.58,
        SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.04,
    )
    slope_softening = hourly_slope <= max(prev_hourly_slope * 0.82, atr_ratio * 0.050)
    reclaim_pressure = (
        current_close >= hourly["ema_fast"] * (1.0 - atr_ratio * 0.03)
        or market_state["histogram"] >= max(market_state.get("prev_histogram", market_state["histogram"]), -0.01)
    )
    return reclaim_pressure and ((adx_rollover and spread_converging) or (spread_converging and slope_softening))


def _sync_short_exit_signal_profiles(positions, market_state, current_close):
    if not positions:
        return
    for position in positions:
        if _position_side(position) != "short":
            continue
        position["entry_signal"] = (
            SHORT_TREND_STOP_SIGNAL
            if _short_trailing_exhaustion_active(position, market_state, current_close)
            else "short_breakdown"
        )


# ==================== Market Data Helpers ====================

def _avg(data, start, end, key):
    total = 0.0
    count = 0
    for i in range(start, end + 1):
        total += data[i][key]
        count += 1
    return total / count if count else 0.0


def _ema(data, start, end, key, period):
    if period <= 1:
        return data[end][key]
    seed_start = max(start, end - period + 1)
    ema = _avg(data, seed_start, end, key)
    alpha = 2.0 / (period + 1.0)
    for i in range(seed_start + 1, end + 1):
        ema = data[i][key] * alpha + ema * (1.0 - alpha)
    return ema


def _window_max(data, start, end, key):
    value = data[start][key]
    for i in range(start + 1, end + 1):
        if data[i][key] > value:
            value = data[i][key]
    return value


def _window_min(data, start, end, key):
    value = data[start][key]
    for i in range(start + 1, end + 1):
        if data[i][key] < value:
            value = data[i][key]
    return value


def _anchored_long_breakout_high(bar, atr_ratio):
    candle = _candle_metrics(bar)
    body_high = max(bar["open"], bar["close"])
    bar_range = _bar_range(bar)
    raw_high = bar["high"]
    wick_excess = max(raw_high - body_high, 0.0)
    upper_wick_ratio = wick_excess / bar_range if bar_range > 0.0 else 0.0
    body_ratio = candle["body_ratio"]
    close_pos = candle["close_pos"]
    strong_bullish_anchor = (
        bar["close"] >= bar["open"]
        and close_pos >= 0.66
        and body_ratio >= 0.26
        and upper_wick_ratio <= 0.36
    )
    if strong_bullish_anchor:
        allowed_wick_excess = max(
            body_high * atr_ratio * 0.34,
            bar_range * 0.20,
        )
    else:
        anchor_quality = min(
            1.0,
            max(0.0, (close_pos - 0.50) / 0.22) * 0.58
            + max(0.0, (body_ratio - 0.14) / 0.20) * 0.42,
        )
        wick_penalty = min(1.0, upper_wick_ratio / 0.30)
        weak_close_wick = upper_wick_ratio >= 0.30 and close_pos <= 0.70 and body_ratio <= 0.30
        stale_wick_anchor = upper_wick_ratio >= 0.42 and close_pos <= 0.74
        compressed_allowance = bar_range * (0.05 + 0.08 * anchor_quality)
        atr_allowance = body_high * atr_ratio * (0.10 + 0.14 * anchor_quality)
        allowed_wick_excess = max(
            min(compressed_allowance, atr_allowance) * (1.0 - 0.64 * wick_penalty),
            min(bar_range * 0.08, body_high * atr_ratio * 0.10),
        )
        if weak_close_wick:
            allowed_wick_excess = min(
                allowed_wick_excess,
                max(
                    min(bar_range * 0.04, body_high * atr_ratio * 0.07),
                    body_high * 0.00012,
                ),
            )
        if stale_wick_anchor:
            allowed_wick_excess = min(
                allowed_wick_excess,
                max(
                    min(bar_range * 0.03, body_high * atr_ratio * 0.05),
                    body_high * 0.00010,
                ),
            )
    return body_high + min(wick_excess, allowed_wick_excess)


def _effective_long_breakout_reference_bar(bar, atr_ratio):
    candle = _candle_metrics(bar)
    bar_range = _bar_range(bar)
    body_high = max(bar["open"], bar["close"])
    upper_wick = max(bar["high"] - body_high, 0.0)
    upper_wick_ratio = upper_wick / bar_range if bar_range > 0.0 else 0.0
    bullish_body = max(bar["close"] - bar["open"], 0.0)
    bullish_body_ratio = bullish_body / bar_range if bar_range > 0.0 else 0.0
    strong_close = candle["close_pos"] >= 0.72 and candle["body_ratio"] >= 0.26
    wick_cap = 0.34 if strong_close else 0.28
    wick_room = 0.24 if strong_close else 0.18
    return (
        bar["close"] >= bar["open"]
        and candle["close_pos"] >= 0.58
        and candle["body_ratio"] >= 0.20
        and bullish_body_ratio >= 0.14
        and bar_range >= max(bar["close"] * atr_ratio * 0.36, body_high * 0.0007)
        and upper_wick_ratio <= wick_cap
        and upper_wick <= max(body_high * atr_ratio * (0.20 if strong_close else 0.16), bar_range * wick_room)
        and upper_wick <= bullish_body + max(body_high * atr_ratio * 0.10, bar_range * 0.08)
    )


def _recent_long_breakout_prepared(data, start, end, reference_high, atr_ratio):
    score = 0
    probe_start = max(start, end - 2)
    close_gap = max(atr_ratio * 0.16, 0.0014)
    high_gap = max(atr_ratio * 0.08, 0.0009)
    for i in range(probe_start, end + 1):
        bar = data[i]
        candle = _candle_metrics(bar)
        anchored_high = _anchored_long_breakout_high(bar, atr_ratio)
        if bar["close"] >= reference_high * (1.0 - close_gap) and candle["close_pos"] >= 0.54:
            score += 1
        if bar["high"] >= reference_high * (1.0 - high_gap):
            score += 1
        if anchored_high >= reference_high * (1.0 - high_gap) and candle["body_ratio"] >= 0.18:
            score += 1
        if _effective_long_breakout_reference_bar(bar, atr_ratio):
            score += 1
    return score >= 4


def _long_breakout_reference_high(data, start, end, atr_ratio):
    reference_high = _anchored_long_breakout_high(data[start], atr_ratio)
    reference_idx = start
    recent_effective_high = 0.0
    recent_effective_idx = -1
    recent_prepared_high = 0.0
    recent_prepared_idx = -1
    window = end - start + 1
    recent_span = max(8, window // 2)
    recent_start = max(start, end - recent_span + 1)
    for i in range(start, end + 1):
        bar = data[i]
        anchored_high = _anchored_long_breakout_high(bar, atr_ratio)
        if anchored_high > reference_high:
            reference_high = anchored_high
            reference_idx = i
        if (
            i >= recent_start
            and _effective_long_breakout_reference_bar(bar, atr_ratio)
            and anchored_high >= recent_effective_high
        ):
            recent_effective_high = anchored_high
            recent_effective_idx = i
        if (
            i >= recent_start
            and bar["close"] >= bar["open"]
            and _candle_metrics(bar)["close_pos"] >= 0.54
            and _candle_metrics(bar)["body_ratio"] >= 0.16
            and anchored_high >= recent_prepared_high
        ):
            recent_prepared_high = anchored_high
            recent_prepared_idx = i

    candidate_high = recent_effective_high
    candidate_idx = recent_effective_idx
    if candidate_idx < 0 and recent_prepared_idx >= 0:
        candidate_high = recent_prepared_high
        candidate_idx = recent_prepared_idx

    if candidate_idx < 0:
        return reference_high
    if reference_idx >= recent_start:
        return max(reference_high, candidate_high)

    stale_gap_pct = (reference_high - candidate_high) / max(candidate_high, 1e-9)
    prepared_breakout = _recent_long_breakout_prepared(data, recent_start, end, candidate_high, atr_ratio)
    recent_close_acceptance = data[end]["close"] >= candidate_high * (1.0 - max(atr_ratio * 0.14, 0.0011))
    recent_high_acceptance = data[end]["high"] >= candidate_high * (1.0 - max(atr_ratio * 0.06, 0.0007))
    if prepared_breakout and stale_gap_pct <= max(atr_ratio * 1.48, 0.0058):
        return candidate_high
    if recent_close_acceptance and stale_gap_pct <= max(atr_ratio * 1.18, 0.0042):
        return candidate_high
    if recent_high_acceptance and stale_gap_pct <= max(atr_ratio * 0.92, 0.0032):
        return candidate_high
    return reference_high


def _bar_is_valid(bar):
    return (
        bar["open"] > 0
        and bar["close"] > 0
        and bar["volume"] > 0
        and bar["high"] >= bar["low"]
    )


def _bar_range(bar):
    return max(bar["high"] - bar["low"], bar["close"] * 1e-9)


def _candle_metrics(bar):
    open_price = bar["open"]
    low = bar["low"]
    close = bar["close"]
    candle_range = _bar_range(bar)
    body = close - open_price
    return {
        "close_pos": (close - low) / candle_range,
        "body_ratio": abs(body) / candle_range,
    }


def _recent_window_stats(data, end_idx, window, price_floor):
    range_total = 0.0
    volume_total = 0.0
    body_ratio_total = 0.0
    for i in range(end_idx - window, end_idx):
        recent_bar = data[i]
        recent_range = _bar_range(recent_bar)
        body = recent_bar["close"] - recent_bar["open"]
        range_total += recent_range
        volume_total += recent_bar["volume"]
        body_ratio_total += abs(body) / recent_range
    return {
        "range_avg": max(range_total / window, price_floor * 1e-9),
        "volume_avg": max(volume_total / window, 1e-9),
        "body_ratio_avg": body_ratio_total / window,
    }


def _intraday_trend_metrics(market_state):
    ema_fast = market_state["ema_fast"]
    ema_slow = market_state["ema_slow"]
    prev_ema_slow = market_state["prev_ema_slow"]
    trend_base = max(abs(ema_slow), 1e-9)
    return {
        "spread_pct": (ema_fast - ema_slow) / trend_base,
        "slope_pct": (ema_slow - prev_ema_slow) / trend_base,
    }


def _position_side(position):
    side = str((position or {}).get("entry_side", "")).strip()
    if side in {"long", "short"}:
        return side
    signal = str((position or {}).get("entry_signal", "")).strip()
    if signal.startswith("short_"):
        return "short"
    if signal.startswith("long_"):
        return "long"
    return ""


def _long_pullback_hold_active(positions):
    if not positions:
        return False
    for position in positions:
        if _position_side(position) != "long":
            continue
        path_tag = str(
            position.get("entry_path_tag")
            or position.get("entry_path_key")
            or position.get("entry_signal")
            or ""
        ).strip()
        normalized_tag = ENTRY_PATH_TAGS.get(path_tag, path_tag)
        if normalized_tag in LONG_PULLBACK_HOLD_TAGS:
            return True
    return False


def _volume_climax_exhaustion_sides(data, idx, positions):
    if not positions or idx <= 0 or idx >= len(data):
        return set()
    current = data[idx]
    lookback = min(20, idx)
    recent = data[idx - lookback:idx]
    if not recent:
        return set()
    current_close = float(current.get("close", 0.0))
    current_open = float(current.get("open", current_close))
    current_high = float(current.get("high", current_close))
    current_low = float(current.get("low", current_close))
    current_volume = float(current.get("volume", 0.0))
    current_range = max(current_high - current_low, abs(current_close) * 1e-9, 1e-9)
    avg_volume = max(sum(float(bar.get("volume", 0.0)) for bar in recent) / len(recent), 1e-9)
    avg_range = max(
        sum(max(float(bar.get("high", 0.0)) - float(bar.get("low", 0.0)), 0.0) for bar in recent) / len(recent),
        abs(current_close) * 1e-9,
        1e-9,
    )
    if current_volume < avg_volume * 2.5 or current_range < avg_range * 0.80:
        return set()
    close_pos = (current_close - current_low) / current_range
    exhausted = set()
    for position in positions:
        side = _position_side(position)
        entry_price = float(position.get("entry_price", 0.0))
        if side == "long" and entry_price > 0.0:
            if current_close > entry_price and current_close >= current_open and close_pos >= 0.65:
                exhausted.add("long")
        elif side == "short" and entry_price > 0.0:
            if current_close < entry_price and current_close <= current_open and close_pos <= 0.35:
                exhausted.add("short")
    return exhausted


def _volume_climax_exhaustion_side(data, idx, positions):
    sides = _volume_climax_exhaustion_sides(data, idx, positions)
    if len(sides) == 1:
        return next(iter(sides))
    return ""


def _long_exit_volume_filter_allows(data, idx):
    if idx <= 0 or idx >= len(data):
        return True
    lookback = min(LONG_EXIT_VOLUME_FILTER_LOOKBACK, idx)
    if lookback <= 0:
        return True
    recent_volume_total = 0.0
    for i in range(idx - lookback, idx):
        recent_volume_total += max(float(data[i].get("volume", 0.0)), 0.0)
    recent_volume_avg = recent_volume_total / lookback if lookback > 0 else 0.0
    if recent_volume_avg <= 0.0:
        return True
    current_volume = max(float(data[idx].get("volume", 0.0)), 0.0)
    return current_volume >= recent_volume_avg * LONG_EXIT_VOLUME_FILTER_MIN_RATIO


def _count_positions_by_side(positions, side):
    if not positions:
        return 0
    return sum(1 for position in positions if _position_side(position) == side)


def _count_true(*conditions):
    return sum(1 for condition in conditions if condition)


def _all_true(*conditions):
    return all(conditions)


def _any_true(*conditions):
    return any(conditions)


def _first_active_lane(*lanes):
    for name, active in lanes:
        if active:
            return name
    return ""


# ==================== Shared Payload And Position Helpers ====================

def _safe_payload_float(payload, key, default):
    if payload is None:
        return default
    try:
        return float(payload.get(key, default))
    except (TypeError, ValueError, AttributeError):
        return default


def _short_impulse_hourly_rsi_ok(market_state):
    hourly = (market_state or {}).get("hourly")
    hourly_rsi = _safe_payload_float(hourly, "rsi", None)
    if hourly_rsi is None:
        hourly_rsi = _safe_payload_float(market_state, "hourly_rsi", None)
    if hourly_rsi is None:
        return True
    return hourly_rsi < 40.0


def _hourly_extension_within(context, fast_atr_mult, fast_spread_mult, anchor_atr_mult, anchor_spread_mult):
    atr_ratio = context["atr_ratio"]
    return (
        context["hourly_fast_extension_pct"] <= max(
            atr_ratio * fast_atr_mult,
            SIDEWAYS_MIN_HOURLY_SPREAD_PCT * fast_spread_mult,
        )
        and context["hourly_anchor_extension_pct"] <= max(
            atr_ratio * anchor_atr_mult,
            SIDEWAYS_MIN_HOURLY_SPREAD_PCT * anchor_spread_mult,
        )
    )


def _hourly_extension_reaches(context, fast_atr_mult, fast_spread_mult, anchor_atr_mult, anchor_spread_mult):
    atr_ratio = context["atr_ratio"]
    return (
        context["hourly_fast_extension_pct"] >= max(
            atr_ratio * fast_atr_mult,
            SIDEWAYS_MIN_HOURLY_SPREAD_PCT * fast_spread_mult,
        )
        and context["hourly_anchor_extension_pct"] >= max(
            atr_ratio * anchor_atr_mult,
            SIDEWAYS_MIN_HOURLY_SPREAD_PCT * anchor_spread_mult,
        )
    )


def _position_close_pnl_pct(position, current_close):
    entry_price = float((position or {}).get("entry_price", 0.0))
    if entry_price <= 0.0 or current_close <= 0.0:
        return 0.0
    leverage = max(float(EXIT_PARAMS.get("leverage", 1.0)), 1.0)
    price_move_pct = (current_close - entry_price) / entry_price
    return price_move_pct * leverage * 100.0


def _detect_macd_divergence(data, idx, position):
    def _macd_histogram_window(end_idx):
        warmup = max(int(PARAMS["macd_slow"]) + int(PARAMS["macd_signal"]) + MACD_DIVERGENCE_LOOKBACK, 0)
        if end_idx <= 0:
            return []
        start_idx = max(0, end_idx - warmup + 1)
        histogram_window = []
        for i in range(start_idx, end_idx + 1):
            macd_line = _ema(data, start_idx, i, "close", PARAMS["macd_fast"]) - _ema(
                data,
                start_idx,
                i,
                "close",
                PARAMS["macd_slow"],
            )
            signal_line = 0.0
            signal_start = max(start_idx, i - int(PARAMS["macd_signal"]) + 1)
            signal_count = i - signal_start + 1
            if signal_count > 0:
                macd_sum = 0.0
                for j in range(signal_start, i + 1):
                    macd_sum += _ema(data, start_idx, j, "close", PARAMS["macd_fast"]) - _ema(
                        data,
                        start_idx,
                        j,
                        "close",
                        PARAMS["macd_slow"],
                    )
                signal_line = macd_sum / signal_count
            histogram_window.append({"idx": i, "value": macd_line - signal_line})
        return histogram_window

    def _pivot_indices(values, end_idx, *, use_highs):
        pivots = []
        lookback_start = max(0, end_idx - MACD_DIVERGENCE_LOOKBACK + 1)
        pivot_start = max(lookback_start + MACD_DIVERGENCE_PIVOT_SPAN, 0)
        pivot_end = end_idx - MACD_DIVERGENCE_PIVOT_SPAN
        for i in range(pivot_start, pivot_end + 1):
            center = values.get(i)
            if center is None:
                continue
            is_pivot = True
            for offset in range(1, MACD_DIVERGENCE_PIVOT_SPAN + 1):
                left = values.get(i - offset)
                right = values.get(i + offset)
                if left is None or right is None:
                    is_pivot = False
                    break
                if use_highs:
                    if center < left or center < right:
                        is_pivot = False
                        break
                else:
                    if center > left or center > right:
                        is_pivot = False
                        break
            if is_pivot:
                pivots.append(i)
        return pivots

    def _nearest_hist_pivot(hist_values, hist_pivots, target_idx):
        best_idx = -1
        best_gap = MACD_DIVERGENCE_PIVOT_SPAN + 1
        for pivot_idx in hist_pivots:
            gap = abs(pivot_idx - target_idx)
            if gap > MACD_DIVERGENCE_PIVOT_SPAN:
                continue
            if gap < best_gap:
                best_gap = gap
                best_idx = pivot_idx
        if best_idx < 0:
            return None
        return hist_values.get(best_idx)

    side = _position_side(position)
    if side not in {"long", "short"} or idx <= MACD_DIVERGENCE_LOOKBACK:
        return False
    histogram_window = _macd_histogram_window(idx)
    if len(histogram_window) < MACD_DIVERGENCE_LOOKBACK:
        return False

    price_values = {}
    hist_values = {}
    for item in histogram_window:
        hist_values[item["idx"]] = item["value"]
    lookback_start = max(0, idx - MACD_DIVERGENCE_LOOKBACK + 1)
    for i in range(lookback_start, idx + 1):
        bar = data[i]
        price_values[i] = bar["high"] if side == "long" else bar["low"]

    price_pivots = _pivot_indices(price_values, idx, use_highs=(side == "long"))
    hist_pivots = _pivot_indices(hist_values, idx, use_highs=(side == "long"))
    if len(price_pivots) < 2 or len(hist_pivots) < 2:
        return False

    recent_price_idx = price_pivots[-1]
    prior_price_idx = -1
    for pivot_idx in reversed(price_pivots[:-1]):
        if recent_price_idx - pivot_idx >= MACD_DIVERGENCE_PIVOT_SPAN:
            prior_price_idx = pivot_idx
            break
    if prior_price_idx < 0:
        return False

    recent_hist_value = _nearest_hist_pivot(hist_values, hist_pivots, recent_price_idx)
    prior_hist_value = _nearest_hist_pivot(hist_values, hist_pivots, prior_price_idx)
    if recent_hist_value is None or prior_hist_value is None:
        return False

    recent_price = price_values[recent_price_idx]
    prior_price = price_values[prior_price_idx]
    if side == "long":
        return (
            recent_price > prior_price
            and prior_hist_value > 0.0
            and recent_hist_value > 0.0
            and recent_hist_value < prior_hist_value
        )
    return (
        recent_price < prior_price
        and prior_hist_value < 0.0
        and recent_hist_value < 0.0
        and recent_hist_value > prior_hist_value
    )


def _trailing_activation_ratio_for_position(position, side):
    leverage = max(float(EXIT_PARAMS.get("leverage", 1.0)), 1.0)
    activation_pct = max(
        float(_exit_param_value_for_signal((position or {}).get("entry_signal", ""), "trailing_activation_pct")),
        0.0,
    )
    if side == "long":
        activation_pct *= LONG_TRAILING_MULTIPLIER
    return activation_pct / leverage / 100.0


def _trailing_giveback_ratio_for_position(position, side):
    leverage = max(float(EXIT_PARAMS.get("leverage", 1.0)), 1.0)
    giveback_pct = max(
        float(_exit_param_value_for_signal((position or {}).get("entry_signal", ""), "trailing_giveback_pct")),
        0.0,
    )
    if side == "long":
        giveback_pct *= LONG_TRAILING_GIVEBACK_MULTIPLIER
    return giveback_pct / leverage / 100.0


def _long_pyramid_trigger_pnl(market_state=None):
    base_trigger = max(float(EXIT_PARAMS.get("pyramid_trigger_pnl", 0.0)), 0.0)
    trigger_multiplier = LONG_PYRAMID_TRIGGER_MULTIPLIER
    try:
        intraday_adx = float((market_state or {}).get("adx", 0.0))
    except (TypeError, ValueError, AttributeError):
        intraday_adx = 0.0
    if intraday_adx >= LONG_PYRAMID_STRONG_ADX_MIN:
        trigger_multiplier *= LONG_PYRAMID_STRONG_TRIGGER_RELAX_MULTIPLIER
    return base_trigger * trigger_multiplier


def _long_entry_addition_available(positions, current_close, market_state=None):
    long_positions = _count_positions_by_side(positions, "long")
    if long_positions <= 0:
        return True
    configured_adds = int(EXIT_PARAMS.get("pyramid_max_times", -1))
    long_capacity = float("inf") if configured_adds < 0 else configured_adds + 1
    if long_positions >= long_capacity:
        return False
    youngest_long_hold_bars = None
    for position in positions:
        if _position_side(position) != "long":
            continue
        hold_bars = max(int(position.get("hold_bars", 0)), 0)
        if youngest_long_hold_bars is None or hold_bars < youngest_long_hold_bars:
            youngest_long_hold_bars = hold_bars
    if youngest_long_hold_bars is not None and youngest_long_hold_bars >= LONG_REENTRY_COOLDOWN_BARS:
        return True
    trigger_pnl = _long_pyramid_trigger_pnl(market_state)
    return any(
        _position_close_pnl_pct(position, current_close) >= trigger_pnl
        for position in positions
        if _position_side(position) == "long"
    )


def _short_entry_addition_available(positions):
    return _count_positions_by_side(positions, "short") <= 0


def _long_time_exit_active(positions, current_close):
    if not positions or current_close <= 0.0:
        return False
    long_positions = [position for position in positions if _position_side(position) == "long"]
    if not long_positions:
        return False
    lead_position = long_positions[0]
    if int(lead_position.get("hold_bars", 0)) <= LONG_TIME_EXIT_MIN_HOLD_BARS:
        return False
    total_size = 0.0
    weighted_entry = 0.0
    for position in long_positions:
        size = max(float(position.get("size", 0.0)), 0.0)
        entry_price = float(position.get("entry_price", 0.0))
        if size <= 0.0 or entry_price <= 0.0:
            continue
        total_size += size
        weighted_entry += entry_price * size
    if total_size <= 0.0:
        return False
    avg_entry_price = weighted_entry / total_size
    price_move_pct = (current_close - avg_entry_price) / max(avg_entry_price, 1e-9)
    return price_move_pct < LONG_TIME_EXIT_MAX_PRICE_MOVE_PCT


def _long_profit_protect_exit_active(positions, market_state, current_bar, current_close):
    if not positions or current_close <= 0.0:
        return False
    long_positions = [position for position in positions if _position_side(position) == "long"]
    if not long_positions:
        return False

    total_size = 0.0
    weighted_entry = 0.0
    recent_high = max(float((current_bar or {}).get("high", current_close)), current_close)
    trailing_activation_ratio = None
    trailing_giveback_pct = None
    for position in long_positions:
        size = max(float(position.get("size", 0.0)), 0.0)
        entry_price = float(position.get("entry_price", 0.0))
        favorable_price = float(position.get("favorable_price", 0.0))
        if size <= 0.0 or entry_price <= 0.0:
            continue
        total_size += size
        weighted_entry += entry_price * size
        recent_high = max(recent_high, favorable_price, entry_price)
        position_activation_ratio = _trailing_activation_ratio_for_position(position, "long")
        if trailing_activation_ratio is None or position_activation_ratio < trailing_activation_ratio:
            trailing_activation_ratio = position_activation_ratio
        position_giveback_ratio = _trailing_giveback_ratio_for_position(position, "long")
        if trailing_giveback_pct is None or position_giveback_ratio < trailing_giveback_pct:
            trailing_giveback_pct = position_giveback_ratio
    if total_size <= 0.0:
        return False

    avg_entry_price = weighted_entry / total_size
    unrealized_profit_ratio = (current_close - avg_entry_price) / max(avg_entry_price, 1e-9)
    profit_protect_trigger = max(
        float(EXIT_PARAMS.get("take_profit", 0.0)),
        float(trailing_activation_ratio or 0.0),
    )
    if unrealized_profit_ratio < profit_protect_trigger:
        return False

    atr_ratio = max(float((market_state or {}).get("atr_ratio", 0.0)), 0.0)
    tightened_giveback_ratio = max(float(trailing_giveback_pct or 0.0), 0.0)
    tightened_giveback_ratio += atr_ratio * LONG_TRAILING_GIVEBACK_ATR_BUFFER
    if tightened_giveback_ratio <= 0.0 or recent_high <= 0.0:
        return False
    giveback_ratio = (recent_high - current_close) / max(recent_high, 1e-9)
    return giveback_ratio >= tightened_giveback_ratio


def _short_hourly_bull_exit_active(positions, market_state):
    if not positions or not bool((market_state or {}).get("hourly_bull", False)):
        return False
    for position in positions:
        if _position_side(position) != "short":
            continue
        if max(int(position.get("hold_bars", 0)), 0) >= SHORT_HOURLY_BULL_EXIT_MIN_HOLD_BARS:
            return True
    return False


# ==================== Flow And Participation Analysis ====================

def _flow_alignment_score(market_state, hourly, fourh, params, side):
    def _safe_float(payload, key, default):
        if payload is None:
            return default
        try:
            value = float(payload.get(key, default))
        except (TypeError, ValueError, AttributeError):
            return default
        return value

    intraday_trade_ratio = _safe_float(market_state, "trade_count_ratio", 1.0)
    intraday_buy_ratio = _safe_float(market_state, "taker_buy_ratio", 0.5)
    intraday_sell_ratio = _safe_float(market_state, "taker_sell_ratio", 0.5)
    intraday_imbalance = _safe_float(market_state, "flow_imbalance", 0.0)
    hourly_trade_ratio = _safe_float(hourly, "trade_count_ratio", 1.0)
    hourly_buy_ratio = _safe_float(hourly, "taker_buy_ratio", 0.5)
    hourly_sell_ratio = _safe_float(hourly, "taker_sell_ratio", 0.5)
    hourly_imbalance = _safe_float(hourly, "flow_imbalance", 0.0)
    fourh_buy_ratio = _safe_float(fourh, "taker_buy_ratio", 0.5)
    fourh_sell_ratio = _safe_float(fourh, "taker_sell_ratio", 0.5)
    fourh_imbalance = _safe_float(fourh, "flow_imbalance", 0.0)

    if side == "long":
        score = 0
        if intraday_trade_ratio >= params["breakout_trade_count_ratio_min"]:
            score += 1
        if intraday_buy_ratio >= params["breakout_taker_buy_ratio_min"]:
            score += 1
        if intraday_imbalance >= params["breakout_flow_imbalance_min"]:
            score += 1
        if hourly_trade_ratio >= params["hourly_trade_count_ratio_min"]:
            score += 1
        if hourly_buy_ratio >= params["hourly_taker_buy_ratio_min"]:
            score += 1
        if hourly_imbalance >= params["hourly_flow_confirmation_min"]:
            score += 1
        if fourh_buy_ratio >= params["fourh_taker_buy_ratio_min"]:
            score += 1
        if fourh_imbalance >= params["fourh_flow_confirmation_min"]:
            score += 1
        return score

    score = 0
    if intraday_trade_ratio >= 1.18:
        score += 1
    if intraday_sell_ratio >= 0.54:
        score += 1
    if intraday_imbalance <= -0.08:
        score += 1
    if hourly_trade_ratio >= 0.88:
        score += 1
    if hourly_sell_ratio >= 0.505:
        score += 1
    if hourly_imbalance <= -0.01:
        score += 1
    if fourh_sell_ratio >= 0.50:
        score += 1
    if fourh_imbalance <= 0.0:
        score += 1
    return score


def _flow_confirmation_ok(market_state, hourly, fourh, params, side, strong=False):
    score = _flow_alignment_score(market_state, hourly, fourh, params, side)

    intraday_imbalance = _safe_payload_float(market_state, "flow_imbalance", 0.0)
    hourly_buy_ratio = _safe_payload_float(hourly, "taker_buy_ratio", 0.5)
    hourly_sell_ratio = _safe_payload_float(hourly, "taker_sell_ratio", 0.5)
    hourly_imbalance = _safe_payload_float(hourly, "flow_imbalance", 0.0)
    fourh_buy_ratio = _safe_payload_float(fourh, "taker_buy_ratio", 0.5)
    fourh_sell_ratio = _safe_payload_float(fourh, "taker_sell_ratio", 0.5)
    fourh_imbalance = _safe_payload_float(fourh, "flow_imbalance", 0.0)

    if side == "long":
        long_quality_ready = _trend_quality_long(market_state)
        long_flow_bias_score = _count_true(
            intraday_imbalance >= params["breakout_flow_imbalance_min"],
            hourly_buy_ratio >= params["hourly_taker_buy_ratio_min"],
            hourly_imbalance >= params["hourly_flow_confirmation_min"],
            fourh_buy_ratio >= params["fourh_taker_buy_ratio_min"],
            fourh_imbalance >= params["fourh_flow_confirmation_min"],
        )
        if strong:
            if long_quality_ready:
                return (
                    long_flow_bias_score >= 4
                    and intraday_imbalance >= max(params["breakout_flow_imbalance_min"], 0.02)
                    and hourly_imbalance >= -0.01
                    and fourh_imbalance >= -0.02
                    and hourly_buy_ratio >= max(params["hourly_taker_buy_ratio_min"], 0.5)
                    and fourh_buy_ratio >= max(params["fourh_taker_buy_ratio_min"], 0.495)
                )
            return (
                score >= params["breakout_flow_score_strong_min"]
                and intraday_imbalance >= max(params["breakout_flow_imbalance_min"], 0.02)
                and hourly_imbalance >= -0.01
                and fourh_imbalance >= -0.02
                and hourly_buy_ratio >= max(params["hourly_taker_buy_ratio_min"], 0.5)
                and fourh_buy_ratio >= max(params["fourh_taker_buy_ratio_min"], 0.495)
            )
        if long_quality_ready:
            return (
                long_flow_bias_score >= 3
                and intraday_imbalance >= -0.02
                and fourh_imbalance >= -0.03
            )
        return (
            score >= params["breakout_flow_score_min"]
            and intraday_imbalance >= -0.02
            and fourh_imbalance >= -0.03
        )

    if strong:
        return (
            score >= 7
            and intraday_imbalance <= -0.08
            and hourly_imbalance <= -0.01
            and fourh_imbalance <= -0.005
            and _safe_payload_float(market_state, "taker_sell_ratio", 0.5) >= 0.545
            and hourly_sell_ratio >= 0.512
            and fourh_sell_ratio >= 0.502
        )
    return (
        score >= 6
        and intraday_imbalance <= -0.02
        and hourly_imbalance <= 0.0
        and _safe_payload_float(market_state, "taker_sell_ratio", 0.5) >= 0.535
        and hourly_sell_ratio >= 0.505
        and fourh_sell_ratio >= 0.50
        and fourh_imbalance <= 0.0
    )


def _flow_signal_metrics(market_state, hourly, fourh, params, side):
    intraday_trade_ratio = _safe_payload_float(market_state, "trade_count_ratio", 1.0)
    intraday_buy_ratio = _safe_payload_float(market_state, "taker_buy_ratio", 0.5)
    intraday_sell_ratio = _safe_payload_float(market_state, "taker_sell_ratio", 0.5)
    intraday_imbalance = _safe_payload_float(market_state, "flow_imbalance", 0.0)
    hourly_trade_ratio = _safe_payload_float(hourly, "trade_count_ratio", 1.0)
    hourly_buy_ratio = _safe_payload_float(hourly, "taker_buy_ratio", 0.5)
    hourly_sell_ratio = _safe_payload_float(hourly, "taker_sell_ratio", 0.5)
    hourly_imbalance = _safe_payload_float(hourly, "flow_imbalance", 0.0)
    fourh_buy_ratio = _safe_payload_float(fourh, "taker_buy_ratio", 0.5)
    fourh_sell_ratio = _safe_payload_float(fourh, "taker_sell_ratio", 0.5)
    fourh_imbalance = _safe_payload_float(fourh, "flow_imbalance", 0.0)

    if side == "long":
        participation_bias = (
            max(intraday_trade_ratio - params["breakout_trade_count_ratio_min"], 0.0)
            + max(hourly_trade_ratio - params["hourly_trade_count_ratio_min"], 0.0) * 0.5
        )
        directional_bias = (
            max(intraday_buy_ratio - params["breakout_taker_buy_ratio_min"], 0.0)
            + max(hourly_buy_ratio - params["hourly_taker_buy_ratio_min"], 0.0)
            + max(fourh_buy_ratio - params["fourh_taker_buy_ratio_min"], 0.0)
            + max(intraday_imbalance - params["breakout_flow_imbalance_min"], 0.0) * 2.0
            + max(hourly_imbalance - params["hourly_flow_confirmation_min"], 0.0)
            + max(fourh_imbalance - params["fourh_flow_confirmation_min"], 0.0)
        )
    else:
        participation_bias = (
            max(intraday_trade_ratio - 1.18, 0.0)
            + max(hourly_trade_ratio - 0.88, 0.0) * 0.5
        )
        directional_bias = (
            max(intraday_sell_ratio - 0.54, 0.0)
            + max(hourly_sell_ratio - 0.505, 0.0)
            + max(fourh_sell_ratio - 0.50, 0.0)
            + max(-intraday_imbalance - 0.08, 0.0) * 2.0
            + max(-hourly_imbalance - 0.01, 0.0)
            + max(-fourh_imbalance, 0.0)
        )
    return {
        "score": _flow_alignment_score(market_state, hourly, fourh, params, side),
        "participation_bias": participation_bias,
        "directional_bias": directional_bias,
    }


def _flow_entry_ok(market_state, hourly, fourh, params, side=None, strong=False):
    entry_side = side if side in {"long", "short"} else "short"
    if entry_side == "long" and not strong:
        intraday_imbalance = _safe_payload_float(market_state, "flow_imbalance", 0.0)
        hourly_imbalance = _safe_payload_float(hourly, "flow_imbalance", 0.0)
        fourh_imbalance = _safe_payload_float(fourh, "flow_imbalance", 0.0)
        return intraday_imbalance >= -0.08 and hourly_imbalance >= -0.06 and fourh_imbalance >= -0.06
    return _flow_confirmation_ok(market_state, hourly, fourh, params, entry_side, strong=strong)


def _build_signal_context(data, idx, market_state, params):
    current = data[idx]
    prev = data[idx - 1]
    pre_prev = data[idx - 2]
    hourly = market_state["hourly"]
    fourh = market_state["four_hour"]
    if hourly is None or fourh is None:
        return None
    if not (_bar_is_valid(current) and _bar_is_valid(prev) and _bar_is_valid(pre_prev)):
        return None

    intraday = _intraday_trend_metrics(market_state)
    current_candle = _candle_metrics(current)
    prev_candle = _candle_metrics(prev)
    pre_prev_candle = _candle_metrics(pre_prev)
    avg_volume = max(_avg(data, idx - params["volume_lookback"] + 1, idx, "volume"), 1e-9)
    atr_ratio = market_state["atr_ratio"]
    breakout_high = _long_breakout_reference_high(
        data,
        idx - params["breakout_lookback"],
        idx - 1,
        atr_ratio,
    )
    prev_breakout_high = _long_breakout_reference_high(
        data,
        idx - params["breakout_lookback"] - 1,
        idx - 2,
        atr_ratio,
    )
    breakout_reference_stale_gap_pct = max(
        (
            _window_max(data, idx - params["breakout_lookback"], idx - 1, "high")
            - breakout_high
        )
        / max(breakout_high, 1e-9),
        0.0,
    )
    breakdown_low = _window_min(data, idx - params["breakdown_lookback"], idx - 1, "low")
    prev_breakdown_low = _window_min(data, idx - params["breakdown_lookback"] - 1, idx - 2, "low")
    recent_stats = _recent_window_stats(data, idx, 6, current["close"])
    reversal_reference_low = _window_min(data, idx - 20, idx - 1, "low")
    reversal_volume_avg = max(_avg(data, idx - 5, idx - 1, "volume"), 1e-9)
    short_breakdown_veto_volume_avg = max(
        _avg(data, idx - 20, idx - 1, "volume"),
        1e-9,
    )

    return {
        "current": current,
        "prev": prev,
        "pre_prev": pre_prev,
        "hourly": hourly,
        "fourh": fourh,
        "intraday": intraday,
        "intraday_bull_ema": _ema(
            data,
            0,
            idx,
            "close",
            INTRADAY_BULL_EMA_PERIOD,
        ),
        "current_candle": current_candle,
        "prev_candle": prev_candle,
        "pre_prev_candle": pre_prev_candle,
        "volume_ratio": current["volume"] / avg_volume,
        "prev_volume": max(prev["volume"], 1e-9),
        "pre_prev_volume": max(pre_prev["volume"], 1e-9),
        "breakout_high": breakout_high,
        "prev_breakout_high": prev_breakout_high,
        "breakout_reference_stale_gap_pct": breakout_reference_stale_gap_pct,
        "breakdown_low": breakdown_low,
        "prev_breakdown_low": prev_breakdown_low,
        "atr_ratio": atr_ratio,
        "breakout_distance_pct": (current["close"] - breakout_high) / max(breakout_high, 1e-9),
        "breakout_high_penetration_pct": max((current["high"] - breakout_high) / max(breakout_high, 1e-9), 0.0),
        "prev_breakout_distance_pct": max((prev["close"] - breakout_high) / max(breakout_high, 1e-9), 0.0),
        "prev_breakout_reference_distance_pct": max((prev["close"] - prev_breakout_high) / max(prev_breakout_high, 1e-9), 0.0),
        "prev_breakout_high_penetration_pct": max((prev["high"] - prev_breakout_high) / max(prev_breakout_high, 1e-9), 0.0),
        "breakout_reclaim_gap_pct": max((breakout_high - current["close"]) / max(breakout_high, 1e-9), 0.0),
        "breakout_reclaim_high_gap_pct": max((breakout_high - current["high"]) / max(breakout_high, 1e-9), 0.0),
        "breakdown_distance_pct": (breakdown_low - current["close"]) / max(breakdown_low, 1e-9),
        "breakdown_low_penetration_pct": max((breakdown_low - current["low"]) / max(breakdown_low, 1e-9), 0.0),
        "prev_breakdown_distance_pct": max((breakdown_low - prev["close"]) / max(breakdown_low, 1e-9), 0.0),
        "prev_breakdown_reference_distance_pct": max((prev_breakdown_low - prev["close"]) / max(prev_breakdown_low, 1e-9), 0.0),
        "prev_breakdown_low_penetration_pct": max((prev_breakdown_low - prev["low"]) / max(prev_breakdown_low, 1e-9), 0.0),
        "hourly_fast_extension_pct": (current["close"] - hourly["ema_fast"]) / max(current["close"], 1e-9),
        "hourly_anchor_extension_pct": (current["close"] - hourly["ema_anchor"]) / max(current["close"], 1e-9),
        "hourly_fast_discount_pct": (hourly["ema_fast"] - current["close"]) / max(current["close"], 1e-9),
        "hourly_anchor_discount_pct": (hourly["ema_anchor"] - current["close"]) / max(current["close"], 1e-9),
        "current_range": _bar_range(current),
        "prev_range": _bar_range(prev),
        "prev_prev_range": _bar_range(pre_prev),
        "recent_range_avg": recent_stats["range_avg"],
        "recent_volume_avg": recent_stats["volume_avg"],
        "recent_body_ratio_avg": recent_stats["body_ratio_avg"],
        "reversal_reference_low": reversal_reference_low,
        "reversal_volume_avg": reversal_volume_avg,
        "short_breakdown_veto_volume_avg": short_breakdown_veto_volume_avg,
    }


# ==================== Regime Analysis ====================

def _build_long_trend_state(context, market_state, params):
    current = context["current"]
    hourly = context["hourly"]
    fourh = context["fourh"]
    fourh_bull_base_core = (
        fourh["close"] > fourh["ema_slow"]
        and fourh["trend_spread_pct"] > 0.0
        and fourh["ema_slow_slope_pct"] >= 0.0
    )
    fourh_fast_support = fourh["close"] >= fourh["ema_fast"]
    fourh_macd_support = (
        fourh["macd_line"] > fourh["signal_line"]
        and fourh["adx"] >= max(params["fourh_adx_min"] - 1.0, 11.5)
    )
    fourh_bull_turn_core = (
        fourh["close"] > fourh["ema_slow"]
        and fourh["trend_spread_pct"] > 0.0
        and fourh["ema_slow_slope_pct"] >= 0.0
    )
    fourh_turn_fast_support = (
        fourh["close"] >= fourh["ema_fast"]
        and fourh["ema_fast"] >= fourh["ema_slow"]
    )
    fourh_turn_macd_support = (
        fourh["macd_line"] > fourh["signal_line"]
        and fourh["adx"] >= max(params["fourh_adx_min"] - 0.8, 11.8)
    )
    return {
        "intraday_bull": (
            market_state["adx"] > INTRADAY_BULL_ADX_MIN
            and current["close"] > context["intraday_bull_ema"]
        ),
        "hourly_bull": (
            hourly["close"] > hourly["ema_fast"] > hourly["ema_slow"]
            and hourly["close"] > hourly["ema_anchor"]
            and hourly["macd_line"] > hourly["signal_line"]
            and hourly["adx"] >= params["hourly_adx_min"]
            and hourly["trend_spread_pct"] > 0.0
            and hourly["ema_slow_slope_pct"] > 0.0
        ),
        "hourly_neutral": (
            hourly["close"] >= hourly["ema_slow"]
            and hourly["macd_line"] >= hourly["signal_line"]
            and hourly["trend_spread_pct"] >= 0.0
            and hourly["ema_slow_slope_pct"] >= 0.0
            and hourly["adx"] >= max(params["hourly_adx_min"] - 5.0, 14.0)
        ),
        "hourly_bear": (
            hourly["close"] < hourly["ema_fast"] < hourly["ema_slow"]
            and hourly["close"] < hourly["ema_anchor"]
            and hourly["macd_line"] < hourly["signal_line"]
            and hourly["adx"] >= params["hourly_adx_min"]
            and hourly["trend_spread_pct"] < 0.0
            and hourly["ema_slow_slope_pct"] < 0.0
        ),
        "fourh_bull": (
            fourh["close"] > fourh["ema_fast"] > fourh["ema_slow"]
            and fourh["macd_line"] > fourh["signal_line"]
            and fourh["adx"] >= params["fourh_adx_min"]
            and fourh["trend_spread_pct"] > 0.0
            and fourh["ema_slow_slope_pct"] > 0.0
        ),
        "fourh_bull_base": (
            fourh_bull_base_core
            and (fourh_fast_support or fourh_macd_support)
        ),
        "fourh_bull_turn": (
            fourh_bull_turn_core
            and (fourh_turn_fast_support or fourh_turn_macd_support)
        ),
        "fourh_bear": _fourh_bear_state(fourh, params),
    }


def _fourh_bear_state(fourh, params):
    return (
        fourh["close"] < fourh["ema_slow"]
        and fourh["trend_spread_pct"] < 0.0
        and fourh["ema_slow_slope_pct"] < 0.0
        and fourh["adx"] >= max(params["fourh_adx_min"] - 0.5, 12.0)
    )


def _build_short_trend_state(context, market_state, params):
    current = context["current"]
    hourly = context["hourly"]
    fourh = context["fourh"]
    return {
        "intraday_bear": (
            current["close"] < market_state["ema_fast"] < market_state["ema_slow"]
            and market_state["adx"] >= params["intraday_adx_min"]
            and market_state["macd_line"] < market_state["signal_line"]
        ),
        "hourly_bear": (
            hourly["close"] < hourly["ema_fast"] < hourly["ema_slow"]
            and hourly["close"] < hourly["ema_anchor"]
            and hourly["macd_line"] < hourly["signal_line"]
            and hourly["adx"] >= params["hourly_adx_min"]
            and hourly["trend_spread_pct"] < 0.0
            and hourly["ema_slow_slope_pct"] < 0.0
        ),
        "fourh_bear": _fourh_bear_state(fourh, params),
        "fourh_bear_confirmed": (
            fourh["close"] < fourh["ema_fast"] < fourh["ema_slow"]
            and fourh["macd_line"] < fourh["signal_line"]
            and fourh["trend_spread_pct"] < 0.0
            and fourh["ema_slow_slope_pct"] < 0.0
        ),
    }


def _sideways_release_flags(market_state, positions=None):
    hourly = market_state["hourly"]
    fourh = market_state["four_hour"]
    intraday = _intraday_trend_metrics(market_state)
    intraday_chop = market_state["chop"]
    hourly_chop = hourly["chop"]
    atr_ratio = market_state["atr_ratio"]
    intraday_spread = abs(intraday["spread_pct"])
    hourly_spread = abs(hourly["trend_spread_pct"])
    fourh_spread = abs(fourh["trend_spread_pct"])
    hourly_slope = abs(hourly["ema_slow_slope_pct"])
    fourh_slope = abs(fourh["ema_slow_slope_pct"])
    intraday_directional_spread = intraday["spread_pct"]
    intraday_directional_slope = intraday["slope_pct"]
    adx_soft = hourly["adx"] <= SIDEWAYS_MAX_HOURLY_ADX and fourh["adx"] <= SIDEWAYS_MAX_FOURH_ADX
    aligned_trend = hourly["trend_spread_pct"] * fourh["trend_spread_pct"] > 0.0
    long_pullback_hold = _long_pullback_hold_active(positions)
    relax = SIDEWAYS_RELEASE_RELAX

    intraday_trade_ratio = _safe_payload_float(market_state, "trade_count_ratio", 1.0)
    hourly_trade_ratio = _safe_payload_float(hourly, "trade_count_ratio", 1.0)
    intraday_flow_imbalance = _safe_payload_float(market_state, "flow_imbalance", 0.0)
    hourly_flow_imbalance = _safe_payload_float(hourly, "flow_imbalance", 0.0)
    long_flow_metrics = _flow_signal_metrics(market_state, hourly, fourh, PARAMS, "long")
    mild_long_pullback = (
        long_pullback_hold
        and hourly["trend_spread_pct"] > 0.0
        and fourh["trend_spread_pct"] > 0.0
        and intraday_directional_spread >= -max(atr_ratio * 0.08, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 0.22)
        and intraday_directional_slope >= -atr_ratio * 0.040
        and hourly["trend_spread_pct"] >= max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 0.84, atr_ratio * 0.46)
        and fourh["trend_spread_pct"] >= max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 0.46, atr_ratio * 0.38)
        and hourly["ema_slow_slope_pct"] >= -atr_ratio * 0.016
        and fourh["ema_slow_slope_pct"] >= -atr_ratio * 0.008
        and intraday_trade_ratio >= max(PARAMS["breakout_trade_count_ratio_min"] - 0.20, 0.84)
        and hourly_trade_ratio >= max(PARAMS["hourly_trade_count_ratio_min"] - 0.08, 0.68)
        and intraday_flow_imbalance >= -0.07
        and hourly_flow_imbalance >= -0.04
        and long_flow_metrics["directional_bias"] >= 0.0
    )
    convexity_release = (
        aligned_trend
        and intraday_spread >= atr_ratio * 0.26
        and hourly_spread >= max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.10 * relax["spread_floor_mult"], atr_ratio * 0.66 * relax["spread_floor_mult"])
        and fourh_spread >= max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 0.50 * relax["spread_floor_mult"], atr_ratio * 0.48 * relax["spread_floor_mult"])
        and fourh_spread <= max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 1.18, atr_ratio * 0.98 * relax["atr_ceiling_mult"])
        and hourly_slope >= max(hourly_spread * 0.10 * relax["slope_floor_mult"], atr_ratio * 0.082 * relax["slope_floor_mult"])
        and fourh_slope >= max(fourh_spread * 0.18 * relax["slope_floor_mult"], atr_ratio * 0.028 * relax["slope_floor_mult"])
        and market_state["adx"] >= 13.5
        and hourly["adx"] >= 18.0
        and fourh["adx"] >= 12.0
    )
    trend_awakening = (
        aligned_trend
        and intraday_spread >= atr_ratio * 0.24
        and intraday_spread <= max(hourly_spread * 1.92, atr_ratio * 0.98 * relax["atr_ceiling_mult"])
        and hourly_spread >= max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 0.92 * relax["spread_floor_mult"], atr_ratio * 0.54 * relax["spread_floor_mult"])
        and fourh_spread >= max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 0.42 * relax["spread_floor_mult"], atr_ratio * 0.40 * relax["spread_floor_mult"])
        and fourh_spread <= max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 1.08, atr_ratio * 0.90 * relax["atr_ceiling_mult"])
        and hourly_slope >= max(hourly_spread * 0.12 * relax["slope_floor_mult"], atr_ratio * 0.080 * relax["slope_floor_mult"])
        and fourh_slope >= max(fourh_spread * 0.20 * relax["slope_floor_mult"], atr_ratio * 0.028 * relax["slope_floor_mult"])
        and market_state["adx"] >= 13.0
        and hourly["adx"] >= 17.0
        and fourh["adx"] >= 11.8
        and intraday_chop < SIDEWAYS_HARD_INTRADAY_CHOP_MIN + relax["chop_buffer"]
        and hourly_chop < SIDEWAYS_HARD_HOURLY_CHOP_MIN + relax["chop_buffer"]
    )
    fresh_directional_expansion = (
        aligned_trend
        and intraday_spread >= atr_ratio * 0.22
        and intraday_spread <= max(hourly_spread * 1.35, atr_ratio * 0.92 * relax["atr_ceiling_mult"])
        and hourly_spread >= max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.02 * relax["spread_floor_mult"], atr_ratio * 0.60 * relax["spread_floor_mult"])
        and fourh_spread >= max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 0.56 * relax["spread_floor_mult"], atr_ratio * 0.52 * relax["spread_floor_mult"])
        and fourh_spread <= max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 1.52, atr_ratio * 1.18 * relax["atr_ceiling_mult"])
        and hourly_slope >= max(hourly_spread * 0.13 * relax["slope_floor_mult"], atr_ratio * 0.084 * relax["slope_floor_mult"])
        and fourh_slope >= max(fourh_spread * 0.22 * relax["slope_floor_mult"], atr_ratio * 0.032 * relax["slope_floor_mult"])
        and market_state["adx"] >= 14.0
        and hourly["adx"] >= 18.5
        and fourh["adx"] >= 12.5
    )
    exhausted_drift = (
        aligned_trend
        and hourly_spread >= max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.40, atr_ratio * 0.96)
        and fourh_spread >= max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 1.08, atr_ratio * 0.96)
        and intraday_spread < max(hourly_spread * 0.26, atr_ratio * 0.28)
        and hourly_slope < max(hourly_spread * 0.07, atr_ratio * 0.070)
        and fourh_slope < max(fourh_spread * 0.08, atr_ratio * 0.032)
        and (intraday_chop >= SIDEWAYS_INTRADAY_CHOP_MIN - 2.0 or hourly_chop >= SIDEWAYS_HOURLY_CHOP_MIN - 2.0)
    )
    hard_sideways = (
        (
            intraday_chop >= SIDEWAYS_HARD_INTRADAY_CHOP_MIN
            and hourly_chop >= SIDEWAYS_HARD_HOURLY_CHOP_MIN
            and adx_soft
        )
        or (
            atr_ratio < SIDEWAYS_MIN_ATR_RATIO * relax["hard_sideways_atr_mult"]
            and hourly_spread < SIDEWAYS_MIN_HOURLY_SPREAD_PCT * relax["hard_sideways_spread_mult"]
            and fourh_spread < SIDEWAYS_MIN_FOURH_SPREAD_PCT * relax["hard_sideways_spread_mult"]
            and not (convexity_release or trend_awakening or fresh_directional_expansion)
        )
        or (
            hourly_spread < SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 0.92
            and fourh_spread < SIDEWAYS_MIN_FOURH_SPREAD_PCT * 0.92
            and hourly_slope < atr_ratio * 0.06
            and fourh_slope < atr_ratio * 0.03
        )
    )
    extreme_compression = (
        intraday_chop >= SIDEWAYS_HARD_INTRADAY_CHOP_MIN + 2.0
        and hourly_chop >= SIDEWAYS_HARD_HOURLY_CHOP_MIN + 2.0
        and atr_ratio < SIDEWAYS_MIN_ATR_RATIO * relax["extreme_compression_atr_mult"]
        and hourly_spread < SIDEWAYS_MIN_HOURLY_SPREAD_PCT * relax["extreme_compression_spread_mult"]
        and fourh_spread < SIDEWAYS_MIN_FOURH_SPREAD_PCT * relax["extreme_compression_spread_mult"]
    )
    return {
        "intraday_spread": intraday_spread,
        "hourly_spread": hourly_spread,
        "fourh_spread": fourh_spread,
        "hourly_slope": hourly_slope,
        "fourh_slope": fourh_slope,
        "intraday_chop": intraday_chop,
        "hourly_chop": hourly_chop,
        "atr_ratio": atr_ratio,
        "adx_soft": adx_soft,
        "aligned_trend": aligned_trend,
        "mild_long_pullback": mild_long_pullback,
        "convexity_release": convexity_release,
        "trend_awakening": trend_awakening,
        "fresh_directional_expansion": fresh_directional_expansion,
        "exhausted_drift": exhausted_drift,
        "hard_sideways": hard_sideways,
        "extreme_compression": extreme_compression,
    }


def _sideways_signal_count(
    intraday_chop,
    hourly_chop,
    atr_ratio,
    hourly_spread,
    fourh_spread,
    intraday_spread,
    hourly_slope,
    fourh_slope,
    adx_soft,
    convexity_release,
    fresh_directional_expansion,
    mild_long_pullback,
    extreme_compression,
):
    signals = _count_true(
        _all_true(intraday_chop >= SIDEWAYS_INTRADAY_CHOP_MIN, hourly_chop >= SIDEWAYS_HOURLY_CHOP_MIN),
        _all_true(atr_ratio < SIDEWAYS_MIN_ATR_RATIO, hourly_chop >= SIDEWAYS_HOURLY_CHOP_MIN - 1.0),
        _all_true(hourly_spread < SIDEWAYS_MIN_HOURLY_SPREAD_PCT, fourh_spread < SIDEWAYS_MIN_FOURH_SPREAD_PCT),
        _all_true(
            intraday_spread < atr_ratio * 0.28,
            hourly_slope < atr_ratio * 0.08,
            fourh_slope < atr_ratio * 0.04,
        ),
        adx_soft,
    )
    if _any_true(convexity_release, fresh_directional_expansion):
        signals -= 2
    if _all_true(mild_long_pullback, not extreme_compression):
        signals -= 1
    return signals


def _sideways_structure_blocked(
    intraday,
    hourly,
    fourh,
    intraday_spread,
    hourly_spread,
    fourh_spread,
    hourly_slope,
    fourh_slope,
    atr_ratio,
    intraday_chop,
    hourly_chop,
    adx_soft,
    mild_long_pullback,
):
    mixed_trend = (
        hourly["trend_spread_pct"] * fourh["trend_spread_pct"] <= 0.0
        and intraday_spread < max(atr_ratio * 0.55, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.15)
    )
    if mixed_trend and (hourly_chop >= SIDEWAYS_HOURLY_CHOP_MIN - 1.0 or adx_soft):
        return True

    weak_trend = (
        hourly_spread < max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.20, atr_ratio * 0.72)
        and fourh_spread < max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 1.15, atr_ratio * 0.92)
        and hourly_slope < atr_ratio * 0.09
        and fourh_slope < atr_ratio * 0.045
    )
    if weak_trend and (intraday_chop >= SIDEWAYS_INTRADAY_CHOP_MIN - 1.0 or adx_soft) and not mild_long_pullback:
        return True

    bull_front_run = (
        hourly["trend_spread_pct"] > 0.0
        and fourh["trend_spread_pct"] > 0.0
        and intraday["spread_pct"] > max(hourly_spread * 1.85, atr_ratio * 1.00)
        and hourly_spread < max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.55, atr_ratio * 0.95)
        and fourh_spread < max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 1.20, atr_ratio * 1.02)
        and hourly_slope < atr_ratio * 0.10
        and fourh_slope < atr_ratio * 0.05
        and (hourly_chop >= SIDEWAYS_HOURLY_CHOP_MIN - 2.0 or adx_soft)
    )
    return bull_front_run and not mild_long_pullback


def _is_sideways_regime(market_state, positions=None):
    intraday = _intraday_trend_metrics(market_state)
    hourly = market_state["hourly"]
    fourh = market_state["four_hour"]
    release_flags = _sideways_release_flags(market_state, positions=positions)
    intraday_spread = release_flags["intraday_spread"]
    hourly_spread = release_flags["hourly_spread"]
    fourh_spread = release_flags["fourh_spread"]
    hourly_slope = release_flags["hourly_slope"]
    fourh_slope = release_flags["fourh_slope"]
    intraday_chop = release_flags["intraday_chop"]
    hourly_chop = release_flags["hourly_chop"]
    atr_ratio = release_flags["atr_ratio"]
    adx_soft = release_flags["adx_soft"]
    mild_long_pullback = bool(release_flags.get("mild_long_pullback", False))
    convexity_release = bool(release_flags.get("convexity_release", False))
    trend_awakening = bool(release_flags.get("trend_awakening", False))
    fresh_directional_expansion = bool(release_flags.get("fresh_directional_expansion", False))
    exhausted_drift = bool(release_flags.get("exhausted_drift", False))
    hard_sideways = bool(release_flags.get("hard_sideways", False))
    extreme_compression = bool(release_flags.get("extreme_compression", False))
    if hard_sideways and not (mild_long_pullback and not extreme_compression):
        return True
    if exhausted_drift and not convexity_release and not mild_long_pullback:
        return True
    if trend_awakening or fresh_directional_expansion:
        return False

    if _sideways_structure_blocked(
        intraday,
        hourly,
        fourh,
        intraday_spread,
        hourly_spread,
        fourh_spread,
        hourly_slope,
        fourh_slope,
        atr_ratio,
        intraday_chop,
        hourly_chop,
        adx_soft,
        mild_long_pullback,
    ):
        return True

    signals = _sideways_signal_count(
        intraday_chop,
        hourly_chop,
        atr_ratio,
        hourly_spread,
        fourh_spread,
        intraday_spread,
        hourly_slope,
        fourh_slope,
        adx_soft,
        convexity_release,
        fresh_directional_expansion,
        mild_long_pullback,
        extreme_compression,
    )
    return signals >= 3


# ==================== Trend Quality And Followthrough ====================

def _directional_trend_metrics(market_state, side):
    intraday = _intraday_trend_metrics(market_state)
    hourly = market_state["hourly"]
    fourh = market_state["four_hour"]
    direction = 1.0 if side == "long" else -1.0
    return {
        "intraday_spread": direction * intraday["spread_pct"],
        "hourly_spread": direction * hourly["trend_spread_pct"],
        "fourh_spread": direction * fourh["trend_spread_pct"],
        "hourly_slope": direction * hourly["ema_slow_slope_pct"],
        "fourh_slope": direction * fourh["ema_slow_slope_pct"],
        "atr_ratio": market_state["atr_ratio"],
    }


def _trend_quality_long(market_state):
    p = PARAMS
    hourly = market_state["hourly"]
    fourh = market_state["four_hour"]
    metrics = _directional_trend_metrics(market_state, "long")
    atr_ratio = metrics["atr_ratio"]
    intraday_adx_gate = max(p["intraday_adx_min"] - 0.3, 12.2)

    confirms = _count_true(
        market_state["adx"] >= intraday_adx_gate,
        metrics["intraday_spread"] >= atr_ratio * 0.25,
        metrics["hourly_spread"] >= max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.10, atr_ratio * 0.66),
        metrics["fourh_spread"] >= max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 0.62, atr_ratio * 0.58),
        metrics["hourly_slope"] >= atr_ratio * 0.064 and metrics["fourh_slope"] >= atr_ratio * 0.025,
    )

    hourly_fast_extension = (hourly["close"] - hourly["ema_fast"]) / max(hourly["close"], 1e-9)
    hourly_anchor_extension = (hourly["close"] - hourly["ema_anchor"]) / max(hourly["close"], 1e-9)
    fourh_expansion_floor = (
        metrics["fourh_spread"] >= max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 0.58, atr_ratio * 0.56)
        and metrics["fourh_slope"] >= atr_ratio * 0.028
        and fourh["adx"] >= max(p["fourh_adx_min"] - 0.2, 12.8)
    )
    overextended_without_fourh = (
        hourly_fast_extension >= max(atr_ratio * 0.88, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 2.00)
        and hourly_anchor_extension >= max(atr_ratio * 1.32, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 3.10)
        and not fourh_expansion_floor
    )
    if overextended_without_fourh:
        return False
    return confirms >= 4


def _fourh_trend_quality_long_score(market_state, params):
    fourh = market_state["four_hour"]
    metrics = _directional_trend_metrics(market_state, "long")
    atr_ratio = metrics["atr_ratio"]

    confirms = _count_true(
        metrics["fourh_spread"] >= max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 0.70, atr_ratio * 0.66),
        metrics["fourh_slope"] >= atr_ratio * 0.028,
        fourh["adx"] >= max(params["fourh_adx_min"] - 0.2, 12.8),
        fourh["close"] >= fourh["ema_fast"] or fourh["macd_line"] > fourh["signal_line"],
    )
    return confirms / 4.0


def _trend_quality_short(market_state):
    p = PARAMS
    hourly = market_state["hourly"]
    fourh = market_state["four_hour"]
    metrics = _directional_trend_metrics(market_state, "short")
    atr_ratio = metrics["atr_ratio"]
    intraday_adx_gate = max(p["intraday_adx_min"] * 1.34, 16.8)
    hourly_adx_gate = max(p["hourly_adx_min"] * 1.28, p["hourly_adx_min"] + 3.5)
    fourh_adx_gate = max(p["fourh_adx_min"] * 1.24, p["fourh_adx_min"] + 2.4)
    histogram_pressure_floor = max(p["breakdown_hist_max"] * 0.044, 0.52)

    confirms = _count_true(
        market_state["adx"] >= intraday_adx_gate,
        metrics["intraday_spread"] >= atr_ratio * 0.30,
        metrics["hourly_spread"] >= max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.24, atr_ratio * 0.78),
        metrics["fourh_spread"] >= max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 0.78, atr_ratio * 0.72),
        metrics["hourly_slope"] >= atr_ratio * 0.076 and metrics["fourh_slope"] >= atr_ratio * 0.032,
    )

    hourly_fast_discount = (hourly["ema_fast"] - hourly["close"]) / max(hourly["close"], 1e-9)
    hourly_anchor_discount = (hourly["ema_anchor"] - hourly["close"]) / max(hourly["close"], 1e-9)
    fourh_participation_ok = (
        metrics["fourh_spread"] >= max(metrics["hourly_spread"] * 0.74, atr_ratio * 0.78)
        and metrics["fourh_slope"] >= atr_ratio * 0.032
        and fourh["adx"] >= fourh_adx_gate
    )
    fresh_pressure_ok = (
        metrics["hourly_spread"] >= max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.54, atr_ratio * 0.92)
        and metrics["fourh_spread"] >= max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 0.84, atr_ratio * 0.78)
        and metrics["hourly_slope"] >= atr_ratio * 0.088
        and metrics["fourh_slope"] >= atr_ratio * 0.036
        and market_state["adx"] >= max(intraday_adx_gate - 0.6, 16.2)
    )
    macd_pressure_ok = (
        market_state["histogram"] <= -histogram_pressure_floor
        and market_state["macd_line"] < market_state["signal_line"]
        and hourly["macd_line"] < hourly["signal_line"]
        and fourh["macd_line"] < fourh["signal_line"]
    )
    overdiscounted_without_fourh = (
        hourly_fast_discount >= max(atr_ratio * 0.96, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 2.18)
        and hourly_anchor_discount >= max(atr_ratio * 1.52, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 3.62)
        and not fourh_participation_ok
    )
    if overdiscounted_without_fourh and not fresh_pressure_ok:
        return False
    return (
        confirms >= 4
        and macd_pressure_ok
        and hourly["adx"] >= hourly_adx_gate
        and (fourh_participation_ok or fresh_pressure_ok)
    )


def _trend_quality_ok(market_state, side):
    if side == "long":
        return _trend_quality_long(market_state)
    return _trend_quality_short(market_state)


def _impulse_passes_final_check(decision, market_state):
    if not isinstance(decision, dict):
        return False
    entry_path_tag = str(
        decision.get("entry_path_tag")
        or ENTRY_PATH_TAGS.get(str(decision.get("entry_path_key", "")).strip(), "")
        or ""
    ).strip()
    if entry_path_tag != "short_impulse":
        return True
    hourly = (market_state or {}).get("hourly", {})
    hourly_adx = _safe_payload_float(hourly, "adx", 0.0)
    net_flow_delta = _safe_payload_float(market_state, "net_flow_delta", None)
    if net_flow_delta is None:
        net_flow_delta = _safe_payload_float(hourly, "net_flow_delta", None)
    if net_flow_delta is None:
        net_flow_delta = _safe_payload_float(market_state, "flow_imbalance", 0.0)
    return hourly_adx >= 26.0 and net_flow_delta < -0.3


def _trend_followthrough_long(market_state, trigger_price, current_close):
    hourly = market_state["hourly"]
    fourh = market_state["four_hour"]
    metrics = _directional_trend_metrics(market_state, "long")
    atr_ratio = metrics["atr_ratio"]
    breakout_distance_pct = (current_close - trigger_price) / max(trigger_price, 1e-9)
    hourly_fast_extension = (current_close - hourly["ema_fast"]) / max(current_close, 1e-9)
    hourly_anchor_extension = (current_close - hourly["ema_anchor"]) / max(current_close, 1e-9)
    quality_ready = _trend_quality_long(market_state)

    confirms = _count_true(
        metrics["intraday_spread"] >= atr_ratio * 0.22,
        metrics["hourly_spread"] >= max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.08, atr_ratio * 0.66),
        metrics["fourh_spread"] >= max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 0.58, atr_ratio * 0.56),
        metrics["hourly_slope"] >= atr_ratio * 0.052 and metrics["fourh_slope"] >= atr_ratio * 0.018,
        breakout_distance_pct >= -atr_ratio * 0.01,
    )

    mild_continuation = (
        quality_ready
        and breakout_distance_pct >= -atr_ratio * 0.01
        and metrics["hourly_spread"] >= max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.02, atr_ratio * 0.62)
        and metrics["fourh_spread"] >= max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 0.54, atr_ratio * 0.50)
        and (
            metrics["hourly_slope"] >= atr_ratio * 0.044
            or metrics["fourh_slope"] >= atr_ratio * 0.020
            or metrics["intraday_spread"] >= atr_ratio * 0.26
        )
    )
    pullback_recovery = (
        quality_ready
        and breakout_distance_pct >= -atr_ratio * 0.01
        and breakout_distance_pct <= atr_ratio * 0.12
        and metrics["hourly_spread"] >= max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 0.92, atr_ratio * 0.54)
        and metrics["fourh_spread"] >= max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 0.48, atr_ratio * 0.46)
        and metrics["hourly_slope"] >= atr_ratio * 0.022
        and metrics["fourh_slope"] >= 0.0
    )

    stale_chase = (
        breakout_distance_pct >= atr_ratio * 0.14
        and hourly_fast_extension >= max(atr_ratio * 0.82, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.90)
        and hourly_anchor_extension >= max(atr_ratio * 1.24, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 2.98)
        and (
            metrics["fourh_spread"] < max(metrics["hourly_spread"] * 0.90, atr_ratio * 0.92)
            or metrics["fourh_slope"] < atr_ratio * 0.036
        )
    )
    if stale_chase:
        return False
    if mild_continuation or pullback_recovery:
        return True
    return confirms >= 4


def _hourly_long_exit_regime_weak(market_state, atr_ratio, long_exit_relax_mult):
    hourly = market_state["hourly"]
    price_buffer_pct = max(float(EXIT_PARAMS.get("regime_price_confirm_buffer_pct", 0.0)), 0.0)
    price_buffer = max(price_buffer_pct, atr_ratio * (0.20 * long_exit_relax_mult))
    trend_buffer = max(price_buffer_pct * 0.5, atr_ratio * 0.08)

    hourly_price_lost = hourly["close"] <= hourly["ema_fast"] * (1.0 - price_buffer)
    hourly_structure_weak = (
        hourly["ema_fast"] <= hourly["ema_anchor"] * (1.0 + trend_buffer)
        and hourly["trend_spread_pct"] <= max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 0.52, atr_ratio * 0.28)
        and hourly["ema_slow_slope_pct"] <= atr_ratio * 0.018
    )
    hourly_flow_weak = (
        hourly["macd_line"] <= hourly["signal_line"]
        and hourly["taker_buy_ratio"] <= max(PARAMS["hourly_taker_buy_ratio_min"] + 0.003, 0.5)
        and hourly["flow_imbalance"] <= max(PARAMS["hourly_flow_confirmation_min"] + 0.01, 0.01)
    )
    return hourly_price_lost and hourly_structure_weak and hourly_flow_weak


def _trend_followthrough_exit_long(market_state, trigger_price, current_close):
    hourly = market_state["hourly"]
    fourh = market_state["four_hour"]
    metrics = _directional_trend_metrics(market_state, "long")
    atr_ratio = metrics["atr_ratio"]
    long_stop_atr_mult = (
        EXIT_PARAMS["long_breakout_stop_atr_mult"] + EXIT_PARAMS["long_pullback_stop_atr_mult"]
    ) / 2.0
    long_exit_relax_mult = max(long_stop_atr_mult / max(EXIT_PARAMS["stop_atr_mult"], 1e-9), 1.0)
    breakout_distance_pct = (current_close - trigger_price) / max(trigger_price, 1e-9)
    hourly_fast_extension = (current_close - hourly["ema_fast"]) / max(current_close, 1e-9)
    hourly_anchor_extension = (current_close - hourly["ema_anchor"]) / max(current_close, 1e-9)
    hourly_regime_weak = _hourly_long_exit_regime_weak(market_state, atr_ratio, long_exit_relax_mult)

    confirms = _count_true(
        metrics["intraday_spread"] >= atr_ratio * 0.18,
        metrics["hourly_spread"] >= max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 0.88, atr_ratio * 0.50),
        metrics["fourh_spread"] >= max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 0.44, atr_ratio * 0.42),
        metrics["hourly_slope"] >= atr_ratio * 0.014,
        breakout_distance_pct >= -atr_ratio * (0.04 * long_exit_relax_mult),
    )

    reversal_pressure = (
        market_state["histogram"] <= 0.0
        and market_state["macd_line"] <= market_state["signal_line"]
        and hourly["close"] <= hourly["ema_fast"] * (1.0 + atr_ratio * (0.10 * long_exit_relax_mult))
        and hourly["ema_fast"] <= hourly["ema_anchor"] * (1.0 + atr_ratio * (0.05 * long_exit_relax_mult))
        and (
            breakout_distance_pct <= atr_ratio * (0.04 * long_exit_relax_mult)
            or hourly_fast_extension <= atr_ratio * (0.06 * long_exit_relax_mult)
            or metrics["hourly_slope"] <= 0.0
        )
    )
    support_lost = (
        current_close <= hourly["ema_fast"] * (1.0 + atr_ratio * (0.04 * long_exit_relax_mult))
        and (
            hourly_fast_extension <= atr_ratio * (0.03 * long_exit_relax_mult)
            or hourly_anchor_extension <= atr_ratio * (0.10 * long_exit_relax_mult)
            or breakout_distance_pct <= -atr_ratio * (0.01 * max(long_exit_relax_mult - 1.0, 0.0))
        )
        and metrics["hourly_slope"] <= atr_ratio * 0.010
        and metrics["intraday_spread"] <= atr_ratio * (0.24 * long_exit_relax_mult)
    )
    deeper_reversal = (
        breakout_distance_pct <= -atr_ratio * (0.02 * long_exit_relax_mult)
        and hourly_fast_extension <= atr_ratio * (0.02 * long_exit_relax_mult)
        and (
            metrics["hourly_slope"] <= 0.0
            or metrics["fourh_slope"] <= atr_ratio * 0.010
            or market_state["histogram"] <= -0.01
        )
    )
    soft_pullback_hold = (
        breakout_distance_pct >= -atr_ratio * (0.08 * long_exit_relax_mult)
        and metrics["hourly_spread"] >= max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 0.74, atr_ratio * 0.40)
        and metrics["fourh_spread"] >= max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 0.38, atr_ratio * 0.34)
        and metrics["hourly_slope"] >= -atr_ratio * 0.010
        and metrics["fourh_slope"] >= -atr_ratio * 0.004
        and current_close >= hourly["ema_anchor"] * (1.0 - atr_ratio * (0.16 * long_exit_relax_mult))
    )
    reversal_signals = int(reversal_pressure) + int(support_lost) + int(deeper_reversal)
    if deeper_reversal and reversal_signals >= 2 and hourly_regime_weak and not soft_pullback_hold:
        return False
    if reversal_signals >= 3 and hourly_regime_weak:
        return False
    trend_cushion_active = (
        breakout_distance_pct >= atr_ratio * 0.05
        and metrics["hourly_slope"] >= atr_ratio * 0.010
        and metrics["fourh_slope"] >= 0.0
    )
    required_confirms = 2 if trend_cushion_active else 3
    if soft_pullback_hold:
        required_confirms = max(required_confirms - 1, 2)
    if hourly_regime_weak:
        required_confirms += 1
    return confirms >= required_confirms


def _short_followthrough_profile(path_key):
    normalized_key = str(path_key or "").strip()
    normalized_tag = ENTRY_PATH_TAGS.get(normalized_key, normalized_key)
    if normalized_key == "short_reaccel" or normalized_tag == "short_reaccel":
        return {
            "momentum_mult": 0.72,
            "required_confirms": 0,
            "trend_cushion_confirms": 0,
        }
    if normalized_key == "short_breakdown":
        return {
            "momentum_mult": 0.82,
            "required_confirms": 0,
            "trend_cushion_confirms": 0,
        }
    if normalized_tag == "short_impulse" or normalized_key in {"short_trend", "short_impulse"}:
        return {
            "momentum_mult": 1.08,
            "required_confirms": 1,
            "trend_cushion_confirms": 0,
        }
    return {
        "momentum_mult": 1.0,
        "required_confirms": 0,
        "trend_cushion_confirms": 0,
    }


def _short_required_confirms(profile, trend_cushion_active, quality_relax_ok):
    required_confirms = 4 if trend_cushion_active else 5
    required_confirms += int(profile["trend_cushion_confirms"] if trend_cushion_active else profile["required_confirms"])
    if quality_relax_ok:
        required_confirms -= 1
    return max(1, min(required_confirms, 5))


def _trend_followthrough_short(
    market_state,
    trigger_price,
    current_close,
    entry_path_key=None,
    quality_relax_ok=False,
):
    hourly = market_state["hourly"]
    fourh = market_state["four_hour"]
    metrics = _directional_trend_metrics(market_state, "short")
    atr_ratio = metrics["atr_ratio"]
    profile = _short_followthrough_profile(entry_path_key)
    momentum_mult = profile["momentum_mult"]
    breakdown_distance_pct = (trigger_price - current_close) / max(trigger_price, 1e-9)
    hourly_fast_discount = (hourly["ema_fast"] - current_close) / max(current_close, 1e-9)
    hourly_anchor_discount = (hourly["ema_anchor"] - current_close) / max(current_close, 1e-9)

    confirms = _count_true(
        metrics["intraday_spread"] >= atr_ratio * (0.28 * momentum_mult),
        metrics["hourly_spread"] >= max(
            SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.24 * momentum_mult,
            atr_ratio * (0.80 * momentum_mult),
        ),
        metrics["fourh_spread"] >= max(
            SIDEWAYS_MIN_FOURH_SPREAD_PCT * 0.74 * momentum_mult,
            atr_ratio * (0.70 * momentum_mult),
        ),
        metrics["hourly_slope"] >= atr_ratio * (0.078 * momentum_mult)
        and metrics["fourh_slope"] >= atr_ratio * (0.032 * momentum_mult),
        breakdown_distance_pct >= atr_ratio * (0.05 * momentum_mult),
    )

    exhausted_selloff = (
        breakdown_distance_pct >= atr_ratio * 0.20
        and hourly_fast_discount >= max(atr_ratio * 0.98, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 2.22)
        and hourly_anchor_discount >= max(atr_ratio * 1.58, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 3.72)
        and (
            metrics["fourh_spread"] < max(metrics["hourly_spread"] * 0.88, atr_ratio * 1.04)
            or metrics["fourh_slope"] < atr_ratio * 0.042
        )
    )
    rebound_pressure = (
        market_state["histogram"] >= 0.0
        and market_state["macd_line"] >= market_state["signal_line"]
        and hourly["close"] >= hourly["ema_fast"] * (1.0 - atr_ratio * 0.04)
        and (
            breakdown_distance_pct <= atr_ratio * 0.08
            or hourly_fast_discount <= atr_ratio * 0.12
            or metrics["hourly_slope"] <= atr_ratio * 0.056
        )
    )
    trend_floor_lost = (
        current_close >= hourly["ema_fast"] * (1.0 - atr_ratio * 0.02)
        and (
            hourly_fast_discount <= atr_ratio * 0.08
            or hourly_anchor_discount <= atr_ratio * 0.18
            or breakdown_distance_pct <= atr_ratio * 0.04
        )
        and metrics["hourly_slope"] <= atr_ratio * 0.062
        and metrics["intraday_spread"] <= atr_ratio * 0.24
    )
    reversal_followthrough = (
        breakdown_distance_pct <= atr_ratio * 0.03
        and hourly_fast_discount <= atr_ratio * 0.10
        and (
            metrics["hourly_slope"] <= atr_ratio * 0.052
            or metrics["fourh_slope"] <= atr_ratio * 0.024
            or hourly["macd_line"] >= hourly["signal_line"]
        )
    )
    if exhausted_selloff:
        return False
    if rebound_pressure or trend_floor_lost or reversal_followthrough:
        return False
    trend_cushion_active = (
        breakdown_distance_pct >= atr_ratio * 0.14
        and metrics["hourly_slope"] >= atr_ratio * (0.082 * momentum_mult)
        and metrics["fourh_slope"] >= atr_ratio * (0.034 * momentum_mult)
    )
    return confirms >= _short_required_confirms(profile, trend_cushion_active, quality_relax_ok)


def _trend_followthrough_ok(market_state, side, trigger_price, current_close):
    if side == "long":
        return _trend_followthrough_long(market_state, trigger_price, current_close)
    return _trend_followthrough_short(market_state, trigger_price, current_close)


def _active_long_exit_followthrough_ok(positions, market_state, current_close):
    if not positions:
        return True
    long_positions = [position for position in positions if _position_side(position) == "long"]
    if not long_positions:
        return True
    lead_position = long_positions[0]
    trigger_price = float(lead_position.get("entry_price", current_close))
    try:
        return _trend_followthrough_exit_long(market_state, trigger_price, current_close)
    except (KeyError, TypeError):
        return True


def _active_long_exit_signal(positions, market_state, current_bar, current_close):
    return (
        not _active_long_exit_followthrough_ok(positions, market_state, current_close)
        or _long_profit_protect_exit_active(positions, market_state, current_bar, current_close)
    )


def _active_short_exit_followthrough_ok(positions, market_state, current_close):
    if not positions:
        return True
    short_positions = [position for position in positions if _position_side(position) == "short"]
    if not short_positions:
        return True
    lead_position = short_positions[0]
    trigger_price = float(lead_position.get("entry_price", current_close))
    entry_path_key = str(
        lead_position.get("entry_path_tag")
        or lead_position.get("entry_path_key")
        or lead_position.get("entry_signal")
        or ""
    ).strip()
    try:
        return _trend_followthrough_short(
            market_state,
            trigger_price,
            current_close,
            entry_path_key=entry_path_key,
        )
    except (KeyError, TypeError):
        return True


def _active_short_exit_signal(positions, market_state, current_bar, current_close):
    return not _active_short_exit_followthrough_ok(positions, market_state, current_close)


# ==================== Long Entry Signals ====================

def _long_durable_hold_active(market_state):
    fourh = market_state["four_hour"]
    if fourh is None:
        return False
    return (
        fourh["adx"] >= 22.0
        and fourh["trend_spread_pct"] > 0.0
        and fourh["close"] > fourh["ema_slow"]
    )


def _long_reclaim_ready(context, market_state, params):
    return (
        context["current"]["close"] > market_state["ema_fast"] > market_state["ema_slow"]
        and market_state["macd_line"] > market_state["signal_line"]
        and market_state["adx"] >= max(params["intraday_adx_min"] - 1.6, 11.5)
        and context["breakout_distance_pct"] >= -context["atr_ratio"] * 0.02
        and _hourly_extension_within(context, 0.84, 1.92, 1.22, 2.92)
    )


def _long_hourly_turn_repair_ready(context, params):
    hourly = context["hourly"]
    return (
        hourly["close"] > hourly["ema_slow"]
        and hourly["macd_line"] > hourly["signal_line"]
        and (hourly["ema_fast"] >= hourly["ema_slow"] or hourly["close"] >= hourly["ema_fast"])
        and hourly["trend_spread_pct"] >= max(
            SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 0.40,
            context["atr_ratio"] * 0.22,
        )
        and hourly["ema_slow_slope_pct"] >= 0.0
        and hourly["adx"] >= max(params["hourly_adx_min"] - 6.0, 13.5)
    )


def _long_late_mature_guard(context):
    return (
        _hourly_extension_reaches(context, 0.82, 1.88, 1.24, 2.96)
        and context["breakout_distance_pct"] >= max(
            context["prev_breakout_distance_pct"] - context["atr_ratio"] * 0.01,
            context["atr_ratio"] * 0.10,
        )
        and (
            context["fourh"]["trend_spread_pct"] < max(
                context["hourly"]["trend_spread_pct"] * 0.90,
                context["atr_ratio"] * 0.98,
            )
            or context["fourh"]["ema_slow_slope_pct"] < max(
                context["fourh"]["trend_spread_pct"] * 0.10,
                context["atr_ratio"] * 0.038,
            )
        )
    )


def _long_fourh_not_strong_bear(context, params):
    return not (
        context["fourh"]["close"] < context["fourh"]["ema_slow"]
        and context["fourh"]["trend_spread_pct"] <= -max(
            SIDEWAYS_MIN_FOURH_SPREAD_PCT * 0.62,
            context["atr_ratio"] * 0.50,
        )
        and context["fourh"]["ema_slow_slope_pct"] <= -max(
            context["atr_ratio"] * 0.020,
            SIDEWAYS_MIN_FOURH_SPREAD_PCT * 0.14,
        )
        and context["fourh"]["macd_line"] < context["fourh"]["signal_line"]
        and context["fourh"]["adx"] >= max(params["fourh_adx_min"] - 0.8, 11.8)
    )


def _strong_long_flow_ok(context, market_state, params, flow_metrics):
    return (
        _flow_confirmation_ok(
            market_state,
            context["hourly"],
            context["fourh"],
            params,
            "long",
            strong=True,
        )
        and flow_metrics["directional_bias"] >= 0.018
        and market_state["histogram"] >= max(params["breakout_hist_min"], -1.0)
        and market_state["macd_line"] >= market_state["signal_line"] - max(context["atr_ratio"] * 900.0, 4.0)
    )


def _long_outer_lane_name(
    long_state,
    context,
    reclaim_ready,
    hourly_turn_repair_ready,
    late_mature_guard,
    fourh_not_strong_bear,
    strong_long_flow,
):
    hourly = context["hourly"]
    fourh = context["fourh"]
    atr_ratio = context["atr_ratio"]
    price_holds_hourly_slow = context["current"]["close"] >= hourly["ema_slow"] * (1.0 - atr_ratio * 0.10)
    hourly_structure_ready = (
        hourly["close"] >= hourly["ema_slow"] * (1.0 - atr_ratio * 0.08)
        and hourly["trend_spread_pct"] >= -max(atr_ratio * 0.08, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 0.20)
        and hourly["ema_slow_slope_pct"] >= -atr_ratio * 0.016
        and hourly["adx"] >= max(PARAMS["hourly_adx_min"] - 3.0, 10.0)
    )
    fourh_structure_ready = (
        fourh_not_strong_bear
        and fourh["close"] >= fourh["ema_slow"] * (1.0 - atr_ratio * 0.16)
        and fourh["trend_spread_pct"] >= -max(atr_ratio * 0.12, SIDEWAYS_MIN_FOURH_SPREAD_PCT * 0.24)
        and fourh["ema_slow_slope_pct"] >= -atr_ratio * 0.020
    )
    mature_trend_lane = (
        price_holds_hourly_slow
        and hourly_structure_ready
        and fourh_structure_ready
        and (long_state["hourly_bull"] or long_state["fourh_bull_base"])
        and not late_mature_guard
    )
    soft_trend_lane = (
        price_holds_hourly_slow
        and hourly_structure_ready
        and fourh_structure_ready
        and (long_state["intraday_bull"] or reclaim_ready)
        and _hourly_extension_within(context, 0.96, 2.20, 1.38, 3.24)
        and not late_mature_guard
    )
    early_turn_outer_lane = (
        reclaim_ready
        and hourly_turn_repair_ready
        and fourh_structure_ready
        and (strong_long_flow or context["volume_ratio"] >= max(PARAMS["breakout_volume_ratio_min"], 1.0))
        and not late_mature_guard
        and _hourly_extension_within(context, 0.86, 1.94, 1.24, 2.96)
    )
    return _first_active_lane(
        ("trend", mature_trend_lane),
        ("soft_trend", soft_trend_lane),
        ("early_turn", early_turn_outer_lane),
    )


def long_outer_context_ok(context, market_state, params):
    long_state = _build_long_trend_state(context, market_state, params)
    context["long_outer_lane"] = ""
    flow_metrics = _flow_signal_metrics(market_state, context["hourly"], context["fourh"], params, "long")
    reclaim_ready = _long_reclaim_ready(context, market_state, params)
    context["long_reclaim_ready"] = reclaim_ready
    hourly_turn_repair_ready = _long_hourly_turn_repair_ready(context, params)
    late_mature_guard = _long_late_mature_guard(context)
    context["long_late_mature_guard"] = late_mature_guard
    fourh_not_strong_bear = _long_fourh_not_strong_bear(context, params)
    strong_long_flow = _strong_long_flow_ok(context, market_state, params, flow_metrics)
    context["long_outer_lane"] = _long_outer_lane_name(
        long_state,
        context,
        reclaim_ready,
        hourly_turn_repair_ready,
        late_mature_guard,
        fourh_not_strong_bear,
        strong_long_flow,
    )
    return bool(context["long_outer_lane"])


def long_breakout_ok(context, market_state, params):
    current = context["current"]
    prev = context["prev"]
    hourly = context["hourly"]
    fourh = context["fourh"]
    current_candle = context["current_candle"]
    atr_ratio = context["atr_ratio"]
    breakout_distance_pct = context["breakout_distance_pct"]
    breakout_high = context["breakout_high"]
    breakout_high_penetration_pct = context["breakout_high_penetration_pct"]
    direct_breakout = (
        current["close"] >= breakout_high * (1.0 + params["breakout_buffer_pct"])
        and breakout_distance_pct >= -atr_ratio * 0.01
        and breakout_distance_pct <= atr_ratio * 0.30
        and breakout_high_penetration_pct >= max(atr_ratio * 0.025, breakout_distance_pct * 0.35)
        and current["high"] >= prev["high"]
        and current["close"] >= prev["close"] * (1.0 - atr_ratio * 0.02)
    )
    range_release = (
        current["high"] >= breakout_high * (1.0 - max(atr_ratio * 0.16, 0.0010))
        and current["close"] >= breakout_high * (1.0 - max(atr_ratio * 0.08, 0.0007))
        and breakout_distance_pct <= atr_ratio * 0.22
        and current["close"] >= max(prev["close"], market_state["ema_fast"] * (1.0 - atr_ratio * 0.03))
        and current["high"] >= prev["high"] * (1.0 - atr_ratio * 0.04)
    )
    candle_acceptance = (
        context["current_range"] >= context["recent_range_avg"] * 0.68
        and current_candle["close_pos"] >= max(params["breakout_close_pos_min"] - 0.08, 0.48)
        and current_candle["body_ratio"] >= max(params["breakout_body_ratio_min"] - 0.08, 0.18)
    )
    participation = (
        context["volume_ratio"] >= max(params["breakout_volume_ratio_min"] - 0.16, 0.82)
        and current["volume"] >= max(context["prev_volume"] * 0.76, context["recent_volume_avg"] * 0.78)
    )
    trend_context = (
        market_state["adx"] >= max(params["breakout_adx_min"] - 2.5, params["intraday_adx_min"])
        and params["breakout_rsi_min"] <= market_state["rsi"] <= params["breakout_rsi_max"]
        and hourly["close"] >= hourly["ema_slow"] * (1.0 - atr_ratio * 0.06)
        and hourly["trend_spread_pct"] >= -max(atr_ratio * 0.05, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 0.15)
        and hourly["ema_slow_slope_pct"] >= -atr_ratio * 0.012
        and fourh["trend_spread_pct"] >= -max(atr_ratio * 0.10, SIDEWAYS_MIN_FOURH_SPREAD_PCT * 0.22)
        and fourh["ema_slow_slope_pct"] >= -atr_ratio * 0.018
    )
    macd_confirmation = (
        market_state["macd_line"] >= market_state["signal_line"] - max(atr_ratio * 900.0, 4.0)
        and market_state["histogram"] >= params["breakout_hist_min"]
    )
    return (
        (direct_breakout or range_release)
        and candle_acceptance
        and participation
        and trend_context
        and macd_confirmation
        and _flow_entry_ok(market_state, hourly, fourh, params, "long", strong=False)
        and _hourly_extension_within(context, 1.05, 2.38, 1.52, 3.56)
    )


def long_pullback_ok(context, market_state, params):
    current = context["current"]
    prev = context["prev"]
    hourly = context["hourly"]
    fourh = context["fourh"]
    atr_ratio = context["atr_ratio"]
    breakout_high = context["breakout_high"]
    breakout_distance_pct = context["breakout_distance_pct"]
    breakout_high_penetration_pct = context["breakout_high_penetration_pct"]
    intraday_support = max(float(market_state["ema_fast"]), float(market_state["ema_slow"]))
    prior_acceptance = (
        prev["high"] >= breakout_high * (1.0 - max(atr_ratio * 0.08, params["breakout_buffer_pct"]))
        and context["prev_breakout_distance_pct"] <= atr_ratio * 0.12
        and prev["low"] <= max(breakout_high, market_state["ema_fast"]) * (1.0 + atr_ratio * 0.16)
        and prev["low"] >= market_state["ema_slow"] * (1.0 - atr_ratio * 0.34)
    )
    reclaim = (
        current["close"] >= max(breakout_high * (1.0 + params["breakout_buffer_pct"] * 0.35), prev["close"])
        and breakout_distance_pct >= -atr_ratio * 0.03
        and breakout_distance_pct <= atr_ratio * 0.24
        and current["close"] >= market_state["ema_fast"] * (1.0 - atr_ratio * 0.05)
    )
    ema_reclaim = (
        prev["low"] <= intraday_support * (1.0 + atr_ratio * 0.16)
        and current["low"] <= intraday_support * (1.0 + atr_ratio * 0.22)
        and current["close"] >= intraday_support * (1.0 - atr_ratio * 0.03)
        and current["close"] >= prev["close"] * (1.0 - atr_ratio * 0.02)
        and current["high"] >= breakout_high * (1.0 - max(atr_ratio * 0.28, 0.0018))
        and breakout_distance_pct >= -atr_ratio * 0.24
        and breakout_distance_pct <= atr_ratio * 0.20
    )
    trend_hold_reclaim = (
        current["close"] >= intraday_support * (1.0 - atr_ratio * 0.04)
        and prev["close"] >= market_state["ema_slow"] * (1.0 - atr_ratio * 0.08)
        and current["close"] >= prev["close"] * (1.0 - atr_ratio * 0.025)
        and current["high"] >= prev["high"] * (1.0 - atr_ratio * 0.06)
        and context["breakout_reclaim_gap_pct"] <= max(atr_ratio * 0.40, 0.0032)
        and breakout_distance_pct <= atr_ratio * 0.18
        and hourly["close"] >= hourly["ema_slow"] * (1.0 - atr_ratio * 0.10)
        and fourh["close"] >= fourh["ema_slow"] * (1.0 - atr_ratio * 0.22)
    )
    structure_upturn = (
        current["close"] >= intraday_support * (1.0 - atr_ratio * 0.06)
        and current["close"] >= prev["close"] * (1.0 - atr_ratio * 0.06)
        and current["high"] >= prev["high"] * (1.0 - atr_ratio * 0.10)
        and context["breakout_reclaim_gap_pct"] <= max(atr_ratio * 0.72, 0.0055)
        and breakout_distance_pct >= -atr_ratio * 0.58
        and breakout_distance_pct <= atr_ratio * 0.22
        and market_state["adx"] >= max(params["intraday_adx_min"] - 2.0, 9.5)
        and hourly["close"] >= hourly["ema_slow"] * (1.0 - atr_ratio * 0.14)
        and fourh["close"] >= fourh["ema_slow"] * (1.0 - atr_ratio * 0.28)
        and hourly["ema_slow_slope_pct"] >= -atr_ratio * 0.030
        and fourh["ema_slow_slope_pct"] >= -atr_ratio * 0.036
    )
    candle_recovery = (
        context["current_range"] >= max(context["prev_range"] * 0.66, context["recent_range_avg"] * 0.62)
        and context["current_candle"]["close_pos"] >= max(params["breakout_close_pos_min"] - 0.10, 0.46)
        and context["current_candle"]["body_ratio"] >= max(params["breakout_body_ratio_min"] - 0.10, 0.16)
    )
    trend_context = (
        hourly["close"] >= hourly["ema_slow"] * (1.0 - atr_ratio * 0.08)
        and hourly["ema_slow_slope_pct"] >= -atr_ratio * 0.018
        and fourh["close"] >= fourh["ema_slow"] * (1.0 - atr_ratio * 0.18)
        and fourh["ema_slow_slope_pct"] >= -atr_ratio * 0.024
        and market_state["adx"] >= max(params["intraday_adx_min"], params["breakout_adx_min"] - 2.5)
    )
    participation = (
        current["volume"] >= max(context["prev_volume"] * 0.70, context["recent_volume_avg"] * 0.72)
        and context["volume_ratio"] >= max(params["breakout_volume_ratio_min"] - 0.22, 0.76)
    )
    macd_confirmation = market_state["macd_line"] >= market_state["signal_line"] - max(atr_ratio * 1000.0, 5.0)
    return (
        ((prior_acceptance and reclaim) or ema_reclaim or trend_hold_reclaim or structure_upturn)
        and candle_recovery
        and trend_context
        and participation
        and macd_confirmation
        and _flow_entry_ok(market_state, hourly, fourh, params, "long", strong=False)
        and _hourly_extension_within(context, 0.98, 2.18, 1.42, 3.28)
    )


def long_trend_reaccel_ok(context, market_state, params):
    current = context["current"]
    prev = context["prev"]
    hourly = context["hourly"]
    fourh = context["fourh"]
    atr_ratio = context["atr_ratio"]
    breakout_distance_pct = context["breakout_distance_pct"]
    breakout_high = context["breakout_high"]
    breakout_high_penetration_pct = context["breakout_high_penetration_pct"]
    flow_metrics = _flow_signal_metrics(market_state, hourly, fourh, params, "long")
    strong_structure = (
        current["close"] >= breakout_high * (1.0 + params["breakout_buffer_pct"])
        and breakout_distance_pct >= atr_ratio * 0.10
        and breakout_distance_pct <= atr_ratio * 0.36
        and breakout_high_penetration_pct >= max(atr_ratio * 0.14, breakout_distance_pct * 0.72)
        and current["close"] >= prev["high"] * (1.0 - atr_ratio * 0.02)
    )
    strong_candle = (
        context["current_range"] >= context["recent_range_avg"] * 0.95
        and context["current_candle"]["close_pos"] >= max(params["breakout_close_pos_min"] + 0.08, 0.64)
        and context["current_candle"]["body_ratio"] >= max(params["breakout_body_ratio_min"] + 0.08, 0.34)
        and context["volume_ratio"] >= max(params["breakout_volume_ratio_min"] + 0.08, 1.08)
    )
    strong_trend = (
        market_state["adx"] >= max(params["breakout_adx_min"] + 1.5, 20.0)
        and hourly["trend_spread_pct"] >= max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 0.92, atr_ratio * 0.56)
        and hourly["ema_slow_slope_pct"] >= atr_ratio * 0.018
        and fourh["trend_spread_pct"] >= max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 0.44, atr_ratio * 0.40)
        and fourh["ema_slow_slope_pct"] >= 0.0
    )
    return (
        strong_structure
        and strong_candle
        and strong_trend
        and market_state["histogram"] >= max(params["breakout_hist_min"], -1.0)
        and _flow_entry_ok(market_state, hourly, fourh, params, "long", strong=True)
        and flow_metrics["directional_bias"] >= 0.02
    )


def long_signal_path_ok(breakout_ok, pullback_ok, reaccel_ok):
    return breakout_ok or pullback_ok or reaccel_ok


def _merged_long_core_path_ok(breakout_ok, pullback_ok):
    return breakout_ok or pullback_ok


def _long_reversal_sniper_ok(context):
    return False


def _long_strong_trend_bypass(context, market_state, params):
    hourly = context["hourly"]
    fourh = context["fourh"]
    atr_ratio = context["atr_ratio"]
    metrics = _directional_trend_metrics(market_state, "long")
    flow_metrics = _flow_signal_metrics(market_state, hourly, fourh, params, "long")

    trend_confirms = _count_true(
        market_state["adx"] >= max(params["breakout_adx_min"] - 0.5, params["intraday_adx_min"] + 1.0),
        metrics["intraday_spread"] >= atr_ratio * 0.30,
        metrics["hourly_spread"] >= max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.28, atr_ratio * 0.82),
        metrics["fourh_spread"] >= max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 0.82, atr_ratio * 0.78),
        metrics["hourly_slope"] >= atr_ratio * 0.078,
        metrics["fourh_slope"] >= atr_ratio * 0.032,
    )

    trend_score = trend_confirms / 6.0
    ema_bull_stack = (
        context["current"]["close"] > market_state["ema_fast"] > market_state["ema_slow"]
        and hourly["close"] > hourly["ema_fast"] > hourly["ema_slow"]
        and fourh["close"] > fourh["ema_fast"] > fourh["ema_slow"]
    )
    macd_above_zero = (
        market_state["macd_line"] > 0.0
        and market_state["signal_line"] > 0.0
        and hourly["macd_line"] > 0.0
        and hourly["signal_line"] > 0.0
    )
    return (
        _flow_confirmation_ok(market_state, hourly, fourh, params, "long", strong=True)
        and flow_metrics["directional_bias"] >= 0.04
        and trend_score > 0.75
        and _trend_quality_long(market_state)
        and ema_bull_stack
        and macd_above_zero
    )


def long_final_veto_clear(
    context,
    market_state,
    params,
    breakout_ok,
    pullback_ok,
    reaccel_ok,
    relay_ok=False,
    strong_trend_bypass=False,
):
    quality_relax_gate = 0.60
    fourh_quality_score = _fourh_trend_quality_long_score(market_state, params)
    high_quality_long = fourh_quality_score >= quality_relax_gate
    atr_ratio = context["atr_ratio"]
    rsi = market_state["rsi"]
    breakout_distance_pct = context["breakout_distance_pct"]
    hourly_fast_extension_pct = context["hourly_fast_extension_pct"]
    hourly_anchor_extension_pct = context["hourly_anchor_extension_pct"]
    hourly_fast_discount_pct = context["hourly_fast_discount_pct"]
    strict_rsi_cap = 72.0 if (breakout_ok or reaccel_ok) else 70.0
    relaxed_rsi_cap = strict_rsi_cap + 3.0
    strict_fast_extension_cap = max(atr_ratio * 1.24, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 2.74)
    relaxed_fast_extension_cap = max(atr_ratio * 1.48, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 3.18)
    strict_anchor_extension_cap = max(atr_ratio * 1.76, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 3.96)
    relaxed_anchor_extension_cap = max(atr_ratio * 2.06, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 4.48)
    strict_breakout_distance_cap = atr_ratio * 0.36
    relaxed_breakout_distance_cap = atr_ratio * 0.48
    pullback_reclaim_room = (
        (pullback_ok or relay_ok)
        and hourly_fast_discount_pct <= max(atr_ratio * 0.18, 0.0030)
    )
    if pullback_reclaim_room:
        strict_breakout_distance_cap += max(atr_ratio * 0.05, 0.0008)
        relaxed_breakout_distance_cap += max(atr_ratio * 0.07, 0.0011)
    mature_extension_clear = (
        breakout_distance_pct <= (relaxed_breakout_distance_cap if high_quality_long else strict_breakout_distance_cap)
        and hourly_fast_extension_pct <= (
            relaxed_fast_extension_cap if high_quality_long else strict_fast_extension_cap
        )
        and hourly_anchor_extension_pct <= (
            relaxed_anchor_extension_cap if high_quality_long else strict_anchor_extension_cap
        )
    )
    rsi_clear = rsi <= (relaxed_rsi_cap if high_quality_long else strict_rsi_cap)
    if strong_trend_bypass:
        return _trend_quality_ok(market_state, "long")
    if high_quality_long:
        return rsi_clear and mature_extension_clear
    return rsi_clear and mature_extension_clear


# ==================== Short Entry Helpers Kept For Safety, Entry Disabled ====================

def _short_fourh_bear_gate(context, short_state):
    return (
        short_state["fourh_bear"]
        or (
            context["fourh"]["trend_spread_pct"] <= -max(
                SIDEWAYS_MIN_FOURH_SPREAD_PCT * 0.68,
                context["atr_ratio"] * 0.58,
            )
            and context["fourh"]["ema_slow_slope_pct"] <= -max(
                context["atr_ratio"] * 0.022,
                SIDEWAYS_MIN_FOURH_SPREAD_PCT * 0.18,
            )
        )
    )


def _short_extreme_bull_trend(context, market_state):
    return (
        context["current"]["close"] > market_state["ema_fast"] > market_state["ema_slow"]
        and market_state["macd_line"] > market_state["signal_line"]
        and context["hourly"]["close"] > context["hourly"]["ema_fast"] > context["hourly"]["ema_slow"]
        and context["hourly"]["close"] > context["hourly"]["ema_anchor"]
        and context["hourly"]["macd_line"] > context["hourly"]["signal_line"]
        and context["hourly"]["trend_spread_pct"] > 0.0
        and context["hourly"]["ema_slow_slope_pct"] > 0.0
        and context["fourh"]["close"] > context["fourh"]["ema_fast"] > context["fourh"]["ema_slow"]
        and context["fourh"]["macd_line"] > context["fourh"]["signal_line"]
        and context["fourh"]["trend_spread_pct"] > 0.0
        and context["fourh"]["ema_slow_slope_pct"] > 0.0
    )


def short_outer_context_ok(context, market_state, params):
    short_state = _build_short_trend_state(context, market_state, params)
    context["short_outer_lane"] = ""
    short_fourh_bear_gate = _short_fourh_bear_gate(context, short_state)
    strict_trend_lane = (
        short_state["intraday_bear"]
        and short_state["hourly_bear"]
        and short_fourh_bear_gate
        and _trend_quality_short(market_state)
    )
    extreme_bull_trend = _short_extreme_bull_trend(context, market_state)
    breakdown_release_lane = (
        not strict_trend_lane
        and not extreme_bull_trend
        and short_fourh_bear_gate
        and context["current"]["close"] <= context["breakdown_low"] * (1.0 - params["breakdown_buffer_pct"])
        and context["breakdown_distance_pct"] >= context["atr_ratio"] * 0.06
        and context["current_candle"]["close_pos"] <= min(params["breakdown_close_pos_max"] + 0.03, 0.37)
        and context["current_candle"]["body_ratio"] >= max(params["breakdown_body_ratio_min"] - 0.05, 0.34)
    )
    context["short_outer_lane"] = _first_active_lane(
        ("trend", strict_trend_lane),
        ("breakdown_release", breakdown_release_lane),
    )
    return bool(context["short_outer_lane"])


def breakdown_ready(context, market_state, params):
    current = context["current"]
    prev = context["prev"]
    return (
        current["close"] <= context["breakdown_low"] * (1.0 - params["breakdown_buffer_pct"])
        and context["breakdown_distance_pct"] >= context["atr_ratio"] * 0.10
        and current["close"] < prev["low"]
        and context["current_candle"]["close_pos"] <= params["breakdown_close_pos_max"]
        and context["current_candle"]["body_ratio"] >= params["breakdown_body_ratio_min"]
        and context["volume_ratio"] >= params["breakdown_volume_ratio_min"]
        and current["volume"] >= context["prev_volume"] * 0.94
        and market_state["adx"] >= params["breakdown_adx_min"]
        and params["breakdown_rsi_min"] <= market_state["rsi"] <= params["breakdown_rsi_max"]
        and market_state["histogram"] <= params["breakdown_hist_max"]
    )


def _short_breakdown_path_ok(context, market_state, params, require_breakdown_gate=True):
    hourly = context["hourly"]
    fourh = context["fourh"]
    atr_ratio = context["atr_ratio"]
    flow_metrics = _flow_signal_metrics(market_state, hourly, fourh, params, "short")
    flow_ready = _flow_entry_ok(market_state, hourly, fourh, params, "short", strong=False)
    direct_breakdown = (
        context["prev_breakdown_distance_pct"] <= atr_ratio * 0.04
        and context["current_candle"]["close_pos"] <= min(params["breakdown_close_pos_max"] + 0.01, 0.30)
        and context["current_candle"]["body_ratio"] >= max(params["breakdown_body_ratio_min"] - 0.01, 0.40)
        and context["current"]["volume"] >= max(context["prev_volume"] * 0.98, context["recent_volume_avg"] * 1.00)
        and flow_metrics["score"] >= 5
        and flow_metrics["directional_bias"] >= 0.04
    )
    acceptance_breakdown = (
        context["breakdown_distance_pct"] <= atr_ratio * 0.22
        and context["prev_breakdown_distance_pct"] <= atr_ratio * 0.04
        and context["current"]["low"] < context["prev"]["low"]
        and context["current_range"] >= max(context["prev_range"] * 0.96, context["recent_range_avg"] * 0.92)
        and context["current_candle"]["close_pos"] <= min(params["breakdown_close_pos_max"] + 0.03, 0.32)
        and context["current_candle"]["body_ratio"] >= max(params["breakdown_body_ratio_min"] - 0.03, 0.36)
        and context["current"]["volume"] >= max(context["prev_volume"] * 0.95, context["recent_volume_avg"] * 0.98)
        and flow_metrics["score"] >= 5
        and (
            flow_metrics["directional_bias"] >= 0.04
            or context["volume_ratio"] >= max(params["breakdown_volume_ratio_min"], 1.10)
        )
    )
    return (
        (not require_breakdown_gate or breakdown_ready(context, market_state, params))
        and context["breakdown_distance_pct"] <= atr_ratio * 0.30
        and context["breakdown_low_penetration_pct"] >= max(atr_ratio * 0.14, context["breakdown_distance_pct"] * 0.96)
        and flow_ready
        and (direct_breakdown or acceptance_breakdown)
    )


def short_breakdown_ok(context, market_state, params):
    return _short_breakdown_path_ok(context, market_state, params, require_breakdown_gate=True)


def _short_bounce_fail_path_ok(context, market_state, params, require_breakdown_gate=True):
    current = context["current"]
    prev = context["prev"]
    hourly = context["hourly"]
    fourh = context["fourh"]
    atr_ratio = context["atr_ratio"]
    flow_metrics = _flow_signal_metrics(market_state, hourly, fourh, params, "short")
    prior_breakdown_hold = context["prev_breakdown_distance_pct"] >= atr_ratio * 0.05 or prev["low"] <= context["breakdown_low"] * (1.0 + atr_ratio * 0.04)
    return (
        (not require_breakdown_gate or breakdown_ready(context, market_state, params))
        and prior_breakdown_hold
        and context["breakdown_distance_pct"] >= atr_ratio * 0.07
        and context["breakdown_distance_pct"] <= atr_ratio * 0.18
        and prev["high"] >= context["breakdown_low"] * (1.0 + atr_ratio * 0.03)
        and prev["high"] <= hourly["ema_fast"] * (1.0 + atr_ratio * 0.36)
        and prev["close"] >= prev["low"] + context["prev_range"] * 0.36
        and prev["close"] >= context["breakdown_low"] * (1.0 + atr_ratio * 0.01)
        and current["close"] < prev["low"]
        and context["current_range"] >= max(context["prev_range"] * 1.02, context["recent_range_avg"] * 0.94)
        and context["current_candle"]["body_ratio"] >= max(context["prev_candle"]["body_ratio"] * 1.02, 0.40)
        and current["volume"] >= max(context["prev_volume"] * 1.02, context["recent_volume_avg"] * 1.04)
        and flow_metrics["score"] >= 5
        and flow_metrics["directional_bias"] >= 0.04
        and _flow_entry_ok(market_state, hourly, fourh, params, "short", strong=False)
        and fourh["trend_spread_pct"] <= max(hourly["trend_spread_pct"] * 0.52, -atr_ratio * 0.58)
    )


def short_bounce_fail_ok(context, market_state, params):
    return _short_bounce_fail_path_ok(context, market_state, params, require_breakdown_gate=True)


def short_trend_reaccel_ok(context, market_state, params):
    current = context["current"]
    prev = context["prev"]
    hourly = context["hourly"]
    fourh = context["fourh"]
    atr_ratio = context["atr_ratio"]
    flow_metrics = _flow_signal_metrics(market_state, hourly, fourh, params, "short")
    prior_breakdown_hold = context["prev_breakdown_distance_pct"] >= atr_ratio * 0.05 or prev["close"] <= context["breakdown_low"] * (1.0 + atr_ratio * 0.04)
    strong_fourh_bear = (
        fourh["trend_spread_pct"] <= -max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 1.06, atr_ratio * 0.68)
        and fourh["ema_slow_slope_pct"] <= -atr_ratio * 0.032
        and fourh["macd_line"] < fourh["signal_line"]
    )
    price_reaccel_ready = (
        current["close"] <= context["breakdown_low"] * (1.0 - params["breakdown_buffer_pct"] * 0.18)
        and context["breakdown_distance_pct"] >= atr_ratio * 0.04
        and context["breakdown_distance_pct"] <= atr_ratio * 0.30
        and current["low"] <= prev["low"] * (1.0 + atr_ratio * 0.04)
        and current["close"] <= prev["close"] * (1.0 + atr_ratio * 0.02)
    )
    range_reaccel_ready = (
        context["current_range"] >= max(context["prev_range"] * 0.92, context["recent_range_avg"] * 0.88)
    )
    volume_reaccel_ready = (
        current["volume"] >= max(context["prev_volume"] * 0.84, context["recent_volume_avg"] * 0.86)
    )
    adx_reaccel_ready = (
        market_state["adx"] >= max(params["breakdown_adx_min"] - 2.6, params["intraday_adx_min"])
    )
    hourly_reaccel_ready = (
        hourly["trend_spread_pct"] <= -max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.08, atr_ratio * 0.68)
    )
    flow_reaccel_ready = (
        _flow_entry_ok(market_state, hourly, fourh, params, "short", strong=not strong_fourh_bear)
        and flow_metrics["directional_bias"] >= (0.025 if strong_fourh_bear else 0.035)
    )
    return (
        price_reaccel_ready
        and prior_breakdown_hold
        and range_reaccel_ready
        and volume_reaccel_ready
        and adx_reaccel_ready
        and hourly_reaccel_ready
        and fourh["trend_spread_pct"] <= -max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 0.74, atr_ratio * 0.66)
        and fourh["ema_slow_slope_pct"] <= -atr_ratio * (0.032 if strong_fourh_bear else 0.036)
        and flow_reaccel_ready
    )


def _short_trend_path_ok(context, market_state, params):
    if context.get("short_outer_lane") != "trend":
        return False
    current = context["current"]
    prev = context["prev"]
    hourly = context["hourly"]
    fourh = context["fourh"]
    atr_ratio = context["atr_ratio"]
    flow_metrics = _flow_signal_metrics(market_state, hourly, fourh, params, "short")
    price_trend_ready = (
        current["close"] <= context["breakdown_low"] * (1.0 + atr_ratio * 0.04)
        and context["breakdown_distance_pct"] >= atr_ratio * 0.02
        and context["breakdown_distance_pct"] <= atr_ratio * 0.26
        and current["close"] <= prev["close"] * (1.0 + atr_ratio * 0.03)
    )
    continuation_shape_ok = (
        context["current_candle"]["close_pos"] <= min(params["breakdown_close_pos_max"] + 0.05, 0.39)
        and context["current_candle"]["body_ratio"] >= max(params["breakdown_body_ratio_min"] - 0.07, 0.32)
        and context["current_range"] >= max(context["prev_range"] * 0.84, context["recent_range_avg"] * 0.82)
    )
    participation_ok = (
        current["volume"] >= max(context["prev_volume"] * 0.80, context["recent_volume_avg"] * 0.84)
        and flow_metrics["score"] >= 4
        and flow_metrics["directional_bias"] >= 0.02
    )
    trend_structure_ok = (
        hourly["trend_spread_pct"] <= -max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.00, atr_ratio * 0.62)
        and fourh["trend_spread_pct"] <= -max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 0.70, atr_ratio * 0.62)
        and fourh["ema_slow_slope_pct"] <= -atr_ratio * 0.030
    )
    return (
        _trend_quality_short(market_state)
        and price_trend_ready
        and continuation_shape_ok
        and participation_ok
        and trend_structure_ok
    )


def _short_final_veto_blocked(context, market_state, params, short_path_key, breakdown_ok, bounce_fail_ok, reaccel_ok, flow_metrics):
    hourly = context["hourly"]
    fourh = context["fourh"]
    atr_ratio = context["atr_ratio"]
    breakdown_volume_confirmed = (
        context["current"]["volume"] > context["short_breakdown_veto_volume_avg"] * SHORT_BREAKDOWN_FINAL_VETO_VOLUME_AVG_MULT
        or context["current"]["volume"] >= context["prev_volume"] * SHORT_BREAKDOWN_FINAL_VETO_VOLUME_PREV_MULT
    )
    exhausted_selloff = (
        context["breakdown_distance_pct"] >= atr_ratio * 0.20
        and context["hourly_fast_discount_pct"] >= max(atr_ratio * 0.98, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 2.22)
        and context["hourly_anchor_discount_pct"] >= max(atr_ratio * 1.58, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 3.72)
        and (
            fourh["trend_spread_pct"] > min(hourly["trend_spread_pct"] * 0.90, -atr_ratio * 1.02)
            or fourh["ema_slow_slope_pct"] > -atr_ratio * 0.040
            or fourh["adx"] < max(params["fourh_adx_min"], 13.8)
        )
    )
    stale_breakdown_risk = (
        context["prev_breakdown_reference_distance_pct"] >= atr_ratio * 0.08
        and context["breakdown_distance_pct"] < max(context["prev_breakdown_reference_distance_pct"] + atr_ratio * 0.04, atr_ratio * 0.18)
        and context["current_range"] < max(context["prev_range"] * 1.04, context["recent_range_avg"] * 1.04)
        and context["current"]["volume"] < max(context["prev_volume"] * 1.04, context["recent_volume_avg"] * 1.04)
    )
    weak_flow_dump = (
        flow_metrics["score"] < 5
        and flow_metrics["directional_bias"] < 0.04
        and not (breakdown_ok or bounce_fail_ok)
        and context["breakdown_distance_pct"] >= atr_ratio * 0.12
    )
    return (
        (exhausted_selloff and not reaccel_ok)
        or (stale_breakdown_risk and bounce_fail_ok and not reaccel_ok)
        or (stale_breakdown_risk and not (breakdown_ok or reaccel_ok))
        or weak_flow_dump
        or (short_path_key == "short_breakdown" and not breakdown_volume_confirmed)
    )


def short_final_veto_clear(context, market_state, params, short_path_key, breakdown_ok, bounce_fail_ok, reaccel_ok):
    hourly = context["hourly"]
    fourh = context["fourh"]
    atr_ratio = context["atr_ratio"]
    flow_metrics = _flow_signal_metrics(market_state, hourly, fourh, params, "short")
    relaxed_quality_ok = (
        atr_ratio >= SHORT_FINAL_VETO_RELAXED_ATR_MIN
        and market_state["adx"] >= SHORT_FINAL_VETO_RELAXED_ADX_MIN
        and hourly["adx"] >= max(SHORT_FINAL_VETO_RELAXED_ADX_MIN - 2.0, params["hourly_adx_min"] + 2.0)
    )
    if _short_final_veto_blocked(
        context,
        market_state,
        params,
        short_path_key,
        breakdown_ok,
        bounce_fail_ok,
        reaccel_ok,
        flow_metrics,
    ):
        return False
    if str(short_path_key or "").strip() in {"short_trend", "short_impulse"}:
        if not _flow_confirmation_ok(
            market_state,
            hourly,
            fourh,
            params,
            "short",
            strong=True,
        ):
            return False
        if _trend_quality_short(market_state) <= 0.2:
            return False
    return _trend_followthrough_short(
        market_state,
        context["breakdown_low"],
        context["current"]["close"],
        entry_path_key=short_path_key,
        quality_relax_ok=relaxed_quality_ok,
    )


# ==================== Legacy Entry Adapters ====================

def _long_entry_signal(data, idx, positions, market_state):
    p = PARAMS
    context = _strategy_entry_context(data, idx, positions, market_state, p)
    if context is None:
        return None
    if not long_outer_context_ok(context, market_state, p):
        return None
    long_breakout_path = long_breakout_ok(context, market_state, p)
    long_pullback_path = long_pullback_ok(context, market_state, p)
    merged_long_core_path = _merged_long_core_path_ok(long_breakout_path, long_pullback_path)
    long_reaccel_path = long_trend_reaccel_ok(context, market_state, p)
    if _long_reversal_sniper_ok(context) and merged_long_core_path:
        return normalize_entry_signal("long_reversal_sniper", fallback_side="long") or None
    if long_signal_path_ok(merged_long_core_path, merged_long_core_path, long_reaccel_path):
        return normalize_entry_signal("long_pullback", fallback_side="long") or None
    return None


def _strategy_entry_context(data, idx, positions, market_state, params, allow_sideways=False):
    if idx < params["min_history"]:
        return None
    context = _build_signal_context(data, idx, market_state, params)
    if context is None:
        return None
    sideways_regime = _is_sideways_regime(market_state, positions=positions)
    context["sideways_regime"] = sideways_regime
    if sideways_regime and not allow_sideways:
        return None
    return context


def _short_entry_path_key(context, market_state, params, require_breakdown_gate=False):
    short_impulse_rsi_ok = _short_impulse_hourly_rsi_ok(market_state)
    short_trend_path = _short_trend_path_ok(context, market_state, params)
    if require_breakdown_gate:
        short_breakdown_path = short_breakdown_ok(context, market_state, params)
        short_bounce_fail_path = short_bounce_fail_ok(context, market_state, params)
    else:
        short_breakdown_path = _short_breakdown_path_ok(
            context,
            market_state,
            params,
            require_breakdown_gate=False,
        )
        short_bounce_fail_path = _short_bounce_fail_path_ok(
            context,
            market_state,
            params,
            require_breakdown_gate=False,
        )
    if not short_impulse_rsi_ok:
        short_trend_path = False
        short_breakdown_path = False
    if short_breakdown_path:
        return "short_breakdown"
    if short_bounce_fail_path:
        return "short_bounce_fail"
    if short_trend_reaccel_ok(context, market_state, params):
        return "short_reaccel"
    return ""


def _long_entry_result(
    context,
    market_state,
    params,
    positions,
    long_breakout_path,
    long_pullback_path,
    long_reaccel_path,
    long_ownership_relay,
    *,
    as_decision,
):
    if not (long_signal_path_ok(long_breakout_path, long_pullback_path, long_reaccel_path) or long_ownership_relay):
        return None
    _record_funnel_pass("long", "path_pass")
    try:
        strong_trend_bypass = _long_strong_trend_bypass(context, market_state, params)
    except (KeyError, TypeError):
        strong_trend_bypass = False
    if not long_final_veto_clear(
        context,
        market_state,
        params,
        long_breakout_path,
        long_pullback_path,
        long_reaccel_path,
        long_ownership_relay,
        strong_trend_bypass=strong_trend_bypass,
    ):
        return None
    _record_funnel_pass("long", "final_veto_pass")
    if not _long_entry_addition_available(positions, context["current"]["close"], market_state):
        return None

    path_key = "long_relay"
    if long_breakout_path:
        path_key = "long_breakout"
    elif long_pullback_path:
        path_key = "long_pullback"
    elif long_reaccel_path:
        path_key = "long_reaccel"

    if as_decision:
        return {
            "entry_signal": "long_pullback",
            "entry_side": "long",
            "entry_path_key": path_key,
            "entry_path_tag": ENTRY_PATH_TAGS.get(path_key, path_key),
        }
    return normalize_entry_signal("long_pullback", fallback_side="long") or None


def _short_entry_result(context, market_state, params, short_path_key, *, as_decision):
    return None


def _short_entry_signal(data, idx, positions, market_state):
    return None


def _decision_signal_strength(context, market_state, params, side, entry_path_key=""):
    if side != "long":
        return 0.0
    flow_metrics = _flow_signal_metrics(
        market_state,
        context["hourly"],
        context["fourh"],
        params,
        side,
    )
    followthrough_ok = _trend_followthrough_long(
        market_state,
        context["breakout_high"],
        context["current"]["close"],
    )
    quality_ok = _trend_quality_long(market_state)
    return (
        float(flow_metrics["score"])
        + flow_metrics["directional_bias"] * 10.0
        + flow_metrics["participation_bias"] * 4.0
        + (1.0 if quality_ok else 0.0)
        + (1.0 if followthrough_ok else 0.0)
    )


def _prefer_long_on_close_decision(context, market_state, params, long_strength, short_strength):
    return True


def _long_quality_override(market_state, params):
    return (
        0.65 * float(_trend_quality_long(market_state))
        + 0.35 * _fourh_trend_quality_long_score(market_state, params)
    ) >= 0.60


def _long_paths_with_handoff(context, market_state, params, long_breakout_path, long_pullback_path, long_reaccel_path):
    has_long_signal_path = long_signal_path_ok(long_breakout_path, long_pullback_path, long_reaccel_path)
    if has_long_signal_path:
        return long_breakout_path, long_pullback_path, has_long_signal_path

    long_handoff_ready = (
        context.get("long_outer_lane") == "early_turn"
        and context["long_reclaim_ready"]
        and context["current"]["high"] >= context["breakout_high"]
        and context["current"]["close"] >= context["breakout_high"] * (1.0 - context["atr_ratio"] * 0.015)
        and context["breakout_distance_pct"] >= -context["atr_ratio"] * 0.02
        and context["breakout_distance_pct"] <= context["atr_ratio"] * 0.14
        and context["current"]["close"] >= context["prev"]["close"]
        and context["current_candle"]["close_pos"] >= max(params["breakout_close_pos_min"] - 0.08, 0.48)
        and context["volume_ratio"] >= max(params["breakout_volume_ratio_min"] - 0.16, 0.82)
        and context["current"]["volume"] >= max(context["prev_volume"] * 0.78, context["recent_volume_avg"] * 0.80)
        and context["breakout_reference_stale_gap_pct"] <= max(context["atr_ratio"] * 0.52, 0.0040)
        and _flow_entry_ok(
            market_state,
            context["hourly"],
            context["fourh"],
            params,
            "long",
            strong=False,
        )
    )
    long_handoff_breakout = (
        long_handoff_ready
        and context["current"]["close"] >= context["breakout_high"] * (1.0 + params["breakout_buffer_pct"] * 0.35)
        and context["current"]["close"] >= context["prev"]["high"] * (1.0 - context["atr_ratio"] * 0.04)
        and context["current_range"] >= context["recent_range_avg"] * 0.72
        and context["current_candle"]["body_ratio"] >= max(params["breakout_body_ratio_min"] - 0.08, 0.18)
    )
    long_handoff_pullback = (
        long_handoff_ready
        and not long_handoff_breakout
        and context["prev"]["low"] <= context["breakout_high"] * (1.0 + context["atr_ratio"] * 0.18)
        and context["current"]["close"] > max(
            context["prev"]["close"],
            context["breakout_high"] * (1.0 - context["atr_ratio"] * 0.010),
        )
        and context["prev_breakout_distance_pct"] <= context["atr_ratio"] * 0.10
        and context["current_range"] >= max(context["prev_range"] * 0.72, context["recent_range_avg"] * 0.68)
    )
    long_breakout_path = long_breakout_path or long_handoff_breakout
    long_pullback_path = long_pullback_path or long_handoff_pullback
    return (
        long_breakout_path,
        long_pullback_path,
        long_signal_path_ok(long_breakout_path, long_pullback_path, long_reaccel_path),
    )


def _long_ownership_relay_ready(context, market_state, params):
    long_ownership_relay = (
        context.get("long_outer_lane") != "early_turn"
        and context["long_reclaim_ready"]
        and context["current"]["high"] >= context["breakout_high"]
        and context["current"]["close"] >= context["breakout_high"] * (1.0 - context["atr_ratio"] * 0.012)
        and context["breakout_distance_pct"] >= -context["atr_ratio"] * 0.02
        and context["breakout_distance_pct"] <= context["atr_ratio"] * 0.12
        and context["current"]["close"] >= context["prev"]["close"]
        and context["current_candle"]["close_pos"] >= max(params["breakout_close_pos_min"] - 0.08, 0.48)
        and context["current"]["volume"] >= max(context["prev_volume"] * 0.78, context["recent_volume_avg"] * 0.80)
        and _flow_entry_ok(
            market_state,
            context["hourly"],
            context["fourh"],
            params,
            "long",
            strong=False,
        )
    )
    if long_ownership_relay:
        return True
    return (
        _long_quality_override(market_state, params)
        and context["long_reclaim_ready"]
        and context["current"]["high"] >= context["breakout_high"]
        and context["current"]["close"] >= context["breakout_high"] * (1.0 + params["breakout_buffer_pct"])
    )


# ==================== Fixed Factor Slot Edit Surface ====================
#
# Research candidates may change only PARAMS, open EXIT_PARAMS, FACTOR_SLOT_PARAMS
# numeric values, and the fixed _slot_* function bodies. For long entry changes,
# edit the relevant _slot_long_* function instead of the locked helper underneath:
# _slot_long_context   -> outer long regime admission
# _slot_long_breakout  -> breakout / upward release path
# _slot_long_pullback  -> EMA retest / reclaim path
# _slot_long_reaccel   -> trend continuation path
# _slot_long_flow      -> participation and directional flow quality
# _slot_long_veto      -> negative filters; return negative values to block
# _slot_long_extra_*   -> spare bounded experiments

def _slot_config(slot_name):
    return FACTOR_SLOT_PARAMS.get(slot_name, {"enabled": 0, "weight": 0.0, "threshold": 0.0})


def _slot_enabled(slot_name):
    try:
        return int(_slot_config(slot_name).get("enabled", 0) or 0) != 0
    except (TypeError, ValueError):
        return False


def _slot_weight(slot_name):
    try:
        return max(float(_slot_config(slot_name).get("weight", 0.0) or 0.0), 0.0)
    except (TypeError, ValueError):
        return 0.0


def _slot_threshold(slot_name):
    try:
        return float(_slot_config(slot_name).get("threshold", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _slot_score_value(raw_score):
    if isinstance(raw_score, bool):
        return 1.0 if raw_score else 0.0
    try:
        value = float(raw_score)
    except (TypeError, ValueError):
        return 0.0
    return max(min(value, 1.0), -1.0)


def _slot_safe_eval(slot_name, context, market_state, params, side):
    evaluators = {
        "regime_trend": _slot_regime_trend,
        "regime_sideways": _slot_regime_sideways,
        "regime_volatility": _slot_regime_volatility,
        "regime_external": _slot_regime_external,
        "long_context": _slot_long_context,
        "long_breakout": _slot_long_breakout,
        "long_pullback": _slot_long_pullback,
        "long_reaccel": _slot_long_reaccel,
        "long_flow": _slot_long_flow,
        "long_veto": _slot_long_veto,
        "long_extra_1": _slot_long_extra_1,
        "long_extra_2": _slot_long_extra_2,
        "short_context": _slot_short_context,
        "short_breakdown": _slot_short_breakdown,
        "short_bounce_fail": _slot_short_bounce_fail,
        "short_reaccel": _slot_short_reaccel,
        "short_flow": _slot_short_flow,
        "short_veto": _slot_short_veto,
        "short_extra_1": _slot_short_extra_1,
        "short_extra_2": _slot_short_extra_2,
    }
    evaluator = evaluators.get(slot_name)
    if evaluator is None:
        return 0.0
    try:
        return _slot_score_value(evaluator(context, market_state, params, side))
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return 0.0


def _slot_gate_ok(slot_scores, slot_name):
    if not _slot_enabled(slot_name):
        return True
    return _slot_score_value(slot_scores.get(slot_name, 0.0)) >= _slot_threshold(slot_name)


def _slot_path_ok(slot_scores, slot_name):
    if not _slot_enabled(slot_name):
        return False
    return _slot_score_value(slot_scores.get(slot_name, 0.0)) >= _slot_threshold(slot_name)


def _slot_bundle_score(slot_scores):
    weighted_total = 0.0
    weight_total = 0.0
    for slot_name, raw_score in slot_scores.items():
        if not _slot_enabled(slot_name):
            continue
        weight = _slot_weight(slot_name)
        if weight <= 0.0:
            continue
        weighted_total += max(_slot_score_value(raw_score), 0.0) * weight
        weight_total += weight
    if weight_total <= 0.0:
        return 0.0
    return weighted_total / weight_total


def _slot_regime_trend(context, market_state, params, side):
    if side == "short":
        return _trend_quality_short(market_state)
    return _trend_quality_long(market_state)


def _slot_regime_sideways(context, market_state, params, side):
    return 0.0 if bool(context.get("sideways_regime", False)) else 1.0


def _slot_regime_volatility(context, market_state, params, side):
    atr_ratio = float(context.get("atr_ratio", 0.0) or 0.0)
    if atr_ratio <= 0.0:
        return 0.0
    return min(atr_ratio / max(SIDEWAYS_MIN_ATR_RATIO, 1e-9), 1.0)


def _slot_regime_external(context, market_state, params, side):
    fear_greed = _safe_payload_float(market_state, "fear_greed_value", 50.0)
    delta3 = _safe_payload_float(market_state, "fear_greed_delta3", 0.0)
    flow = _safe_payload_float(market_state, "flow_imbalance", 0.0)
    sentiment_centered = (fear_greed - 50.0) / 50.0
    direction = 1.0 if side == "long" else -1.0
    return 0.5 + 0.25 * direction * sentiment_centered + 0.15 * direction * delta3 + 0.10 * direction * flow


def _slot_long_context(context, market_state, params, side):
    if long_outer_context_ok(context, market_state, params):
        return 1.0

    current = context["current"]
    hourly = context["hourly"]
    fourh = context["fourh"]
    atr_ratio = max(float(context.get("atr_ratio", 0.0) or 0.0), 0.0)
    flow_metrics = _flow_signal_metrics(market_state, hourly, fourh, params, "long")
    late_mature_guard = _long_late_mature_guard(context)
    fourh_not_strong_bear = _long_fourh_not_strong_bear(context, params)
    reclaim_ready = _long_reclaim_ready(context, market_state, params)
    hourly_turn_repair_ready = _long_hourly_turn_repair_ready(context, params)

    intraday_ok = (
        current["close"] >= context["intraday_bull_ema"] * (1.0 - atr_ratio * 0.10)
        and market_state["adx"] >= max(params["intraday_adx_min"] - 1.0, 10.0)
    )
    hourly_direction_bias = max(
        hourly["trend_spread_pct"],
        hourly["ema_fast_slope_pct"],
        hourly["ema_slow_slope_pct"],
    )
    hourly_ok = (
        hourly["close"] >= hourly["ema_slow"] * (1.0 - atr_ratio * 0.10)
        and hourly_direction_bias >= -max(atr_ratio * 0.040, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 0.12)
        and hourly["ema_slow_slope_pct"] >= -atr_ratio * 0.018
        and hourly["adx"] >= max(params["hourly_adx_min"] - 3.2, 9.8)
    )
    fourh_ok = (
        fourh["close"] >= fourh["ema_slow"] * (1.0 - atr_ratio * 0.18)
        and fourh["trend_spread_pct"] >= -max(atr_ratio * 0.12, SIDEWAYS_MIN_FOURH_SPREAD_PCT * 0.24)
        and fourh["ema_slow_slope_pct"] >= -atr_ratio * 0.024
        and fourh["adx"] >= max(params["fourh_adx_min"] - 2.0, 8.5)
    )
    flow_ok = (
        flow_metrics["directional_bias"] >= -0.01
        or flow_metrics["score"] >= max(float(params.get("breakout_flow_score_min", 1) or 1), 3.0)
    )

    extension_ok = _hourly_extension_within(
        context,
        1.02,
        2.32,
        1.48,
        3.44,
    )
    breakout_distance_cap = atr_ratio * 1.10
    volatility_ok = (
        context["breakout_distance_pct"] <= breakout_distance_cap
        and context["prev_breakout_distance_pct"] <= breakout_distance_cap * 0.92
        and extension_ok
    )

    support_count = _count_true(intraday_ok, hourly_ok, fourh_ok, flow_ok)
    if support_count >= 3 and volatility_ok and fourh_not_strong_bear and not late_mature_guard:
        return 1.0
    if reclaim_ready and hourly_turn_repair_ready and (hourly_ok or flow_ok) and volatility_ok and not late_mature_guard:
        return 0.72
    return 0.0


def _slot_long_breakout(context, market_state, params, side):
    if long_breakout_ok(context, market_state, params):
        return 1.0
    current = context["current"]
    hourly = context["hourly"]
    fourh = context["fourh"]
    atr_ratio = context["atr_ratio"]
    near_breakout = (
        current["high"] >= context["breakout_high"] * (1.0 - max(atr_ratio * 0.36, 0.0026))
        and current["close"] >= context["breakout_high"] * (1.0 - max(atr_ratio * 0.22, 0.0018))
        and context["breakout_distance_pct"] <= atr_ratio * 0.24
        and current["close"] >= max(float(market_state["ema_fast"]), float(market_state["ema_slow"])) * (1.0 - atr_ratio * 0.04)
        and hourly["close"] >= hourly["ema_slow"] * (1.0 - atr_ratio * 0.12)
        and fourh["close"] >= fourh["ema_slow"] * (1.0 - atr_ratio * 0.24)
        and context["current_candle"]["close_pos"] >= 0.42
    )
    return 0.35 if near_breakout else 0.0


def _slot_long_pullback(context, market_state, params, side):
    current = context["current"]
    prev = context["prev"]
    pre_prev = context["pre_prev"]
    hourly = context["hourly"]
    fourh = context["fourh"]
    atr_ratio = context["atr_ratio"]
    support = max(float(market_state["ema_fast"]), float(market_state["ema_slow"]))
    pullback_depth_ok = current["close"] <= context["breakout_high"] * (1.0 - atr_ratio * 0.8)
    if not pullback_depth_ok:
        return 0.0
    base_score = 0.0
    if long_pullback_ok(context, market_state, params):
        base_score = 1.0
    else:
        if current["close"] > context["breakout_high"] * (1.0 - atr_ratio * 0.8):
            return 0.0
        simple_structure = (
            current["close"] >= support * (1.0 - atr_ratio * 0.08)
            and context["breakout_reclaim_gap_pct"] <= max(atr_ratio * 0.90, 0.0068)
            and context["breakout_distance_pct"] >= -atr_ratio * 0.72
            and context["breakout_distance_pct"] <= atr_ratio * 0.26
            and hourly["close"] >= hourly["ema_slow"] * (1.0 - atr_ratio * 0.16)
            and fourh["close"] >= fourh["ema_slow"] * (1.0 - atr_ratio * 0.32)
            and hourly["ema_slow_slope_pct"] >= -atr_ratio * 0.040
            and fourh["ema_slow_slope_pct"] >= -atr_ratio * 0.048
            and market_state["adx"] >= max(params["intraday_adx_min"] - 3.0, 8.5)
            and context["current_candle"]["close_pos"] >= 0.40
            and context["volume_ratio"] >= 0.58
        )
        base_score = 0.35 if simple_structure else 0.0
    if base_score <= 0.0:
        return 0.0

    support_wick_confirmed = False
    for bar in (pre_prev, prev, current):
        lower_wick = min(bar["open"], bar["close"]) - bar["low"]
        body = abs(bar["close"] - bar["open"])
        if lower_wick > body and bar["close"] >= (bar["high"] + bar["low"]) * 0.5:
            support_wick_confirmed = True
            break

    baseline_volume = max(
        current["volume"] / max(float(context["volume_ratio"]), 1e-9),
        float(context["recent_volume_avg"]),
        1e-9,
    )
    prior_avg_volume = (float(pre_prev["volume"]) + float(prev["volume"])) * 0.5
    shrink_then_pop = (
        prior_avg_volume < baseline_volume
        and current["volume"] > prior_avg_volume
    )

    if support_wick_confirmed and shrink_then_pop:
        return min(base_score * 1.3, 1.0)
    if not support_wick_confirmed and not shrink_then_pop:
        return base_score * 0.7
    return base_score


def _slot_long_reaccel(context, market_state, params, side):
    current = context["current"]
    prev = context["prev"]
    pre_prev = context["pre_prev"]
    hourly = context["hourly"]
    fourh = context["fourh"]
    atr_ratio = max(float(context.get("atr_ratio", 0.0) or 0.0), 0.0)
    ema20 = _safe_payload_float(
        market_state,
        "ema20",
        _safe_payload_float(
            market_state,
            "ema_20",
            _safe_payload_float(market_state, "ema_slow", current["close"]),
        ),
    )
    recent_low_floor = min(
        float(context.get("reversal_reference_low", current["low"])),
        float(prev["low"]),
        float(pre_prev["low"]),
    )
    hist = _safe_payload_float(market_state, "histogram", 0.0)
    prev_hist = _safe_payload_float(market_state, "prev_histogram", hist)
    pre_prev_hist = _safe_payload_float(market_state, "prev_prev_histogram", prev_hist)
    flow_metrics = _flow_signal_metrics(market_state, hourly, fourh, params, "long")
    flow_aligned = (
        flow_metrics["directional_bias"] >= 0.0
        or _safe_payload_float(market_state, "flow_imbalance", 0.0) >= 0.0
        or (
            hourly["flow_imbalance"] >= 0.0
            and fourh["flow_imbalance"] >= -0.01
        )
    )
    rebound_from_low = (
        current["close"] >= recent_low_floor * (1.0 + atr_ratio * 0.010)
        and current["low"] >= recent_low_floor * (1.0 + atr_ratio * 0.002)
        and current["close"] >= prev["close"] * (1.0 + atr_ratio * 0.004)
    )
    ema20_reclaim = (
        current["close"] >= ema20
        and current["low"] >= ema20 * (1.0 - atr_ratio * 0.03)
        and prev["close"] <= ema20 * (1.0 + atr_ratio * 0.02)
    )
    macd_accel = (
        hist > 0.0
        and prev_hist > 0.0
        and hist >= prev_hist >= pre_prev_hist
    )
    volume_accel = (
        current["volume"] >= max(float(context["recent_volume_avg"]) * 0.90, float(prev["volume"]) * 1.02)
        and context["volume_ratio"] >= 0.86
    )
    trend_support = (
        current["close"] >= hourly["ema_slow"] * (1.0 - atr_ratio * 0.08)
        and hourly["ema_slow_slope_pct"] >= -atr_ratio * 0.012
        and fourh["close"] >= fourh["ema_slow"] * (1.0 - atr_ratio * 0.14)
        and fourh["ema_slow_slope_pct"] >= -atr_ratio * 0.016
        and market_state["adx"] >= max(params["intraday_adx_min"] + 0.8, 12.0)
        and context["current_candle"]["close_pos"] >= 0.52
    )
    if rebound_from_low and ema20_reclaim and macd_accel and volume_accel and trend_support:
        return 1.0

    if rebound_from_low and ema20_reclaim and macd_accel and trend_support:
        score = 0.78
        if volume_accel:
            score += 0.08
        if flow_aligned:
            score += 0.06
        return min(score, 1.0)

    if ema20_reclaim and macd_accel and trend_support:
        score = 0.52
        if rebound_from_low:
            score += 0.08
        if volume_accel:
            score += 0.08
        if flow_aligned:
            score += 0.06
        return min(score, 1.0)

    return 0.0


def _slot_long_flow(context, market_state, params, side):
    metrics = _flow_signal_metrics(market_state, context["hourly"], context["fourh"], params, "long")
    target = max(float(params.get("breakout_flow_score_strong_min", 1) or 1), 1.0)
    score_ratio = float(metrics.get("score", 0.0)) / target
    bias_bonus = max(float(metrics.get("directional_bias", 0.0)), 0.0) * 2.0
    return min(score_ratio + bias_bonus, 1.0)


def _slot_long_veto(context, market_state, params, side):
    sentiment = str((market_state or {}).get("sentiment", "") or "").strip().lower()
    fear_greed_value = _safe_payload_float(market_state, "fear_greed_value", 50.0)
    if sentiment == "fear" or fear_greed_value < 35.0:
        return -1.0

    if _is_sideways_regime(market_state):
        return -1.0

    hourly = context["hourly"]
    fourh = context["fourh"]
    intraday_chop = _safe_payload_float(market_state, "chop", 0.0)
    hourly_chop = _safe_payload_float(hourly, "chop", 0.0)
    intraday_flow_imbalance = _safe_payload_float(market_state, "flow_imbalance", 0.0)
    hourly_flow_imbalance = _safe_payload_float(hourly, "flow_imbalance", 0.0)
    fourh_flow_imbalance = _safe_payload_float(fourh, "flow_imbalance", 0.0)
    flow_metrics = _flow_signal_metrics(market_state, hourly, fourh, params, "long")

    severe_counter_flow = (
        (hourly_flow_imbalance <= -0.06 and fourh_flow_imbalance <= -0.04)
        or (intraday_flow_imbalance <= -0.14 and hourly_flow_imbalance <= -0.03)
    )
    if severe_counter_flow:
        return -1.0

    high_chop_no_direction = (
        intraday_chop >= 52.0
        and hourly_chop >= 57.0
        and max(intraday_flow_imbalance, hourly_flow_imbalance) <= 0.05
        and flow_metrics["directional_bias"] <= 0.08
    )
    if high_chop_no_direction:
        return -1.0

    if intraday_chop >= 60.0:
        return -1.0

    return 1.0


def _slot_long_extra_1(context, market_state, params, side):
    fear_greed_value = _safe_payload_float(market_state, "fear_greed_value", 50.0)
    flow_imbalance = _safe_payload_float(market_state, "flow_imbalance", 0.0)
    if fear_greed_value >= 82.0 and flow_imbalance < -0.02:
        return 0.0
    return 1.0


def _slot_long_extra_2(context, market_state, params, side):
    current = context["current"]
    prev = context["prev"]
    pre_prev = context["pre_prev"]
    atr_ratio = context["atr_ratio"]
    fear_greed_value = _safe_payload_float(market_state, "fear_greed_value", 50.0)
    flow_imbalance = _safe_payload_float(market_state, "flow_imbalance", 0.0)
    ema20 = _safe_payload_float(
        market_state,
        "ema20",
        _safe_payload_float(
            market_state,
            "ema_20",
            _safe_payload_float(market_state, "ema_slow", current["close"]),
        ),
    )

    recent_low_floor = min(
        float(context.get("reversal_reference_low", current["low"])),
        float(pre_prev["low"]),
    )
    higher_low_reversal = (
        prev["low"] >= pre_prev["low"]
        and current["low"] >= prev["low"]
        and current["low"] > recent_low_floor * (1.0 + atr_ratio * 0.12)
    )
    volume_expansion = current["volume"] >= max(float(context["recent_volume_avg"]) * 1.2, float(prev["volume"]) * 1.02)
    close_reclaim = current["close"] > ema20 and current["close"] >= prev["close"] * 1.002
    candle_quality = context["current_candle"]["close_pos"] >= 0.58 and context["current_candle"]["body_ratio"] >= 0.24

    if (
        fear_greed_value < 30.0
        and higher_low_reversal
        and close_reclaim
        and flow_imbalance > -0.3
        and volume_expansion
        and candle_quality
    ):
        return 0.72
    return 0.0


def _slot_short_context(context, market_state, params, side):
    return 0.0


def _slot_short_breakdown(context, market_state, params, side):
    return 0.0


def _slot_short_bounce_fail(context, market_state, params, side):
    return 0.0


def _slot_short_reaccel(context, market_state, params, side):
    return 0.0


def _slot_short_flow(context, market_state, params, side):
    return 0.0


def _slot_short_veto(context, market_state, params, side):
    return 0.0


def _slot_short_extra_1(context, market_state, params, side):
    return 0.0


def _slot_short_extra_2(context, market_state, params, side):
    return 0.0


def _build_strategy_context(data, idx, positions, market_state, params):
    return _strategy_entry_context(data, idx, positions, market_state, params, allow_sideways=True)


def _classify_strategy_regime(context, market_state, positions):
    return {
        "sideways": bool(context.get("sideways_regime", False)),
        "has_long_position": _count_positions_by_side(positions, "long") > 0,
        "has_short_position": _count_positions_by_side(positions, "short") > 0,
    }


def _evaluate_factor_slots(context, market_state, params, side):
    slot_scores = {}
    for slot_name in FACTOR_SLOT_NAMES:
        if slot_name.startswith("long_") and side != "long":
            continue
        if slot_name.startswith("short_") and side != "short":
            continue
        slot_scores[slot_name] = _slot_safe_eval(slot_name, context, market_state, params, side)
    return slot_scores


def _build_position_state(data, idx, positions, market_state, context, regime):
    if regime["has_short_position"]:
        _sync_short_exit_signal_profiles(positions, market_state, context["current"]["close"])

    long_divergence_exit_active = regime["has_long_position"] and any(
        _position_side(position) == "long" and _detect_macd_divergence(data, idx, position)
        for position in positions
    )
    short_divergence_exit_active = regime["has_short_position"] and any(
        _position_side(position) == "short" and _detect_macd_divergence(data, idx, position)
        for position in positions
    )
    long_exit_active = regime["has_long_position"] and _active_long_exit_signal(
        positions,
        market_state,
        context["current"],
        context["current"]["close"],
    )
    if long_exit_active and not _long_exit_volume_filter_allows(data, idx):
        long_exit_active = False
    short_exit_active = regime["has_short_position"] and _active_short_exit_signal(
        positions,
        market_state,
        context["current"],
        context["current"]["close"],
    )
    if not short_exit_active and regime["has_short_position"]:
        short_exit_active = _short_hourly_bull_exit_active(positions, market_state)

    return {
        "long_divergence_exit_active": long_divergence_exit_active,
        "short_divergence_exit_active": short_divergence_exit_active,
        "long_exit_active": long_exit_active,
        "short_exit_active": short_exit_active,
    }


def _candidate_from_decision(decision, context, market_state, params, slot_scores):
    if decision is None:
        return None
    side = str(decision.get("entry_side", "")).strip()
    path_key = str(decision.get("entry_path_key", "")).strip()
    try:
        strength = _decision_signal_strength(context, market_state, params, side, entry_path_key=path_key)
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        strength = 0.0
    return {
        "decision": decision,
        "side": side,
        "path_key": path_key,
        "strength": float(strength) + _slot_bundle_score(slot_scores),
    }


def _long_reversal_candidate(context, market_state, positions):
    _record_funnel_pass("long", "final_veto_pass")
    if not _long_entry_addition_available(positions, context["current"]["close"], market_state):
        return None
    return {
        "entry_signal": "long_pullback",
        "entry_side": "long",
        "entry_path_key": "long_reversal_sniper",
        "entry_path_tag": ENTRY_PATH_TAGS.get("long_reversal_sniper", "long_reversal_sniper"),
    }


def _build_long_candidate(context, market_state, params, positions, regime):
    slot_scores = _evaluate_factor_slots(context, market_state, params, "long")
    if not _slot_gate_ok(slot_scores, "long_context"):
        return None
    if not _slot_gate_ok(slot_scores, "long_flow"):
        return None
    if not _slot_gate_ok(slot_scores, "long_veto"):
        return None
    if not _slot_gate_ok(slot_scores, "long_extra_1") or not _slot_gate_ok(slot_scores, "long_extra_2"):
        return None

    _record_funnel_pass("long", "outer_context_pass")
    long_breakout_path = _slot_path_ok(slot_scores, "long_breakout")
    long_pullback_path = _slot_path_ok(slot_scores, "long_pullback")
    merged_long_core_path = _merged_long_core_path_ok(long_breakout_path, long_pullback_path)
    long_breakout_path = merged_long_core_path
    long_pullback_path = merged_long_core_path
    long_reaccel_path = _slot_path_ok(slot_scores, "long_reaccel")
    long_breakout_path, long_pullback_path, has_long_signal_path = _long_paths_with_handoff(
        context,
        market_state,
        params,
        long_breakout_path,
        long_pullback_path,
        long_reaccel_path,
    )
    if _long_reversal_sniper_ok(context) and not regime["sideways"] and merged_long_core_path:
        return _candidate_from_decision(
            _long_reversal_candidate(context, market_state, positions),
            context,
            market_state,
            params,
            slot_scores,
        )

    long_ownership_relay = False if has_long_signal_path else _long_ownership_relay_ready(context, market_state, params)
    decision = _long_entry_result(
        context,
        market_state,
        params,
        positions,
        long_breakout_path,
        long_pullback_path,
        long_reaccel_path,
        long_ownership_relay,
        as_decision=True,
    )
    return _candidate_from_decision(decision, context, market_state, params, slot_scores)


def _structured_short_path_key(context, market_state, params, slot_scores):
    return ""


def _build_short_candidate(context, market_state, params, positions, regime, *, require_impulse_final):
    return None


def _select_entry_candidate(context, market_state, params, long_candidate, short_candidate, *, compare_strength):
    if long_candidate is not None:
        return long_candidate
    return short_candidate


def _format_strategy_output(candidate, as_decision):
    if candidate is None:
        return None
    decision = candidate.get("decision")
    if not isinstance(decision, dict):
        return None
    if as_decision:
        return decision
    return normalize_entry_signal(
        decision.get("entry_signal", ""),
        fallback_side=decision.get("entry_side", ""),
    ) or None


def _strategy_core(data, idx, positions, market_state, *, as_decision):
    params = PARAMS
    context = _build_strategy_context(data, idx, positions, market_state, params)
    if context is None:
        return None

    regime = _classify_strategy_regime(context, market_state, positions)
    position_state = _build_position_state(data, idx, positions, market_state, context, regime)

    _record_funnel_pass("long", "sideways_pass")
    _record_funnel_pass("short", "sideways_pass")

    if position_state["long_divergence_exit_active"] or position_state["short_divergence_exit_active"]:
        return None

    if position_state["long_exit_active"]:
        return None

    long_candidate = _build_long_candidate(context, market_state, params, positions, regime)

    if position_state["short_exit_active"]:
        return None

    short_candidate = None
    return _format_strategy_output(
        _select_entry_candidate(
            context,
            market_state,
            params,
            long_candidate,
            short_candidate,
            compare_strength=as_decision,
        ),
        as_decision,
    )


def strategy_decision(data, idx, positions, market_state):
    return _strategy_core(data, idx, positions, market_state, as_decision=True)


def strategy(data, idx, positions, market_state):
    return _strategy_core(data, idx, positions, market_state, as_decision=False)
