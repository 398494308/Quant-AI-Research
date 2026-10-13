"""Bounded local grid search: rank on training, validate one frozen winner."""
from __future__ import annotations

import hashlib
import itertools
import json
import statistics
from pathlib import Path
from typing import Any

from research_control.baseline import ResearchBacktest
from research_control.core import ResearchConfig, direction_status


def candidate_grid(config: ResearchConfig, direction: str, strategy_params: dict,
                   exit_params: dict) -> list[dict[str, Any]]:
    if direction not in config.search.spaces:
        raise ValueError(f"未知研究方向：{direction}")
    space = config.search.spaces[direction]
    axes = []
    for target, mapping in space.items():
        base = strategy_params if target == "strategy" else exit_params
        for name, values in mapping.items():
            if name not in base:
                raise ValueError(f"参数 {target}.{name} 不存在于当前策略")
            if target == "exit" and name in ResearchBacktest.COST_FIELDS:
                raise ValueError(f"成本参数 {name} 不允许参与搜索")
            axes.append((target, name, values))
    size = 1
    for _, _, values in axes:
        size *= len(values)
    if size > config.search.max_candidates:
        raise ValueError(f"总参数空间有 {size} 个组合，超过上限 {config.search.max_candidates}")
    candidates = []
    for combination in itertools.product(*(values for _, _, values in axes)):
        parameters = {f"{target}.{name}": value
                      for (target, name, _), value in zip(axes, combination)}
        if all((strategy_params if target == "strategy" else exit_params)[name] == value
               for (target, name, _), value in zip(axes, combination)):
            continue
        candidates.append(parameters)
    if not candidates:
        raise ValueError("本批参数组合与基线完全相同，没有可测试的候选")
    return candidates


def apply_candidate(parameters: dict[str, Any], strategy_params: dict,
                    exit_params: dict) -> tuple[dict, dict]:
    candidate_strategy = dict(strategy_params)
    candidate_exit = dict(exit_params)
    for name, value in parameters.items():
        target, key = name.split(".", 1)
        (candidate_strategy if target == "strategy" else candidate_exit)[key] = value
    return candidate_strategy, candidate_exit


def batch_prefix(direction: str, grid: list[dict[str, Any]]) -> str:
    encoded = json.dumps(grid, sort_keys=True, separators=(",", ":"))
    space_id = hashlib.sha256(encoded.encode()).hexdigest()[:10]
    return f"search-{direction}-{space_id}-"


def next_search_directions(config: ResearchConfig, records: list[dict[str, Any]],
                           strategy_params: dict, exit_params: dict) -> list[str]:
    status = direction_status(records, config)
    if status["leader"] is None:
        return []
    active_baseline = next(item for item in reversed(records) if item["direction"] == "baseline")
    active_records = records[records.index(active_baseline) + 1:]
    available = []
    for direction, state in status["directions"].items():
        if state["paused"]:
            continue
        grid = candidate_grid(config, direction, strategy_params, exit_params)
        prefix = batch_prefix(direction, grid)
        batch_count = sum(item["id"].startswith(prefix) for item in active_records)
        total = len(grid)
        if batch_count * config.search.batch_size < total:
            available.append((direction, state["attempts"]))
    if not available:
        return []
    fewest = min(attempts for _, attempts in available)
    return sorted(direction for direction, attempts in available if attempts == fewest)


