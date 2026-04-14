#!/usr/bin/env python3
'''极致激进策略：严入场 + 慢止盈 + 慢止损 + 高杠杆。'''

SIDEWAYS_INTRADAY_CHOP_MIN = 60.0
SIDEWAYS_HOURLY_CHOP_MIN = 58.0
SIDEWAYS_HARD_INTRADAY_CHOP_MIN = 62.0
SIDEWAYS_HARD_HOURLY_CHOP_MIN = 60.0
SIDEWAYS_MIN_ATR_RATIO = 0.0020
SIDEWAYS_MIN_HOURLY_SPREAD_PCT = 0.0016
SIDEWAYS_MIN_FOURH_SPREAD_PCT = 0.0020
SIDEWAYS_MAX_HOURLY_ADX = 18.0
SIDEWAYS_MAX_FOURH_ADX = 16.0

# PARAMS_START
PARAMS = {'breakdown_adx_min': 25.6,
 'breakdown_body_ratio_min': 0.39,
 'breakdown_buffer_pct': 0.0002,
 'breakdown_close_pos_max': 0.36,
 'breakdown_hist_max': 16.0,
 'breakdown_lookback': 22,
 'breakdown_rsi_max': 42.0,
 'breakdown_rsi_min': 21.0,
 'breakdown_volume_ratio_min': 1.08,
 'breakout_adx_min': 18.3,
 'breakout_body_ratio_min': 0.22,
 'breakout_buffer_pct': 0.0,
 'breakout_close_pos_min': 0.48,
 'breakout_hist_min': -95.0,
 'breakout_lookback': 20,
 'breakout_rsi_max': 81.6,
 'breakout_rsi_min': 44.0,
 'breakout_volume_ratio_min': 1.12,
 'fourh_adx_min': 12.5,
 'fourh_ema_fast': 10,
 'fourh_ema_slow': 34,
 'hourly_adx_min': 19.0,
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
    open_price = bar['open']
    high = bar['high']
    low = bar['low']
    close = bar['close']
    candle_range = max(high - low, close * 1e-9)
    body = close - open_price
    return {
        'body_pct': body / open_price if open_price > 0 else 0.0,
        'close_pos': (close - low) / candle_range,
        'body_ratio': abs(body) / candle_range,
    }


def _position_side(position):
    signal = position.get('entry_signal', '')
    return 'short' if signal.startswith('short_') else 'long'


def _intraday_trend_metrics(market_state):
    ema_fast = market_state['ema_fast']
    ema_slow = market_state['ema_slow']
    prev_ema_slow = market_state['prev_ema_slow']
    trend_base = max(abs(ema_slow), 1e-9)
    return {
        'spread_pct': (ema_fast - ema_slow) / trend_base,
        'slope_pct': (ema_slow - prev_ema_slow) / trend_base,
    }


def _is_sideways_regime(market_state):
    hourly = market_state['hourly']
    fourh = market_state['four_hour']
    intraday = _intraday_trend_metrics(market_state)
    intraday_chop = market_state['chop']
    hourly_chop = hourly['chop']
    atr_ratio = market_state['atr_ratio']
    intraday_spread = abs(intraday['spread_pct'])
    hourly_spread = abs(hourly['trend_spread_pct'])
    fourh_spread = abs(fourh['trend_spread_pct'])
    hourly_slope = abs(hourly['ema_slow_slope_pct'])
    fourh_slope = abs(fourh['ema_slow_slope_pct'])
    adx_soft = hourly['adx'] <= SIDEWAYS_MAX_HOURLY_ADX and fourh['adx'] <= SIDEWAYS_MAX_FOURH_ADX

    hard_sideways = (
        (
            intraday_chop >= SIDEWAYS_HARD_INTRADAY_CHOP_MIN
            and hourly_chop >= SIDEWAYS_HARD_HOURLY_CHOP_MIN
            and adx_soft
        )
        or (
            atr_ratio < SIDEWAYS_MIN_ATR_RATIO * 1.10
            and hourly_spread < SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.15
            and fourh_spread < SIDEWAYS_MIN_FOURH_SPREAD_PCT * 1.15
        )
        or (
            hourly_spread < SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 0.92
            and fourh_spread < SIDEWAYS_MIN_FOURH_SPREAD_PCT * 0.92
            and hourly_slope < atr_ratio * 0.06
            and fourh_slope < atr_ratio * 0.03
        )
    )
    if hard_sideways:
        return True

    mixed_trend = (
        hourly['trend_spread_pct'] * fourh['trend_spread_pct'] <= 0.0
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
    if weak_trend and (intraday_chop >= SIDEWAYS_INTRADAY_CHOP_MIN - 1.0 or adx_soft):
        return True

    bull_front_run = (
        hourly['trend_spread_pct'] > 0.0
        and fourh['trend_spread_pct'] > 0.0
        and intraday['spread_pct'] > max(hourly_spread * 1.85, atr_ratio * 1.00)
        and hourly_spread < max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.55, atr_ratio * 0.95)
        and fourh_spread < max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 1.20, atr_ratio * 1.02)
        and hourly_slope < atr_ratio * 0.10
        and fourh_slope < atr_ratio * 0.05
        and (hourly_chop >= SIDEWAYS_HOURLY_CHOP_MIN - 2.0 or adx_soft)
    )
    if bull_front_run:
        return True

    signals = 0
    if intraday_chop >= SIDEWAYS_INTRADAY_CHOP_MIN and hourly_chop >= SIDEWAYS_HOURLY_CHOP_MIN:
        signals += 1
    if atr_ratio < SIDEWAYS_MIN_ATR_RATIO and hourly_chop >= SIDEWAYS_HOURLY_CHOP_MIN - 1.0:
        signals += 1
    if hourly_spread < SIDEWAYS_MIN_HOURLY_SPREAD_PCT and fourh_spread < SIDEWAYS_MIN_FOURH_SPREAD_PCT:
        signals += 1
    if intraday_spread < atr_ratio * 0.28 and hourly_slope < atr_ratio * 0.08 and fourh_slope < atr_ratio * 0.04:
        signals += 1
    if adx_soft:
        signals += 1
    return signals >= 3


