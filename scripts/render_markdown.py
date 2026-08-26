#!/usr/bin/env python3
"""Render a complete Scruffy Markdown report from schema-v2 source data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from report_contract import (
    CAPABILITY_LABELS,
    CAPABILITY_STATUS_LABELS,
    PRODUCT_BASIS_LABELS,
    QUESTION_LABELS,
    TASK_STATUS_LABELS,
    assumption_rows,
    disposition_label,
    evidence_by_id,
    facet_labels,
    humanize_text,
    item_label_map,
    plain_category_label,
    public_evidence_summary,
    referral_rows,
    routing_rows,
    score_display,
    severity_label,
    status_label,
)


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"FAIL: {path} must contain an object")
    return data


def clean(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def bullets(values: list[Any], empty: str = "None recorded.") -> str:
    return "\n".join(f"- {clean(value)}" for value in values) if values else empty


def table(headers: list[str], rows: list[list[Any]]) -> str:
    output = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    output.extend("| " + " | ".join(clean(value) for value in row) + " |" for row in rows)
    return "\n".join(output)


def render_item(
    item: dict[str, Any],
    decision: dict[str, Any] | None,
    context: dict[str, Any],
    item_labels: dict[str, str],
) -> str:
    evidence_assets = evidence_by_id(context)
    destination = f" → {item_labels.get(item['destination_id'], 'another review item')}" if item.get("destination_id") else ""
    dependencies = ", ".join(item_labels.get(value, "another review item") for value in item.get("depends_on", [])) or "No dependencies"
    decision_text = ""
    if item["kind"] in {"finding", "enhancement"}:
        row = decision or {}
        decision_label = {
            "pending": "Not decided",
            "approve": "Approve",
            "defer": "Decide later",
            "reject": "Reject",
        }.get(row.get("decision", "pending"), str(row.get("decision", "pending")).title())
        decision_text = (
            f"\n\n**Decision:** {clean(decision_label)}  "
            f"\n**Decision note:** {clean(row.get('note', '')) or 'None.'}"
        )
    facets = ", ".join(facet_labels(item.get("facets", []))) or "None"
    receipts = public_evidence_summary(item.get("evidence_refs"), context, item_labels=item_labels) or "No supporting records listed"
    editorial = item.get("editorial_review")
    editorial_text = ""
    if isinstance(editorial, dict):
        families = ", ".join(str(value).replace("_", " ") for value in editorial.get("independent_signal_families", [])) or "not applicable"
        editorial_text = (
            f"\n\n**How the copy was reviewed:** {clean(str(editorial.get('review_type', 'review')).replace('_', ' ').title())} · "
            f"{clean(str(editorial.get('sample_adequacy', 'not recorded')).replace('_', ' ').title())} sample · "
            f"signals checked: {clean(families)}. This checks writing quality only; it does not guess who or what wrote the copy."
        )
    return f"""<!-- anti-slop-item:{item['id']} -->
### {clean(item_labels.get(item['id'], 'Review item'))} · {clean(humanize_text(item['title'], item_labels=item_labels, evidence_assets=evidence_assets))}

> {clean(item.get('plain') or item['title'])}

**Area:** {clean(plain_category_label(item['category']))} · **Related themes:** {clean(facets)}

**Impact or priority:** {clean(severity_label(item))} · **Confidence:** {clean(str(item['confidence']).title())}

**Status:** {clean(status_label(item['status']))} · **Review history:** {clean(disposition_label(item['revision_disposition']))}{destination}

{clean(humanize_text(item['observation'], item_labels=item_labels, evidence_assets=evidence_assets))}

**User impact:** {clean(humanize_text(item['user_impact'], item_labels=item_labels, evidence_assets=evidence_assets))}

**What supports this**

{bullets([humanize_text(value, item_labels=item_labels, evidence_assets=evidence_assets) for value in item.get('evidence', [])])}

**Supporting records:** {clean(receipts)}{editorial_text}

**Cause:** {clean(humanize_text(item['cause'], item_labels=item_labels, evidence_assets=evidence_assets))}

**Recommended next step:** {clean(humanize_text(item['recommendation'], item_labels=item_labels, evidence_assets=evidence_assets))}

**How to verify it**

{bullets([humanize_text(value, item_labels=item_labels, evidence_assets=evidence_assets) for value in item.get('acceptance_checks', [])], 'No additional verification required for this strength.')}

