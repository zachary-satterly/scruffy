#!/usr/bin/env python3
"""Outcomes ledger: did the audit turn into shipped, verified fixes?

Process metrics (routing agreement, schema validity, prose lint) say whether
Scruffy followed its own method. They say nothing about value. Value is:

  raised     items the audit put in front of a human
  approved   items the human said yes to
  verified   approved items whose executable acceptance checks passed
  reopened   items that came back after being called fixed

Feed it one or more revisions (registry + decisions + optional verification)
and it emits `outcomes.json` plus a table, per category and per kind. A rule
or category whose leads are never approved is a candidate for retirement; a
category with high approvals and no verifications is where the fix loop is
broken.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

ACTIVE = {"open", "needs-verification"}


def load(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"FAIL: {path} must contain an object")
    return data


def decision_map(decisions: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in decisions.get("decisions", []) or []:
        item_id = row.get("item_id") or row.get("finding_id")
        if item_id:
            out[str(item_id)] = str(row.get("decision") or "pending")
    return out


def verification_map(verification: dict[str, Any]) -> dict[str, str]:
    return {str(row.get("id")): str(row.get("result") or "not_run") for row in verification.get("items", []) or []}


def bucket_for(item: dict[str, Any]) -> tuple[str, str]:
    return str(item.get("kind") or "finding"), str(item.get("category") or "unknown")


def rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 3) if denominator else None


def summarize(revisions: list[tuple[dict[str, Any], dict[str, str], dict[str, str]]]) -> dict[str, Any]:
    per_key: dict[tuple[str, str], dict[str, int]] = defaultdict(
        lambda: {"raised": 0, "approved": 0, "deferred": 0, "rejected": 0, "pending": 0, "verified": 0, "failed": 0, "fixed": 0, "reopened": 0, "cleared": 0}
    )
    # Later revisions override earlier ones per item id, so an item raised in r1
    # and carried into r2 counts once, in its latest state.
    latest: dict[str, tuple[str, dict[str, Any], str, str]] = {}
    for registry, decisions, verification in revisions:
        revision_id = str(registry.get("revision_id") or "")
        for item in registry.get("items", []):
            latest[str(item["id"])] = (
                revision_id,
                item,
                decisions.get(str(item["id"]), "pending"),
                verification.get(str(item["id"]), ""),
            )
    rows: list[dict[str, Any]] = []
    for revision_id, item, decision, verdict in latest.values():
        kind, category = bucket_for(item)
        if kind == "strength":
            continue
        counts = per_key[(kind, category)]
        status = str(item.get("status") or "")
        disposition = str(item.get("revision_disposition") or "")
        if status in ACTIVE:
            counts["raised"] += 1
            counts[{"approve": "approved", "defer": "deferred", "reject": "rejected"}.get(decision, "pending")] += 1
            if decision == "approve":
                if verdict == "verified":
                    counts["verified"] += 1
                elif verdict == "failed":
                    counts["failed"] += 1
        if status == "fixed":
            counts["fixed"] += 1
        if status == "cleared":
            counts["cleared"] += 1
        if disposition == "reopened":
            counts["reopened"] += 1
        rows.append(
            {
                "revision_id": revision_id,
                "id": item["id"],
                "kind": kind,
                "category": category,
                "status": status,
                "disposition": disposition,
                "decision": decision if status in ACTIVE else None,
                "verification": verdict or None,
                "rule_refs": list(item.get("principle_refs") or []) + list(item.get("detector_refs") or []),
            }
        )

    buckets = []
    total = {"raised": 0, "approved": 0, "verified": 0, "failed": 0, "fixed": 0, "reopened": 0, "cleared": 0, "deferred": 0, "rejected": 0, "pending": 0}
    for (kind, category), counts in sorted(per_key.items()):
        for key in total:
            total[key] += counts[key]
        buckets.append(
            {
                "kind": kind,
                "category": category,
                **counts,
                "approve_rate": rate(counts["approved"], counts["raised"]),
                "verify_rate": rate(counts["verified"], counts["approved"]),
                "reopen_rate": rate(counts["reopened"], counts["fixed"] + counts["reopened"]),
            }
        )
    total_row = {
        **total,
        "approve_rate": rate(total["approved"], total["raised"]),
        "verify_rate": rate(total["verified"], total["approved"]),
        "reopen_rate": rate(total["reopened"], total["fixed"] + total["reopened"]),
    }
    rule_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"raised": 0, "approved": 0})
    for row in rows:
        if row["decision"] is None:
            continue
        for ref in row["rule_refs"]:
            rule_counts[str(ref)]["raised"] += 1
            if row["decision"] == "approve":
                rule_counts[str(ref)]["approved"] += 1
    never_approved = sorted(ref for ref, c in rule_counts.items() if c["raised"] >= 3 and c["approved"] == 0)
    return {
        "schema_version": "1.0",
        "revisions": [str(r.get("revision_id") or "") for r, _, _ in revisions],
        "total": total_row,
        "by_category": buckets,
        "rules": {ref: c for ref, c in sorted(rule_counts.items())},
        "retirement_candidates": never_approved,
        "items": rows,
    }


def table(report: dict[str, Any]) -> str:
    def fmt(value: float | None) -> str:
        return "—" if value is None else f"{value:.0%}"

    lines = ["kind         category                   raised approved verified fixed reopened  approve  verify  reopen"]
    for b in report["by_category"]:
        lines.append(
            f"{b['kind']:<12} {b['category']:<26} {b['raised']:>6} {b['approved']:>8} {b['verified']:>8} {b['fixed']:>5} {b['reopened']:>8}  "
            f"{fmt(b['approve_rate']):>7} {fmt(b['verify_rate']):>7} {fmt(b['reopen_rate']):>7}"
        )
    t = report["total"]
    lines.append(
        f"{'TOTAL':<12} {'':<26} {t['raised']:>6} {t['approved']:>8} {t['verified']:>8} {t['fixed']:>5} {t['reopened']:>8}  "
        f"{fmt(t['approve_rate']):>7} {fmt(t['verify_rate']):>7} {fmt(t['reopen_rate']):>7}"
    )
    if report["retirement_candidates"]:
        lines.append("rules raised 3+ times and never approved: " + ", ".join(report["retirement_candidates"]))
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "revision",
        nargs="+",
        help="findings.json[:decisions.json[:verification.json]] per revision, oldest first",
    )
    parser.add_argument("--output", type=Path, default=Path("outcomes.json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    revisions = []
    for spec in args.revision:
        parts = spec.split(":")
        registry = load(Path(parts[0]))
        decisions = decision_map(load(Path(parts[1]))) if len(parts) > 1 and parts[1] else {}
        verification = verification_map(load(Path(parts[2]))) if len(parts) > 2 and parts[2] else {}
        revisions.append((registry, decisions, verification))
    report = summarize(revisions)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(table(report))
    print(f"PASS: outcomes written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