def run_batch(config: ResearchConfig, records: list[dict[str, Any]], *, direction: str,
              repo_root: Path, intraday_file: Path, execution_file: Path,
              funding_file: Path, sentiment_file: Path | None = None,
              runner: ResearchBacktest | None = None) -> dict[str, Any]:
    status = direction_status(records, config)
    if status["leader"] is None:
        raise ValueError("请先建立真实基线，再进行批量搜索")
    runner = runner or ResearchBacktest(
        config, repo_root=repo_root, intraday_file=intraday_file,
        execution_file=execution_file, funding_file=funding_file, sentiment_file=sentiment_file,
    )
    active_baseline = next(item for item in reversed(records) if item["direction"] == "baseline")
    expected = (runner.data_id, runner.code_id, config.windows.score_id, runner.cost_model_id)
    actual = tuple(active_baseline[name] for name in
                   ("data_id", "code_id", "score_id", "cost_model_id"))
    if actual != expected:
        raise ValueError("数据、策略代码、评分或成本假设与当前基线不符；请先重建基线")
    if direction not in next_search_directions(
            config, records, runner.strategy_params, runner.exit_params):
        raise ValueError(f"方向 {direction} 当前不在轮换名单中，已暂停或参数空间已用尽")
    full_grid = candidate_grid(config, direction, runner.strategy_params, runner.exit_params)
    prefix = batch_prefix(direction, full_grid)
    active_records = records[records.index(active_baseline) + 1:]
    batch_index = sum(item["id"].startswith(prefix) for item in active_records)
    start = batch_index * config.search.batch_size
    grid = full_grid[start:start + config.search.batch_size]
    signature = json.dumps({"direction": direction, "grid": grid, "baseline": active_baseline["id"]},
                           sort_keys=True, separators=(",", ":"))
    batch_id = (f"{prefix}{runner.data_id[:10]}-{runner.code_id[:10]}-"
                f"{hashlib.sha256(signature.encode()).hexdigest()[:12]}")
    if any(item["id"] == batch_id for item in records):
        raise ValueError(f"本批搜索已记录：{batch_id}；请调整参数空间后再运行")

    results = []
    for parameters in grid:
        strategy_params, exit_params = apply_candidate(
            parameters, runner.strategy_params, runner.exit_params,
        )
        training = runner.evaluate(
            strategy_params, exit_params, (config.windows.training,),
        )[0]
        results.append({
            "parameters": parameters,
            "training_score": float(training["score"]),
            "training_return_pct": (float(training["return"])
                                    if "return" in training else None),
            "training_max_drawdown_pct": float(training["max_drawdown"]),
            "training_trades": int(training["trades"]) if "trades" in training else None,
            "training_fee_drag_pct": (float(training["fee_drag_pct"])
                                      if "fee_drag_pct" in training else None),
        })
    ranked = sorted(results, key=lambda item: (
        -item["training_score"], item["training_max_drawdown_pct"],
        json.dumps(item["parameters"], sort_keys=True),
    ))
    winner = ranked[0]
    strategy_params, exit_params = apply_candidate(
        winner["parameters"], runner.strategy_params, runner.exit_params,
    )
    validation = runner.evaluate(
        strategy_params, exit_params, config.windows.validation,
    )
    record = {
        "id": batch_id,
        "data_id": runner.data_id,
        "code_id": runner.code_id,
        "score_id": config.windows.score_id,
        "cost_model_id": runner.cost_model_id,
        "costs_included": True,
        "direction": direction,
        "parameters": winner["parameters"],
        "training_score": winner["training_score"],
        "validation_score": float(statistics.median(row["score"] for row in validation)),
        "validation_blocks": [float(row["score"]) for row in validation],
        "max_drawdown_pct": max(float(row["max_drawdown"]) for row in validation),
    }
    promoted = direction_status([*records, record], config)["leader"]["id"] == batch_id
    return {
        "batch_id": batch_id,
        "baseline_id": active_baseline["id"],
        "leader_before": status["leader"]["id"],
        "candidate_count": len(grid),
        "batch_index": batch_index,
        "configured_grid": full_grid,
        "training_ranked": ranked,
        "validation_details": [
            {"window": [start, end], "score": float(row["score"]),
             "return_pct": float(row["return"]) if "return" in row else None,
             "max_drawdown_pct": float(row["max_drawdown"]),
             "trades": int(row["trades"]) if "trades" in row else None,
             "fee_drag_pct": float(row["fee_drag_pct"]) if "fee_drag_pct" in row else None}
            for (start, end), row in zip(config.windows.validation, validation)
        ],
        "record": record,
        "meaningful_progress": promoted,
        "selection_rule": "仅按训练分排序，只有第一名进入固定验证窗口；冻结测试集未读取",
    }
