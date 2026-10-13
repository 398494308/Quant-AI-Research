import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from research_control.ai import (
    AiCallError,
    check_chatgpt_login,
    propose_direction,
    reserve_call,
    subscription_environment,
)
from research_control.baseline import run_baseline, verify_execution_coverage
from research_control.core import (
    append_record,
    decision_packet,
    direction_status,
    load_config,
    load_ledger,
    next_directions,
)
from research_control.search import batch_prefix, candidate_grid, next_search_directions, run_batch


class ResearchControlTest(unittest.TestCase):
    def setUp(self):
        self.config = load_config(REPO_ROOT / "config/research_control.toml")
        self.baseline = self.record("base", "baseline", 10.0)

    def record(self, record_id, direction, score, *, drawdown=10.0, blocks=None):
        return {
            "id": record_id,
            "data_id": "snapshot-a",
            "code_id": f"commit-{record_id}",
            "score_id": "score-v1",
            "cost_model_id": "cost-v1",
            "costs_included": True,
            "parameters": {},
            "direction": direction,
            "training_score": 0.50,
            "validation_score": score,
            "validation_blocks": blocks if blocks is not None else [0.1, 0.2, 0.3, -0.1],
            "max_drawdown_pct": drawdown,
        }

    def test_microgain_and_worse_drawdown_do_not_reinforce_a_direction(self):
        records = [self.baseline,
                   self.record("micro", "entry", 10.2),
                   self.record("riskier", "entry", 12.0, drawdown=13.0),
                   self.record("one-block", "entry", 13.0, blocks=[0.3, -0.2, -0.1, -0.4]),
                   self.record("again", "entry", 10.2)]
        status = direction_status(records, self.config)
        self.assertEqual(status["leader"]["id"], "base")
        self.assertTrue(status["directions"]["entry"]["paused"])
        self.assertNotIn("entry", next_directions(status))
        self.assertEqual(set(decision_packet(records, self.config)["allowed_directions"]),
                         {"exit", "risk", "regime"})

    def test_meaningful_progress_updates_leader_and_rotates_exploration(self):
        records = [self.baseline, self.record("entry-good", "entry", 11.2, drawdown=11.0)]
        status = direction_status(records, self.config)
        self.assertEqual(status["leader"]["id"], "entry-good")
        self.assertEqual(set(next_directions(status)), {"exit", "risk", "regime"})

    def test_ledger_requires_baseline_and_keeps_test_set_locked(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "experiments.jsonl"
            with self.assertRaisesRegex(ValueError, "基线"):
                append_record(path, self.record("candidate", "entry", 0.45), self.config)
            append_record(path, self.baseline, self.config)
            leaked = self.record("leaked", "entry", 0.45)
            leaked["test_score"] = 0.9
            with self.assertRaisesRegex(ValueError, "冻结测试集"):
                append_record(path, leaked, self.config)
            self.assertEqual(load_ledger(path, self.config), [self.baseline])

    def test_new_score_or_cost_assumptions_require_fresh_baseline(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "experiments.jsonl"
            append_record(path, self.baseline, self.config)
            changed = self.record("changed", "entry", 0.5)
            changed["score_id"] = "score-v2"
            with self.assertRaisesRegex(ValueError, "基线"):
                append_record(path, changed, self.config)
            changed["direction"] = "baseline"
            append_record(path, changed, self.config)
            self.assertEqual(direction_status(load_ledger(path, self.config), self.config)["leader"]["id"],
                             "changed")

    def test_strategy_code_change_requires_fresh_baseline(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "experiments.jsonl"
            append_record(path, self.baseline, self.config)
            with self.assertRaisesRegex(ValueError, "代码变化"):
                append_record(path, self.record("candidate", "entry", 12.0), self.config)

    def test_gross_return_cannot_be_recorded(self):
        gross = self.record("gross", "baseline", 0.8)
        gross["costs_included"] = False
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError, "交易成本"):
                append_record(Path(root) / "experiments.jsonl", gross, self.config)

    def test_call_budget_is_a_hard_local_limit(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "calls.jsonl"
            reserve_call(path, cycle_id="a:one", rules=self.config.ai)
            with self.assertRaisesRegex(AiCallError, "这轮"):
                reserve_call(path, cycle_id="a:one", rules=self.config.ai)
            reserve_call(path, cycle_id="a:two", rules=self.config.ai)
            with self.assertRaisesRegex(AiCallError, "今天"):
                reserve_call(path, cycle_id="a:three", rules=self.config.ai)

    def test_api_credentials_are_removed_and_api_login_is_rejected(self):
        with mock.patch.dict("os.environ", {"OPENAI_API_KEY": "secret", "CODEX_API_KEY": "secret",
                                           "DEEPSEEK_API_KEY": "secret"}):
            environment = subscription_environment()
        self.assertNotIn("OPENAI_API_KEY", environment)
        self.assertNotIn("CODEX_API_KEY", environment)
        self.assertNotIn("DEEPSEEK_API_KEY", environment)
        with mock.patch("research_control.ai.shutil.which", return_value="/bin/codex"):
            with mock.patch("research_control.ai.subprocess.run") as run:
                run.return_value.returncode = 0
                run.return_value.stdout = "Logged in using an API key"
                run.return_value.stderr = ""
                with self.assertRaisesRegex(AiCallError, "API 计费"):
                    check_chatgpt_login()

    def test_ai_uses_fresh_read_only_cli_call_and_checks_direction(self):
        packet = decision_packet([self.baseline], self.config)
        proposal = {
            "direction": "entry", "hypothesis": "Improve entries",
            "distinct_from_recent": "New signal", "disproof_condition": "No validation gain",
            "evaluation_plan": "Compare training and validation blocks",
        }
        with tempfile.TemporaryDirectory() as root:
            with mock.patch("research_control.ai.check_chatgpt_login", return_value="ok"):
                with mock.patch("research_control.ai.shutil.which", return_value="/bin/codex"):
                    with mock.patch("research_control.ai.subprocess.run") as run:
                        def fake_run(command, **kwargs):
                            target = Path(command[command.index("--output-last-message") + 1])
                            target.write_text(json.dumps(proposal), encoding="utf-8")
                            self.assertIn("--ignore-user-config", command)
                            self.assertIn("--ephemeral", command)
                            self.assertIn("--skip-git-repo-check", command)
                            self.assertEqual(command[command.index("--sandbox") + 1], "read-only")
                            self.assertNotIn("OPENAI_API_KEY", kwargs["env"])
                            self.assertNotEqual(kwargs["cwd"], REPO_ROOT)
                            return mock.Mock(returncode=0, stderr="")
                        run.side_effect = fake_run
                        answer = propose_direction(packet, rules=self.config.ai,
                                                   usage_path=Path(root) / "usage.jsonl")
        self.assertEqual(answer, proposal)

    def test_baseline_uses_fixed_windows_and_requires_full_funding(self):
        with tempfile.TemporaryDirectory() as root:
            data_root = Path(root)
            paths = [data_root / name for name in ("intraday.csv", "execution.csv", "funding.csv")]
            for path in paths:
                path.write_text("sample", encoding="utf-8")
            scores = iter([1.0, 2.0, 3.0, 4.0, 5.0])
            calls = []

            def fake_backtest(**kwargs):
                calls.append((kwargs["start_date"], kwargs["end_date"]))
                return {"score": next(scores), "max_drawdown": 8.0,
                        "funding_coverage_mode": "full"}

            with mock.patch("backtest_macd_aggressive.prepare_backtest_context", return_value={}) as prepare:
                with mock.patch("research_control.baseline.verify_execution_coverage"):
                    with mock.patch("backtest_macd_aggressive.backtest_macd_aggressive",
                                    side_effect=fake_backtest):
                        record = run_baseline(self.config, repo_root=REPO_ROOT,
                                              intraday_file=paths[0], execution_file=paths[1],
                                              funding_file=paths[2])
            self.assertEqual(prepare.call_count, 1)
            self.assertEqual(calls[0], self.config.windows.training)
            self.assertEqual(calls[1:], list(self.config.windows.validation))
            self.assertEqual(record["validation_score"], 3.5)
            self.assertEqual(record["validation_blocks"], [2.0, 3.0, 4.0, 5.0])
            self.assertTrue(record["costs_included"])

            with mock.patch("backtest_macd_aggressive.prepare_backtest_context", return_value={}):
                with mock.patch("research_control.baseline.verify_execution_coverage"):
                    with mock.patch("backtest_macd_aggressive.backtest_macd_aggressive",
                                    return_value={"score": 1.0, "max_drawdown": 8.0,
                                                  "funding_coverage_mode": "partial"}):
                        with self.assertRaisesRegex(ValueError, "funding coverage"):
                            run_baseline(self.config, repo_root=REPO_ROOT,
                                         intraday_file=paths[0], execution_file=paths[1],
                                         funding_file=paths[2])

    def test_one_minute_execution_gaps_are_rejected(self):
        prepared = {
            "intraday_timestamps": [0, 900_000],
            "intraday_interval_ms": 900_000,
            "execution_timestamps": [i * 60_000 for i in range(30)],
            "execution_interval_ms": 60_000,
        }
        verify_execution_coverage(prepared, (("a", "b"),), lambda *_: (0, 2))
        prepared["execution_timestamps"].pop(12)
        with self.assertRaisesRegex(ValueError, "gaps"):
            verify_execution_coverage(prepared, (("a", "b"),), lambda *_: (0, 2))
        prepared["execution_timestamps"] = [i * 60_000 for i in range(45)]
        prepared["intraday_timestamps"] = [0, 900_000, 2_700_000]
        with self.assertRaisesRegex(ValueError, "15-minute research data has gaps"):
            verify_execution_coverage(prepared, (("a", "b"),), lambda *_: (0, 3))

    def test_search_only_validates_training_winner_and_restores_legacy_globals(self):
        import strategy_macd_aggressive as strategy

        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            paths = [folder / name for name in ("intraday.csv", "execution.csv", "funding.csv")]
            for path in paths:
                path.write_text("sample", encoding="utf-8")
            seen = []
            original = strategy.PARAMS["breakout_adx_min"]

            def fake_backtest(**kwargs):
                value = strategy.PARAMS["breakout_adx_min"]
                self.assertEqual(value, kwargs["strategy_params"]["breakout_adx_min"])
                seen.append((value, kwargs["start_date"]))
                return {"score": value, "max_drawdown": 8.0,
                        "funding_coverage_mode": "full", "trades": 10}

            with mock.patch("backtest_macd_aggressive.prepare_backtest_context", return_value={}):
                with mock.patch("research_control.baseline.verify_execution_coverage"):
                    with mock.patch("backtest_macd_aggressive.backtest_macd_aggressive",
                                    side_effect=fake_backtest):
                        baseline = run_baseline(
                            self.config, repo_root=REPO_ROOT, intraday_file=paths[0],
                            execution_file=paths[1], funding_file=paths[2],
                        )
                        seen.clear()
                        report = run_batch(
                            self.config, [baseline], direction="entry", repo_root=REPO_ROOT,
                            intraday_file=paths[0], execution_file=paths[1], funding_file=paths[2],
                        )
            self.assertEqual(strategy.PARAMS["breakout_adx_min"], original)
            self.assertEqual([value for value, _ in seen[:2]], [15.5, 16.5])
            self.assertEqual(len(seen), 2 + len(self.config.windows.validation))
            self.assertTrue(all(value == 16.5 for value, _ in seen[2:]))
            self.assertEqual(report["record"]["parameters"], {"strategy.breakout_adx_min": 16.5})
            self.assertEqual(report["record"]["validation_score"], 16.5)
            self.assertFalse(report["meaningful_progress"])
            with self.assertRaisesRegex(ValueError, "轮换名单"):
                run_batch(self.config, [baseline, report["record"]], direction="entry",
                          repo_root=REPO_ROOT, intraday_file=paths[0],
                          execution_file=paths[1], funding_file=paths[2])

    def test_search_grid_limit_and_cost_fields(self):
        import strategy_macd_aggressive as strategy

        spaces = dict(self.config.search.spaces)
        spaces["entry"] = {"strategy": {"breakout_adx_min": (10.0, 11.0, 12.0)}}
        limited = replace(self.config, search=replace(self.config.search,
                                                       max_candidates=2, spaces=spaces))
        with self.assertRaisesRegex(ValueError, "超过上限"):
            candidate_grid(limited, "entry", strategy.PARAMS, strategy.EXIT_PARAMS)
        spaces["entry"] = {"exit": {"slippage_pct": (0.01, 0.02)}}
        guarded = replace(self.config, search=replace(self.config.search,
                                                       max_candidates=2, spaces=spaces))
        with self.assertRaisesRegex(ValueError, "不允许参与搜索"):
            candidate_grid(guarded, "entry", strategy.PARAMS, strategy.EXIT_PARAMS)

    def test_search_rotation_stops_when_all_configured_batches_are_used(self):
        import strategy_macd_aggressive as strategy

        records = [self.baseline]
        self.assertEqual(set(next_search_directions(
            self.config, records, strategy.PARAMS, strategy.EXIT_PARAMS)),
            set(self.config.directions))
        for direction, count in (("entry", 3), ("exit", 2), ("risk", 2), ("regime", 2)):
            prefix = batch_prefix(direction, candidate_grid(
                self.config, direction, strategy.PARAMS, strategy.EXIT_PARAMS))
            for index in range(count):
                records.append(self.record(f"{prefix}{index}", direction, 10.2))
        self.assertEqual(next_search_directions(
            self.config, records, strategy.PARAMS, strategy.EXIT_PARAMS), [])
        spaces = dict(self.config.search.spaces)
        spaces["entry"] = {"strategy": {"breakout_adx_min": (14.5, 15.5)}}
        revised = replace(self.config, search=replace(self.config.search, spaces=spaces))
        self.assertEqual(next_search_directions(
            revised, records, strategy.PARAMS, strategy.EXIT_PARAMS), ["entry"])


if __name__ == "__main__":
    unittest.main()
