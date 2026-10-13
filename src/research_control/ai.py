"""One-shot Codex calls using the current ChatGPT login and a local call budget."""
from __future__ import annotations

import fcntl
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from research_control.core import AiRules


PROPOSAL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "direction": {"type": "string"},
        "hypothesis": {"type": "string"},
        "distinct_from_recent": {"type": "string"},
        "disproof_condition": {"type": "string"},
        "evaluation_plan": {"type": "string"},
    },
    "required": ["direction", "hypothesis", "distinct_from_recent",
                 "disproof_condition", "evaluation_plan"],
    "additionalProperties": False,
}


class AiCallError(RuntimeError):
    """The account, budget, or Codex invocation is not usable."""


def subscription_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for name in ("OPENAI_API_KEY", "CODEX_API_KEY", "CODEX_ACCESS_TOKEN",
                 "OPENAI_BASE_URL", "OPENAI_API_BASE", "DEEPSEEK_API_KEY"):
        environment.pop(name, None)
    return environment


def check_chatgpt_login(codex_bin: str = "codex") -> str:
    resolved = shutil.which(codex_bin)
    if resolved is None:
        raise AiCallError("未找到 Codex CLI；AI 调用已停止。")
    result = subprocess.run(
        [resolved, "login", "status"],
        capture_output=True,
        text=True,
        timeout=15,
        env=subscription_environment(),
        check=False,
    )
    status = f"{result.stdout}\n{result.stderr}"
    if result.returncode != 0 or "Logged in using ChatGPT" not in status:
        raise AiCallError("Codex CLI 未使用 ChatGPT 账户登录；为避免 API 计费，AI 调用已停止。")
    return "ChatGPT 登录已确认"


def reserve_call(path: Path, *, cycle_id: str, rules: AiRules) -> None:
    if not cycle_id.strip():
        raise ValueError("cycle_id must not be empty")
    path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    with path.open("a+", encoding="utf-8") as usage:
        fcntl.flock(usage, fcntl.LOCK_EX)
        usage.seek(0)
        entries = [json.loads(line) for line in usage if line.strip()]
        today = now.date().isoformat()
        if sum(item["day"] == today for item in entries) >= rules.max_calls_per_day:
            raise AiCallError("今天的 AI 调用次数已达到配置上限。")
        if sum(item["cycle_id"] == cycle_id for item in entries) >= rules.max_calls_per_cycle:
            raise AiCallError("这轮研究的 AI 调用次数已达到配置上限；请先取得新实验结果。")
        usage.seek(0, os.SEEK_END)
        usage.write(json.dumps({"day": today, "cycle_id": cycle_id,
                                "time": now.isoformat(), "model": rules.model}) + "\n")
        usage.flush()
        os.fsync(usage.fileno())


def propose_direction(
    packet: dict[str, Any],
    *,
    rules: AiRules,
    usage_path: Path,
    codex_bin: str = "codex",
) -> dict[str, str]:
    check_chatgpt_login(codex_bin)
    cycle_id = f"{packet['data_id']}:{packet['recent_experiments'][-1]['id']}"
    reserve_call(usage_path, cycle_id=cycle_id, rules=rules)
    environment = subscription_environment()
    with tempfile.TemporaryDirectory(prefix="quant-ai-proposal-") as temp_dir:
        schema_path = Path(temp_dir) / "schema.json"
        output_path = Path(temp_dir) / "proposal.json"
        schema_path.write_text(json.dumps(PROPOSAL_SCHEMA, ensure_ascii=False), encoding="utf-8")
        prompt = (
            "你是虚拟货币策略研究员。只根据下面的客观研究摘要提出一个下一轮可证伪假设。"
            "不得读取仓库、修改文件、调用工具、使用测试集或请求额外数据。"
            "direction 必须从 allowed_directions 中选择；不要把微小改善当成有效进步。"
            "说明与近期尝试的实质区别、什么结果会否定它、如何用训练和验证集检验。"
            "只返回符合 schema 的 JSON。\n\n"
            + json.dumps(packet, ensure_ascii=False, sort_keys=True)
        )
        command = [
            shutil.which(codex_bin) or codex_bin,
            "exec", "--ignore-user-config", "--sandbox", "read-only",
            "--ephemeral", "--skip-git-repo-check", "--model", rules.model,
            "--output-schema", str(schema_path),
            "--output-last-message", str(output_path), "-",
        ]
        try:
            result = subprocess.run(
                command, input=prompt, capture_output=True, text=True,
                timeout=rules.timeout_seconds, cwd=temp_dir, env=environment,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise AiCallError("Codex 调用超时，本轮额度仍计入，避免自动重试产生额外用量。") from exc
        if result.returncode != 0:
            raise AiCallError(f"Codex 调用失败：{result.stderr.strip()[-500:]}")
        if not output_path.exists():
            raise AiCallError("Codex 未生成结构化研究建议。")
        try:
            proposal = json.loads(output_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise AiCallError("Codex 返回内容不是有效 JSON。") from exc
    if not isinstance(proposal, dict) or set(proposal) != set(PROPOSAL_SCHEMA["required"]):
        raise AiCallError("Codex 建议缺少必需字段。")
    if proposal["direction"] not in packet["allowed_directions"]:
        raise AiCallError("Codex 选择了暂停或不在本轮探索范围内的方向。")
    if any(not isinstance(value, str) or not value.strip() for value in proposal.values()):
        raise AiCallError("Codex 建议存在空白字段。")
    return proposal
