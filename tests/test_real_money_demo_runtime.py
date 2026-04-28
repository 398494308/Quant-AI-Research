import json
import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
REAL_MONEY_DIR = REPO_ROOT / "real-money-test"
if str(REAL_MONEY_DIR) not in sys.path:
    sys.path.insert(0, str(REAL_MONEY_DIR))

import build_runtime_config as runtime_builder
import daily_report as demo_report
import pin_strategy as pin_strategy_module
from runtime_common import BotStatus


class DemoRuntimeTest(unittest.TestCase):
    def setUp(self):
        self.base_config = REAL_MONEY_DIR / "config.base.json"
        self.source_config = REAL_MONEY_DIR / "config.base.json"

    def test_build_runtime_config_demo_enables_sandbox_and_isolates_bot_name(self):
        with tempfile.TemporaryDirectory() as temp_dir, mock.patch.dict(
            os.environ,
            {
                "OKX_DEMO_API_KEY": "demo-key",
                "OKX_DEMO_API_SECRET": "demo-secret",
                "OKX_DEMO_API_PASSWORD": "demo-pass",
            },
            clear=False,
        ):
            output_path = Path(temp_dir) / "config.runtime.json"
            runtime_builder.build_runtime_config(
                "demo",
                self.base_config,
                self.source_config,
                output_path,
            )
            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertFalse(payload["dry_run"])
        self.assertEqual(payload["bot_name"], "macd-aggressive-demo")
        self.assertTrue(payload["exchange"]["ccxt_config"]["sandbox"])
        self.assertTrue(payload["exchange"]["ccxt_async_config"]["sandbox"])
        self.assertTrue(payload["exchange"]["ccxt_sync_config"]["sandbox"])
        self.assertIn("tradesv3.demo.sqlite", payload["db_url"])

    def test_build_runtime_config_demo_requires_demo_credentials(self):
        with tempfile.TemporaryDirectory() as temp_dir, mock.patch.dict(
            os.environ,
            {
                "OKX_DEMO_API_KEY": "",
                "OKX_DEMO_API_SECRET": "",
                "OKX_DEMO_API_PASSWORD": "",
                "OKX_API_KEY": "live-key",
                "OKX_API_SECRET": "live-secret",
                "OKX_API_PASSWORD": "live-pass",
            },
            clear=False,
        ):
            output_path = Path(temp_dir) / "config.runtime.json"
            with self.assertRaises(SystemExit) as exc:
                runtime_builder.build_runtime_config(
                    "demo",
                    self.base_config,
                    self.source_config,
                    output_path,
                )
        self.assertIn("OKX_DEMO", str(exc.exception))

    def test_pin_strategy_writes_frozen_copy_and_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source_path = temp_root / "strategy_macd_aggressive.py"
            source_path.write_text("PARAMS = {}\n", encoding="utf-8")
            target_strategy = temp_root / "pinned" / "demo" / "strategy_macd_aggressive.py"
            target_metadata = temp_root / "pinned" / "demo" / "metadata.json"
            with mock.patch.object(
                pin_strategy_module,
                "pinned_strategy_path",
                return_value=target_strategy,
            ), mock.patch.object(
                pin_strategy_module,
                "pinned_metadata_path",
                return_value=target_metadata,
            ):
                strategy_path, metadata_path = pin_strategy_module.pin_strategy(source_path, mode="demo")

            self.assertEqual(strategy_path, target_strategy)
            self.assertEqual(metadata_path, target_metadata)
            self.assertEqual(target_strategy.read_text(encoding="utf-8"), "PARAMS = {}\n")
            metadata = json.loads(target_metadata.read_text(encoding="utf-8"))
            self.assertEqual(metadata["source_name"], "strategy_macd_aggressive.py")
            self.assertEqual(metadata["target_path"], str(target_strategy.resolve()))
            self.assertEqual(len(metadata["code_hash_short"]), 12)

    def test_daily_report_build_message_marks_demo_strategy_and_degraded_account(self):
        now = datetime(2026, 4, 28, 12, 0, 0, tzinfo=demo_report.CN_TZ)
        status = BotStatus(running=True, pid="12345", heartbeat_at=now, last_log_at=now)
        runtime_config = {
            "stake_currency": "USDT",
            "max_open_trades": 4,
            "timeframe": "15m",
            "exchange": {"pair_whitelist": ["BTC/USDT:USDT"]},
        }
        summary = {
            "total_trades": 8,
            "open_trades": 1,
            "closed_trades": 7,
            "closed_pnl_abs": 18.0,
            "open_realized_pnl_abs": 2.5,
            "unrealized_pnl_abs": -1.2,
            "day_closed_trades": 2,
            "day_wins": 1,
            "day_pnl_abs": 3.4,
            "open_positions": [
                {
                    "pair": "BTC/USDT:USDT",
                    "is_short": 0,
                    "leverage": 10,
                    "stake_amount": 100.0,
                    "unrealized_pnl_abs": -1.2,
                    "enter_tag": "long_pullback",
                }
            ],
            "recent_closes": [],
        }
        degraded_snapshot = demo_report.AccountSnapshot(
            equity=None,
            available_balance=None,
            source_label="local_estimate",
            degraded_reason="missing OKX_DEMO_* credentials",
        )
        with tempfile.TemporaryDirectory() as temp_dir, mock.patch.object(
            demo_report,
            "fetch_okx_account_snapshot",
            return_value=degraded_snapshot,
        ), mock.patch.object(
            demo_report,
            "load_pinned_metadata",
            return_value={"code_hash_short": "abc123def456", "source_name": "champion.py"},
        ):
            message = demo_report.build_message(
                now,
                "demo",
                status,
                runtime_config,
                summary,
                {},
                Path(temp_dir) / "snapshots.json",
            )

        self.assertIn("【OKX Demo】", message)
        self.assertIn("策略 abc123def456 | champion.py", message)
        self.assertIn("degraded=missing OKX_DEMO_* credentials", message)
        self.assertIn("tag=long_pullback", message)


if __name__ == "__main__":
    unittest.main()