**Dependencies:** {clean(dependencies)}  
**Review-history reason:** {clean(humanize_text(item.get('disposition_reason') or 'New in this review.', item_labels=item_labels, evidence_assets=evidence_assets))}{decision_text}
"""


def render(registry: dict[str, Any], context: dict[str, Any], decision_doc: dict[str, Any]) -> str:
    items = registry["items"]
    by_id = {item["id"]: item for item in items}
    item_labels = item_label_map(items)
    evidence_assets = evidence_by_id(context)
    decisions = {row["item_id"]: row for row in decision_doc.get("decisions", [])}
    presentation = registry["presentation"]
    prioritized_findings = [by_id[item_id] for item_id in presentation["prioritized_finding_ids"]]
    prioritized_finding_ids = set(presentation["prioritized_finding_ids"])
    additional_findings = [
        item for item in items
        if item["kind"] == "finding"
        and item["status"] in {"open", "needs-verification"}
        and item["id"] not in prioritized_finding_ids
    ]
    prioritized_enhancements = [by_id[item_id] for item_id in presentation["prioritized_enhancement_ids"]]
    prioritized_enhancement_ids = set(presentation["prioritized_enhancement_ids"])
    additional_enhancements = [
        item for item in items
        if item["kind"] == "enhancement"
        and item["status"] in {"open", "needs-verification"}
        and item["id"] not in prioritized_enhancement_ids
    ]
    strengths = [by_id[item_id] for item_id in presentation["strength_ids"]]
    resolved = [item for item in items if item["status"] in {"fixed", "cleared", "merged", "superseded"}]

    def item_group(values: list[dict[str, Any]], empty: str) -> str:
        return "\n\n".join(render_item(item, decisions.get(item["id"]), context, item_labels) for item in values) if values else empty

    outcome = context.get("outcome", {})
    product_table_rows = [
        [
            QUESTION_LABELS.get(row.get("key"), row.get("question", "")),
            humanize_text(row.get("answer", ""), item_labels=item_labels, evidence_assets=evidence_assets),
            PRODUCT_BASIS_LABELS.get(row.get("basis"), str(row.get("basis", "")).title()),
        ]
        for row in context.get("product_frame", [])
    ]
    task_table_rows = [
        [
            f"Journey {index}",
            humanize_text(row.get("goal", ""), item_labels=item_labels, evidence_assets=evidence_assets),
            humanize_text(row.get("result", ""), item_labels=item_labels, evidence_assets=evidence_assets),
            TASK_STATUS_LABELS.get(row.get("status", ""), status_label(row.get("status", ""))),
            humanize_text(row.get("evidence", ""), item_labels=item_labels, evidence_assets=evidence_assets)
            or public_evidence_summary(row.get("evidence_refs"), context, item_labels=item_labels),
        ]
        for index, row in enumerate(context.get("tasks", []), start=1)
    ]
    capability_table_rows = [
        [
            CAPABILITY_LABELS.get(row.get("key"), str(row.get("key", "")).replace("_", " ").title()),
            CAPABILITY_STATUS_LABELS.get(row.get("status"), status_label(row.get("status", ""))),
            humanize_text(row.get("scope", ""), item_labels=item_labels, evidence_assets=evidence_assets),
        ]
        for row in context.get("capabilities", [])
    ]
    route_table_rows = [
        [humanize_text(value, item_labels=item_labels, evidence_assets=evidence_assets) for value in row]
        for row in routing_rows(context)
    ]
    assumption_table_rows = [
        [humanize_text(value, item_labels=item_labels, evidence_assets=evidence_assets) for value in row]
        for row in assumption_rows(context)
    ]
    referral_table_rows = [
        [humanize_text(value, item_labels=item_labels, evidence_assets=evidence_assets) for value in row]
        for row in referral_rows(context)
    ]
    score_table_rows = [
        [
            plain_category_label(row.get("category", "")),
            score_display(row.get("score", "")),
            humanize_text(row.get("evidence", ""), item_labels=item_labels, evidence_assets=evidence_assets),
        ]
        for row in sorted(
            context.get("scores", []),
            key=lambda score: (0, -score.get("score")) if isinstance(score.get("score"), int) else (1, 0),
        )
    ]
    reconciliation_rows = [
        [
            item_labels.get(item["id"], "Review item"),
            status_label(item["status"]),
            disposition_label(item["revision_disposition"]),
            item_labels.get(item.get("destination_id"), "-") if item.get("destination_id") else "-",
            humanize_text(item.get("disposition_reason") or "New in this review.", item_labels=item_labels, evidence_assets=evidence_assets),
        ]
        for item in items
    ]
    work_orders = []
    for index, order in enumerate(context.get("work_orders", []), start=1):
        related_items = ", ".join(item_labels.get(item_id, "Review item") for item_id in order.get("item_ids", [])) or "None"
        work_orders.append(
            f"### Work package {index} · {clean(humanize_text(order.get('title', ''), item_labels=item_labels, evidence_assets=evidence_assets))}\n\n"
            f"{clean(humanize_text(order.get('summary', ''), item_labels=item_labels, evidence_assets=evidence_assets))}\n\n"
            f"**Related items:** {clean(related_items)}  \n"
            f"**How to verify:** {clean(humanize_text(order.get('verification', ''), item_labels=item_labels, evidence_assets=evidence_assets))}\n\n"
            f"{bullets([humanize_text(value, item_labels=item_labels, evidence_assets=evidence_assets) for value in order.get('acceptance_checks', [])], 'No verification steps recorded.')}"
        )

    humanized_checks = [
        humanize_text(
            f"{row.get('check', '')} — {row.get('reason', '')} Impact: {row.get('impact', '')}" if isinstance(row, dict) else row,
            item_labels=item_labels,
            evidence_assets=evidence_assets,
        )
        for row in context.get("checks_not_run", [])
    ]
    title = clean(humanize_text(context.get("title", "Product review"), item_labels=item_labels, evidence_assets=evidence_assets))
    return f"""# {title}

