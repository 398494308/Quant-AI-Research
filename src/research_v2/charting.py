#!/usr/bin/env python3
"""研究器 v2 的收益对比图。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PerformanceChartPaths:
    validation_chart: Path | None
    selection_chart: Path | None


def _load_matplotlib():
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt
    except Exception:
        return None, None, None
    return matplotlib, mdates, plt


def charts_available() -> bool:
    matplotlib, _mdates, _plt = _load_matplotlib()
    return matplotlib is not None


def _normalized_series(daily_equity_curve: list[dict[str, Any]]) -> tuple[list[str], list[float], list[float], list[float]]:
    if len(daily_equity_curve) < 2:
        raise ValueError("daily_equity_curve too short")

    dates = [str(point.get("date", "")) for point in daily_equity_curve]
    equities = [float(point.get("equity", 0.0)) for point in daily_equity_curve]
    market_closes = [float(point.get("market_close", 0.0)) for point in daily_equity_curve]
    if any(not date for date in dates):
        raise ValueError("daily_equity_curve missing date")
    if equities[0] <= 1e-9 or market_closes[0] <= 1e-9:
        raise ValueError("invalid normalization baseline")

    strategy_nav = [value / equities[0] for value in equities]
    market_nav = [value / market_closes[0] for value in market_closes]
    peak = strategy_nav[0]
    drawdown = []
    for value in strategy_nav:
        peak = max(peak, value)
        drawdown.append(value / peak - 1.0 if peak > 1e-9 else 0.0)
    return dates, strategy_nav, market_nav, drawdown


def render_performance_chart(
    *,
    daily_equity_curve: list[dict[str, Any]],
    output_path: Path,
    title: str,
    subtitle: str,
) -> Path | None:
    matplotlib, mdates, plt = _load_matplotlib()
    if matplotlib is None or mdates is None or plt is None:
        return None

    dates, strategy_nav, market_nav, drawdown = _normalized_series(daily_equity_curve)

    fig, (ax_top, ax_bottom) = plt.subplots(
        2,
        1,
        figsize=(12.8, 7.2),
        dpi=120,
        gridspec_kw={"height_ratios": [3.2, 1.2]},
        sharex=True,
    )
    fig.patch.set_facecolor("#f7f4ed")
    for axis in (ax_top, ax_bottom):
        axis.set_facecolor("#fffdf8")
        axis.grid(True, alpha=0.22, color="#7c6a46", linewidth=0.8)

    x_values = [mdates.datestr2num(item) for item in dates]
    strategy_color = "#0f4c81"
    market_color = "#cb6d51"
    drawdown_color = "#cc5a43"

    ax_top.plot(x_values, strategy_nav, color=strategy_color, linewidth=2.2, label="Strategy")
    ax_top.plot(x_values, market_nav, color=market_color, linewidth=2.0, alpha=0.92, label="BTC")
    ax_top.legend(loc="upper left", frameon=False)
    ax_top.set_ylabel("Normalized")

    ax_bottom.axhline(0.0, color="#6f6556", linewidth=1.0, alpha=0.8)
    ax_bottom.fill_between(x_values, drawdown, 0.0, color=drawdown_color, alpha=0.24)
    ax_bottom.plot(x_values, drawdown, color=drawdown_color, linewidth=1.4)
    ax_bottom.set_ylabel("Drawdown")
    ax_bottom.set_xlabel("Date")

    locator = mdates.AutoDateLocator(minticks=6, maxticks=10)
    formatter = mdates.ConciseDateFormatter(locator)
    ax_bottom.xaxis.set_major_locator(locator)
    ax_bottom.xaxis.set_major_formatter(formatter)

    ax_top.set_title(title, loc="left", fontsize=14, fontweight="bold")
    ax_top.text(
        0.0,
        1.02,
        subtitle,
        transform=ax_top.transAxes,
        fontsize=10,
        color="#5f5648",
        va="bottom",
    )

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    return output_path
