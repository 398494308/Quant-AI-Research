#!/usr/bin/env python3
"""激进版双向趋势策略：Long Breakout/Pullback + Short Breakdown/Bounce-Fail。"""

# PARAMS_START
PARAMS = {'bounce_fail_adx_min': 23.0,
 'bounce_fail_body_min': 0.0011,
 'bounce_fail_distance_max': 0.0135,
 'bounce_fail_hist_max': 22.0,
 'bounce_fail_rsi_max': 49.0,
 'bounce_fail_rsi_min': 30.0,
 'bounce_fail_volume_ratio_min': 0.84,
 'breakdown_adx_min': 17.2,
 'breakdown_body_ratio_min': 0.34,
 'breakdown_buffer_pct': 0.0001,
 'breakdown_close_pos_max': 0.43,
 'breakdown_fourh_adx_min': 23.5,
 'breakdown_hist_max': 34.0,
 'breakdown_hour_dist_fast_max': 0.038,
 'breakdown_hourly_adx_min': 20.0,
 'breakdown_hourly_atr_ratio_max': 0.0091,
 'breakdown_hourly_spread_max': -0.0041,
 'breakdown_lookback': 16,
 'breakdown_rsi_max': 49.0,
 'breakdown_rsi_min': 20.0,
 'breakdown_volume_ratio_min': 0.98,
 'breakout_adx_min': 9.2,
 'breakout_body_ratio_min': 0.15,
 'breakout_buffer_pct': 0.0,
 'breakout_close_pos_min': 0.41,
 'breakout_fourh_adx_min': 11.5,
 'breakout_hist_min': -90.0,
 'breakout_hourly_adx_min': 9.0,
 'breakout_hourly_spread_min': 0.0001,
 'breakout_lookback': 6,
 'breakout_rsi_max': 95.0,
 'breakout_rsi_min': 42.0,
 'breakout_volume_ratio_min': 0.46,
 'fear_greed_breakout_min': 28,
 'fear_greed_delta3_min': -10.0,
 'fear_greed_enabled': 1,
 'fear_greed_extreme_greed_max': 82,
 'fear_greed_pullback_min': 30,
 'fear_greed_short_delta3_max': 8.0,
 'fear_greed_short_extreme_fear_min': 20,
 'fear_greed_short_max': 68,
 'fear_greed_short_min': 16,
 'fourh_adx_min': 6.5,
 'fourh_chop_max': 70.0,
 'fourh_ema_fast': 18,
 'fourh_ema_slow': 55,
 'fourh_ema_slow_slope_min': 2e-05,
 'fourh_trend_spread_min': 0.00015,
 'hourly_adx_min': 7.8,
 'hourly_atr_ratio_min': 0.0015,
 'hourly_chop_max': 67.0,
 'hourly_ema_anchor': 168,
 'hourly_ema_fast': 24,
 'hourly_ema_slow': 96,
 'hourly_ema_slow_slope_min': 2e-05,
 'hourly_macd_hist_min': -125.0,
 'hourly_trend_spread_min': 5e-05,
 'intraday_adx_min': 8.5,
 'intraday_atr_ratio_min': 0.0009,
 'intraday_chop_max': 64.0,
 'intraday_ema_fast': 20,
 'intraday_ema_slow': 55,
 'intraday_rsi_max': 94.0,
 'intraday_rsi_min': 42.0,
 'macd_fast': 12,
 'macd_signal': 9,
 'macd_slow': 26,
 'min_history': 260,
 'pullback_adx_min': 10.8,
 'pullback_bounce_body_min': 0.0002,
 'pullback_distance_max': 0.032,
 'pullback_ema_len': 21,
 'pullback_enabled': 1,
 'pullback_hist_min': -72.0,
 'pullback_reclaim_buffer_pct': 0.0,
 'pullback_rsi_max': 89.0,
 'pullback_rsi_min': 38.0,
 'pullback_volume_ratio_min': 0.32,
 'short_enabled': 1,
 'volume_lookback': 20}
