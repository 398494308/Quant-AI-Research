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
                        "MACD_V2_ROBUST_BLOCK_WINDOW_DAYS=28",
                        "MACD_V2_ROBUST_BLOCK_STEP_DAYS=14",
                        "MACD_V2_ROBUST_BLOCK_MEAN_WEIGHT=0.60",
                        "MACD_V2_ROBUST_BLOCK_MEDIAN_WEIGHT=0.25",
                        "MACD_V2_ROBUST_BLOCK_P25_WEIGHT=0.15",
                        "MACD_V2_BENCHMARK_HURDLE_WEIGHT=0.25",
                        "MACD_V2_TRADE_IDLE_PENALTY_WEIGHT=0.10",
                        "MACD_V2_MAX_TRADE_IDLE_DAYS=7.0",
                        "MACD_V2_TRADE_PARTICIPATION_TRAIN_FLOOR=0.12",
                        "MACD_V2_TRADE_PARTICIPATION_TRAIN_TARGET=0.22",
                        "MACD_V2_TRADE_PARTICIPATION_VALIDATION_FLOOR=0.15",
                        "MACD_V2_TRADE_PARTICIPATION_VALIDATION_TARGET=0.25",
                        "MACD_V2_ACTIVITY_MULTIPLIER_FLOOR_MONTHLY_ENTRIES=5.0",
                        "MACD_V2_ACTIVITY_MULTIPLIER_LOW_MONTHLY_ENTRIES=7.0",
                        "MACD_V2_ACTIVITY_MULTIPLIER_PREFERRED_MONTHLY_ENTRIES=10.0",
                        "MACD_V2_ACTIVITY_MULTIPLIER_FULL_MONTHLY_ENTRIES=15.0",
                        "MACD_V2_ACTIVITY_MULTIPLIER_FLOOR_VALUE=0.10",
                        "MACD_V2_ACTIVITY_MULTIPLIER_LOW_VALUE=0.35",
                        "MACD_V2_ACTIVITY_MULTIPLIER_PREFERRED_VALUE=0.70",
                        "MACD_V2_CAPTURE_BALANCE_GAP_TOLERANCE=0.08",
                        "MACD_V2_CAPTURE_BALANCE_GAP_FULL=0.24",
                        "MACD_V2_CAPTURE_BALANCE_MAX_WEAK_WEIGHT=0.65",
                        "MACD_V2_CAPTURE_SIDE_MULTIPLIER_FLOOR=0.35",
                        "MACD_V2_CAPTURE_SIDE_MULTIPLIER_FLOOR_SCORE=0.02",
                        "MACD_V2_CAPTURE_SIDE_MULTIPLIER_NEUTRAL_SCORE=0.10",
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
            self.assertEqual(runtime.scoring.robust_block_window_days, 28)
            self.assertEqual(runtime.scoring.robust_block_step_days, 14)
            self.assertAlmostEqual(runtime.scoring.robust_block_mean_weight, 0.60)
            self.assertAlmostEqual(runtime.scoring.robust_block_median_weight, 0.25)
            self.assertAlmostEqual(runtime.scoring.robust_block_p25_weight, 0.15)
            self.assertAlmostEqual(runtime.scoring.benchmark_hurdle_weight, 0.25)
            self.assertAlmostEqual(runtime.scoring.trade_idle_penalty_weight, 0.10)
            self.assertAlmostEqual(runtime.scoring.max_trade_idle_days, 7.0)
            self.assertAlmostEqual(runtime.scoring.trade_participation_train_floor, 0.12)
            self.assertAlmostEqual(runtime.scoring.trade_participation_train_target, 0.22)
            self.assertAlmostEqual(runtime.scoring.trade_participation_validation_floor, 0.15)
            self.assertAlmostEqual(runtime.scoring.trade_participation_validation_target, 0.25)
            self.assertAlmostEqual(runtime.scoring.activity_multiplier_floor_monthly_entries, 5.0)
            self.assertAlmostEqual(runtime.scoring.activity_multiplier_low_monthly_entries, 7.0)
            self.assertAlmostEqual(runtime.scoring.activity_multiplier_preferred_monthly_entries, 10.0)
            self.assertAlmostEqual(runtime.scoring.activity_multiplier_full_monthly_entries, 15.0)
            self.assertAlmostEqual(runtime.scoring.activity_multiplier_floor_value, 0.10)
            self.assertAlmostEqual(runtime.scoring.activity_multiplier_low_value, 0.35)
            self.assertAlmostEqual(runtime.scoring.activity_multiplier_preferred_value, 0.70)
            self.assertAlmostEqual(runtime.scoring.capture_balance_gap_tolerance, 0.08)
            self.assertAlmostEqual(runtime.scoring.capture_balance_gap_full, 0.24)
            self.assertAlmostEqual(runtime.scoring.capture_balance_max_weak_weight, 0.65)
            self.assertAlmostEqual(runtime.scoring.capture_side_multiplier_floor, 0.35)
            self.assertAlmostEqual(runtime.scoring.capture_side_multiplier_floor_score, 0.02)
            self.assertAlmostEqual(runtime.scoring.capture_side_multiplier_neutral_score, 0.10)
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
