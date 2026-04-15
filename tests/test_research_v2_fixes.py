import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import backtest_macd_aggressive as backtest
from research_v2.evaluation import _collect_daily_returns
from research_v2.strategy_code import StrategySourceError, validate_strategy_source


class BacktestFixesTest(unittest.TestCase):
    def test_closed_trade_rollup_treats_tp1_and_final_exit_as_one_trade(self):
        position = {
            "trade_id": 7,
            "entry_signal": "short_breakdown",
            "opened_size_total": 10000.0,
            "pyramids_done": 1,
            "realized_pnl_amount": 0.0,
            "realized_gross_pnl_amount": 0.0,
            "realized_fee_amount": 0.0,
            "realized_funding_amount": 0.0,
            "realized_hold_bars_weighted": 0.0,
            "realized_closed_size": 0.0,
            "realized_leg_count": 0,
        }
        tp1_leg = {
            "trade_id": 7,
            "entry_signal": "short_breakdown",
            "size": 2200.0,
            "pnl_amount": 330.0,
            "gross_pnl_amount": 350.0,
            "fee_amount": 20.0,
            "funding_amount": 0.0,
            "hold_bars": 8,
            "reason": "第一止盈",
            "pnl_pct": 15.0,
            "pyramids_done": 1,
        }
        final_leg = {
            "trade_id": 7,
            "entry_signal": "short_breakdown",
            "size": 7800.0,
            "pnl_amount": -78.0,
            "gross_pnl_amount": -40.0,
            "fee_amount": 38.0,
            "funding_amount": 0.0,
            "hold_bars": 20,
            "reason": "止损",
            "pnl_pct": -1.0,
            "pyramids_done": 1,
        }

        backtest._apply_trade_leg_rollup(position, tp1_leg)
        backtest._apply_trade_leg_rollup(position, final_leg)
        closed_trade = backtest._build_closed_trade(position)

        self.assertEqual(closed_trade["trade_id"], 7)
        self.assertEqual(closed_trade["leg_count"], 2)
        self.assertEqual(closed_trade["reason"], "止损")
        self.assertAlmostEqual(closed_trade["size"], 10000.0)
        self.assertAlmostEqual(closed_trade["closed_size"], 10000.0)
        self.assertAlmostEqual(closed_trade["pnl_amount"], 252.0)
        self.assertAlmostEqual(closed_trade["gross_pnl_amount"], 310.0)
        self.assertAlmostEqual(closed_trade["fee_amount"], 58.0)
        self.assertAlmostEqual(closed_trade["hold_bars"], 17.36, places=2)
        self.assertAlmostEqual(closed_trade["pnl_pct"], 2.52, places=2)

    def test_stop_price_uses_actual_entry_fill_reference(self):
        stop_price, valid_stop = backtest._stop_price_from_entry(
            entry_price=100.03,
            side="short",
            atr=2.0,
            stop_mult=1.5,
            stop_max_loss_pct=50.0,
            leverage=10.0,
        )

        self.assertTrue(valid_stop)
        self.assertAlmostEqual(stop_price, 103.03, places=6)

    def test_pyramid_refresh_reanchors_stop_without_loosen(self):
        position = {
            "entry_signal": "short_breakdown",
            "entry_price": 95.0,
            "stop_price": 110.0,
        }
        market_state = {"atr": 2.0}
        exit_params = {
            "stop_atr_mult": 3.0,
            "breakout_stop_atr_mult": 3.0,
            "stop_max_loss_pct": 50.0,
        }

        backtest._refresh_stop_after_resize(position, market_state, exit_params, leverage=10.0)

        self.assertAlmostEqual(position["stop_price"], 99.75, places=6)


class EvaluationFixesTest(unittest.TestCase):
    def test_collect_daily_returns_deduplicates_overlapping_days(self):
        window1 = type("Window", (), {"group": "eval", "label": "评估1"})()
        window2 = type("Window", (), {"group": "eval", "label": "评估2"})()
        results = [
            {
                "window": window1,
                "result": {
                    "daily_return_points": [
                        {"date": "2026-01-01", "return": 0.01},
                        {"date": "2026-01-02", "return": 0.02},
                    ]
                },
            },
            {
                "window": window2,
                "result": {
                    "daily_return_points": [
                        {"date": "2026-01-02", "return": 0.04},
                        {"date": "2026-01-03", "return": -0.01},
                    ]
                },
            },
        ]

        daily_returns = _collect_daily_returns(results, "eval")
        self.assertEqual(daily_returns, [0.01, 0.03, -0.01])


class StrategyValidationFixesTest(unittest.TestCase):
    def test_validate_strategy_source_rejects_reversed_param_relations(self):
        source = """
# PARAMS_START
PARAMS = {
    'intraday_adx_min': 10,
    'hourly_adx_min': 10,
    'fourh_adx_min': 10,
    'breakout_adx_min': 10,
    'breakdown_adx_min': 10,
    'breakout_lookback': 10,
    'breakdown_lookback': 10,
    'breakout_rsi_min': 60,
    'breakout_rsi_max': 55,
    'breakdown_rsi_min': 20,
    'breakdown_rsi_max': 60,
    'breakout_volume_ratio_min': 1.0,
    'breakdown_volume_ratio_min': 1.0,
    'breakout_body_ratio_min': 0.3,
    'breakdown_body_ratio_min': 0.3,
    'breakout_close_pos_min': 0.5,
    'breakdown_close_pos_max': 0.5,
    'intraday_ema_fast': 20,
    'intraday_ema_slow': 10,
    'hourly_ema_fast': 10,
    'hourly_ema_slow': 20,
    'fourh_ema_fast': 10,
    'fourh_ema_slow': 20,
    'macd_fast': 12,
    'macd_slow': 26,
    'macd_signal': 9,
    'volume_lookback': 10,
}
# PARAMS_END

def _is_sideways_regime(*args, **kwargs):
    return False

def _trend_quality_ok(*args, **kwargs):
    return True

def _trend_followthrough_ok(*args, **kwargs):
    return True

def strategy(*args, **kwargs):
    return None
"""
        with self.assertRaises(StrategySourceError):
            validate_strategy_source(source)


if __name__ == "__main__":
    unittest.main()
