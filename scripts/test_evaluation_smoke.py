#!/usr/bin/env python3
"""Assert the evaluation smoke harness exercises real evaluator/verifier paths.

Each workflow must fail for its intended reason: a clear defect raises leads, an
adjacent legitimate control raises none, a valid repair verifies while the
original and a plausible wrong repair do not, and skipped or failed checks can
never relabel an item as verified or fixed. See run_evaluation_smoke.py.
"""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import run_evaluation_smoke as smoke
from run_evaluation_smoke import (
    CHECK_ADDRESS,
    CHECK_DEFAULT,
    EXPECTED_DEFECT_LEADS,
    ROUTER_VARIANTS,
    _fix_packet,
    _registry_with_packet,
    _verify,
    run_closure_smoke,
    run_detection_smoke,
    run_repair_smoke,
)


def _fake_run(*, returncode=0, write=True, result="verified", malformed=False,
              timeout=False, oserror=False, raw_text=None):
    """Simulate verify_fixes.py's process behavior for failure-mode tests."""
    def runner(command, **kwargs):
        if timeout:
            raise subprocess.TimeoutExpired(command, kwargs.get("timeout"))
        if oserror:
            raise OSError("simulated launch failure")
        output = Path(command[command.index("--output") + 1])
        if write:
            if raw_text is not None:
                output.write_text(raw_text, encoding="utf-8")
            elif malformed:
                output.write_text("not json", encoding="utf-8")
            else:
                output.write_text(json.dumps(
                    {"items": [{"id": "AS-02", "result": result,
                                "checks": [{"index": 0, "kind": "command", "result": "pass"}]}]}),
                    encoding="utf-8")
        return subprocess.CompletedProcess(command, returncode, "", "simulated")
    return runner


class DetectionSmoke(unittest.TestCase):
    def test_defect_raises_expected_leads_and_control_stays_clean(self):
        result = run_detection_smoke()
        # Workflow 1: the clear defects must surface (a positive disposition).
        self.assertEqual(result["missing_expected"], [], result)
        self.assertTrue(EXPECTED_DEFECT_LEADS.issubset(result["defect_leads"]))
        # Workflow 2: the adjacent legitimate control must not become a defect.
        self.assertEqual(result["clean_leads"], [], result)
        self.assertTrue(result["ok"])


class RepairSmoke(unittest.TestCase):
    def test_variants_and_false_closure_through_real_verifier(self):
        result = run_repair_smoke()
        self.assertTrue(result["infrastructure_ok"], result)
        self.assertEqual(result["variants"], result["expected"], result)
        # The wrong repair is plausible (address check passes) and is caught only
        # by the neighboring default-route invariant.
        self.assertTrue(result["neighbor_invariant_caught_wrong_repair"], result)
        # Skipped and manual checks can never report a verified pass.
        self.assertEqual(result["skipped_result"], "not_run", result)
        self.assertEqual(result["manual_result"], "manual", result)
        self.assertTrue(result["ok"])