def _trend_quality_ok(market_state, side):
    hourly = market_state['hourly']
    fourh = market_state['four_hour']
    intraday = _intraday_trend_metrics(market_state)
    atr_ratio = market_state['atr_ratio']
    direction = -1.0 if side == 'short' else 1.0

    intraday_spread = direction * intraday['spread_pct']
    hourly_spread = direction * hourly['trend_spread_pct']
    fourh_spread = direction * fourh['trend_spread_pct']
    hourly_slope = direction * hourly['ema_slow_slope_pct']
    fourh_slope = direction * fourh['ema_slow_slope_pct']

    confirms = 0
    if market_state['adx'] >= 14.0 and hourly['adx'] >= 18.0:
        confirms += 1
    if intraday_spread >= atr_ratio * 0.30:
        confirms += 1
    if hourly_spread >= max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.20, atr_ratio * 0.75):
        confirms += 1
    if fourh_spread >= max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 1.05, atr_ratio * 0.95):
        confirms += 1
    if hourly_slope >= atr_ratio * 0.07 and fourh_slope >= atr_ratio * 0.035:
        confirms += 1

    if side == 'long':
        return confirms >= 3

    if confirms < 3:
        return False

    short_fourh_participation_ok = (
        fourh_spread >= max(hourly_spread * 0.66, atr_ratio * 0.94)
        and fourh_slope >= atr_ratio * 0.040
    )
    if short_fourh_participation_ok:
        return True

    short_acceleration_exception = (
        intraday_spread >= atr_ratio * 0.42
        and hourly_spread >= max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.82, atr_ratio * 1.08)
        and fourh_spread >= max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 1.04, atr_ratio * 0.90)
        and hourly_slope >= atr_ratio * 0.098
        and fourh_slope >= atr_ratio * 0.036
        and market_state['adx'] >= 16.0
        and hourly['adx'] >= 22.0
    )
    return short_acceleration_exception


