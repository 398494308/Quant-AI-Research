"""Freqtrade IStrategy 适配层：尽量复用主策略的参数与入场逻辑。

这层的目标不是复刻自研回测器的全部出场细节，而是：
1. 复用主策略的单一参数源，避免第二份参数长期漂移。
2. 为 freqtrade / 对比工具提供尽量一致的入场信号形态。
"""

from __future__ import annotations

try:
    from freqtrade.strategy import IStrategy, informative
except ImportError:  # pragma: no cover - 允许在无 freqtrade 环境下被对比脚本导入
    class IStrategy:
        pass

    def informative(_timeframe):
        def decorator(func):
            return func

        return decorator

try:
    import talib.abstract as ta
except ImportError:  # pragma: no cover - 对比脚本会显式跳过
    ta = None

import numpy as np
import pandas as pd
from pandas import DataFrame

import backtest_macd_aggressive as backtest_module
import strategy_macd_aggressive as core_strategy


P = core_strategy.PARAMS
E = backtest_module.EXIT_PARAMS


def _require_talib():
    if ta is None:  # pragma: no cover - 运行期依赖检查
        raise ImportError("TA-Lib is required for freqtrade_macd_aggressive")


def _choppiness(dataframe: DataFrame, length: int = 14) -> pd.Series:
    prev_close = dataframe["close"].shift(1)
    true_range = pd.concat(
        [
            (dataframe["high"] - dataframe["low"]).abs(),
            (dataframe["high"] - prev_close).abs(),
            (dataframe["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    tr_sum = true_range.rolling(length).sum()
    high_window = dataframe["high"].rolling(length).max()
    low_window = dataframe["low"].rolling(length).min()
    price_range = (high_window - low_window).clip(lower=1e-9)
    return 100.0 * np.log10((tr_sum / price_range).clip(lower=1e-9)) / np.log10(length)


def _apply_trend_columns(dataframe: DataFrame, ema_fast: int, ema_slow: int, ema_anchor: int | None = None) -> DataFrame:
    _require_talib()
    frame = dataframe.copy()
    frame["ema_fast"] = ta.EMA(frame, timeperiod=ema_fast)
    frame["ema_slow"] = ta.EMA(frame, timeperiod=ema_slow)
    if ema_anchor is not None:
        frame["ema_anchor"] = ta.EMA(frame, timeperiod=ema_anchor)
    trend_base = frame["ema_slow"].abs().clip(lower=1e-9)
    frame["trend_spread_pct"] = (frame["ema_fast"] - frame["ema_slow"]) / trend_base
    frame["ema_slow_slope_pct"] = (frame["ema_slow"] - frame["ema_slow"].shift(1)) / trend_base
    frame["adx"] = ta.ADX(frame, timeperiod=14)
    frame["chop"] = _choppiness(frame, 14)
    return frame


def _apply_intraday_indicators(dataframe: DataFrame) -> DataFrame:
    frame = _apply_trend_columns(dataframe, P["intraday_ema_fast"], P["intraday_ema_slow"])
    macd = ta.MACD(frame, fastperiod=P["macd_fast"], slowperiod=P["macd_slow"], signalperiod=P["macd_signal"])
    frame["macd_line"] = macd["macd"]
    frame["macd_signal_line"] = macd["macdsignal"]
    frame["histogram"] = macd["macdhist"]
    frame["atr"] = ta.ATR(frame, timeperiod=14)
    frame["atr_ratio"] = frame["atr"] / frame["close"].clip(lower=1e-9)
    frame["rsi"] = ta.RSI(frame, timeperiod=14)
    frame["breakout_high"] = frame["high"].rolling(window=P["breakout_lookback"]).max().shift(1)
    frame["breakdown_low"] = frame["low"].rolling(window=P["breakdown_lookback"]).min().shift(1)
    frame["avg_volume"] = frame["volume"].rolling(window=P["volume_lookback"]).mean()
    frame["volume_ratio"] = frame["volume"] / frame["avg_volume"].clip(lower=1e-9)
    candle_range = (frame["high"] - frame["low"]).clip(lower=1e-9)
    body = frame["close"] - frame["open"]
    frame["body_ratio"] = body.abs() / candle_range
    frame["close_pos"] = (frame["close"] - frame["low"]) / candle_range
    return frame


def _apply_hourly_indicators(dataframe: DataFrame) -> DataFrame:
    frame = _apply_trend_columns(
        dataframe,
        P["hourly_ema_fast"],
        P["hourly_ema_slow"],
        ema_anchor=P["hourly_ema_anchor"],
    )
    macd = ta.MACD(frame, fastperiod=P["macd_fast"], slowperiod=P["macd_slow"], signalperiod=P["macd_signal"])
    frame["macd_line"] = macd["macd"]
    frame["macd_signal"] = macd["macdsignal"]
    return frame


def _apply_fourh_indicators(dataframe: DataFrame) -> DataFrame:
    return _apply_trend_columns(dataframe, P["fourh_ema_fast"], P["fourh_ema_slow"])


def _rename_informative(frame: DataFrame, suffix: str, columns: list[str]) -> DataFrame:
    renamed = frame[columns].copy()
    mapping = {column: f"{column}_{suffix}" for column in columns if column != "timestamp"}
    return renamed.rename(columns=mapping)


def _sideways_mask(dataframe: DataFrame) -> pd.Series:
    intraday_spread = dataframe["trend_spread_pct"].abs()
    hourly_spread = dataframe["trend_spread_pct_1h"].abs()
    fourh_spread = dataframe["trend_spread_pct_4h"].abs()
    hourly_slope = dataframe["ema_slow_slope_pct_1h"].abs()
    fourh_slope = dataframe["ema_slow_slope_pct_4h"].abs()
    atr_ratio = dataframe["atr_ratio"]

    signals = (
        ((dataframe["chop"] >= core_strategy.SIDEWAYS_INTRADAY_CHOP_MIN) & (dataframe["chop_1h"] >= core_strategy.SIDEWAYS_HOURLY_CHOP_MIN)).astype(int)
        + ((atr_ratio < core_strategy.SIDEWAYS_MIN_ATR_RATIO) & (dataframe["chop_1h"] >= core_strategy.SIDEWAYS_HOURLY_CHOP_MIN - 1.0)).astype(int)
        + ((hourly_spread < core_strategy.SIDEWAYS_MIN_HOURLY_SPREAD_PCT) & (fourh_spread < core_strategy.SIDEWAYS_MIN_FOURH_SPREAD_PCT)).astype(int)
        + (
            (intraday_spread < atr_ratio * 0.28)
            & (hourly_slope < atr_ratio * 0.08)
            & (fourh_slope < atr_ratio * 0.04)
        ).astype(int)
    )
    return signals >= 2


def _followthrough_mask(dataframe: DataFrame, side: str, trigger_col: str) -> pd.Series:
    direction = -1.0 if side == "short" else 1.0
    atr_ratio = dataframe["atr_ratio"]
    trigger_price = dataframe[trigger_col].clip(lower=1e-9)
    breakout_distance_pct = (dataframe["close"] - trigger_price).abs() / trigger_price

    confirms = (
        (direction * dataframe["trend_spread_pct"] >= atr_ratio * 0.30).astype(int)
        + (direction * dataframe["trend_spread_pct_1h"] >= np.maximum(core_strategy.SIDEWAYS_MIN_HOURLY_SPREAD_PCT * 1.35, atr_ratio * 0.85)).astype(int)
        + (direction * dataframe["trend_spread_pct_4h"] >= np.maximum(core_strategy.SIDEWAYS_MIN_FOURH_SPREAD_PCT * 1.10, atr_ratio * 1.05)).astype(int)
        + (
            (direction * dataframe["ema_slow_slope_pct_1h"] >= atr_ratio * 0.08)
            & (direction * dataframe["ema_slow_slope_pct_4h"] >= atr_ratio * 0.04)
        ).astype(int)
        + (breakout_distance_pct >= atr_ratio * 0.35).astype(int)
    )
    return confirms >= 3


def apply_entry_logic(dataframe: DataFrame) -> DataFrame:
    frame = dataframe.copy()
    frame["enter_long"] = 0
    frame["enter_short"] = 0
    frame["enter_tag"] = None

    sideways = _sideways_mask(frame)

    intraday_bull = (
        (frame["close"] > frame["ema_fast"])
        & (frame["ema_fast"] > frame["ema_slow"])
        & (frame["adx"] >= P["intraday_adx_min"])
        & (frame["macd_line"] > frame["macd_signal_line"])
    )
    hourly_bull = (
        (frame["close_1h"] > frame["ema_fast_1h"])
        & (frame["ema_fast_1h"] > frame["ema_slow_1h"])
        & (frame["close_1h"] > frame["ema_anchor_1h"])
        & (frame["macd_line_1h"] > frame["macd_signal_1h"])
        & (frame["adx_1h"] >= P["hourly_adx_min"])
    )
    fourh_bull = (
        (frame["close_4h"] > frame["ema_fast_4h"])
        & (frame["ema_fast_4h"] > frame["ema_slow_4h"])
        & (frame["adx_4h"] >= P["fourh_adx_min"])
    )
    breakout_ready = (
        (frame["close"] >= frame["breakout_high"] * (1.0 + P["breakout_buffer_pct"]))
        & (frame["close_pos"] >= P["breakout_close_pos_min"])
        & (frame["body_ratio"] >= P["breakout_body_ratio_min"])
        & (frame["volume_ratio"] >= P["breakout_volume_ratio_min"])
        & (frame["adx"] >= P["breakout_adx_min"])
        & (frame["rsi"] >= P["breakout_rsi_min"])
        & (frame["rsi"] <= P["breakout_rsi_max"])
        & (frame["histogram"] >= P["breakout_hist_min"])
    )
    breakout_followthrough = _followthrough_mask(frame, "long", "breakout_high")

    intraday_bear = (
        (frame["close"] < frame["ema_fast"])
        & (frame["ema_fast"] < frame["ema_slow"])
        & (frame["adx"] >= P["intraday_adx_min"])
        & (frame["macd_line"] < frame["macd_signal_line"])
    )
    hourly_bear = (
        (frame["close_1h"] < frame["ema_fast_1h"])
        & (frame["ema_fast_1h"] < frame["ema_slow_1h"])
        & (frame["close_1h"] < frame["ema_anchor_1h"])
        & (frame["macd_line_1h"] < frame["macd_signal_1h"])
        & (frame["adx_1h"] >= P["hourly_adx_min"])
    )
    fourh_bear = (
        (frame["close_4h"] < frame["ema_slow_4h"])
        & (frame["adx_4h"] >= P["fourh_adx_min"])
    )
    breakdown_ready = (
        (frame["close"] <= frame["breakdown_low"] * (1.0 - P["breakdown_buffer_pct"]))
        & (frame["close_pos"] <= P["breakdown_close_pos_max"])
        & (frame["body_ratio"] >= P["breakdown_body_ratio_min"])
        & (frame["volume_ratio"] >= P["breakdown_volume_ratio_min"])
        & (frame["adx"] >= P["breakdown_adx_min"])
        & (frame["rsi"] >= P["breakdown_rsi_min"])
        & (frame["rsi"] <= P["breakdown_rsi_max"])
        & (frame["histogram"] <= P["breakdown_hist_max"])
    )
    breakdown_followthrough = _followthrough_mask(frame, "short", "breakdown_low")

    long_mask = intraday_bull & hourly_bull & fourh_bull & breakout_ready & breakout_followthrough & (~sideways)
    short_mask = intraday_bear & hourly_bear & fourh_bear & breakdown_ready & breakdown_followthrough & (~sideways)

    frame.loc[long_mask, "enter_long"] = 1
    frame.loc[long_mask, "enter_tag"] = "long_breakout"
    frame.loc[short_mask, "enter_short"] = 1
    frame.loc[short_mask, "enter_tag"] = "short_breakdown"
    return frame


def build_signal_frame(df_15m: DataFrame, df_1h: DataFrame, df_4h: DataFrame) -> DataFrame:
    intraday = _apply_intraday_indicators(df_15m.sort_values("timestamp").reset_index(drop=True))
    hourly = _apply_hourly_indicators(df_1h.sort_values("timestamp").reset_index(drop=True))
    fourh = _apply_fourh_indicators(df_4h.sort_values("timestamp").reset_index(drop=True))

    merged = pd.merge_asof(
        intraday,
        _rename_informative(
            hourly,
            "1h",
            ["timestamp", "close", "ema_fast", "ema_slow", "ema_anchor", "macd_line", "macd_signal", "adx", "trend_spread_pct", "ema_slow_slope_pct", "chop"],
        ),
        on="timestamp",
        direction="backward",
    )
    merged = pd.merge_asof(
        merged,
        _rename_informative(
            fourh,
            "4h",
            ["timestamp", "close", "ema_fast", "ema_slow", "adx", "trend_spread_pct", "ema_slow_slope_pct"],
        ),
        on="timestamp",
        direction="backward",
    )
    return apply_entry_logic(merged)


class MacdAggressiveStrategy(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "15m"
    can_short = True
    minimal_roi = {"0": 999}
    stoploss = -E["stop_max_loss_pct"] / 100.0 / max(E["leverage"], 1)
    leverage_value = E["leverage"]

    macd_fast = P["macd_fast"]
    macd_slow = P["macd_slow"]
    macd_signal = P["macd_signal"]
    intraday_ema_fast = P["intraday_ema_fast"]
    intraday_ema_slow = P["intraday_ema_slow"]
    hourly_ema_fast = P["hourly_ema_fast"]
    hourly_ema_slow = P["hourly_ema_slow"]
    hourly_ema_anchor = P["hourly_ema_anchor"]
    fourh_ema_fast = P["fourh_ema_fast"]
    fourh_ema_slow = P["fourh_ema_slow"]
    intraday_adx_min = P["intraday_adx_min"]
    hourly_adx_min = P["hourly_adx_min"]
    fourh_adx_min = P["fourh_adx_min"]
    breakout_lookback = P["breakout_lookback"]
    breakdown_lookback = P["breakdown_lookback"]
    breakout_rsi_min = P["breakout_rsi_min"]
    breakout_rsi_max = P["breakout_rsi_max"]
    breakdown_rsi_min = P["breakdown_rsi_min"]
    breakdown_rsi_max = P["breakdown_rsi_max"]
    breakout_adx_min = P["breakout_adx_min"]
    breakdown_adx_min = P["breakdown_adx_min"]
    breakout_volume_ratio_min = P["breakout_volume_ratio_min"]
    breakdown_volume_ratio_min = P["breakdown_volume_ratio_min"]
    breakout_body_ratio_min = P["breakout_body_ratio_min"]
    breakdown_body_ratio_min = P["breakdown_body_ratio_min"]
    breakout_close_pos_min = P["breakout_close_pos_min"]
    breakdown_close_pos_max = P["breakdown_close_pos_max"]
    breakout_hist_min = P["breakout_hist_min"]
    breakdown_hist_max = P["breakdown_hist_max"]
    breakout_buffer_pct = P["breakout_buffer_pct"]
    breakdown_buffer_pct = P["breakdown_buffer_pct"]
    volume_lookback = P["volume_lookback"]
    min_history = P["min_history"]

    trailing_stop = True
    trailing_stop_positive = E["breakout_trailing_giveback_pct"] / 100.0 / max(E["leverage"], 1)
    trailing_stop_positive_offset = E["breakout_trailing_activation_pct"] / 100.0 / max(E["leverage"], 1)
    trailing_only_offset_is_reached = True

    def leverage(self, pair, current_time, current_rate, proposed_leverage, max_leverage, entry_tag, side, **kwargs):
        return min(self.leverage_value, max_leverage)

    def informative_pairs(self):
        return [
            ("BTC/USDT:USDT", "1h"),
            ("BTC/USDT:USDT", "4h"),
        ]

    @informative("1h")
    def populate_indicators_1h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return _apply_hourly_indicators(dataframe)

    @informative("4h")
    def populate_indicators_4h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return _apply_fourh_indicators(dataframe)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return _apply_intraday_indicators(dataframe)

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return apply_entry_logic(dataframe)

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, "exit_long"] = 0
        dataframe.loc[:, "exit_short"] = 0
        return dataframe
