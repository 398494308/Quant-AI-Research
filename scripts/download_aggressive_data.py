#!/usr/bin/env python3
"""Download and derive the OKX-only market data used by the aggressive strategy."""
from __future__ import annotations

import csv
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SRC_DIR = REPO_ROOT / "src"

import sys

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from market_data_catalog import (
    DATA_END_STR,
    DATA_START_STR,
    DEFAULT_INSTRUMENT_ID,
    PRICE_DIR,
    PRICE_HEADER,
    FUNDING_DIR,
    default_market_data_paths,
    funding_filename,
    okx_flow_proxy,
    price_filename,
)


OKX_CANDLES_API_URL = "https://www.okx.com/api/v5/market/history-candles"
OKX_FUNDING_API_URL = "https://www.okx.com/api/v5/public/funding-rate-history"
OKX_LIMIT = 300
OKX_BAR_MAP = {
    "1m": "1m",
    "15m": "15m",
}


def _timestamp_ms(date_str: str) -> int:
    return int(datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC).timestamp() * 1000)


def _format_decimal(value: float | str) -> str:
    if isinstance(value, str):
        try:
            value = float(value)
        except ValueError:
            return value
    return f"{float(value):.12f}".rstrip("0").rstrip(".") or "0"


def _reverse_copy_data_rows(descending_path: Path, output_path: Path) -> int:
    block_size = 1024 * 1024
    buffer = ""
    written = 0

    with output_path.open("w", newline="") as out_handle:
        writer = csv.writer(out_handle)
        writer.writerow(PRICE_HEADER)
        with descending_path.open("rb") as in_handle:
            in_handle.seek(0, 2)
            position = in_handle.tell()
            while position > 0:
                read_size = min(block_size, position)
                position -= read_size
                in_handle.seek(position)
                chunk = in_handle.read(read_size).decode("utf-8")
                buffer = chunk + buffer
                lines = buffer.splitlines()
                if position > 0:
                    buffer = lines[0]
                    lines = lines[1:]
                else:
                    buffer = ""
                for line in reversed(lines):
                    if not line.strip():
                        continue
                    writer.writerow(line.split(","))
                    written += 1
            if buffer.strip():
                writer.writerow(buffer.split(","))
                written += 1
    return written


def _okx_candle_to_row(raw_row: list[str]) -> dict[str, str]:
    timestamp = int(raw_row[0])
    open_price = float(raw_row[1])
    high_price = float(raw_row[2])
    low_price = float(raw_row[3])
    close_price = float(raw_row[4])
    volume = float(raw_row[5])
    quote_volume = float(raw_row[7]) if len(raw_row) > 7 and raw_row[7] not in ("", None) else volume * close_price
    flow_proxy = okx_flow_proxy(
        open_price=open_price,
        high_price=high_price,
        low_price=low_price,
        close_price=close_price,
        volume=volume,
        quote_volume=quote_volume,
    )
    return {
        "timestamp": str(timestamp),
        "open": _format_decimal(open_price),
        "high": _format_decimal(high_price),
        "low": _format_decimal(low_price),
        "close": _format_decimal(close_price),
        "volume": _format_decimal(volume),
        "quote_volume": _format_decimal(quote_volume),
        "trade_count": _format_decimal(float(flow_proxy["trade_count"])),
        "taker_buy_volume": _format_decimal(float(flow_proxy["taker_buy_volume"])),
        "taker_sell_volume": _format_decimal(float(flow_proxy["taker_sell_volume"])),
        "flow_metric_source": str(flow_proxy["flow_metric_source"]),
    }


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(PRICE_HEADER)
        for row in rows:
            writer.writerow(
                [
                    row["timestamp"],
                    row["open"],
                    row["high"],
                    row["low"],
                    row["close"],
                    row["volume"],
                    row.get("quote_volume", "0"),
                    row.get("trade_count", "0"),
                    row.get("taker_buy_volume", "0"),
                    row.get("taker_sell_volume", "0"),
                    row.get("flow_metric_source", "unknown"),
                ]
            )


def _aggregate_rows(rows: list[dict[str, str]], bars_per_bucket: int) -> list[dict[str, str]]:
    buckets: list[dict[str, str]] = []
    current: list[dict[str, str]] = []
    for row in rows:
        current.append(row)
        if len(current) != bars_per_bucket:
            continue
        volume = sum(float(item["volume"]) for item in current)
        quote_volume = sum(float(item.get("quote_volume", 0.0) or 0.0) for item in current)
        taker_buy_volume = sum(float(item.get("taker_buy_volume", 0.0) or 0.0) for item in current)
        taker_sell_volume = sum(float(item.get("taker_sell_volume", 0.0) or 0.0) for item in current)
        buckets.append(
            {
                "timestamp": current[0]["timestamp"],
                "open": current[0]["open"],
                "high": _format_decimal(max(float(item["high"]) for item in current)),
                "low": _format_decimal(min(float(item["low"]) for item in current)),
                "close": current[-1]["close"],
                "volume": _format_decimal(volume),
                "quote_volume": _format_decimal(quote_volume),
                "trade_count": _format_decimal(sum(float(item.get("trade_count", 0.0) or 0.0) for item in current)),
                "taker_buy_volume": _format_decimal(taker_buy_volume),
                "taker_sell_volume": _format_decimal(taker_sell_volume),
                "flow_metric_source": "okx_candle_proxy_agg",
            }
        )
        current = []
    return buckets


