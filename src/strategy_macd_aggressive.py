#!/usr/bin/env python3
"""极致激进策略：严入场 + 慢止盈 + 慢止损 + 高杠杆。"""

# PARAMS_START
PARAMS = {'breakdown_adx_min': 21.5,
 'breakdown_body_ratio_min': 0.39,
 'breakdown_buffer_pct': 0.0002,
 'breakdown_close_pos_max': 0.36,
 'breakdown_hist_max': 16.0,
 'breakdown_lookback': 26,
 'breakdown_rsi_max': 42.0,
 'breakdown_rsi_min': 21.0,
 'breakdown_volume_ratio_min': 1.08,
 'breakout_adx_min': 12.6,
 'breakout_body_ratio_min': 0.22,
 'breakout_buffer_pct': 0.0,
 'breakout_close_pos_min': 0.48,
 'breakout_hist_min': -95.0,
 'breakout_lookback': 21,
 'breakout_rsi_max': 92.0,
 'breakout_rsi_min': 44.0,
 'breakout_volume_ratio_min': 0.84,
 'fourh_adx_min': 10.8,
 'fourh_ema_fast': 10,
 'fourh_ema_slow': 34,
 'hourly_adx_min': 12.8,
 'hourly_ema_anchor': 85,
 'hourly_ema_fast': 12,
 'hourly_ema_slow': 50,
 'intraday_adx_min': 12.5,
 'intraday_ema_fast': 9,
 'intraday_ema_slow': 28,
 'macd_fast': 5,
 'macd_signal': 3,
 'macd_slow': 16,
 'min_history': 260,
 'volume_lookback': 9}
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
    if hourly is None or fourh is None:
        return None

    for bar in (current, prev):
        if bar["open"] <= 0 or bar["close"] <= 0 or bar["volume"] <= 0 or bar["high"] < bar["low"]:
            return None

    current_candle = _candle_metrics(current)
    avg_volume = max(_avg(data, idx - p["volume_lookback"] + 1, idx, "volume"), 1e-9)
    volume_ratio = current["volume"] / avg_volume
    breakout_high = _window_max(data, idx - p["breakout_lookback"], idx - 1, "high")
    breakdown_low = _window_min(data, idx - p["breakdown_lookback"], idx - 1, "low")

    # 做多：三周期共振 + Breakout
    intraday_bull = (
        current["close"] > market_state["ema_fast"] > market_state["ema_slow"]
        and market_state["adx"] >= p["intraday_adx_min"]
        and market_state["macd_line"] > market_state["signal_line"]
    )
    hourly_bull = (
        hourly["close"] > hourly["ema_fast"] > hourly["ema_slow"]
        and hourly["close"] > hourly["ema_anchor"]
        and hourly["macd_line"] > hourly["signal_line"]
        and hourly["adx"] >= p["hourly_adx_min"]
    )
    fourh_bull = (
        fourh["close"] > fourh["ema_fast"] > fourh["ema_slow"]
        and fourh["adx"] >= p["fourh_adx_min"]
    )

    if intraday_bull and hourly_bull and fourh_bull:
        breakout_ready = (
            current["close"] >= breakout_high * (1.0 + p["breakout_buffer_pct"])
            and current_candle["close_pos"] >= p["breakout_close_pos_min"]
            and current_candle["body_ratio"] >= p["breakout_body_ratio_min"]
            and volume_ratio >= p["breakout_volume_ratio_min"]
            and market_state["adx"] >= p["breakout_adx_min"]
            and p["breakout_rsi_min"] <= market_state["rsi"] <= p["breakout_rsi_max"]
            and market_state["histogram"] >= p["breakout_hist_min"]
        )
        if breakout_ready:
            return "long_breakout"

    # 做空：三周期共振 + Breakdown
    intraday_bear = (
        current["close"] < market_state["ema_fast"] < market_state["ema_slow"]
        and market_state["adx"] >= p["intraday_adx_min"]
        and market_state["macd_line"] < market_state["signal_line"]
    )
    hourly_bear = (
        hourly["close"] < hourly["ema_fast"] < hourly["ema_slow"]
        and hourly["close"] < hourly["ema_anchor"]
        and hourly["macd_line"] < hourly["signal_line"]
        and hourly["adx"] >= p["hourly_adx_min"]
    )
    fourh_bear = (
        fourh["close"] < fourh["ema_slow"]
        and fourh["adx"] >= p["fourh_adx_min"]
    )

    if intraday_bear and hourly_bear and fourh_bear:
        breakdown_ready = (
            current["close"] <= breakdown_low * (1.0 - p["breakdown_buffer_pct"])
            and current_candle["close_pos"] <= p["breakdown_close_pos_max"]
            and current_candle["body_ratio"] >= p["breakdown_body_ratio_min"]
            and volume_ratio >= p["breakdown_volume_ratio_min"]
            and market_state["adx"] >= p["breakdown_adx_min"]
            and p["breakdown_rsi_min"] <= market_state["rsi"] <= p["breakdown_rsi_max"]
            and market_state["histogram"] <= p["breakdown_hist_max"]
        )
        if breakdown_ready:
            return "short_breakdown"

    return None