def _trend_followthrough_ok(market_state, side, trigger_price, current_close):
    hourly = market_state['hourly']
    fourh = market_state['four_hour']
    intraday = _intraday_trend_metrics(market_state)
    atr_ratio = market_state['atr_ratio']
    direction = -1.0 if side == 'short' else 1.0
    breakout_distance_pct = abs(current_close - trigger_price) / max(trigger_price, 1e-9)

    confirms = 0
    if direction * intraday['spread_pct'] >= atr_ratio * 0.30:
        confirms += 1
    if direction * hourly['trend_spread_pct'] >= max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.35, atr_ratio * 0.85):
        confirms += 1
    if direction * fourh['trend_spread_pct'] >= max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 1.10, atr_ratio * 1.05):
        confirms += 1
    if (
        direction * hourly['ema_slow_slope_pct'] >= atr_ratio * 0.08
        and direction * fourh['ema_slow_slope_pct'] >= atr_ratio * 0.04
    ):
        confirms += 1
    if breakout_distance_pct >= atr_ratio * 0.35:
        confirms += 1

    if side == 'long':
        hourly_fast_extension = (current_close - hourly['ema_fast']) / max(current_close, 1e-9)
        hourly_anchor_extension = (current_close - hourly['ema_anchor']) / max(current_close, 1e-9)
        if (
            hourly_fast_extension <= max(atr_ratio * 1.45, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 3.2)
            and hourly_anchor_extension <= max(atr_ratio * 2.20, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 5.0)
        ):
            confirms += 1
        else:
            long_continuation_exception = (
                direction * hourly['trend_spread_pct'] >= max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.72, atr_ratio * 1.05)
                and direction * fourh['trend_spread_pct'] >= max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 1.26, atr_ratio * 1.18)
                and direction * hourly['ema_slow_slope_pct'] >= atr_ratio * 0.10
                and direction * fourh['ema_slow_slope_pct'] >= atr_ratio * 0.05
                and breakout_distance_pct >= atr_ratio * 0.42
            )
            if long_continuation_exception:
                confirms += 1

        long_late_drift = (
            breakout_distance_pct >= atr_ratio * 0.34
            and hourly_fast_extension >= max(atr_ratio * 1.25, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 2.8)
            and hourly_anchor_extension >= max(atr_ratio * 2.00, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 4.7)
            and direction * hourly['ema_slow_slope_pct'] < atr_ratio * 0.095
            and direction * fourh['ema_slow_slope_pct'] < atr_ratio * 0.047
        )
        if long_late_drift:
            long_continuation_exception = (
                direction * hourly['trend_spread_pct'] >= max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.85, atr_ratio * 1.08)
                and direction * fourh['trend_spread_pct'] >= max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 1.30, atr_ratio * 1.20)
                and direction * hourly['ema_slow_slope_pct'] >= atr_ratio * 0.105
                and direction * fourh['ema_slow_slope_pct'] >= atr_ratio * 0.052
                and breakout_distance_pct >= atr_ratio * 0.46
            )
            if not long_continuation_exception:
                return False

        long_chase_risk = (
            breakout_distance_pct >= atr_ratio * 0.24
            and hourly_fast_extension >= max(atr_ratio * 1.08, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 2.45)
            and hourly_anchor_extension >= max(atr_ratio * 1.72, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 4.05)
            and (
                direction * hourly['trend_spread_pct'] < max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.62, atr_ratio * 0.98)
                or direction * fourh['trend_spread_pct'] < max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 1.18, atr_ratio * 1.10)
                or direction * hourly['ema_slow_slope_pct'] < atr_ratio * 0.092
                or direction * fourh['ema_slow_slope_pct'] < atr_ratio * 0.046
            )
        )
        if long_chase_risk:
            long_reacceleration_exception = (
                direction * hourly['trend_spread_pct'] >= max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.92, atr_ratio * 1.10)
                and direction * fourh['trend_spread_pct'] >= max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 1.34, atr_ratio * 1.22)
                and direction * hourly['ema_slow_slope_pct'] >= atr_ratio * 0.108
                and direction * fourh['ema_slow_slope_pct'] >= atr_ratio * 0.054
                and breakout_distance_pct >= atr_ratio * 0.32
            )
            if not long_reacceleration_exception:
                return False
        return confirms >= 4

    hourly_fast_discount = (hourly['ema_fast'] - current_close) / max(current_close, 1e-9)
    hourly_anchor_discount = (hourly['ema_anchor'] - current_close) / max(current_close, 1e-9)
    short_fourh_participation_gap = (
        breakout_distance_pct >= atr_ratio * 0.22
        and direction * intraday['spread_pct'] >= atr_ratio * 0.34
        and direction * hourly['trend_spread_pct'] >= max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.55, atr_ratio * 0.98)
        and (
            direction * fourh['trend_spread_pct'] < max(direction * hourly['trend_spread_pct'] * 0.62, atr_ratio * 0.96)
            or direction * fourh['ema_slow_slope_pct'] < atr_ratio * 0.039
            or fourh['adx'] < 15.0
        )
        and hourly_fast_discount >= max(atr_ratio * 0.92, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 2.15)
        and hourly_anchor_discount >= max(atr_ratio * 1.48, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 3.55)
    )
    if short_fourh_participation_gap:
        short_broad_acceleration_exception = (
            direction * hourly['trend_spread_pct'] >= max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.95, atr_ratio * 1.12)
            and direction * fourh['trend_spread_pct'] >= max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 1.26, atr_ratio * 1.14)
            and direction * hourly['ema_slow_slope_pct'] >= atr_ratio * 0.106
            and direction * fourh['ema_slow_slope_pct'] >= atr_ratio * 0.048
            and breakout_distance_pct >= atr_ratio * 0.34
            and fourh['adx'] >= 17.0
            and hourly['adx'] >= 23.0
        )
        if not short_broad_acceleration_exception:
            return False

    short_late_drift = (
        breakout_distance_pct >= atr_ratio * 0.32
        and hourly_fast_discount >= max(atr_ratio * 1.20, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 2.7)
        and hourly_anchor_discount >= max(atr_ratio * 1.90, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 4.4)
        and direction * hourly['ema_slow_slope_pct'] < atr_ratio * 0.095
        and direction * fourh['ema_slow_slope_pct'] < atr_ratio * 0.047
    )
    if short_late_drift:
        short_continuation_exception = (
            direction * hourly['trend_spread_pct'] >= max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.75, atr_ratio * 1.05)
            and direction * fourh['trend_spread_pct'] >= max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 1.28, atr_ratio * 1.18)
            and direction * hourly['ema_slow_slope_pct'] >= atr_ratio * 0.10
            and direction * fourh['ema_slow_slope_pct'] >= atr_ratio * 0.05
            and breakout_distance_pct >= atr_ratio * 0.42
        )
        if not short_continuation_exception:
            return False

    short_chase_risk = (
        breakout_distance_pct >= atr_ratio * 0.24
        and hourly_fast_discount >= max(atr_ratio * 1.05, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 2.35)
        and hourly_anchor_discount >= max(atr_ratio * 1.68, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 3.95)
        and (
            direction * hourly['trend_spread_pct'] < max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.60, atr_ratio * 0.96)
            or direction * fourh['trend_spread_pct'] < max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 1.16, atr_ratio * 1.08)
            or direction * hourly['ema_slow_slope_pct'] < atr_ratio * 0.092
            or direction * fourh['ema_slow_slope_pct'] < atr_ratio * 0.046
        )
    )
    if short_chase_risk:
        short_reacceleration_exception = (
            direction * hourly['trend_spread_pct'] >= max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.88, atr_ratio * 1.08)
            and direction * fourh['trend_spread_pct'] >= max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 1.32, atr_ratio * 1.20)
            and direction * hourly['ema_slow_slope_pct'] >= atr_ratio * 0.106
            and direction * fourh['ema_slow_slope_pct'] >= atr_ratio * 0.053
            and breakout_distance_pct >= atr_ratio * 0.30
        )
        if not short_reacceleration_exception:
            return False

    short_extended_move = (
        breakout_distance_pct >= atr_ratio * 0.20
        and hourly_fast_discount >= max(atr_ratio * 0.98, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 2.22)
        and hourly_anchor_discount >= max(atr_ratio * 1.58, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 3.72)
    )
    required_confirms = 4 if short_extended_move else 3
    return confirms >= required_confirms


