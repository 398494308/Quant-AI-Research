#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

from runtime_common import CN_TZ, REPO_ROOT, normalize_mode, pinned_metadata_path, pinned_strategy_path


DEFAULT_SOURCE = REPO_ROOT / "backups" / "strategy_macd_aggressive_v2_champion.py"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(resolved)


def pin_strategy(source_path: Path, *, mode: str = "demo") -> tuple[Path, Path]:
    resolved_mode = normalize_mode(mode)
    if resolved_mode != "demo":
        raise SystemExit("当前只支持为 demo 固定策略副本")
    if not source_path.exists():
        raise SystemExit(f"strategy source not found: {source_path}")

    source_text = source_path.read_text(encoding="utf-8")
    if not source_text.strip():
        raise SystemExit(f"strategy source is empty: {source_path}")

    target_strategy_path = pinned_strategy_path(resolved_mode)
    target_metadata_path = pinned_metadata_path(resolved_mode)
    target_strategy_path.parent.mkdir(parents=True, exist_ok=True)

    code_sha256 = sha256_text(source_text)
    metadata = {
        "mode": resolved_mode,
        "pinned_at": datetime.now(CN_TZ).isoformat(),
        "source_path": _display_path(source_path),
        "source_name": source_path.name,
        "code_sha256": code_sha256,
        "code_hash_short": code_sha256[:12],
        "target_path": _display_path(target_strategy_path),
    }

    target_strategy_path.write_text(source_text, encoding="utf-8")
    target_metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return target_strategy_path, target_metadata_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pin a fixed strategy copy for demo trading")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--mode", choices=("demo",), default="demo")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    strategy_path, metadata_path = pin_strategy(args.source, mode=args.mode)
    print(strategy_path)
    print(metadata_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
