"""Run the unchanged strategy on fixed training and validation windows."""
from __future__ import annotations

import hashlib
import json
import statistics
from bisect import bisect_left
from pathlib import Path
from typing import Any

from research_control.core import ResearchConfig


def file_fingerprint(paths: dict[str, Path]) -> str:
    digest = hashlib.sha256()
    for name, path in sorted(paths.items()):
        if not path.is_file():
            raise FileNotFoundError(f"缺少 {name} 行情文件：{path}")
        digest.update(name.encode("utf-8"))
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def source_fingerprint(repo_root: Path) -> str:
    return file_fingerprint({
        "strategy": repo_root / "src/strategy_macd_aggressive.py",
        "backtest": repo_root / "src/backtest_macd_aggressive.py",
    })


def verify_execution_coverage(prepared: dict[str, Any], windows: tuple[tuple[str, str], ...], index_fn) -> None:
    intraday_times = prepared["intraday_timestamps"]
    execution_times = prepared["execution_timestamps"]
    minute_ms = 60_000
    if not execution_times or prepared["execution_interval_ms"] != minute_ms:
        raise ValueError("one-minute execution data is missing or has the wrong interval")
    for start, end in windows:
        first, last = index_fn(intraday_times, start, end)
        if first >= last:
            raise ValueError(f"missing 15-minute data for {start}–{end}")
        window_start = intraday_times[first]
        window_end = intraday_times[last - 1] + prepared["intraday_interval_ms"]
        left = bisect_left(execution_times, window_start)
        right = bisect_left(execution_times, window_end)
        if (left >= right or execution_times[left] != window_start
                or execution_times[right - 1] != window_end - minute_ms):
            raise ValueError(f"one-minute execution data does not fully cover {start}–{end}")
        if any(execution_times[index] - execution_times[index - 1] != minute_ms
               for index in range(left + 1, right)):
            raise ValueError(f"one-minute execution data has gaps in {start}–{end}")


def run_baseline(
    config: ResearchConfig,
    *,
    repo_root: Path,
    intraday_file: Path,
    execution_file: Path,
    funding_file: Path,
    sentiment_file: Path | None = None,
) -> dict[str, Any]:
    import backtest_macd_aggressive as backtest
    import strategy_macd_aggressive as strategy

    paths = {"intraday_15m": intraday_file, "execution_1m": execution_file,
             "funding": funding_file}
    if sentiment_file is not None:
        paths["sentiment"] = sentiment_file
    data_id = file_fingerprint(paths)
    code_id = source_fingerprint(repo_root)
    exit_params = dict(getattr(strategy, "EXIT_PARAMS", backtest.EXIT_PARAMS))
    if any(int(exit_params.get(name, 0)) != 1 for name in
           ("trading_fee_enabled", "funding_fee_enabled", "execution_use_1m")):
        raise ValueError("baseline requires fees, funding and one-minute execution")
    if float(exit_params.get("slippage_pct", 0)) <= 0:
        raise ValueError("baseline requires positive slippage")
    cost_fields = ("trading_fee_enabled", "funding_fee_enabled", "execution_use_1m",
                   "okx_maker_fee_rate", "okx_taker_fee_rate", "slippage_pct")
    cost_values = {name: exit_params[name] for name in cost_fields}
    cost_model_id = hashlib.sha256(
        json.dumps(cost_values, sort_keys=True).encode("utf-8")
    ).hexdigest()
    prepared = backtest.prepare_backtest_context(
        strategy.PARAMS,
        intraday_file=intraday_file,
        sentiment_file=sentiment_file,
        execution_file=execution_file,
        funding_file=funding_file,
        exit_params=exit_params,
    )
    verify_execution_coverage(
        prepared,
        (config.windows.training, *config.windows.validation),
        backtest._beijing_window_indices_from_timestamps,
    )

    def evaluate(start: str, end: str) -> dict[str, Any]:
        result = backtest.backtest_macd_aggressive(
            strategy_func=strategy.strategy,
            intraday_file=intraday_file,
            hourly_file=intraday_file,
            start_date=start,
            end_date=end,
            strategy_params=strategy.PARAMS,
            exit_params=exit_params,
            sentiment_file=sentiment_file,
            execution_file=execution_file,
            funding_file=funding_file,
            prepared_context=prepared,
        )
        if result.get("funding_coverage_mode") != "full":
            raise ValueError(f"funding coverage is incomplete for {start}–{end}")
        return result

    training = evaluate(*config.windows.training)
    validation = [evaluate(*block) for block in config.windows.validation]
    return {
        "id": f"baseline-{data_id[:12]}-{code_id[:12]}",
        "data_id": data_id,
        "code_id": code_id,
        "score_id": config.windows.score_id,
        "cost_model_id": cost_model_id,
        "costs_included": True,
        "direction": "baseline",
        "parameters": {},
        "training_score": float(training["score"]),
        "validation_score": float(statistics.median(result["score"] for result in validation)),
        "validation_blocks": [float(result["score"]) for result in validation],
        "max_drawdown_pct": max(float(result["max_drawdown"]) for result in validation),
    }