# PARAMS_END


def _avg(data, start, end, key):
    total = 0.0
    count = 0
    for i in range(start, end + 1):
        total += data[i][key]
        count += 1
    return total / count if count else 0.0


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


def _ema(data, end_idx, length, key):
    alpha = 2.0 / (length + 1.0)
    start_idx = max(0, end_idx - length * 3)
    ema = data[start_idx][key]
    for i in range(start_idx + 1, end_idx + 1):
        ema = alpha * data[i][key] + (1.0 - alpha) * ema
    return ema


def _candle_metrics(bar):
    open_price = bar["open"]
    high = bar["high"]
    low = bar["low"]
    close = bar["close"]
    candle_range = max(high - low, close * 1e-9)
    body = close - open_price
    return {
        "body_pct": body / open_price if open_price > 0 else 0.0,
        "close_pos": (close - low) / candle_range,
        "body_ratio": abs(body) / candle_range,
    }


def _sentiment_allows_long(sentiment, threshold, delta_min, extreme_max):
    if sentiment is None:
        return True
    value = sentiment.get("value", 50.0)
    delta3 = sentiment.get("delta3", 0.0)
    ema = sentiment.get("ema7", value)
    return value >= threshold and delta3 >= delta_min and value <= extreme_max and value >= ema - 4.0


def _sentiment_allows_short(sentiment, low_threshold, high_threshold, delta_max):
    if sentiment is None:
        return True
    value = sentiment.get("value", 50.0)
    delta3 = sentiment.get("delta3", 0.0)
    ema = sentiment.get("ema7", value)
    return low_threshold <= value <= high_threshold and delta3 <= delta_max and value <= ema + 4.0


def _position_side(position):
    signal = position.get("entry_signal", "")
    return "short" if signal.startswith("short_") else "long"


