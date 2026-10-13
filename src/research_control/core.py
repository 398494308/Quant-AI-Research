"""Research ledger and deterministic direction controls."""
from __future__ import annotations

import json
import math
import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DecisionRules:
    min_validation_score_gain: float
    min_positive_validation_blocks: int
    max_drawdown_increase_points: float
    max_attempts_without_progress: int


@dataclass(frozen=True)
class AiRules:
    model: str
    max_calls_per_day: int
    max_calls_per_cycle: int
    max_context_records: int
    timeout_seconds: int


@dataclass(frozen=True)
class WindowRules:
    training: tuple[str, str]
    validation: tuple[tuple[str, str], ...]
    score_id: str


@dataclass(frozen=True)
class ResearchConfig:
    market: str
    goal: str
    directions: tuple[str, ...]
    windows: WindowRules
    decision: DecisionRules
    ai: AiRules


def load_config(path: Path) -> ResearchConfig:
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    research, windows, decision, ai = (raw[name] for name in ("research", "windows", "decision", "ai"))
    directions = tuple(str(value).strip() for value in research["directions"])
    if not directions or len(set(directions)) != len(directions) or not all(directions):
        raise ValueError("研究方向必须填写且不能重复")
    rules = DecisionRules(**decision)
    ai_rules = AiRules(**ai)
    window_rules = WindowRules(
        training=tuple(windows["training"]),
        validation=tuple(tuple(block) for block in windows["validation"]),
        score_id=str(windows["score_id"]).strip(),
    )
    if (len(window_rules.training) != 2 or not window_rules.validation
            or any(len(block) != 2 for block in window_rules.validation)
            or not window_rules.score_id):
        raise ValueError("请配置训练窗口、验证窗口和评分口径")
    ranges = [window_rules.training, *window_rules.validation]
    parsed = [(date.fromisoformat(start), date.fromisoformat(end)) for start, end in ranges]
    if any(start > end for start, end in parsed):
        raise ValueError("研究窗口的开始日期不能晚于结束日期")
    if any(left[1] >= right[0] for left, right in zip(parsed, parsed[1:])):
        raise ValueError("训练窗口和验证窗口不能重叠")
    if rules.min_positive_validation_blocks > len(window_rules.validation):
        raise ValueError("正收益分块门槛超过了验证分块数量")
    if rules.min_validation_score_gain < 0 or rules.max_drawdown_increase_points < 0:
        raise ValueError("研究门槛不能为负数")
    if rules.min_positive_validation_blocks < 1 or rules.max_attempts_without_progress < 1:
        raise ValueError("研究次数门槛必须大于零")
    if min(ai_rules.max_calls_per_day, ai_rules.max_calls_per_cycle,
           ai_rules.max_context_records, ai_rules.timeout_seconds) < 1:
        raise ValueError("AI 调用限制必须大于零")
    return ResearchConfig(
        market=str(research["market"]).strip(),
        goal=str(research["goal"]).strip(),
        directions=directions,
        windows=window_rules,
        decision=rules,
        ai=ai_rules,
    )


def validate_record(record: dict[str, Any], config: ResearchConfig) -> dict[str, Any]:
    required = {"id", "data_id", "code_id", "score_id", "cost_model_id",
                "costs_included", "direction", "training_score", "validation_score",
                "validation_blocks", "max_drawdown_pct", "parameters"}
    if missing := required - record.keys():
        raise ValueError(f"实验记录缺少字段：{', '.join(sorted(missing))}")
    if extra := record.keys() - required:
        raise ValueError(f"实验记录包含多余字段，冻结测试集不得进入研究账本：{', '.join(sorted(extra))}")
    if record["direction"] not in (*config.directions, "baseline"):
        raise ValueError(f"未知研究方向：{record['direction']}")
    if any(not isinstance(record[key], str) or not record[key].strip()
           for key in ("id", "data_id", "code_id", "score_id", "cost_model_id")):
        raise ValueError("实验、数据、代码、评分和成本版本标识不能为空")
    if record["costs_included"] is not True:
        raise ValueError("回测成绩必须计入交易成本")
    parameters = record["parameters"]
    if not isinstance(parameters, dict) or any(
        not isinstance(name, str) or not name.strip()
        or not isinstance(value, (int, float, bool))
        or (isinstance(value, (int, float)) and not math.isfinite(value))
        for name, value in parameters.items()
    ):
        raise ValueError("参数必须是简单的名称和值")
    blocks = record["validation_blocks"]
    if not isinstance(blocks, list) or len(blocks) < config.decision.min_positive_validation_blocks:
        raise ValueError("验证分块数量不足")
    for value in [record["training_score"], record["validation_score"],
                  record["max_drawdown_pct"], *blocks]:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("分数、回撤和验证分块必须是有限数字")
    if record["max_drawdown_pct"] < 0:
        raise ValueError("回撤不能为负数")
    return {key: record[key] for key in sorted(required)}


