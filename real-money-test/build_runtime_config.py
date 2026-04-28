#!/usr/bin/env python3
"""Build a local freqtrade runtime config for dry-run, demo or live trading."""

from __future__ import annotations

import argparse
import json
import os
import sys
from copy import deepcopy
from pathlib import Path

from runtime_common import get_mode_spec, normalize_mode, resolve_runtime_paths


BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
SRC_DIR = REPO_ROOT / "src"
DEFAULT_BASE_CONFIG = BASE_DIR / "config.base.json"
DEFAULT_SOURCE_CONFIG = BASE_DIR / "config.base.json"
SECRETS_ENV_FILE = REPO_ROOT / "config" / "secrets.env"
INHERITED_EXECUTION_KEYS = ("entry_pricing", "exit_pricing", "unfilledtimeout")

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import backtest_macd_aggressive as backtest_module
import strategy_macd_aggressive as strategy_module


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _deep_merge(dst: dict, src: dict) -> dict:
    for key, value in src.items():
        if isinstance(value, dict) and isinstance(dst.get(key), dict):
            _deep_merge(dst[key], value)
        else:
            dst[key] = deepcopy(value)
    return dst


def _optional_positive_float_from_env(*env_names: str) -> float | None:
    for env_name in env_names:
        raw_value = os.getenv(env_name, "").strip()
        if not raw_value:
            continue
        try:
            value = float(raw_value)
        except ValueError as exc:
            raise SystemExit(f"invalid float in {env_name}: {raw_value}") from exc
        if value <= 0:
            raise SystemExit(f"{env_name} must be > 0")
        return value
    return None


def _copy_exchange_credentials(runtime_config: dict, source_config: dict, *, mode: str) -> None:
    _load_env_file(SECRETS_ENV_FILE)
    source_exchange = source_config.get("exchange", {})
    target_exchange = runtime_config.setdefault("exchange", {})
    required_keys = ("key", "secret", "password")
    if mode == "demo":
        env_aliases = {
            "key": ("OKX_DEMO_API_KEY",),
            "secret": ("OKX_DEMO_API_SECRET",),
            "password": ("OKX_DEMO_API_PASSWORD",),
        }
    else:
        env_aliases = {
            "key": ("OKX_API_KEY", "FT_OKX_API_KEY"),
            "secret": ("OKX_API_SECRET", "FT_OKX_API_SECRET"),
            "password": ("OKX_API_PASSWORD", "FT_OKX_API_PASSWORD"),
        }

    resolved: dict[str, object] = {}
    missing: list[str] = []
    for key in required_keys:
        value = None
        for env_name in env_aliases[key]:
            env_value = os.getenv(env_name, "").strip()
            if env_value:
                value = env_value
                break
        if value is None and mode != "demo":
            source_value = source_exchange.get(key)
            if isinstance(source_value, str) and source_value.strip():
                value = source_value.strip()
        if value is None:
            missing.append(key)
            continue
        resolved[key] = value

    if missing:
        missing_text = ", ".join(missing)
        if mode == "demo":
            raise SystemExit(
                "missing OKX exchange credentials. "
                f"Set OKX_DEMO_* env vars: {missing_text}"
            )
        raise SystemExit(
            "missing OKX exchange credentials. "
            f"Set OKX_API_* env vars or provide a populated source config: {missing_text}"
        )

    for key in required_keys:
        target_exchange[key] = resolved[key]
    for key in ("ccxt_config", "ccxt_async_config", "ccxt_sync_config"):
        if key in source_exchange:
            target_exchange[key] = deepcopy(source_exchange[key])


def _enable_okx_demo_sandbox(runtime_config: dict) -> None:
    exchange = runtime_config.setdefault("exchange", {})
    for key in ("ccxt_config", "ccxt_async_config", "ccxt_sync_config"):
        payload = exchange.setdefault(key, {})
        payload["sandbox"] = True


