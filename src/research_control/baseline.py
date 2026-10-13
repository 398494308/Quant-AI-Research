"""Run the unchanged strategy on fixed training and validation windows."""
from __future__ import annotations

import hashlib
import json
import math
import statistics
from bisect import bisect_left
from contextlib import contextmanager
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
    intraday_interval_ms = 15 * minute_ms
    if prepared["intraday_interval_ms"] != intraday_interval_ms:
        raise ValueError("15-minute research data has the wrong interval")
    if not execution_times or prepared["execution_interval_ms"] != minute_ms:
        raise ValueError("one-minute execution data is missing or has the wrong interval")
    for start, end in windows:
        first, last = index_fn(intraday_times, start, end)
        if first >= last:
            raise ValueError(f"missing 15-minute data for {start}–{end}")
        if any(intraday_times[index] - intraday_times[index - 1] != intraday_interval_ms
               for index in range(first + 1, last)):
            raise ValueError(f"15-minute research data has gaps in {start}–{end}")
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


@contextmanager
def active_parameters(strategy, strategy_params: dict, exit_params: dict):
    """The legacy strategy reads module globals; restore them after each run."""
    original_strategy = dict(strategy.PARAMS)
    original_exit = dict(strategy.EXIT_PARAMS)
    try:
        strategy.PARAMS.clear()
        strategy.PARAMS.update(strategy_params)
        strategy.EXIT_PARAMS.clear()
        strategy.EXIT_PARAMS.update(exit_params)
        yield
    finally:
        strategy.PARAMS.clear()
        strategy.PARAMS.update(original_strategy)
        strategy.EXIT_PARAMS.clear()
        strategy.EXIT_PARAMS.update(original_exit)


class ResearchBacktest:
    """One data snapshot, one cost model, reusable prepared contexts."""

    COST_FIELDS = ("trading_fee_enabled", "funding_fee_enabled", "execution_use_1m",
                   "okx_maker_fee_rate", "okx_taker_fee_rate", "slippage_pct")

    def __init__(self, config: ResearchConfig, *, repo_root: Path, intraday_file: Path,
                 execution_file: Path, funding_file: Path, sentiment_file: Path | None = None):
        import backtest_macd_aggressive as backtest
        import strategy_macd_aggressive as strategy

        self.config = config
        self.backtest = backtest
        self.strategy = strategy
        self.intraday_file = intraday_file
        self.execution_file = execution_file
        self.funding_file = funding_file
        self.sentiment_file = sentiment_file
        paths = {"intraday_15m": intraday_file, "execution_1m": execution_file,
                 "funding": funding_file}
        if sentiment_file is not None:
            paths["sentiment"] = sentiment_file
        self.data_id = file_fingerprint(paths)
        self.code_id = source_fingerprint(repo_root)
        self.strategy_params = dict(strategy.PARAMS)
        self.exit_params = dict(getattr(strategy, "EXIT_PARAMS", backtest.EXIT_PARAMS))
        if any(int(self.exit_params.get(name, 0)) != 1 for name in
               ("trading_fee_enabled", "funding_fee_enabled", "execution_use_1m")):
            raise ValueError("research requires fees, funding and one-minute execution")
        if float(self.exit_params.get("slippage_pct", 0)) <= 0:
            raise ValueError("research requires positive slippage")
        cost_values = {name: self.exit_params[name] for name in self.COST_FIELDS}
        self.cost_model_id = hashlib.sha256(
            json.dumps(cost_values, sort_keys=True).encode("utf-8")
        ).hexdigest()
        self._prepared: dict[tuple, dict[str, Any]] = {}

    def evaluate(self, strategy_params: dict, exit_params: dict,
                 windows: tuple[tuple[str, str], ...]) -> list[dict[str, Any]]:
        if any(exit_params[name] != self.exit_params[name] for name in self.COST_FIELDS):
            raise ValueError("搜索过程中不得改变手续费、滑点、资金费率或执行精度")
        context_key = tuple(sorted(strategy_params.items()))
        with active_parameters(self.strategy, strategy_params, exit_params):
            if context_key not in self._prepared:
                prepared = self.backtest.prepare_backtest_context(
                    strategy_params,
                    intraday_file=self.intraday_file,
                    sentiment_file=self.sentiment_file,
                    execution_file=self.execution_file,
                    funding_file=self.funding_file,
                    exit_params=exit_params,
                )
                verify_execution_coverage(
                    prepared,
                    (self.config.windows.training, *self.config.windows.validation),
                    self.backtest._beijing_window_indices_from_timestamps,
                )
                self._prepared[context_key] = prepared
            prepared = self._prepared[context_key]
            results = []
            for start, end in windows:
                result = self.backtest.backtest_macd_aggressive(
                    strategy_func=self.strategy.strategy,
                    intraday_file=self.intraday_file,
                    hourly_file=self.intraday_file,
                    start_date=start,
                    end_date=end,
                    strategy_params=strategy_params,
                    exit_params=exit_params,
                    sentiment_file=self.sentiment_file,
                    execution_file=self.execution_file,
                    funding_file=self.funding_file,
                    prepared_context=prepared,
                )
                if result.get("funding_coverage_mode") != "full":
                    raise ValueError(f"funding coverage is incomplete for {start}–{end}")
                metric_names = ("score", "max_drawdown", "return", "fee_drag_pct")
                if any(name in result and not math.isfinite(float(result[name]))
                       for name in metric_names):
                    raise ValueError(f"non-finite backtest result for {start}–{end}")
                results.append(result)
            return results


def run_baseline(
    config: ResearchConfig,
    *,
    repo_root: Path,
    intraday_file: Path,
    execution_file: Path,
    funding_file: Path,
    sentiment_file: Path | None = None,
) -> dict[str, Any]:
    runner = ResearchBacktest(
        config, repo_root=repo_root, intraday_file=intraday_file,
        execution_file=execution_file, funding_file=funding_file, sentiment_file=sentiment_file,
    )
    training, *validation = runner.evaluate(
        runner.strategy_params, runner.exit_params,
        (config.windows.training, *config.windows.validation),
    )
    return {
        "id": f"baseline-{runner.data_id[:12]}-{runner.code_id[:12]}",
        "data_id": runner.data_id,
        "code_id": runner.code_id,
        "score_id": config.windows.score_id,
        "cost_model_id": runner.cost_model_id,
        "costs_included": True,
        "direction": "baseline",
        "parameters": {},
        "training_score": float(training["score"]),
        "validation_score": float(statistics.median(result["score"] for result in validation)),
        "validation_blocks": [float(result["score"]) for result in validation],
        "max_drawdown_pct": max(float(result["max_drawdown"]) for result in validation),
    }