def strategy(data, idx, positions, market_state):
    p = PARAMS
    if idx < p['min_history']:
        return None

    current = data[idx]
    prev = data[idx - 1]
    hourly = market_state['hourly']
    fourh = market_state['four_hour']
    if hourly is None or fourh is None:
        return None

    for bar in (current, prev):
        if bar['open'] <= 0 or bar['close'] <= 0 or bar['volume'] <= 0 or bar['high'] < bar['low']:
            return None

    if _is_sideways_regime(market_state):
        return None

    intraday = _intraday_trend_metrics(market_state)
    current_candle = _candle_metrics(current)
    prev_candle = _candle_metrics(prev)
    avg_volume = max(_avg(data, idx - p['volume_lookback'] + 1, idx, 'volume'), 1e-9)
    volume_ratio = current['volume'] / avg_volume
    prev_volume = max(prev['volume'], 1e-9)
    breakout_high = _window_max(data, idx - p['breakout_lookback'], idx - 1, 'high')
    breakdown_low = _window_min(data, idx - p['breakdown_lookback'], idx - 1, 'low')
    atr_ratio = market_state['atr_ratio']
    breakout_distance_pct = (current['close'] - breakout_high) / max(breakout_high, 1e-9)
    breakdown_distance_pct = (breakdown_low - current['close']) / max(breakdown_low, 1e-9)
    breakdown_low_penetration_pct = (breakdown_low - current['low']) / max(breakdown_low, 1e-9)
    hourly_fast_extension_pct = (current['close'] - hourly['ema_fast']) / max(current['close'], 1e-9)
    hourly_anchor_extension_pct = (current['close'] - hourly['ema_anchor']) / max(current['close'], 1e-9)
    hourly_fast_discount_pct = (hourly['ema_fast'] - current['close']) / max(current['close'], 1e-9)
    hourly_anchor_discount_pct = (hourly['ema_anchor'] - current['close']) / max(current['close'], 1e-9)

    # 做多：三周期共振 + Breakout
    intraday_bull = (
        current['close'] > market_state['ema_fast'] > market_state['ema_slow']
        and market_state['adx'] >= p['intraday_adx_min']
        and market_state['macd_line'] > market_state['signal_line']
    )
    hourly_bull = (
        hourly['close'] > hourly['ema_fast'] > hourly['ema_slow']
        and hourly['close'] > hourly['ema_anchor']
        and hourly['macd_line'] > hourly['signal_line']
        and hourly['adx'] >= p['hourly_adx_min']
    )
    fourh_bull = (
        fourh['close'] > fourh['ema_fast'] > fourh['ema_slow']
        and fourh['adx'] >= p['fourh_adx_min']
    )

    if intraday_bull and hourly_bull and fourh_bull and _trend_quality_ok(market_state, 'long'):
        long_trend_expansion_ok = (
            hourly['trend_spread_pct'] >= max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.45, atr_ratio * 0.95)
            and fourh['trend_spread_pct'] >= max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 1.20, atr_ratio * 1.10)
            and hourly['ema_slow_slope_pct'] >= atr_ratio * 0.09
            and fourh['ema_slow_slope_pct'] >= atr_ratio * 0.045
        )
        long_higher_tf_participation_ok = (
            hourly['trend_spread_pct'] >= intraday['spread_pct'] * 0.42
            and fourh['trend_spread_pct'] >= hourly['trend_spread_pct'] * 0.68
        )
        long_absorption_exception = (
            hourly['trend_spread_pct'] >= max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.80, atr_ratio * 1.10)
            and fourh['trend_spread_pct'] >= max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 1.30, atr_ratio * 1.20)
            and hourly['ema_slow_slope_pct'] >= atr_ratio * 0.10
            and fourh['ema_slow_slope_pct'] >= atr_ratio * 0.05
            and hourly['trend_spread_pct'] >= intraday['spread_pct'] * 0.46
            and fourh['trend_spread_pct'] >= hourly['trend_spread_pct'] * 0.72
            and volume_ratio >= max(p['breakout_volume_ratio_min'], 1.28)
            and market_state['adx'] >= max(p['breakout_adx_min'], p['intraday_adx_min'] + 2.0)
        )
        long_late_breakout_exhaustion = (
            breakout_distance_pct >= atr_ratio * 0.30
            and hourly_fast_extension_pct >= max(atr_ratio * 1.30, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 2.9)
            and hourly_anchor_extension_pct >= max(atr_ratio * 2.00, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 4.8)
            and hourly['ema_slow_slope_pct'] < atr_ratio * 0.095
            and fourh['ema_slow_slope_pct'] < atr_ratio * 0.047
            and volume_ratio < max(p['breakout_volume_ratio_min'] + 0.12, 1.30)
        )
        long_structure_extension_ok = (
            (
                not (
                    breakout_distance_pct >= atr_ratio * 0.45
                    and hourly_fast_extension_pct >= max(atr_ratio * 1.55, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 3.4)
                    and hourly_anchor_extension_pct >= max(atr_ratio * 2.35, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 5.4)
                )
                and not long_late_breakout_exhaustion
            )
            or long_absorption_exception
        )
        long_chase_breakout = (
            breakout_distance_pct >= atr_ratio * 0.22
            and hourly_fast_extension_pct >= max(atr_ratio * 1.02, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 2.35)
            and hourly_anchor_extension_pct >= max(atr_ratio * 1.66, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 3.95)
        )
        long_reacceleration_ok = (
            current_candle['close_pos'] >= max(p['breakout_close_pos_min'] + 0.10, 0.72)
            and current_candle['body_ratio'] >= max(p['breakout_body_ratio_min'] + 0.08, 0.38)
            and current_candle['body_ratio'] >= max(prev_candle['body_ratio'] * 0.92, 0.30)
            and volume_ratio >= max(p['breakout_volume_ratio_min'] + 0.10, 1.24)
            and current['close'] > prev['close']
            and current['volume'] >= prev_volume * 0.92
        )
        breakout_ready = (
            current['close'] >= breakout_high * (1.0 + p['breakout_buffer_pct'])
            and breakout_distance_pct >= atr_ratio * 0.15
            and current['close'] > prev['high']
            and current_candle['close_pos'] >= max(p['breakout_close_pos_min'], 0.62)
            and current_candle['body_ratio'] >= max(p['breakout_body_ratio_min'], 0.30)
            and volume_ratio >= max(p['breakout_volume_ratio_min'], 1.18)
            and market_state['adx'] >= max(p['breakout_adx_min'], p['intraday_adx_min'] + 1.5)
            and p['breakout_rsi_min'] <= market_state['rsi'] <= min(p['breakout_rsi_max'], 72.0)
            and market_state['histogram'] >= max(p['breakout_hist_min'], 0.0)
        )
        if (
            long_trend_expansion_ok
            and long_higher_tf_participation_ok
            and long_structure_extension_ok
            and (not long_chase_breakout or long_reacceleration_ok or long_absorption_exception)
            and breakout_ready
            and _trend_followthrough_ok(market_state, 'long', breakout_high, current['close'])
        ):
            return 'long_breakout'

    # 做空：三周期共振 + Breakdown
    intraday_bear = (
        current['close'] < market_state['ema_fast'] < market_state['ema_slow']
        and market_state['adx'] >= p['intraday_adx_min']
        and market_state['macd_line'] < market_state['signal_line']
    )
    hourly_bear = (
        hourly['close'] < hourly['ema_fast'] < hourly['ema_slow']
        and hourly['close'] < hourly['ema_anchor']
        and hourly['macd_line'] < hourly['signal_line']
        and hourly['adx'] >= p['hourly_adx_min']
    )
    fourh_bear = (
        fourh['close'] < fourh['ema_slow']
        and fourh['adx'] >= p['fourh_adx_min']
    )
    fourh_bear_confirmed = (
        fourh['close'] < fourh['ema_fast'] < fourh['ema_slow']
        and fourh['macd_line'] < fourh['signal_line']
    )

    if intraday_bear and hourly_bear and fourh_bear and _trend_quality_ok(market_state, 'short'):
        short_trend_expansion_ok = (
            hourly['trend_spread_pct'] <= -max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.28, atr_ratio * 0.82)
            and fourh['trend_spread_pct'] <= -max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 1.08, atr_ratio * 1.00)
            and hourly['ema_slow_slope_pct'] <= -atr_ratio * 0.075
            and fourh['ema_slow_slope_pct'] <= -atr_ratio * 0.038
        )
        intraday_bear_spread = max(-intraday['spread_pct'], 0.0)
        hourly_bear_spread = max(-hourly['trend_spread_pct'], 0.0)
        fourh_bear_spread = max(-fourh['trend_spread_pct'], 0.0)
        short_higher_tf_participation_ok = (
            hourly_bear_spread >= max(intraday_bear_spread * 0.42, atr_ratio * 0.72)
            and fourh_bear_spread >= max(hourly_bear_spread * 0.64, atr_ratio * 0.92)
        )
        short_participation_exception = (
            hourly_bear_spread >= max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.70, atr_ratio * 1.00)
            and fourh_bear_spread >= max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 1.30, atr_ratio * 1.16)
            and hourly['ema_slow_slope_pct'] <= -atr_ratio * 0.095
            and fourh['ema_slow_slope_pct'] <= -atr_ratio * 0.048
            and volume_ratio >= max(p['breakdown_volume_ratio_min'], 1.24)
            and market_state['adx'] >= max(p['breakdown_adx_min'], p['intraday_adx_min'] + 2.0)
        )
        short_fourh_structure_ok = (
            fourh_bear_confirmed
            or (
                fourh_bear_spread >= max(hourly_bear_spread * 0.74, atr_ratio * 1.02)
                and fourh['ema_slow_slope_pct'] <= -atr_ratio * 0.044
                and volume_ratio >= max(p['breakdown_volume_ratio_min'], 1.14)
                and breakdown_distance_pct >= atr_ratio * 0.20
            )
            or short_participation_exception
        )
        short_absorption_exception = (
            hourly['trend_spread_pct'] <= -max(SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.72, atr_ratio * 1.02)
            and fourh['trend_spread_pct'] <= -max(SIDEWAYS_MIN_FOURH_SPREAD_PCT * 1.24, atr_ratio * 1.15)
            and hourly['ema_slow_slope_pct'] <= -atr_ratio * 0.098
            and fourh['ema_slow_slope_pct'] <= -atr_ratio * 0.049
            and volume_ratio >= max(p['breakdown_volume_ratio_min'], 1.22)
            and market_state['adx'] >= max(p['breakdown_adx_min'], p['intraday_adx_min'] + 2.5)
        )
        short_structure_extension_ok = (
            not (
                breakdown_distance_pct >= atr_ratio * 0.32
                and hourly_fast_discount_pct >= max(atr_ratio * 1.18, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 2.7)
                and hourly_anchor_discount_pct >= max(atr_ratio * 1.88, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 4.4)
                and hourly['ema_slow_slope_pct'] > -atr_ratio * 0.082
                and fourh['ema_slow_slope_pct'] > -atr_ratio * 0.041
            )
            or short_absorption_exception
        )
        short_chase_breakdown = (
            breakdown_distance_pct >= atr_ratio * 0.22
            and hourly_fast_discount_pct >= max(atr_ratio * 1.00, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 2.28)
            and hourly_anchor_discount_pct >= max(atr_ratio * 1.62, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 3.88)
        )
        short_deep_discount = (
            breakdown_distance_pct >= atr_ratio * 0.18
            and hourly_fast_discount_pct >= max(atr_ratio * 0.92, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 2.10)
            and hourly_anchor_discount_pct >= max(atr_ratio * 1.48, SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 3.60)
        )
        short_discounted_reacceleration_ok = (
            current_candle['close_pos'] <= min(p['breakdown_close_pos_max'] - 0.06, 0.28)
            and current_candle['body_ratio'] >= max(p['breakdown_body_ratio_min'] + 0.08, 0.47)
            and current_candle['body_ratio'] >= max(prev_candle['body_ratio'] * 0.96, 0.36)
            and volume_ratio >= max(p['breakdown_volume_ratio_min'] + 0.12, 1.22)
            and current['close'] < prev['low']
            and current['volume'] >= prev_volume * 0.96
            and fourh_bear_spread >= max(hourly_bear_spread * 0.72, atr_ratio * 0.98)
            and fourh['ema_slow_slope_pct'] <= -atr_ratio * 0.043
        )
        short_reacceleration_ok = (
            current_candle['close_pos'] <= min(p['breakdown_close_pos_max'] - 0.08, 0.24)
            and current_candle['body_ratio'] >= max(p['breakdown_body_ratio_min'] + 0.06, 0.46)
            and current_candle['body_ratio'] >= max(prev_candle['body_ratio'] * 0.90, 0.34)
            and volume_ratio >= max(p['breakdown_volume_ratio_min'] + 0.10, 1.20)
            and current['close'] < prev['close']
            and current['volume'] >= prev_volume * 0.92
        )
        short_marginal_breakdown = (
            breakdown_distance_pct < atr_ratio * 0.14
            or breakdown_low_penetration_pct < atr_ratio * 0.18
        )
        short_extra_confirmation_needed = (
            short_marginal_breakdown
            or short_deep_discount
            or not fourh_bear_confirmed
        )
        short_penetration_confirmation_ok = (
            breakdown_distance_pct >= atr_ratio * 0.12
            and breakdown_low_penetration_pct >= max(atr_ratio * 0.18, breakdown_distance_pct * 1.20)
            and current_candle['close_pos'] <= min(p['breakdown_close_pos_max'] - 0.05, 0.30)
            and current_candle['body_ratio'] >= max(p['breakdown_body_ratio_min'] + 0.05, 0.45)
            and current_candle['body_ratio'] >= max(prev_candle['body_ratio'] * 0.94, 0.34)
            and volume_ratio >= max(p['breakdown_volume_ratio_min'] + 0.08, 1.18)
            and current['close'] < prev['low']
            and current['volume'] >= prev_volume * 0.94
        )
        breakdown_ready = (
            current['close'] <= breakdown_low * (1.0 - p['breakdown_buffer_pct'])
            and breakdown_distance_pct >= atr_ratio * 0.10
            and current['close'] < prev['low']
            and current_candle['close_pos'] <= p['breakdown_close_pos_max']
            and current_candle['body_ratio'] >= p['breakdown_body_ratio_min']
            and volume_ratio >= p['breakdown_volume_ratio_min']
            and market_state['adx'] >= p['breakdown_adx_min']
            and p['breakdown_rsi_min'] <= market_state['rsi'] <= p['breakdown_rsi_max']
            and market_state['histogram'] <= p['breakdown_hist_max']
        )
        short_discount_ok = (
            not short_deep_discount
            or fourh_bear_confirmed
            or short_participation_exception
            or short_discounted_reacceleration_ok
        )
        if (
            short_trend_expansion_ok
            and (short_higher_tf_participation_ok or short_participation_exception)
            and short_fourh_structure_ok
            and short_structure_extension_ok
            and short_discount_ok
            and (not short_chase_breakdown or short_reacceleration_ok or short_absorption_exception)
            and (not short_extra_confirmation_needed or short_penetration_confirmation_ok or short_participation_exception)
            and breakdown_ready
            and _trend_followthrough_ok(market_state, 'short', breakdown_low, current['close'])
        ):
            return 'short_breakdown'

    return None
