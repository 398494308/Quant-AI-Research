#!/usr/bin/env python3
"""回测窗口切片与运行态准备。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class BacktestWindowRuntime:
    intraday_data: list[dict[str, Any]]
    intraday_start_idx: int
    intraday_end_idx: int
    start_ts: int
    end_ts: int
    execution_rows: list[dict[str, Any]]
    execution_timestamps: list[int]
    funding_rows: list[dict[str, Any]]
    funding_timestamps: list[int]
    funding_coverage: dict[str, Any]
    four_hour_window_state: list[dict[str, Any]]
    four_hour_window_close_timestamps: list[int]


def prepare_backtest_window_runtime(
    prepared_context: dict[str, Any],
    *,
    start_date: str,
    end_date: str,
    exit_params: dict[str, Any],
    include_diagnostics: bool,
    beijing_window_indices_from_timestamps: Callable[[list[int], str, str], tuple[int, int]],
    timestamp_window_indices_inclusive: Callable[[list[int], int, int], tuple[int, int]],
    funding_interval_ms: Callable[[list[int]], int],
    funding_window_coverage_report: Callable[[list[int], int, int], dict[str, Any]],
) -> BacktestWindowRuntime:
    intraday_all = prepared_context["intraday_all"]
    intraday_timestamps = prepared_context["intraday_timestamps"]
    intraday_interval_ms = prepared_context["intraday_interval_ms"]
    intraday_start_idx, intraday_end_idx = beijing_window_indices_from_timestamps(intraday_timestamps, start_date, end_date)
    intraday_data = intraday_all[intraday_start_idx:intraday_end_idx]
    if not intraday_data or not prepared_context["hourly_all"]:
        raise ValueError(f"missing data for window {start_date}~{end_date}")

    start_ts = intraday_data[0]["timestamp"]
    end_ts = intraday_data[-1]["timestamp"] + intraday_interval_ms

    execution_rows: list[dict[str, Any]] = []
    execution_timestamps: list[int] = []
    execution_all = prepared_context["execution_all"]
    if execution_all:
        full_execution_timestamps = prepared_context["execution_timestamps"]
        execution_start_idx, execution_end_idx = timestamp_window_indices_inclusive(
            full_execution_timestamps,
            start_ts,
            end_ts + 60_000,
        )
        execution_rows = execution_all[execution_start_idx:execution_end_idx]
        execution_timestamps = full_execution_timestamps[execution_start_idx:execution_end_idx]

    funding_rows: list[dict[str, Any]] = []
    funding_timestamps: list[int] = []
    funding_coverage: dict[str, Any] = {
        "mode": "disabled" if int(exit_params.get("funding_fee_enabled", 1)) <= 0 else "none",
        "ratio": 0.0,
        "gap_count": 0,
    }
    funding_all = prepared_context["funding_all"]
    if funding_all:
        full_funding_timestamps = prepared_context["funding_timestamps"]
        current_funding_interval_ms = funding_interval_ms(full_funding_timestamps)
        validation_start_idx, validation_end_idx = timestamp_window_indices_inclusive(
            full_funding_timestamps,
            start_ts - current_funding_interval_ms,
            end_ts + current_funding_interval_ms,
        )
        funding_coverage = funding_window_coverage_report(
            full_funding_timestamps[validation_start_idx:validation_end_idx],
            start_ts,
            end_ts,
        )
        funding_start_idx, funding_end_idx = timestamp_window_indices_inclusive(
            full_funding_timestamps,
            start_ts,
            end_ts,
        )
        funding_rows = funding_all[funding_start_idx:funding_end_idx]
        funding_timestamps = full_funding_timestamps[funding_start_idx:funding_end_idx]

    four_hour_window_state: list[dict[str, Any]] = []
    four_hour_window_close_timestamps: list[int] = []
    if include_diagnostics:
        full_four_hour_close_timestamps = prepared_context["four_hour_close_timestamps"]
        four_hour_start_idx, four_hour_end_idx = timestamp_window_indices_inclusive(
            full_four_hour_close_timestamps,
            start_ts,
            end_ts,
        )
        four_hour_window_state = prepared_context["four_hour_state"][four_hour_start_idx:four_hour_end_idx]
        four_hour_window_close_timestamps = full_four_hour_close_timestamps[four_hour_start_idx:four_hour_end_idx]

    return BacktestWindowRuntime(
        intraday_data=intraday_data,
        intraday_start_idx=intraday_start_idx,
        intraday_end_idx=intraday_end_idx,
        start_ts=start_ts,
        end_ts=end_ts,
        execution_rows=execution_rows,
        execution_timestamps=execution_timestamps,
        funding_rows=funding_rows,
        funding_timestamps=funding_timestamps,
        funding_coverage=funding_coverage,
        four_hour_window_state=four_hour_window_state,
        four_hour_window_close_timestamps=four_hour_window_close_timestamps,
    )