def download_okx_candles(
    interval: str,
    *,
    inst_id: str = DEFAULT_INSTRUMENT_ID,
    start_str: str = DATA_START_STR,
    end_str: str = DATA_END_STR,
) -> Path:
    okx_bar = OKX_BAR_MAP.get(interval)
    if okx_bar is None:
        raise ValueError(f"unsupported interval for direct OKX download: {interval}")

    start_ms = _timestamp_ms(start_str)
    end_ms = _timestamp_ms(end_str)
    output_path = PRICE_DIR / price_filename(interval, start_str=start_str, end_str=end_str, inst_id=inst_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile("w", delete=False, dir=output_path.parent, suffix=".desc.csv") as temp_handle:
        temp_path = Path(temp_handle.name)
        writer = csv.writer(temp_handle)
        cursor = str(end_ms)
        total_rows = 0
        while True:
            response = requests.get(
                OKX_CANDLES_API_URL,
                params={
                    "instId": inst_id,
                    "bar": okx_bar,
                    "limit": OKX_LIMIT,
                    "after": cursor,
                },
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
            rows = payload.get("data", [])
            if not rows:
                break

            oldest_ts = None
            wrote_in_batch = 0
            for raw_row in rows:
                timestamp = int(raw_row[0])
                oldest_ts = timestamp if oldest_ts is None else min(oldest_ts, timestamp)
                if timestamp < start_ms:
                    continue
                if timestamp >= end_ms:
                    continue
                normalized = _okx_candle_to_row(raw_row)
                writer.writerow([normalized[column] for column in PRICE_HEADER])
                total_rows += 1
                wrote_in_batch += 1

            if oldest_ts is None or oldest_ts <= start_ms:
                break
            cursor = str(oldest_ts)
            time.sleep(0.06 if interval == "15m" else 0.03)

        temp_handle.flush()

    written = _reverse_copy_data_rows(temp_path, output_path)
    temp_path.unlink(missing_ok=True)
    print(f"{output_path}: {written} rows")
    return output_path


def build_derived_dataset(
    source_interval: str,
    target_interval: str,
    *,
    start_str: str = DATA_START_STR,
    end_str: str = DATA_END_STR,
    inst_id: str = DEFAULT_INSTRUMENT_ID,
) -> Path:
    source_path = PRICE_DIR / price_filename(source_interval, start_str=start_str, end_str=end_str, inst_id=inst_id)
    target_path = PRICE_DIR / price_filename(target_interval, start_str=start_str, end_str=end_str, inst_id=inst_id)
    rows = _read_csv_rows(source_path)
    bars_per_bucket = {"1h": 4, "4h": 16}.get(target_interval)
    if bars_per_bucket is None:
        raise ValueError(f"unsupported derived target interval: {target_interval}")
    _write_rows(target_path, _aggregate_rows(rows, bars_per_bucket))
    print(f"{target_path}: derived from {source_path.name}")
    return target_path


def download_okx_funding(
    *,
    inst_id: str = DEFAULT_INSTRUMENT_ID,
    start_str: str = DATA_START_STR,
    end_str: str = DATA_END_STR,
) -> Path:
    start_ms = _timestamp_ms(start_str)
    end_ms = _timestamp_ms(end_str)
    rows_by_ts: dict[int, dict[str, str]] = {}
    cursor = None

    while True:
        params = {"instId": inst_id, "limit": 100}
        if cursor is not None:
            params["after"] = cursor
        response = requests.get(OKX_FUNDING_API_URL, params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data", [])
        if not data:
            break

        oldest_ts = None
        for item in data:
            timestamp = int(item["fundingTime"])
            oldest_ts = timestamp if oldest_ts is None else min(oldest_ts, timestamp)
            if start_ms <= timestamp < end_ms:
                rows_by_ts[timestamp] = {
                    "timestamp": str(timestamp),
                    "funding_rate": item.get("realizedRate") or item.get("fundingRate") or "0",
                }
        if oldest_ts is None or oldest_ts <= start_ms:
            break
        cursor = oldest_ts
        time.sleep(0.12)

    output_path = FUNDING_DIR / funding_filename(start_str=start_str, end_str=end_str, inst_id=inst_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp", "funding_rate"])
        for timestamp in sorted(rows_by_ts):
            writer.writerow([timestamp, rows_by_ts[timestamp]["funding_rate"]])
    print(f"{output_path}: {len(rows_by_ts)} rows")
    if rows_by_ts:
        first_ts = min(rows_by_ts)
        first_dt = datetime.fromtimestamp(first_ts / 1000, UTC).strftime("%Y-%m-%d")
        if first_ts > start_ms:
            print(
                "note: OKX public funding history did not reach the requested start date; "
                f"earliest available row is {first_dt}. Older windows will run with zero funding fallback."
            )
    return output_path


def main() -> None:
    download_okx_candles("15m")
    build_derived_dataset("15m", "1h")
    build_derived_dataset("15m", "4h")
    download_okx_candles("1m")
    download_okx_funding()
    paths = default_market_data_paths()
    print(f"default data paths -> 15m={paths.intraday_15m.name}, 1m={paths.execution_1m.name}, funding={paths.funding.name}")


if __name__ == "__main__":
    main()
