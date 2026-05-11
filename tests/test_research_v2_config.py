import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from research_v2.config import load_research_runtime_config


class ResearchRuntimeConfigTest(unittest.TestCase):
    def test_load_research_runtime_config_reads_robustness_overrides_from_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            config_dir = repo_root / "config"
            config_dir.mkdir(parents=True, exist_ok=True)
            (config_dir / "research_v2.env").write_text(
                "\n".join(
                    [
                        "MACD_V2_MIN_VALIDATION_CLOSED_TRADES=0",
                        "MACD_V2_PROMOTION_CAPTURE_WEIGHT=0.00",
                        "MACD_V2_PROMOTION_TIMED_RETURN_WEIGHT=0.50",
                        "MACD_V2_PROMOTION_TRADE_ACTIVITY_PENALTY_WEIGHT=0.15",
                        "MACD_V2_TRADE_IDLE_PENALTY_WEIGHT=0.10",
                        "MACD_V2_MAX_TRADE_IDLE_DAYS=7.0",
                        "MACD_V2_TRADE_PARTICIPATION_PENALTY_WEIGHT=0.10",
                        "MACD_V2_TRADE_PARTICIPATION_TRAIN_FLOOR=0.12",
                        "MACD_V2_TRADE_PARTICIPATION_TRAIN_TARGET=0.22",
                        "MACD_V2_TRADE_PARTICIPATION_VALIDATION_FLOOR=0.15",
                        "MACD_V2_TRADE_PARTICIPATION_VALIDATION_TARGET=0.25",
                        "MACD_V2_TRADE_ACTIVITY_PENALTY_CAP=0.35",
                        "MACD_V2_CAPTURE_BALANCE_GAP_TOLERANCE=0.08",
                        "MACD_V2_CAPTURE_BALANCE_GAP_FULL=0.24",
                        "MACD_V2_CAPTURE_BALANCE_MAX_WEAK_WEIGHT=0.65",
                        "MACD_V2_CAPTURE_CORE_PERIOD_WEIGHT=0.70",
                        "MACD_V2_CAPTURE_RETURN_DISCOUNT_FLOOR=0.03",
                        "MACD_V2_CAPTURE_RETURN_NEUTRAL_SCORE=0.12",
                        "MACD_V2_CAPTURE_RETURN_MIN_MULTIPLIER=0.25",
                        "MACD_V2_CAPTURE_RETURN_TAIL_GAIN=0.45",
                        "MACD_V2_CAPTURE_RETURN_TAIL_SCALE=0.20",
                        "MACD_V2_TRADE_ACTIVITY_TRAIN_RANGE_LOW=180",
                        "MACD_V2_TRADE_ACTIVITY_TRAIN_RANGE_HIGH=270",
                        "MACD_V2_TRADE_ACTIVITY_VALIDATION_RANGE_LOW=120",
                        "MACD_V2_TRADE_ACTIVITY_VALIDATION_RANGE_HIGH=180",
                        "MACD_V2_ROBUSTNESS_PENALTY_CAP=0.31",
                        "MACD_V2_ROBUSTNESS_SCORE_CENTER_WARN_UNITS=2.5",
                        "MACD_V2_ROBUSTNESS_SCORE_CENTER_FAIL_UNITS=4.5",
                        "MACD_V2_ROBUSTNESS_SCORE_CENTER_EXTREME_UNITS=8.5",
                        "MACD_V2_ROBUSTNESS_SCORE_CENTER_PENALTY_MAX=0.06",
                        "MACD_V2_ROBUSTNESS_SCORE_SPREAD_WARN_RATIO=3.5",
                        "MACD_V2_ROBUSTNESS_SCORE_SPREAD_FAIL_RATIO=6.5",
                        "MACD_V2_ROBUSTNESS_SCORE_SPREAD_EXTREME_RATIO=10.5",
                        "MACD_V2_ROBUSTNESS_SCORE_SPREAD_PENALTY_MAX=0.04",
                        "MACD_V2_ROBUSTNESS_SCORE_ENVELOPE_MULTIPLIER=4.5",
                        "MACD_V2_ROBUSTNESS_SCORE_ENVELOPE_FAIL_UNITS=2.5",
                        "MACD_V2_ROBUSTNESS_SCORE_ENVELOPE_EXTREME_UNITS=5.5",
                        "MACD_V2_ROBUSTNESS_SCORE_ENVELOPE_PENALTY_MAX=0.05",
                        "MACD_V2_ROBUSTNESS_ULCER_WARN_RATIO=3.2",
                        "MACD_V2_ROBUSTNESS_ULCER_FAIL_RATIO=6.2",
                        "MACD_V2_ROBUSTNESS_ULCER_EXTREME_RATIO=10.2",
                        "MACD_V2_ROBUSTNESS_ULCER_PENALTY_MAX=0.07",
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.dict(os.environ, {}, clear=True):
                runtime = load_research_runtime_config(repo_root)

            self.assertEqual(runtime.gates.min_validation_closed_trades, 0)
            self.assertAlmostEqual(runtime.gates.min_development_mean_score, -1.00)
            self.assertAlmostEqual(runtime.gates.min_development_median_score, -1.00)
            self.assertAlmostEqual(runtime.gates.min_validation_hit_rate, 0.20)
            self.assertEqual(runtime.gates.validation_block_count, 4)
            self.assertAlmostEqual(runtime.gates.min_validation_block_floor, -0.10)
            self.assertEqual(runtime.gates.max_validation_block_failures, 3)
            self.assertAlmostEqual(runtime.scoring.promotion_capture_weight, 0.00)
            self.assertAlmostEqual(runtime.scoring.promotion_timed_return_weight, 0.50)
            self.assertAlmostEqual(runtime.scoring.promotion_trade_activity_penalty_weight, 0.15)
            self.assertAlmostEqual(runtime.scoring.trade_idle_penalty_weight, 0.10)
            self.assertAlmostEqual(runtime.scoring.max_trade_idle_days, 7.0)
            self.assertAlmostEqual(runtime.scoring.trade_participation_penalty_weight, 0.10)
            self.assertAlmostEqual(runtime.scoring.trade_participation_train_floor, 0.12)
            self.assertAlmostEqual(runtime.scoring.trade_participation_train_target, 0.22)
            self.assertAlmostEqual(runtime.scoring.trade_participation_validation_floor, 0.15)
            self.assertAlmostEqual(runtime.scoring.trade_participation_validation_target, 0.25)
            self.assertAlmostEqual(runtime.scoring.trade_activity_penalty_cap, 0.35)
            self.assertAlmostEqual(runtime.scoring.capture_balance_gap_tolerance, 0.08)
            self.assertAlmostEqual(runtime.scoring.capture_balance_gap_full, 0.24)
            self.assertAlmostEqual(runtime.scoring.capture_balance_max_weak_weight, 0.65)
            self.assertAlmostEqual(runtime.scoring.capture_core_period_weight, 0.70)
            self.assertAlmostEqual(runtime.scoring.capture_return_discount_floor, 0.03)
            self.assertAlmostEqual(runtime.scoring.capture_return_neutral_score, 0.12)
            self.assertAlmostEqual(runtime.scoring.capture_return_min_multiplier, 0.25)
            self.assertAlmostEqual(runtime.scoring.capture_return_tail_gain, 0.45)
            self.assertAlmostEqual(runtime.scoring.capture_return_tail_scale, 0.20)
            self.assertEqual(runtime.scoring.trade_activity_train_range_low, 180)
            self.assertEqual(runtime.scoring.trade_activity_train_range_high, 270)
            self.assertEqual(runtime.scoring.trade_activity_validation_range_low, 120)
            self.assertEqual(runtime.scoring.trade_activity_validation_range_high, 180)
            self.assertAlmostEqual(runtime.scoring.robustness_penalty_cap, 0.31)
            self.assertAlmostEqual(runtime.scoring.robustness_score_center_warn_units, 2.5)
            self.assertAlmostEqual(runtime.scoring.robustness_score_center_fail_units, 4.5)
            self.assertAlmostEqual(runtime.scoring.robustness_score_center_extreme_units, 8.5)
            self.assertAlmostEqual(runtime.scoring.robustness_score_center_penalty_max, 0.06)
            self.assertAlmostEqual(runtime.scoring.robustness_score_spread_warn_ratio, 3.5)
            self.assertAlmostEqual(runtime.scoring.robustness_score_spread_fail_ratio, 6.5)
            self.assertAlmostEqual(runtime.scoring.robustness_score_spread_extreme_ratio, 10.5)
            self.assertAlmostEqual(runtime.scoring.robustness_score_spread_penalty_max, 0.04)
            self.assertAlmostEqual(runtime.scoring.robustness_score_envelope_multiplier, 4.5)
            self.assertAlmostEqual(runtime.scoring.robustness_score_envelope_fail_units, 2.5)
            self.assertAlmostEqual(runtime.scoring.robustness_score_envelope_extreme_units, 5.5)
            self.assertAlmostEqual(runtime.scoring.robustness_score_envelope_penalty_max, 0.05)
            self.assertAlmostEqual(runtime.scoring.robustness_ulcer_warn_ratio, 3.2)
            self.assertAlmostEqual(runtime.scoring.robustness_ulcer_fail_ratio, 6.2)
            self.assertAlmostEqual(runtime.scoring.robustness_ulcer_extreme_ratio, 10.2)
            self.assertAlmostEqual(runtime.scoring.robustness_ulcer_penalty_max, 0.07)


if __name__ == "__main__":
    unittest.main()
