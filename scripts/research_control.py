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
from research_control.baseline import ResearchBacktest, run_baseline
from research_control.core import (
    append_record,
    decision_packet,
    direction_status,
    load_config,
    load_ledger,
)
from research_control.search import next_search_directions, run_batch

CONFIG_PATH = REPO_ROOT / "config/research_control.toml"
LEDGER_PATH = REPO_ROOT / "research/experiments.jsonl"
PROPOSALS_PATH = REPO_ROOT / "research/proposals.jsonl"
USAGE_PATH = REPO_ROOT / "state/research_control_ai_calls.jsonl"
BATCHES_DIR = REPO_ROOT / "research/batches"


def add_data_arguments(command):
    command.add_argument("--intraday", required=True, type=Path, help="15 分钟行情 CSV")
    command.add_argument("--execution", required=True, type=Path, help="1 分钟执行行情 CSV")
    command.add_argument("--funding", required=True, type=Path, help="资金费率 CSV")
    command.add_argument("--sentiment", type=Path, help="可选情绪数据 CSV")


def save_batch(report, config):
    BATCHES_DIR.mkdir(parents=True, exist_ok=True)
    report_path = BATCHES_DIR / f"{report['batch_id']}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    append_record(LEDGER_PATH, report["record"], config)
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(description="虚拟货币研究管理")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="查看研究方向和 Plus 登录状态")
    baseline_command = commands.add_parser("baseline", help="用固定窗口运行当前策略并保存真实基线")
    add_data_arguments(baseline_command)
    search_command = commands.add_parser("search", help="训练集穷举，第一名进入固定验证集")
    search_command.add_argument("--direction", required=True, help="entry/exit/risk/regime")
    add_data_arguments(search_command)
    auto_command = commands.add_parser("auto", help="有预算上限地自动轮换研究方向")
    add_data_arguments(auto_command)
    auto_command.add_argument("--max-batches", type=int, help="本次最多完成几批；不得超过配置上限")
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

        if args.command == "search":
            records = load_ledger(LEDGER_PATH, config)
            report = run_batch(
                config, records, direction=args.direction, repo_root=REPO_ROOT,
                intraday_file=args.intraday, execution_file=args.execution,
                funding_file=args.funding, sentiment_file=args.sentiment,
            )
            report_path = save_batch(report, config)
            outcome = "达到初始实质进展门槛" if report["meaningful_progress"] else "未达到初始实质进展门槛"
            print(f"已完成 {report['candidate_count']} 个训练候选，验证第一名；{outcome}。")
            print(f"实验报告：{report_path}")
            return 0

        if args.command == "auto":
            limit = (config.search.max_batches_per_run if args.max_batches is None
                     else args.max_batches)
            if limit < 1 or limit > config.search.max_batches_per_run:
                raise ValueError("本次批次数必须是正数，且不能超过配置上限")
            records = load_ledger(LEDGER_PATH, config)
            if not records:
                raise ValueError("请先建立真实基线，再启动自动搜索")
            runner = ResearchBacktest(
                config, repo_root=REPO_ROOT, intraday_file=args.intraday,
                execution_file=args.execution, funding_file=args.funding,
                sentiment_file=args.sentiment,
            )
            completed = 0
            for _ in range(limit):
                choices = next_search_directions(
                    config, records, runner.strategy_params, runner.exit_params,
                )
                if not choices:
                    break
                report = run_batch(
                    config, records, direction=choices[0], repo_root=REPO_ROOT,
                    intraday_file=args.intraday, execution_file=args.execution,
                    funding_file=args.funding, sentiment_file=args.sentiment, runner=runner,
                )
                save_batch(report, config)
                records.append(report["record"])
                completed += 1
                print(f"第 {completed} 批：{choices[0]}，训练 {report['candidate_count']} 组；"
                      f"验证分 {report['record']['validation_score']:.3f}，"
                      f"实质进展：{'是' if report['meaningful_progress'] else '否'}。")
            print(f"本次完成 {completed} 批；达到预算或当前参数空间/方向规则已用尽。")
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
                import strategy_macd_aggressive as strategy

                print(f"数据版本：{status['data_id']}\n当前基准：{status['leader']['id']}")
                for name, state in status["directions"].items():
                    label = "暂停" if state["paused"] else "可探索"
                    print(f"  {name}: {label}，尝试 {state['attempts']} 次，连续无实质进展 {state['without_progress']} 次")
                search_choices = next_search_directions(
                    config, records, strategy.PARAMS, strategy.EXIT_PARAMS,
                )
                print("下一轮可自动搜索的方向：" + (", ".join(search_choices) or "无"))
            else:
                print("研究流程已配置；尚无基线。先固定数据并复现基线，再按轮换方向搜索。")
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
