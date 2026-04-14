#!/usr/bin/env python3
"""Local Codex CLI client for strategy generation."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class StrategyGenerationError(RuntimeError):
    """Base error for Codex-backed strategy generation failures."""


class StrategyGenerationTransientError(StrategyGenerationError):
    """Raised when Codex appears temporarily unavailable or times out."""


@dataclass(frozen=True)
class StrategyClientConfig:
    codex_bin: str
    model: str
    reasoning_effort: str
    sandbox: str
    timeout_seconds: int
    use_ephemeral: bool

    def describe(self) -> str:
        return (
            f"runner={self.codex_bin} "
            f"model={self.model} "
            f"effort={self.reasoning_effort} "
            f"sandbox={self.sandbox} "
            f"timeout={self.timeout_seconds}s "
            f"ephemeral={int(self.use_ephemeral)}"
        )


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def load_strategy_client_config() -> StrategyClientConfig:
    return StrategyClientConfig(
        codex_bin=os.getenv("CODEX_BIN", "codex").strip() or "codex",
        model=os.getenv("CODEX_MODEL", os.getenv("OPENAI_MODEL", "gpt-5.4")).strip() or "gpt-5.4",
        reasoning_effort=os.getenv("CODEX_REASONING_EFFORT", "medium").strip() or "medium",
        sandbox=os.getenv("CODEX_SANDBOX", "read-only").strip() or "read-only",
        timeout_seconds=int(os.getenv("CODEX_TIMEOUT_SECONDS", "900")),
        use_ephemeral=_env_flag("CODEX_EPHEMERAL", True),
    )


def describe_client_config(config: StrategyClientConfig | None = None) -> str:
    return (config or load_strategy_client_config()).describe()


def build_json_text_format(
    *,
    schema: dict[str, Any] | None = None,
    schema_name: str = "response_payload",
    strict: bool = True,
) -> dict[str, Any]:
    if schema is None:
        return {"type": "json_object"}
    return {
        "type": "json_schema",
        "name": schema_name,
        "schema": schema,
        "strict": strict,
    }


def _extract_schema(text_format: dict[str, Any] | None) -> dict[str, Any] | None:
    if not text_format:
        return None
    if text_format.get("type") == "json_schema":
        schema = text_format.get("schema")
        if isinstance(schema, dict):
            return schema
    return None


def _build_codex_prompt(prompt: str, system_prompt: str) -> str:
    parts = []
    if system_prompt.strip():
        parts.append(system_prompt.strip())
    parts.append("严格遵守给定的输出 schema。不要输出 schema 之外的内容。")
    parts.append(prompt.strip())
    return "\n\n".join(parts)


def _tail(text: str, limit: int = 1200) -> str:
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[-limit:]


def _is_retryable_error(stderr: str) -> bool:
    haystack = stderr.lower()
    return any(
        needle in haystack
        for needle in (
            "timed out",
            "timeout",
            "temporarily unavailable",
            "connection reset",
            "connection aborted",
            "connection refused",
            "connection error",
            "network error",
            "rate limit",
            "429",
            "500",
            "502",
            "503",
            "504",
        )
    )


def _read_output_message(path: Path, stdout: str) -> str:
    if path.exists():
        text = path.read_text().strip()
        if text:
            return text
    return stdout.strip()


def generate_json_object(
    prompt: str,
    system_prompt: str,
    max_output_tokens: int = 3200,
    timeout: float | tuple[float, float] | None = None,
    config: StrategyClientConfig | None = None,
    text_format: dict[str, Any] | None = None,
) -> dict[str, Any]:
    del max_output_tokens, timeout

    client_config = config or load_strategy_client_config()
    if shutil.which(client_config.codex_bin) is None:
        raise StrategyGenerationError(f"missing Codex CLI binary: {client_config.codex_bin}")

    schema = _extract_schema(text_format)
    if schema is None:
        raise StrategyGenerationError("Codex CLI client requires a json_schema output format")

    command = [
        client_config.codex_bin,
        "exec",
        "--cd",
        str(Path.cwd()),
        "--sandbox",
        client_config.sandbox,
        "--skip-git-repo-check",
        "--color",
        "never",
        "-m",
        client_config.model,
        "-c",
        f'model_reasoning_effort="{client_config.reasoning_effort}"',
    ]
    if client_config.use_ephemeral:
        command.append("--ephemeral")

    with tempfile.TemporaryDirectory(prefix="codex-exec-") as temp_dir:
        temp_root = Path(temp_dir)
        schema_path = temp_root / "schema.json"
        output_path = temp_root / "last_message.json"
        schema_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2))
        command.extend(
            [
                "--output-schema",
                str(schema_path),
                "--output-last-message",
                str(output_path),
                "-",
            ]
        )
        full_prompt = _build_codex_prompt(prompt, system_prompt)
        try:
            completed = subprocess.run(
                command,
                input=full_prompt,
                text=True,
                capture_output=True,
                timeout=client_config.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise StrategyGenerationTransientError(
                f"codex exec timed out after {client_config.timeout_seconds}s"
            ) from exc

        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        if completed.returncode != 0:
            message = (
                f"codex exec failed with exit code {completed.returncode}: "
                f"{_tail(stderr or stdout or 'no output')}"
            )
            if _is_retryable_error(stderr):
                raise StrategyGenerationTransientError(message)
            raise StrategyGenerationError(message)

        raw_text = _read_output_message(output_path, stdout)
        if not raw_text:
            raise StrategyGenerationError("codex exec returned an empty final message")
        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise StrategyGenerationError(
                f"codex exec returned invalid JSON (line {exc.lineno}, column {exc.colno}): "
                f"{exc.msg}. Raw prefix: {raw_text[:400]!r}"
            ) from exc
        if not isinstance(payload, dict):
            raise StrategyGenerationError("codex exec returned a non-object JSON payload")
        return payload