def _apply_demo_capital_controls(runtime_config: dict) -> None:
    available_capital = _optional_positive_float_from_env(
        "OKX_DEMO_AVAILABLE_CAPITAL",
        "FT_DEMO_AVAILABLE_CAPITAL",
    )
    if available_capital is None:
        return
    runtime_config["available_capital"] = available_capital
    runtime_config.pop("tradable_balance_ratio", None)


def build_runtime_config(
    mode: str,
    base_config_path: Path,
    source_config_path: Path,
    output_path: Path | None = None,
    include_telegram: bool = False,
    include_api_server: bool = False,
) -> Path:
    mode = normalize_mode(mode)
    runtime_config = _load_json(base_config_path)
    source_config = _load_json(source_config_path)

    _copy_exchange_credentials(runtime_config, source_config, mode=mode)

    # 只继承执行参数（pricing / timeout），不继承 telegram / api_server
    for key in INHERITED_EXECUTION_KEYS:
        if key in source_config:
            runtime_config[key] = _deep_merge(runtime_config.get(key, {}), source_config[key])

    # telegram 和 api_server 只在显式请求时继承
    if include_telegram and "telegram" in source_config:
        runtime_config["telegram"] = deepcopy(source_config["telegram"])
    if include_api_server and "api_server" in source_config:
        runtime_config["api_server"] = deepcopy(source_config["api_server"])

    spec = get_mode_spec(mode)
    paths = resolve_runtime_paths(mode)
    runtime_dir = paths.runtime_dir
    user_data_dir = paths.user_data_dir
    runtime_dir.mkdir(parents=True, exist_ok=True)
    user_data_dir.mkdir(parents=True, exist_ok=True)
    (user_data_dir / "data").mkdir(parents=True, exist_ok=True)

    if output_path is None:
        output_path = paths.config_path

    is_exchange_mode = spec.is_exchange_mode
    runtime_config["dry_run"] = not is_exchange_mode
    if not is_exchange_mode:
        runtime_config.setdefault("dry_run_wallet", 1000)
    else:
        runtime_config.pop("dry_run_wallet", None)
    if mode == "demo":
        _enable_okx_demo_sandbox(runtime_config)
        _apply_demo_capital_controls(runtime_config)

    runtime_config["db_url"] = f"sqlite:///{runtime_dir / spec.db_name}"
    runtime_config["datadir"] = str(user_data_dir / "data")
    runtime_config["user_data_dir"] = str(user_data_dir)
    runtime_config["bot_name"] = spec.bot_name
    runtime_config["position_adjustment_enable"] = True
    runtime_config["max_entry_position_adjustment"] = max(
        0,
        int(getattr(strategy_module, "EXIT_PARAMS", backtest_module.EXIT_PARAMS).get("pyramid_max_times", 0)),
    )

    order_types = runtime_config.get("order_types", {})
    if order_types.get("entry") == "market":
        runtime_config.setdefault("entry_pricing", {})["price_side"] = "other"
    if order_types.get("exit") == "market":
        runtime_config.setdefault("exit_pricing", {})["price_side"] = "other"

    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(runtime_config, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build freqtrade runtime config")
    parser.add_argument("--mode", choices=("dry-run", "demo", "live"), default="demo")
    parser.add_argument("--base-config", type=Path, default=DEFAULT_BASE_CONFIG)
    parser.add_argument("--source-config", type=Path, default=DEFAULT_SOURCE_CONFIG)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--include-telegram", action="store_true",
                        help="从 source config 继承 telegram 配置")
    parser.add_argument("--include-api-server", action="store_true",
                        help="从 source config 继承 api_server 配置")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = build_runtime_config(
        args.mode,
        args.base_config,
        args.source_config,
        args.output,
        include_telegram=args.include_telegram,
        include_api_server=args.include_api_server,
    )
    print(output_path)


if __name__ == "__main__":
    main()
