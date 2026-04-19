#!/usr/bin/env python3
"""研究窗口生成。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from research_v2.config import WindowConfig


# ==================== 数据结构 ====================


@dataclass(frozen=True)
class ResearchWindow:
    group: str
    label: str
    start_date: str
    end_date: str
    weight: float


# ==================== 窗口生成 ====================


def _parse_date(raw: str) -> datetime:
    return datetime.strptime(raw, "%Y-%m-%d")


def build_research_windows(config: WindowConfig) -> list[ResearchWindow]:
    development_start = _parse_date(config.development_start_date)
    development_end = _parse_date(config.development_end_date)
    validation_start = _parse_date(config.validation_start_date)
    validation_end = _parse_date(config.validation_end_date)
    test_start = _parse_date(config.test_start_date)
    test_end = _parse_date(config.test_end_date)

    if development_end < development_start:
        raise ValueError(
            f"invalid development range: {config.development_start_date}..{config.development_end_date}"
        )
    if validation_end < validation_start:
        raise ValueError(
            f"invalid validation range: {config.validation_start_date}..{config.validation_end_date}"
        )
    if test_end < test_start:
        raise ValueError(
            f"invalid test range: {config.test_start_date}..{config.test_end_date}"
        )
    if development_end >= validation_start:
        raise ValueError("development range must end before validation starts")
    if validation_end >= test_start:
        raise ValueError("validation range must end before test starts")
    if config.eval_window_days < 7:
        raise ValueError(f"eval_window_days too small: {config.eval_window_days}")
    if config.eval_step_days < 5:
        raise ValueError(f"eval_step_days too small: {config.eval_step_days}")

    eval_windows: list[ResearchWindow] = []
    cursor = development_start
    window_index = 1
    while True:
        window_end = cursor + timedelta(days=config.eval_window_days - 1)
        if window_end > development_end:
            break
        eval_windows.append(
            ResearchWindow(
                group="eval",
                label=f"train{window_index}",
                start_date=cursor.strftime("%Y-%m-%d"),
                end_date=window_end.strftime("%Y-%m-%d"),
                weight=1.0,
            )
        )
        window_index += 1
        cursor += timedelta(days=config.eval_step_days)

    tail_start = development_end - timedelta(days=config.eval_window_days - 1)
    if tail_start >= development_start:
        tail_start_str = tail_start.strftime("%Y-%m-%d")
        tail_end_str = development_end.strftime("%Y-%m-%d")
        if not eval_windows or (
            eval_windows[-1].start_date != tail_start_str
            or eval_windows[-1].end_date != tail_end_str
        ):
            eval_windows.append(
                ResearchWindow(
                    group="eval",
                    label=f"train{window_index}",
                    start_date=tail_start_str,
                    end_date=tail_end_str,
                    weight=1.0,
                )
            )

    if len(eval_windows) < 4:
        raise ValueError(f"not enough eval windows: {len(eval_windows)}")

    validation_window = ResearchWindow(
        group="validation",
        label="val1",
        start_date=validation_start.strftime("%Y-%m-%d"),
        end_date=validation_end.strftime("%Y-%m-%d"),
        weight=1.0,
    )
    test_window = ResearchWindow(
        group="test",
        label="test1",
        start_date=test_start.strftime("%Y-%m-%d"),
        end_date=test_end.strftime("%Y-%m-%d"),
        weight=1.0,
    )
    return [*eval_windows, validation_window, test_window]
