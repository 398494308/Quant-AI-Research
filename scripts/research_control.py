#!/usr/bin/env python3
"""Inspect research evidence and request a bounded, fresh AI hypothesis."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from research_control.ai import AiCallError, check_chatgpt_login, propose_direction
from research_control.baseline import run_baseline
from research_control.core import (
    append_record,
    decision_packet,
    direction_status,
    load_config,
    load_ledger,
    next_directions,
)

CONFIG_PATH = REPO_ROOT / "config/research_control.toml"
LEDGER_PATH = REPO_ROOT / "research/experiments.jsonl"
PROPOSALS_PATH = REPO_ROOT / "research/proposals.jsonl"
USAGE_PATH = REPO_ROOT / "state/research_control_ai_calls.jsonl"


def main() -> int:
    parser = argparse.ArgumentParser(description="虚拟货币研究管理")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="查看研究方向和 Plus 登录状态")
    baseline_command = commands.add_parser("baseline", help="用固定窗口运行当前策略并保存真实基线")
    baseline_command.add_argument("--intraday", required=True, type=Path, help="15 分钟行情 CSV")
    baseline_command.add_argument("--execution", required=True, type=Path, help="1 分钟执行行情 CSV")
    baseline_command.add_argument("--funding", required=True, type=Path, help="资金费率 CSV")
    baseline_command.add_argument("--sentiment", type=Path, help="可选情绪数据 CSV")
    record_command = commands.add_parser("record", help="把回测结果加入实验账本")
    record_command.add_argument("result_file", type=Path)
    propose_command = commands.add_parser("propose", help="生成下一轮的独立研究摘要")
    propose_command.add_argument("--use-ai", action="store_true", help="消耗一次 Plus/Codex 用量，请 AI 提案")
    args = parser.parse_args()

    try:
        config = load_config(CONFIG_PATH)
        if args.command == "baseline":
            record = run_baseline(
                config,
                repo_root=REPO_ROOT,
                intraday_file=args.intraday,
                execution_file=args.execution,
                funding_file=args.funding,
                sentiment_file=args.sentiment,
            )
            if any(item["id"] == record["id"] for item in load_ledger(LEDGER_PATH, config)):
                print(f"基线 {record['id']} 已存在，无需重复保存。")
                return 0
            append_record(LEDGER_PATH, record, config)
            print(f"已保存基线 {record['id']}，验证分 {record['validation_score']:.3f}。")
            return 0
        if args.command == "record":
            record = json.loads(args.result_file.read_text(encoding="utf-8"))
            append_record(LEDGER_PATH, record, config)
            print(f"已记录实验 {record['id']}；请在里程碑后运行安全保存脚本同步 GitHub。")
            return 0

        records = load_ledger(LEDGER_PATH, config)
        status = direction_status(records, config)
        if args.command == "status":
            try:
                login = check_chatgpt_login()
            except AiCallError as exc:
                login = str(exc)
            print(f"市场：{config.market}\n账户：{login}\n实验数：{len(records)}")
            if status["leader"]:
                print(f"数据版本：{status['data_id']}\n当前基准：{status['leader']['id']}")
                for name, state in status["directions"].items():
                    label = "暂停" if state["paused"] else "可探索"
                    print(f"  {name}: {label}，尝试 {state['attempts']} 次，连续无实质进展 {state['without_progress']} 次")
                print("下一轮允许的方向：" + ", ".join(next_directions(status)))
            else:
                print("尚无基线；等待固定数据与基线回测。")
            return 0

        packet = decision_packet(records, config)
        if not args.use_ai:
            print(json.dumps(packet, ensure_ascii=False, indent=2))
            print("如需消耗一次 Plus/Codex 用量获取新假设，添加 --use-ai。", file=sys.stderr)
            return 0
        proposal = propose_direction(packet, rules=config.ai, usage_path=USAGE_PATH)
        PROPOSALS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with PROPOSALS_PATH.open("a", encoding="utf-8") as output:
            output.write(json.dumps({"data_id": packet["data_id"],
                                     "after_experiment": packet["recent_experiments"][-1]["id"],
                                     "model": config.ai.model, "proposal": proposal},
                                    ensure_ascii=False, sort_keys=True) + "\n")
        print(json.dumps(proposal, ensure_ascii=False, indent=2))
        print("建议已记录；它只是待验证假设，尚未修改策略或使用测试集。")
        return 0
    except (AiCallError, ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"研究管理已停止：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