class VerifyProcessFailures(unittest.TestCase):
    """The helper must never accept stale or absent data as a verified pass."""

    def setUp(self):
        self.registry, self.decisions = _registry_with_packet(_fix_packet(CHECK_ADDRESS, CHECK_DEFAULT))

    def _run(self, runner, variant="wrong_repair"):
        with mock.patch.object(smoke.subprocess, "run", side_effect=runner):
            return _verify(self.registry, self.decisions, ROUTER_VARIANTS[variant], execute=True)

    def test_injected_failure_after_a_real_success_is_not_verified(self):
        # The reproduced counterexample: a genuine success, then a failing
        # invocation must not read the prior receipt as its own evidence.
        good = _verify(self.registry, self.decisions, ROUTER_VARIANTS["valid_repair"], execute=True)
        self.assertEqual(good["result"], "verified")
        bad = self._run(_fake_run(returncode=2, write=False))
        self.assertFalse(bad["ok_infra"])
        self.assertNotEqual(bad["result"], "verified")

    def test_timeout_is_infrastructure_failure(self):
        row = self._run(_fake_run(timeout=True))
        self.assertFalse(row["ok_infra"])
        self.assertNotEqual(row["result"], "verified")

    def test_missing_receipt_is_infrastructure_failure(self):
        row = self._run(_fake_run(returncode=0, write=False))
        self.assertFalse(row["ok_infra"])

    def test_malformed_receipt_is_infrastructure_failure(self):
        row = self._run(_fake_run(returncode=0, malformed=True))
        self.assertFalse(row["ok_infra"])

    def test_exit_result_mismatch_is_infrastructure_failure(self):
        # A receipt claiming "verified" while the process reported a failure exit.
        row = self._run(_fake_run(returncode=1, result="verified"))
        self.assertFalse(row["ok_infra"])
        self.assertNotEqual(row["result"], "verified")

    def test_launch_failure_is_infrastructure_failure(self):
        # An OSError raising from the subprocess launch must be caught, not raised.
        row = self._run(_fake_run(oserror=True))
        self.assertFalse(row["ok_infra"])
        self.assertEqual(row["result"], "infrastructure_failure")

    def test_structurally_hostile_receipts_are_infrastructure_failures(self):
        # Each malformed receipt shape must resolve to a non-pass without raising
        # (notably an unhashable [] or {} result must not blow up membership).
        cases = {
            "root_list": "[]",
            "items_null": json.dumps({"items": [None]}),
            "result_list": json.dumps(
                {"items": [{"id": "AS-02", "result": [], "checks": []}]}),
            "unknown_status": json.dumps(
                {"items": [{"id": "AS-02", "result": "bogus", "checks": []}]}),
            "non_list_checks": json.dumps(
                {"items": [{"id": "AS-02", "result": "verified", "checks": {}}]}),
        }
        for name, raw in cases.items():
            with self.subTest(case=name):
                row = self._run(_fake_run(returncode=0, raw_text=raw))
                self.assertFalse(row["ok_infra"], row)
                self.assertEqual(row["result"], "infrastructure_failure", row)


class VerifyIsolatedDirectories(unittest.TestCase):
    """A supplied work parent yields a fresh child directory per invocation."""

    def test_two_invocations_use_distinct_fresh_children(self):
        registry, decisions = _registry_with_packet(_fix_packet(CHECK_ADDRESS, CHECK_DEFAULT))
        real_run = smoke.subprocess.run
        seen: list[str] = []

        def recording_run(command, **kwargs):
            # Wrap — never substitute — the real verifier, and record the --cwd it ran in.
            seen.append(command[command.index("--cwd") + 1])
            return real_run(command, **kwargs)

        with tempfile.TemporaryDirectory(prefix="scruffy-smoke-parent-") as parent:
            with mock.patch.object(smoke.subprocess, "run", side_effect=recording_run):
                first = _verify(registry, decisions, ROUTER_VARIANTS["valid_repair"],
                                work=Path(parent), execute=True)
                second = _verify(registry, decisions, ROUTER_VARIANTS["valid_repair"],
                                 work=Path(parent), execute=True)
            self.assertEqual(first["result"], "verified", first)
            self.assertEqual(second["result"], "verified", second)
            self.assertEqual(len(seen), 2)
            child_a, child_b = seen
            self.assertNotEqual(child_a, parent)
            self.assertNotEqual(child_b, parent)
            self.assertNotEqual(child_a, child_b)


class ClosureSmoke(unittest.TestCase):
    def test_skipped_or_failed_checks_cannot_close_a_fix(self):
        result = run_closure_smoke()
        self.assertTrue(result["valid_receipt_accepted"], result)
        self.assertTrue(result["skipped_rejected"], result)
        self.assertTrue(result["failed_rejected"], result)


if __name__ == "__main__":
    unittest.main()
