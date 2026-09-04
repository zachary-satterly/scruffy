#!/usr/bin/env python3
"""Evaluate frozen blind-discovery JSON against a hidden quality expectation key."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def load_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def dispositions(discovery: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
    coverage: dict[str, str] = {}
    problems: list[str] = []
    for field, disposition in (
        ("candidates", "candidate"),
        ("cleared_suspicions", "cleared"),
        ("checks_not_run", "not_run"),
    ):
        entries = discovery.get(field)
        if not isinstance(entries, list):
            problems.append(f"{field} must be a list")
            continue
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict) or not isinstance(entry.get("sample_id"), str) or not entry["sample_id"].strip():
                problems.append(f"{field}[{index}] needs sample_id")
                continue
            sample_id = entry["sample_id"]
            if sample_id in coverage:
                problems.append(f"sample {sample_id} appears more than once")
            coverage[sample_id] = disposition
            if field == "candidates":
                candidate_id = entry.get("candidate_id")
                if not isinstance(candidate_id, str) or not re.fullmatch(r"CAND-\d{3}", candidate_id):
                    problems.append(f"candidate for {sample_id} lacks a temporary CAND- ID")
                signals = entry.get("signals")
                if (not isinstance(signals, list)
                        or not all(isinstance(signal, str) and signal.strip() for signal in signals)
                        or len({signal.strip() for signal in signals}) < 2):
                    problems.append(f"candidate for {sample_id} needs two independent signals")
                evidence = entry.get("evidence")
                if not isinstance(evidence, list) or not evidence or not all(isinstance(value, str) and value.strip() for value in evidence):
                    problems.append(f"candidate for {sample_id} needs nonempty quoted evidence strings")
                for required in ("consequence", "counterexample_tested", "confidence"):
                    if not isinstance(entry.get(required), str) or not entry[required].strip():
                        problems.append(f"candidate for {sample_id} lacks {required}")
    return coverage, problems


def validate_key(key: dict[str, Any]) -> dict[str, Any]:
    expectations = key.get("sample_expectations")
    if not isinstance(expectations, dict) or not expectations:
        raise ValueError("evaluation key needs nonempty sample_expectations")
    for sample_id, expectation in expectations.items():
        if (not isinstance(sample_id, str) or not sample_id.strip()
                or not isinstance(expectation, dict)
                or expectation.get("expected_disposition") not in ("candidate", "cleared", "not_run")):
            raise ValueError("evaluation key has an invalid sample expectation")
    return expectations


def evaluate_one(path: Path, key: dict[str, Any]) -> dict[str, Any]:
    expectations = validate_key(key)
    try:
        discovery = load_object(path)
    except (OSError, ValueError) as error:
        return {
            "path": str(path.resolve()), "agent": None, "passed": False,
            "matched_samples": [], "mismatches": [],
            "integrity_problems": [str(error)], "dispositions": {},
        }
    coverage, problems = dispositions(discovery)
    if discovery.get("phase") != "blind_discovery":
        problems.append("phase must be blind_discovery")
    if discovery.get("authorship_assessment") != "not_performed":
        problems.append("authorship assessment was performed or not explicitly disabled")
    expected_ids = set(expectations)
    actual_ids = set(coverage)
    for sample_id in sorted(expected_ids - actual_ids):
        problems.append(f"missing sample {sample_id}")
    for sample_id in sorted(actual_ids - expected_ids):
        problems.append(f"unexpected sample {sample_id}")

    matches: list[str] = []
    mismatches: list[dict[str, str]] = []
    for sample_id, expectation in expectations.items():
        expected = expectation.get("expected_disposition")
        actual = coverage.get(sample_id, "missing")
        if expected == actual:
            matches.append(sample_id)
        else:
            mismatches.append({"sample_id": sample_id, "expected": str(expected), "actual": actual})

    return {
        "path": str(path.resolve()),
        "agent": discovery.get("agent"),
        "passed": not problems and not mismatches,
        "matched_samples": matches,
        "mismatches": mismatches,
        "integrity_problems": problems,
        "dispositions": coverage,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key", type=Path, required=True)
    parser.add_argument("--discovery", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        key = load_object(args.key)
        validate_key(key)
        if args.output and args.output.resolve() in {path.resolve() for path in [args.key, *args.discovery]}:
            raise ValueError("--output must not overwrite an input artifact")
        results = [evaluate_one(path, key) for path in args.discovery]
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 2

    comparison: dict[str, Any] | None = None
    if len(results) > 1:
        sample_ids = sorted(key["sample_expectations"])
        agreement = [
            sample_id
            for sample_id in sample_ids
            if len({result["dispositions"].get(sample_id) for result in results}) == 1
        ]
        comparison = {
            "agents": [result["agent"] for result in results],
            "agreed_samples": agreement,
            "agreement_rate": round(len(agreement) / len(sample_ids), 3) if sample_ids else 1.0,
        }
    payload = {
        "schema_version": "1.0",
        "authorship_labels_used": False,
        "results": results,
        "comparison": comparison,
        "passed": all(result["passed"] for result in results),
    }
    rendered = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