def strategy(data, idx, positions, market_state):
    p = PARAMS
    if idx < p["min_history"]:
        return None

    current = data[idx]
    prev = data[idx - 1]
    hourly = market_state["hourly"]
    fourh = market_state["four_hour"]
    sentiment = market_state.get("sentiment") if p["fear_greed_enabled"] else None
    if hourly is None or fourh is None:
        return None

    for bar in (current, prev):
        if bar["open"] <= 0 or bar["close"] <= 0 or bar["volume"] <= 0 or bar["high"] < bar["low"]:
            return None

    current_candle = _candle_metrics(current)
    prev_candle = _candle_metrics(prev)
    avg_volume = max(_avg(data, idx - p["volume_lookback"] + 1, idx, "volume"), 1e-9)
    volume_ratio = current["volume"] / avg_volume
    ema_pullback = _ema(data, idx, p["pullback_ema_len"], "close")
    breakout_high = _window_max(data, idx - p["breakout_lookback"], idx - 1, "high")
    breakdown_low = _window_min(data, idx - p["breakdown_lookback"], idx - 1, "low")

    intraday_bull = (
        current["close"] > market_state["ema_fast"] > market_state["ema_slow"]
        and market_state["adx"] >= p["intraday_adx_min"]
        and market_state["atr_ratio"] >= p["intraday_atr_ratio_min"]
        and market_state["chop"] <= p["intraday_chop_max"]
        and p["intraday_rsi_min"] <= market_state["rsi"] <= p["intraday_rsi_max"]
        and market_state["macd_line"] > market_state["signal_line"]
    )
    hourly_bull = (
        hourly["close"] > hourly["ema_fast"] > hourly["ema_slow"]
        and hourly["close"] > hourly["ema_anchor"]
        and hourly["trend_spread_pct"] >= p["hourly_trend_spread_min"]
        and hourly["ema_slow_slope_pct"] >= p["hourly_ema_slow_slope_min"]
        and hourly["macd_line"] > hourly["signal_line"]
        and hourly["histogram"] >= p["hourly_macd_hist_min"]
        and hourly["adx"] >= p["hourly_adx_min"]
        and hourly["atr_ratio"] >= p["hourly_atr_ratio_min"]
        and hourly["chop"] <= p["hourly_chop_max"]
    )
    fourh_bull = (
        fourh["close"] > fourh["ema_fast"] > fourh["ema_slow"]
        and fourh["trend_spread_pct"] >= p["fourh_trend_spread_min"]
        and fourh["ema_slow_slope_pct"] >= p["fourh_ema_slow_slope_min"]
        and fourh["adx"] >= p["fourh_adx_min"]
        and fourh["chop"] <= p["fourh_chop_max"]
    )

    if intraday_bull and hourly_bull and fourh_bull:
        if p["fear_greed_enabled"] and sentiment is not None and sentiment.get("value", 50.0) < 25:
            pass
        else:
            breakout_ready = (
                _sentiment_allows_long(
                    sentiment,
                    p["fear_greed_breakout_min"],
                    p["fear_greed_delta3_min"],
                    p["fear_greed_extreme_greed_max"],
                )
                and hourly["adx"] >= p["breakout_hourly_adx_min"]
                and fourh["adx"] >= p["breakout_fourh_adx_min"]
                and hourly["trend_spread_pct"] >= p["breakout_hourly_spread_min"]
                and current["close"] >= breakout_high * (1.0 + p["breakout_buffer_pct"])
                and current["close"] > market_state["ema_fast"] > market_state["ema_slow"]
                and current_candle["close_pos"] >= p["breakout_close_pos_min"]
                and current_candle["body_ratio"] >= p["breakout_body_ratio_min"]
                and volume_ratio >= p["breakout_volume_ratio_min"]
                and market_state["adx"] >= p["breakout_adx_min"]
                and p["breakout_rsi_min"] <= market_state["rsi"] <= p["breakout_rsi_max"]
                and market_state["histogram"] >= p["breakout_hist_min"]
            )
            if breakout_ready:
                return "long_breakout"

            if p["pullback_enabled"]:
                pullback_distance = abs(prev["low"] / ema_pullback - 1.0)
                pullback_ready = (
                    _sentiment_allows_long(
                        sentiment,
                        p["fear_greed_pullback_min"],
                        p["fear_greed_delta3_min"],
                        p["fear_greed_extreme_greed_max"],
                    )
                    and market_state["adx"] >= p["pullback_adx_min"]
                    and p["pullback_rsi_min"] <= market_state["rsi"] <= p["pullback_rsi_max"]
                    and market_state["histogram"] >= p["pullback_hist_min"]
                    and prev["low"] <= ema_pullback * (1.0 + p["pullback_reclaim_buffer_pct"])
                    and pullback_distance <= p["pullback_distance_max"]
                    and current["close"] > ema_pullback * (1.0 + p["pullback_reclaim_buffer_pct"])
                    and current["close"] > prev["high"]
                    and current_candle["body_pct"] >= p["pullback_bounce_body_min"]
                    and current_candle["close_pos"] > 0.62
                    and prev_candle["close_pos"] > 0.25
                    and volume_ratio >= p["pullback_volume_ratio_min"]
                )
                if pullback_ready:
                    return "long_pullback"

    if not p["short_enabled"]:
        return None

    intraday_bear = (
        current["close"] < market_state["ema_fast"] < market_state["ema_slow"]
        and market_state["adx"] >= p["intraday_adx_min"]
        and market_state["atr_ratio"] >= p["intraday_atr_ratio_min"]
        and market_state["chop"] <= p["intraday_chop_max"]
        and p["breakdown_rsi_min"] <= market_state["rsi"] <= p["breakdown_rsi_max"]
        and market_state["macd_line"] < market_state["signal_line"]
    )
    hourly_bear = (
        hourly["close"] < hourly["ema_fast"] < hourly["ema_slow"]
        and hourly["close"] < hourly["ema_anchor"]
        and hourly["trend_spread_pct"] <= -p["hourly_trend_spread_min"]
        and hourly["ema_slow_slope_pct"] <= -p["hourly_ema_slow_slope_min"]
        and hourly["macd_line"] < hourly["signal_line"]
        and hourly["histogram"] <= -p["hourly_macd_hist_min"]
        and hourly["adx"] >= p["hourly_adx_min"]
        and hourly["atr_ratio"] >= p["hourly_atr_ratio_min"]
        and hourly["chop"] <= p["hourly_chop_max"]
    )
    fourh_bear_supportive = (
        fourh["close"] < fourh["ema_slow"]
        and fourh["trend_spread_pct"] <= -(p["fourh_trend_spread_min"] * 0.5)
        and fourh["ema_slow_slope_pct"] <= 0.0
        and fourh["adx"] >= max(10.0, p["fourh_adx_min"] - 2.0)
        and fourh["chop"] <= p["fourh_chop_max"] + 4.0
    )
    if not (intraday_bear and hourly_bear and fourh_bear_supportive):
        return None

    breakdown_ready = (
        _sentiment_allows_short(
            sentiment,
            p["fear_greed_short_min"],
            p["fear_greed_short_max"],
            p["fear_greed_short_delta3_max"],
        )
        and (sentiment is None or sentiment.get("value", 50.0) >= p["fear_greed_short_extreme_fear_min"])
        and hourly["adx"] >= p["breakdown_hourly_adx_min"]
        and fourh["adx"] >= p["breakdown_fourh_adx_min"]
        and hourly["atr_ratio"] <= p["breakdown_hourly_atr_ratio_max"]
        and (hourly["ema_fast"] - current["close"]) / current["close"] <= p["breakdown_hour_dist_fast_max"]
        and hourly["trend_spread_pct"] <= p["breakdown_hourly_spread_max"]
        and current["close"] <= breakdown_low * (1.0 - p["breakdown_buffer_pct"])
        and current["close"] < market_state["ema_fast"] < market_state["ema_slow"]
        and current_candle["close_pos"] <= p["breakdown_close_pos_max"]
        and current_candle["body_ratio"] >= p["breakdown_body_ratio_min"]
        and volume_ratio >= p["breakdown_volume_ratio_min"]
        and market_state["adx"] >= p["breakdown_adx_min"]
        and p["breakdown_rsi_min"] <= market_state["rsi"] <= p["breakdown_rsi_max"]
        and market_state["histogram"] <= p["breakdown_hist_max"]
    )
    if breakdown_ready:
        return "short_breakdown"

    bounce_distance = abs(prev["high"] / ema_pullback - 1.0)
    bounce_fail_ready = (
        _sentiment_allows_short(
            sentiment,
            p["fear_greed_short_min"],
            p["fear_greed_short_max"],
            p["fear_greed_short_delta3_max"],
        )
        and market_state["adx"] >= p["bounce_fail_adx_min"]
        and p["bounce_fail_rsi_min"] <= market_state["rsi"] <= p["bounce_fail_rsi_max"]
        and market_state["histogram"] <= p["bounce_fail_hist_max"]
        and prev["high"] >= ema_pullback * (1.0 - p["pullback_reclaim_buffer_pct"])
        and bounce_distance <= p["bounce_fail_distance_max"]
        and current["close"] < ema_pullback * (1.0 - p["pullback_reclaim_buffer_pct"])
        and current["close"] < prev["low"]
        and current_candle["body_pct"] <= -p["bounce_fail_body_min"]
        and current_candle["close_pos"] < 0.38
        and prev_candle["close_pos"] < 0.75
        and volume_ratio >= p["bounce_fail_volume_ratio_min"]
    )
    if bounce_fail_ready:
        return "short_bounce_fail"

    return None