Target: {clean(registry.get('target', ''))}  
<!-- anti-slop-meta:audit={registry['audit_id']};revision={registry['revision_id']};baseline={registry.get('baseline_revision_id') or 'none'} -->

<!-- anti-slop-section:outcome -->
## Outcome and evidence boundary

**{clean(humanize_text(outcome.get('label', 'Insufficient evidence'), item_labels=item_labels, evidence_assets=evidence_assets))}** — {clean(humanize_text(outcome.get('summary', ''), item_labels=item_labels, evidence_assets=evidence_assets))}

Confidence: {clean(str(outcome.get('confidence', 'unknown')).title())}

<!-- anti-slop-section:product-frame -->
## What this product is meant to do

{table(['Question', 'Answer', 'How we know'], product_table_rows)}

<!-- anti-slop-section:task-ledger -->
## Representative tasks

{table(['Journey', 'Goal', 'Result', 'Status', 'Supporting records'], task_table_rows)}

<!-- anti-slop-section:capability-ledger -->
## What we could and could not test

{table(['Test area', 'Status', 'What was covered'], capability_table_rows)}

<!-- anti-slop-section:routing -->
## Review routing

{table(['Review area', 'Decision', 'Reason'], route_table_rows) if route_table_rows else 'No routing ledger is present in this legacy context.'}

<!-- anti-slop-section:assumptions -->
## Assumptions that could change the result

{table(['Assumption', 'Status', 'Basis', 'Risk if wrong', 'Evidence needed', 'Decision affected'], assumption_table_rows) if assumption_table_rows else 'No consequential assumptions recorded.'}

<!-- anti-slop-section:referrals -->
## Specialist referrals

{table(['Review area', 'Question', 'Status', 'Why it was referred', 'Claim boundary', 'Supporting records', 'Verified specialist result'], referral_table_rows) if referral_table_rows else 'No specialist referrals recorded.'}

<!-- anti-slop-section:score -->
## Quality scores and result

{table(['Area', 'Result', 'Why'], score_table_rows)}

<!-- anti-slop-section:findings -->
## Prioritized findings

{item_group(prioritized_findings, 'No prioritized findings.')}

## Additional active findings

{item_group(additional_findings, 'No additional active findings.')}

<!-- anti-slop-section:enhancements -->
## Optional enhancements

{item_group(prioritized_enhancements, 'No prioritized optional enhancements. Corrective changes remain listed under Prioritized findings and Recommended work sequence.')}

## Other optional enhancements

{item_group(additional_enhancements, 'No additional enhancements.')}

<!-- anti-slop-section:strengths -->
## Strengths to preserve

{item_group(strengths, 'No strengths recorded.')}

<!-- anti-slop-section:resolved -->
## Closed concerns

{item_group(resolved, 'No resolved items.')}

<!-- anti-slop-section:reconciliation -->
## Review history

{table(['Item', 'Status', 'What changed', 'Replaced by', 'Reason'], reconciliation_rows)}

<!-- anti-slop-section:work-orders -->
## Recommended work sequence

{chr(10).join(work_orders) if work_orders else 'No work orders recorded.'}

<!-- anti-slop-section:checks-not-run -->
## What was not tested

{bullets(humanized_checks, 'Everything in scope was tested.')}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("registry", type=Path)
    parser.add_argument("context", type=Path)
    parser.add_argument("decisions", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    registry = load(args.registry)
    context = load(args.context)
    decisions = load(args.decisions)
    rendered = render(registry, context, decisions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"PASS: rendered {len(registry.get('items', []))} registry items to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