def load_ledger(path: Path, config: ResearchConfig) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    seen = set()
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        record = validate_record(json.loads(line), config)
        if record["id"] in seen:
            raise ValueError(f"实验账本第 {line_no} 行的实验编号重复")
        seen.add(record["id"])
        records.append(record)
    return records


def append_record(path: Path, record: dict[str, Any], config: ResearchConfig) -> None:
    checked = validate_record(record, config)
    records = load_ledger(path, config)
    if any(item["id"] == checked["id"] for item in records):
        raise ValueError(f"实验已存在：{checked['id']}")
    if not records and checked["direction"] != "baseline":
        raise ValueError("请先记录真实基线，再记录候选策略")
    if records and study_key(checked) != study_key(records[-1]) and checked["direction"] != "baseline":
        raise ValueError("数据、评分或成本假设变化后，必须先建立新基线")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as output:
        output.write(json.dumps(checked, ensure_ascii=False, sort_keys=True) + "\n")


def study_key(record: dict[str, Any]) -> tuple[str, str, str]:
    return record["data_id"], record["score_id"], record["cost_model_id"]


def direction_status(records: list[dict[str, Any]], config: ResearchConfig) -> dict[str, Any]:
    if not records:
        return {"data_id": None, "leader": None, "directions": {}}
    active_study = study_key(records[-1])
    data_id = active_study[0]
    current = [record for record in records if study_key(record) == active_study]
    if current[0]["direction"] != "baseline":
        raise ValueError("当前数据版本缺少基线")
    leader = current[0]
    directions = {name: {"attempts": 0, "without_progress": 0, "paused": False}
                  for name in config.directions}
    for record in current[1:]:
        if record["direction"] == "baseline":
            leader = record
            directions = {name: {"attempts": 0, "without_progress": 0, "paused": False}
                          for name in config.directions}
            continue
        state = directions[record["direction"]]
        state["attempts"] += 1
        meaningful = (
            record["validation_score"] - leader["validation_score"]
            >= config.decision.min_validation_score_gain
            and sum(value > 0 for value in record["validation_blocks"])
            >= config.decision.min_positive_validation_blocks
            and record["max_drawdown_pct"]
            <= leader["max_drawdown_pct"] + config.decision.max_drawdown_increase_points
        )
        if meaningful:
            leader = record
            state["without_progress"] = 0
        else:
            state["without_progress"] += 1
        state["paused"] = state["without_progress"] >= config.decision.max_attempts_without_progress
    return {"data_id": data_id, "study_key": active_study,
            "leader": leader, "directions": directions}


def next_directions(status: dict[str, Any]) -> list[str]:
    available = [(name, state["attempts"]) for name, state in status["directions"].items()
                 if not state["paused"]]
    if not available:
        return []
    fewest_attempts = min(count for _, count in available)
    return sorted(name for name, count in available if count == fewest_attempts)


def decision_packet(records: list[dict[str, Any]], config: ResearchConfig) -> dict[str, Any]:
    status = direction_status(records, config)
    if status["leader"] is None:
        raise ValueError("请先用真实回测结果建立基线，AI 不会凭空提出研究方向")
    available = next_directions(status)
    if not available:
        raise ValueError("全部方向均已暂停；请先复核实验，再决定是否重启研究")
    current = [record for record in records if study_key(record) == status["study_key"]]
    return {
        "market": config.market,
        "goal": config.goal,
        "data_id": status["data_id"],
        "score_id": status["study_key"][1],
        "cost_model_id": status["study_key"][2],
        "leader": status["leader"],
        "directions": status["directions"],
        "allowed_directions": available,
        "recent_experiments": current[-config.ai.max_context_records:],
        "rule": "微小改善、单一窗口改善和更差回撤不算有效进步；必须说明假设的否定条件。",
    }
