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


@dataclass(frozen=True)
class ChartSeries:
    dates: list[str]
    strategy_nav: list[float]
    market_nav: list[float]
    equity_base: float
    market_base: float
    latest_equity: float
    latest_market_close: float


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


def _normalized_series(daily_equity_curve: list[dict[str, Any]]) -> ChartSeries:
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
    return ChartSeries(
        dates=dates,
        strategy_nav=strategy_nav,
        market_nav=market_nav,
        equity_base=equities[0],
        market_base=market_closes[0],
        latest_equity=equities[-1],
        latest_market_close=market_closes[-1],
    )


def _format_axis_value(value: float) -> str:
    magnitude = abs(value)
    if magnitude >= 1000:
        return f"{value:,.0f}"
    if magnitude >= 10:
        return f"{value:,.2f}"
    if magnitude >= 1:
        return f"{value:,.3f}"
    return f"{value:,.4f}"


def _format_legend_value(value: float) -> str:
    return _format_axis_value(value)


def _configure_value_panel(
    *,
    axis: Any,
    matplotlib: Any,
    mdates: Any,
    title: str,
    subtitle: str,
    series: ChartSeries,
    strategy_color: str,
    market_color: str,
    show_xlabel: bool = True,
) -> None:
    x_values = [mdates.datestr2num(item) for item in series.dates]
    axis.plot(
        x_values,
        series.strategy_nav,
        color=strategy_color,
        linewidth=2.2,
        label=f"Account ({_format_legend_value(series.latest_equity)})",
    )
    axis.plot(
        x_values,
        series.market_nav,
        color=market_color,
        linewidth=2.0,
        alpha=0.92,
        label=f"BTC ({_format_legend_value(series.latest_market_close)})",
    )
    axis.legend(loc="upper left", frameon=False)
    axis.set_ylabel("Account Value", color=strategy_color)
    axis.tick_params(axis="y", colors=strategy_color)

    def _account_formatter(value: float, _position: float) -> str:
        return _format_axis_value(value * series.equity_base)

    axis.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(_account_formatter))

    price_axis = axis.twinx()
    price_axis.set_ylim(axis.get_ylim())
    price_axis.set_ylabel("BTC Price", color=market_color)
    price_axis.tick_params(axis="y", colors=market_color)
    price_axis.grid(False)

    def _price_formatter(value: float, _position: float) -> str:
        return _format_axis_value(value * series.market_base)

    price_axis.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(_price_formatter))

    locator = mdates.AutoDateLocator(minticks=4, maxticks=8)
    formatter = mdates.ConciseDateFormatter(locator)
    axis.xaxis.set_major_locator(locator)
    axis.xaxis.set_major_formatter(formatter)
    if show_xlabel:
        axis.set_xlabel("Date")

    axis.set_title(title, loc="left", fontsize=14 if show_xlabel else 13, fontweight="bold")
    axis.text(
        0.0,
        1.02,
        subtitle,
        transform=axis.transAxes,
        fontsize=10,
        color="#5f5648",
        va="bottom",
    )


def render_performance_chart(
    *,
    daily_equity_curve: list[dict[str, Any]],
    output_path: Path,
    title: str,
    subtitle: str,
    secondary_daily_equity_curve: list[dict[str, Any]] | None = None,
    secondary_title: str | None = None,
    secondary_subtitle: str | None = None,
) -> Path | None:
    matplotlib, mdates, plt = _load_matplotlib()
    if matplotlib is None or mdates is None or plt is None:
        return None

    primary_series = _normalized_series(daily_equity_curve)
    has_secondary_panel = bool(secondary_daily_equity_curve and len(secondary_daily_equity_curve) >= 2)
    secondary_series: ChartSeries | None = None
    if has_secondary_panel:
        secondary_series = _normalized_series(secondary_daily_equity_curve or [])

    if has_secondary_panel:
        fig = plt.figure(figsize=(12.8, 8.8), dpi=120)
        grid = fig.add_gridspec(2, 1, height_ratios=[3.1, 2.6])
        ax_top = fig.add_subplot(grid[0])
        ax_secondary = fig.add_subplot(grid[1])
    else:
        fig, ax_top = plt.subplots(1, 1, figsize=(12.8, 5.6), dpi=120)
        ax_secondary = None
    fig.patch.set_facecolor("#f7f4ed")
    styled_axes = [ax_top]
    if ax_secondary is not None:
        styled_axes.append(ax_secondary)
    for axis in styled_axes:
        axis.set_facecolor("#fffdf8")
        axis.grid(True, alpha=0.22, color="#7c6a46", linewidth=0.8)

    strategy_color = "#0f4c81"
    market_color = "#cb6d51"

    _configure_value_panel(
        axis=ax_top,
        matplotlib=matplotlib,
        mdates=mdates,
        title=title,
        subtitle=subtitle,
        series=primary_series,
        strategy_color=strategy_color,
        market_color=market_color,
        show_xlabel=ax_secondary is None,
    )
    if ax_secondary is not None:
        _configure_value_panel(
            axis=ax_secondary,
            matplotlib=matplotlib,
            mdates=mdates,
            title=secondary_title or "Test Comparison",
            subtitle=secondary_subtitle or "",
            series=secondary_series,
            strategy_color=strategy_color,
            market_color=market_color,
        )

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    return output_path
