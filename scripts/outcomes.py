#!/usr/bin/env python3
"""Outcomes ledger: did the audit turn into shipped, verified fixes?

Process metrics (routing agreement, schema validity, prose lint) say whether
Scruffy followed its own method. They say nothing about value. Value is:

  raised     items the audit put in front of a human
  approved   items the human said yes to
  verified   approved items whose executable acceptance checks passed
  reopened   items that came back after being called fixed

Approved and verified count each item once across the supplied history; fixed
and cleared describe its latest state. Resolved is the union of items observed
fixed or reopened, so reopening and then fixing an item does not inflate the
reopen-rate denominator. Item identity is scoped to its audit.

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

from validate_audit import validate_registry, validate_decisions, validate_verification_receipt


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


def verification_map(verification: dict[str, Any], registry: dict[str, Any], decisions: dict[str, Any] | None) -> dict[str, str]:
    rows = validate_verification_receipt(verification, registry, decisions)
    return {item_id: str(row["result"]) for item_id, row in rows.items()}


def bucket_for(item: dict[str, Any]) -> tuple[str, str]:
    return str(item.get("kind") or "finding"), str(item.get("category") or "unknown")


def rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 3) if denominator else None


def summarize(revisions: list[tuple[dict[str, Any], dict[str, str], dict[str, str]]]) -> dict[str, Any]:
    per_key: dict[tuple[str, str], dict[str, int]] = defaultdict(
        lambda: {"raised": 0, "approved": 0, "deferred": 0, "rejected": 0, "pending": 0, "verified": 0, "failed": 0, "fixed": 0, "reopened": 0, "cleared": 0, "resolved": 0}
    )
    # Keep the latest displayed state, while retaining supported achievements.
    # Item IDs are unique within an audit, not across unrelated audited products.
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    seen_revisions: set[tuple[str, str]] = set()
    targets: dict[str, str] = {}
    identity_owners: dict[tuple[str, str], str] = {}
    positions = {(registry.get("audit_id"), registry.get("revision_id")): index for index, (registry, _, _) in enumerate(revisions)}
    for index, (registry, _, _) in enumerate(revisions):
        baseline = (registry.get("audit_id"), registry.get("baseline_revision_id"))
        if baseline in positions and positions[baseline] >= index:
            raise ValueError("revisions must be supplied oldest first within each audit")
    for registry, decisions, verification in revisions:
        validate_registry(registry)
        audit_id, revision_id = registry["audit_id"], registry["revision_id"]
        revision_key = (audit_id, revision_id)
        if revision_key in seen_revisions:
            raise ValueError(f"duplicate audit/revision input: {audit_id}/{revision_id}")
        seen_revisions.add(revision_key)
        if audit_id in targets and targets[audit_id] != registry.get("target"):
            raise ValueError(f"audit {audit_id} changed target")
        targets[audit_id] = registry.get("target")
        for item in registry["items"]:
            key = (audit_id, item["id"])
            identity = (audit_id, item["identity_key"])
            if identity in identity_owners and identity_owners[identity] != item["id"]:
                raise ValueError(f"{audit_id}/{item['id']} reused another item's identity")
            identity_owners[identity] = item["id"]
            previous = latest.get(key)
            if previous and previous["item"]["identity_key"] != item["identity_key"]:
                raise ValueError(f"{audit_id}/{item['id']} reused an item identity")
            decision = decisions.get(item["id"], previous["decision"] if previous else "pending")
            verdict = verification.get(item["id"], "")
            references: set[str] = set()
            for field in ("principle_refs", "detector_refs"):
                values = item.get(field) or []
                if not isinstance(values, list) or not all(isinstance(value, str) and value.strip() for value in values):
                    raise ValueError(f"{audit_id}/{item['id']}.{field} must be an array of nonempty strings")
                references.update(values)
            latest[key] = {
                "audit_id": audit_id, "revision_id": revision_id, "item": item,
                "decision": decision,
                "approved": decision == "approve" or bool(previous and previous["approved"]),
                "verified": (decision == "approve" and verdict == "verified") or bool(previous and previous["verified"]),
                "verification": verdict or (previous["verification"] if previous else ""),
                "references": references | (previous["references"] if previous else set()),
                "reopened": item.get("revision_disposition") == "reopened" or bool(previous and previous["reopened"]),
                "resolved": item.get("status") == "fixed" or item.get("revision_disposition") == "reopened" or bool(previous and previous["resolved"]),
            }
    rows: list[dict[str, Any]] = []
    for state in latest.values():
        item = state["item"]
        kind, category = bucket_for(item)
        if kind == "strength":
            continue
        counts = per_key[(kind, category)]
        status = item["status"]
        counts["raised"] += 1
        if state["approved"]:
            counts["approved"] += 1
        else:
            counts[{"defer": "deferred", "reject": "rejected"}.get(state["decision"], "pending")] += 1
        counts["verified"] += int(state["verified"])
        counts["failed"] += int(state["verification"] == "failed")
        counts["fixed"] += int(status == "fixed")
        counts["cleared"] += int(status == "cleared")
        counts["reopened"] += int(state["reopened"])
        counts["resolved"] += int(state["resolved"])
        rows.append({
            "audit_id": state["audit_id"], "revision_id": state["revision_id"],
            "id": item["id"], "kind": kind, "category": category, "status": status,
            "disposition": item.get("revision_disposition", ""),
            "decision": state["decision"], "approved": state["approved"],
            "verified": state["verified"], "verification": state["verification"] or None,
            "rule_refs": sorted(state["references"]),
        })

    buckets = []
    total = {"raised": 0, "approved": 0, "verified": 0, "failed": 0, "fixed": 0, "reopened": 0, "cleared": 0, "deferred": 0, "rejected": 0, "pending": 0, "resolved": 0}
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
                "reopen_rate": rate(counts["reopened"], counts["resolved"]),
            }
        )
    total_row = {
        **total,
        "approve_rate": rate(total["approved"], total["raised"]),
        "verify_rate": rate(total["verified"], total["approved"]),
        "reopen_rate": rate(total["reopened"], total["resolved"]),
    }
    rule_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"raised": 0, "approved": 0, "rejected": 0})
    for row in rows:
        for ref in row["rule_refs"]:
            rule_counts[str(ref)]["raised"] += 1
            if row["approved"]:
                rule_counts[str(ref)]["approved"] += 1
            elif row["decision"] == "reject":
                rule_counts[str(ref)]["rejected"] += 1
    never_approved = sorted(ref for ref, c in rule_counts.items() if c["rejected"] >= 3 and c["approved"] == 0)
    return {
        "schema_version": "1.0",
        "revisions": [str(r.get("revision_id") or "") for r, _, _ in revisions],
        "audit_revisions": [{"audit_id": r["audit_id"], "revision_id": r["revision_id"]} for r, _, _ in revisions],
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
        lines.append("rules explicitly rejected 3+ times and never approved: " + ", ".join(report["retirement_candidates"]))
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
    input_paths: list[Path] = []
    for spec in args.revision:
        parts = spec.split(":")
        if len(parts) > 3 or not parts[0]:
            raise ValueError("each revision must be findings[:decisions[:verification]]")
        paths = [Path(part) if part else None for part in parts]
        input_paths.extend(path.resolve() for path in paths if path is not None)
        registry = load(paths[0])
        validate_registry(registry)
        decision_document = load(paths[1]) if len(paths) > 1 and paths[1] else None
        if decision_document is not None:
            validate_decisions(decision_document, registry)
        decisions = decision_map(decision_document) if decision_document is not None else {}
        verification = {}
        if len(paths) > 2 and paths[2]:
            if decision_document is None:
                raise ValueError("verification requires matching decisions to establish approval")
            verification = verification_map(load(paths[2]), registry, decision_document)
        revisions.append((registry, decisions, verification))
    if args.output.resolve() in input_paths:
        raise ValueError("--output must not overwrite an input artifact")
    report = summarize(revisions)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(table(report))
    print(f"PASS: outcomes written to {args.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        raise SystemExit(f"FAIL: {error}")
