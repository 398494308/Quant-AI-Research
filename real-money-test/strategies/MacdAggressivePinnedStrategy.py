from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PINNED_STRATEGY_DIR = REPO_ROOT / "real-money-test" / "pinned" / "demo"
PINNED_STRATEGY_FILE = PINNED_STRATEGY_DIR / "strategy_macd_aggressive.py"
SRC_DIR = REPO_ROOT / "src"

if not PINNED_STRATEGY_FILE.exists():
    raise ImportError(
        "demo pinned strategy not found. "
        "Run real-money-test/pin_strategy.py before starting demo."
    )

if str(PINNED_STRATEGY_DIR) not in sys.path:
    sys.path.insert(0, str(PINNED_STRATEGY_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from freqtrade_macd_aggressive import MacdAggressiveStrategy as BaseMacdAggressiveStrategy


class MacdAggressivePinnedStrategy(BaseMacdAggressiveStrategy):
    startup_candle_count = 320
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = True
    position_adjustment_enable = True
