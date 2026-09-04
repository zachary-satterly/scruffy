#!/usr/bin/env python3
"""Regression tests for blind output scoring without authorship labels."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "evaluate_blind_outputs.py"


def write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def run(key: Path, discovery: Path, expected: int) -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--key", str(key), "--discovery", str(discovery)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != expected:
        raise AssertionError(f"expected {expected}, got {result.returncode}: {result.stdout}{result.stderr}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="anti-slop-evaluator-test-") as temporary:
        root = Path(temporary)
        key = root / "key.json"
        good = root / "good.json"
        bad = root / "bad.json"
        write(
            key,
            {
                "authorship_labels": "none",
                "sample_expectations": {
                    "A-01": {"expected_disposition": "candidate"},
                    "B-02": {"expected_disposition": "cleared"},
                },
            },
        )
        write(
            good,
            {
                "phase": "blind_discovery",
                "agent": "fixture-agent",
                "authorship_assessment": "not_performed",
                "candidates": [
                    {
                        "candidate_id": "CAND-001", "sample_id": "A-01",
                        "signals": ["repetition", "detail_sparsity"], "evidence": ["quoted"],
                        "consequence": "unclear action", "counterexample_tested": "intentional parallelism",
                        "confidence": "moderate",
                    }
                ],
                "cleared_suspicions": [{"sample_id": "B-02"}],
                "checks_not_run": [],
            },
        )
        run(key, good, 0)
        original = json.loads(good.read_text(encoding="utf-8"))
        for signals in ([], ["one"], ["same", "same"], [{}, {}], [[], []], ["", "two"], [None, "two"]):
            malformed = json.loads(json.dumps(original))
            malformed["candidates"][0]["signals"] = signals
            write(bad, malformed)
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--key", str(key), "--discovery", str(good), "--discovery", str(bad)],
                capture_output=True, text=True,
            )
            assert result.returncode == 1, result.stderr
            report = json.loads(result.stdout)
            assert report["results"][0]["passed"] and not report["results"][1]["passed"]
            assert report["results"][1]["integrity_problems"]
            assert "Traceback" not in result.stderr
        for document in ([], None):
            bad.write_text(json.dumps(document))
            run(key, bad, 1)
        bad.write_text("{broken")
        run(key, bad, 1)
        for expectation in (None, [], {"expected_disposition": []}):
            malformed_key = root / "invalid-key.json"
            write(malformed_key, {"sample_expectations": {"A-01": expectation}})
            run(malformed_key, good, 2)
        contaminated = json.loads(good.read_text(encoding="utf-8"))
        contaminated["authorship_assessment"] = "probably_ai"
        contaminated["candidates"][0]["candidate_id"] = "COPY-001"
        write(bad, contaminated)
        run(key, bad, 1)
    print("PASS: blind evaluator accepts guarded output and rejects authorship/stable-ID contamination")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        sys.exit(1)
