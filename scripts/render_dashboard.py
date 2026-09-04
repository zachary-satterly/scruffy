#!/usr/bin/env python3
"""Render a complete, self-contained Scruffy decision dashboard."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

from evidence_assets import embed_raster

from report_contract import (
    evidence_by_id,
    evidence_public_label,
    facet_labels,
    humanize_text,
    item_label_map,
    plain_category_label,
    public_evidence_summary,
    severity_label,
    status_label,
    disposition_label,
    CAPABILITY_STATUS_LABELS,
    capability_rows,
    score_rows,
    score_number,
    PRODUCT_BASIS_LABELS,
    QUESTION_LABELS,
    TASK_STATUS_LABELS,
    assumption_rows,
    referral_rows,
    routing_rows,
)


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"FAIL: {path} must contain an object")
    return data


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def embed_asset(src: str, base: Path) -> str:
    return embed_raster(src, base)


def visual_evidence_map(context: dict[str, Any]) -> dict[tuple[str, str | None], dict[str, Any]]:
    rows = context.get("visual_evidence", [])
    if not isinstance(rows, list):
        return {}
    return {
        (str(row.get("evidence_id")), row.get("item_id")): row
        for row in rows
        if isinstance(row, dict) and row.get("evidence_id")
    }


def screenshot_figure(
    asset: dict[str, Any],
    base: Path,
    *,
    item_id: str | None = None,
    visual_context: dict[str, Any] | None = None,
    item_labels: dict[str, str] | None = None,
    evidence_assets: dict[str, dict[str, Any]] | None = None,
) -> str:
    source = embed_asset(str(asset.get("src") or asset.get("locator") or ""), base)
    if not source:
        return ""
    evidence_id = str(asset.get("id") or "")
    description = humanize_text(
        asset.get("caption") or asset.get("description") or "Evidence image",
        item_labels=item_labels,
        evidence_assets=evidence_assets,
    )
    alt = str(asset.get("alt") or asset.get("description") or "Evidence image")
    if visual_context:
        alt = humanize_text(
            f"{visual_context.get('state', '')} Look here: {visual_context.get('look_at', '')}".strip(),
            item_labels=item_labels,
            evidence_assets=evidence_assets,
        )
    evidence_attr = f' data-evidence-id="{esc(evidence_id)}"' if evidence_id else ""
    item_attr = f' data-evidence-for="{esc(item_id)}"' if item_id else ""
    caption_attr = f' data-evidence-caption="{esc(evidence_id)}"' if evidence_id else ""
    caption_label = f'<strong>{esc(evidence_public_label(asset))}</strong> — '
    annotations = ""
    visual_caption = ""
    if visual_context:
        annotation = visual_context.get("annotation") if isinstance(visual_context.get("annotation"), dict) else {}
        regions = annotation.get("regions") if isinstance(annotation.get("regions"), list) else []
        rendered_regions: list[str] = []
        for index, region in enumerate(regions):
            if not isinstance(region, dict):
                continue
            style = (
                f"left:{float(region.get('x', 0)):g}%;top:{float(region.get('y', 0)):g}%;"
                f"width:{float(region.get('width', 0)):g}%;height:{float(region.get('height', 0)):g}%"
            )
            rendered_regions.append(
                f'<span class="evidence-annotation" data-evidence-annotation="{index}"{evidence_attr}{item_attr} '
                f'data-evidence-label="{esc(humanize_text(region.get("label", ""), item_labels=item_labels, evidence_assets=evidence_assets))}" style="{style}" aria-hidden="true">'
                f'<span>{esc(humanize_text(region.get("label", ""), item_labels=item_labels, evidence_assets=evidence_assets))}</span></span>'
            )
        annotations = "".join(rendered_regions)
        context_rows = "".join(
            f'<div><dt>{label}</dt><dd data-evidence-context="{field}"{evidence_attr}{item_attr}>'
            f'{esc(humanize_text(visual_context.get(field, ""), item_labels=item_labels, evidence_assets=evidence_assets))}</dd></div>'
            for field, label in (("state", "State"), ("look_at", "Look here"), ("connection", "Why it matters"))
        )
        annotation_reason = ""
        if annotation.get("status") == "not_needed":
            annotation_reason = (
                f'<p class="whole-frame" data-evidence-whole-frame="true"{evidence_attr}{item_attr}>'
                f'<strong>Whole-frame evidence.</strong> '
                f'<span data-evidence-context="annotation_reason"{evidence_attr}{item_attr}>'
                f'{esc(humanize_text(annotation.get("reason", ""), item_labels=item_labels, evidence_assets=evidence_assets))}</span></p>'
            )
        visual_caption = f'<dl class="evidence-context">{context_rows}</dl>{annotation_reason}'
    return (
        f'<figure{evidence_attr}{item_attr}>'
        f'<div class="evidence-image"><img{evidence_attr}{item_attr} src="{source}" alt="{esc(alt)}">{annotations}</div>'
        f'<figcaption{caption_attr}{item_attr}><p class="evidence-receipt">{caption_label}{esc(description)}</p>{visual_caption}</figcaption>'
        "</figure>"
    )


def list_html(values: list[Any], empty: str = "None recorded.") -> str:
    if not values:
        return f'<p class="quiet">{esc(empty)}</p>'
    return "<ul>" + "".join(f"<li>{esc(value)}</li>" for value in values) + "</ul>"


def humanized_list_html(
    values: list[Any],
    *,
    item_labels: dict[str, str],
    evidence_assets: dict[str, dict[str, Any]],
    empty: str = "None recorded.",
) -> str:
    return list_html(
        [humanize_text(value, item_labels=item_labels, evidence_assets=evidence_assets) for value in values],
        empty,
    )


def table_html(headers: list[str], rows: list[list[Any]], class_name: str = "") -> str:
    head = "".join(f"<th scope=\"col\">{esc(value)}</th>" for value in headers)
    body = "".join("<tr>" + "".join(f"<td>{esc(value)}</td>" for value in row) + "</tr>" for row in rows)
    return f'<div class="table-wrap"><table class="{esc(class_name)}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def decision_control(item: dict[str, Any], decision: dict[str, Any] | None) -> str:
    if item["kind"] not in {"finding", "enhancement"} or item["status"] not in {"open", "needs-verification"}:
        return ""
    current = (decision or {}).get("decision", "pending")
    note = (decision or {}).get("note", "")
    decision_labels = {
        "pending": "Not decided",
        "approve": "Approve",
        "defer": "Decide later",
        "reject": "Reject",
    }
    options = "".join(
        f'<option value="{value}"{" selected" if current == value else ""}>{decision_labels[value]}</option>'
        for value in ("pending", "approve", "defer", "reject")
    )
    item_id = esc(item["id"])
    return f"""
      <div class="decision-row">
        <label>Decision<select data-decision-for="{item_id}">{options}</select></label>
        <label>Note<input data-note-for="{item_id}" value="{esc(note)}"></label>
      </div>"""


def evidence_html(
    item: dict[str, Any],
    context: dict[str, Any],
    base: Path,
    item_labels: dict[str, str],
) -> str:
    raw_assets = context.get("evidence_assets", {})
    if isinstance(raw_assets, dict):
        assets = raw_assets.get(item["id"], [])
    else:
        lookup = evidence_by_id(context)
        assets = [lookup[evidence_id] for evidence_id in item.get("evidence_refs", []) if evidence_id in lookup]
    visual_contexts = visual_evidence_map(context)
    evidence_assets = evidence_by_id(context)
    rendered: list[str] = []
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        if asset.get("kind") not in {None, "screenshot"}:
            continue
        figure = screenshot_figure(
            asset,
            base,
            item_id=item["id"],
            visual_context=visual_contexts.get((str(asset.get("id")), item["id"])),
            item_labels=item_labels,
            evidence_assets=evidence_assets,
        )
        if figure:
            rendered.append(figure)
    return '<div class="evidence-grid">' + "".join(rendered) + "</div>" if rendered else ""


def unattached_screenshot_html(
    registry: dict[str, Any],
    context: dict[str, Any],
    base: Path,
    item_labels: dict[str, str],
) -> str:
    raw_assets = context.get("evidence_assets", [])
    if not isinstance(raw_assets, list):
        return ""
    attached = {
        evidence_id
        for item in registry.get("items", [])
        for evidence_id in item.get("evidence_refs", [])
    }
    visual_contexts = visual_evidence_map(context)
    evidence_assets = evidence_by_id(context)
    figures = [
        screenshot_figure(
            asset,
            base,
            visual_context=visual_contexts.get((str(asset.get("id")), None)),
            item_labels=item_labels,
            evidence_assets=evidence_assets,
        )
        for asset in raw_assets
        if isinstance(asset, dict)
        and asset.get("kind") == "screenshot"
        and asset.get("id") not in attached
    ]
    figures = [figure for figure in figures if figure]
    if not figures:
        return ""
    return (
        '<section id="visual-evidence"><h2>Additional screenshots</h2>'
        '<p class="section-note">These operated screens add product context but are not the sole proof of a finding. '
        'Screenshots tied to a finding appear beside that finding.</p>'
        f'<div class="evidence-grid">{"".join(figures)}</div></section>'
    )


CHECK_KIND_LABELS = {
    "command": "Command",
    "dom_state": "Page state",
    "measurement": "Measurement",
    "manual": "Manual",
}


def check_summary(check: dict[str, Any]) -> str:
    """One readable line per acceptance check, whatever shape it carries."""
    for key in ("summary", "run", "selector", "metric"):
        value = check.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    expect = check.get("expect")
    return json.dumps(expect, sort_keys=True) if expect else "no detail recorded"


def fix_packet_html(item: dict[str, Any]) -> str:
    """Render the executable repair so a reader can see the promised change.

    A prose acceptance check is a promise; a fix packet is the executable form
    of it. Rendering it is what lets a human approve the actual change rather
    than a description of one. Manual checks are labelled second-class here for
    the same reason the skill calls them second-class: nothing runs them.
    """
    packet = item.get("fix_packet")
    if not isinstance(packet, dict):
        return ""
    targets = ", ".join(
        f'{esc(str(target.get("kind", "target")))}: {esc(str(target.get("value", "")))}'
        for target in packet.get("target", [])
        if isinstance(target, dict)
    ) or "not recorded"
    effort = {"S": "Small", "M": "Medium", "L": "Large"}.get(str(packet.get("effort")), str(packet.get("effort", "not recorded")))
    rows = []
    for check in packet.get("acceptance", []) or []:
        if not isinstance(check, dict):
            continue
        kind = str(check.get("kind") or "manual")
        label = CHECK_KIND_LABELS.get(kind, kind.replace("_", " ").title())
        manual = kind == "manual"
        note = " <span class=\"check-manual\">needs a person; no tool can pass it</span>" if manual else ""
        rows.append(
            f'<li class="check-{esc(kind)}"><span class="check-kind">{esc(label)}</span> {esc(check_summary(check))}{note}</li>'
        )
    checks_html = f'<ul class="fix-checks">{"".join(rows)}</ul>' if rows else '<p class="quiet">No acceptance checks recorded.</p>'
    return (
        '<div class="fix-packet"><h4>Executable fix packet</h4>'
        f'<p class="meta"><strong>Where:</strong> {targets} · <strong>Effort:</strong> {esc(effort)}</p>'
        f'<p><strong>Change:</strong> {esc(str(packet.get("change", "not recorded")))}</p>'
        f'<p><strong>Undo:</strong> {esc(str(packet.get("rollback", "not recorded")))}</p>'
        f'<p class="meta">Acceptance checks</p>{checks_html}</div>'
    )


def item_html(
    item: dict[str, Any],
    decision: dict[str, Any] | None,
    context: dict[str, Any],
    base: Path,
    item_labels: dict[str, str],
) -> str:
    evidence_assets = evidence_by_id(context)
    destination = f' → {esc(item_labels.get(item["destination_id"], "another review item"))}' if item.get("destination_id") else ""
    dependencies = ", ".join(item_labels.get(value, "another review item") for value in item.get("depends_on", [])) or "No dependencies"
    item_id = esc(item["id"])
    item_label = item_labels.get(item["id"], "Review item")
    facets = facet_labels(item.get("facets", []))
    meta_parts = [plain_category_label(item["category"]), *facets, f'{str(item.get("confidence", "unknown")).title()} confidence', disposition_label(item.get("revision_disposition"))]
    receipts = public_evidence_summary(item.get("evidence_refs"), context, item_labels=item_labels) or "No supporting records listed"
    editorial = item.get("editorial_review")
    editorial_html = ""
    if isinstance(editorial, dict):
        families = ", ".join(str(value).replace("_", " ") for value in editorial.get("independent_signal_families", [])) or "not applicable"
        language = {"en": "English", "non_en": "another verified language", "unknown": "unknown language", "not_applicable": "not applicable"}.get(
            editorial.get("analysis_language_scope"), str(editorial.get("analysis_language_scope", "not recorded")).replace("_", " ")
        )
        editorial_html = (
            '<details class="method-details"><summary>How the copy was reviewed</summary>'
            f'<p>{esc(str(editorial.get("review_type", "review")).replace("_", " ").title())} · '
            f'{esc(str(editorial.get("sample_adequacy", "not recorded")).replace("_", " ").title())} sample · '
            f'{esc(language)} · signals checked: {esc(families)}.</p>'
            '<p>This checks writing quality only; it does not guess who or what wrote the copy.</p></details>'
        )
    return f"""
    <article class="registry-item" data-item-id="{item_id}" data-kind="{esc(item['kind'])}" data-status="{esc(item['status'])}" data-severity="{esc(item['severity'])}">
      <div class="item-rail">
        <span class="item-id">{esc(item_label)}</span>
        <span class="badge {esc(item['status'])}">{esc(status_label(item['status']))}</span>
        <span class="severity {esc(item['severity'])}">{esc(severity_label(item))}</span>
        <span class="cat-chip">{esc(plain_category_label(item['category']))}</span>
      </div>
      <div class="item-body">
        <p class="plain-lead">{esc(item.get('plain') or humanize_text(item['title'], item_labels=item_labels, evidence_assets=evidence_assets))}</p>
        <h3>{esc(humanize_text(item['title'], item_labels=item_labels, evidence_assets=evidence_assets))}</h3>
        <p class="meta">{esc(' · '.join(meta_parts))}{destination}</p>
        <p>{esc(humanize_text(item['observation'], item_labels=item_labels, evidence_assets=evidence_assets))}</p>
        {evidence_html(item, context, base, item_labels)}
        <div class="item-columns">
          <div><h4>User impact</h4><p>{esc(humanize_text(item['user_impact'], item_labels=item_labels, evidence_assets=evidence_assets))}</p></div>
          <div><h4>Cause</h4><p>{esc(humanize_text(item['cause'], item_labels=item_labels, evidence_assets=evidence_assets))}</p></div>
        </div>
        <h4>What supports this</h4>{humanized_list_html(item.get('evidence', []), item_labels=item_labels, evidence_assets=evidence_assets)}
        <p class="meta"><strong>Supporting records:</strong> {esc(receipts)}</p>
        {editorial_html}
        <h4>Recommended next step</h4><p>{esc(humanize_text(item['recommendation'], item_labels=item_labels, evidence_assets=evidence_assets))}</p>
        <h4>How to verify it</h4>{humanized_list_html(item.get('acceptance_checks', []), item_labels=item_labels, evidence_assets=evidence_assets, empty='No additional verification required for this strength.')}
        {fix_packet_html(item)}
        {f'<p class="verification-override"><strong>Marked fixed without executable proof:</strong> {esc(str(item["verification_override"]))}</p>' if item.get("verification_override") else ""}
        <p class="dependency"><strong>Dependencies:</strong> {esc(dependencies)} · <strong>Review history:</strong> {esc(humanize_text(item['disposition_reason'] or 'New in this review.', item_labels=item_labels, evidence_assets=evidence_assets))}</p>
        {decision_control(item, decision)}
      </div>
    </article>"""


def section_items(
    title: str,
    intro: str,
    items: list[dict[str, Any]],
    decisions: dict[str, dict[str, Any]],
    context: dict[str, Any],
    base: Path,
    item_labels: dict[str, str],
) -> str:
    content = "".join(item_html(item, decisions.get(item["id"]), context, base, item_labels) for item in items)
    if not content:
        content = '<p class="quiet">No items in this section.</p>'
    return f'<h3 class="subhead">{esc(title)}</h3><p class="section-note">{esc(intro)}</p><div class="item-list">{content}</div>'


def render(registry: dict[str, Any], context: dict[str, Any], decision_doc: dict[str, Any], context_path: Path) -> str:
    items = registry["items"]
    by_id = {item["id"]: item for item in items}
    item_labels = item_label_map(items)
    evidence_assets = evidence_by_id(context)
    decision_map = {row["item_id"]: row for row in decision_doc.get("decisions", [])}
    presentation = registry["presentation"]

    prioritized_findings = [by_id[item_id] for item_id in presentation["prioritized_finding_ids"]]
    prioritized_set = set(presentation["prioritized_finding_ids"])
    additional_findings = [item for item in items if item["kind"] == "finding" and item["status"] in {"open", "needs-verification"} and item["id"] not in prioritized_set]
    enhancement_priority = [by_id[item_id] for item_id in presentation["prioritized_enhancement_ids"]]
    enhancement_set = set(presentation["prioritized_enhancement_ids"])
    additional_enhancements = [item for item in items if item["kind"] == "enhancement" and item["status"] in {"open", "needs-verification"} and item["id"] not in enhancement_set]
    strengths = [by_id[item_id] for item_id in presentation["strength_ids"]]
    resolved = [item for item in items if item["status"] in {"fixed", "cleared", "merged", "superseded"}]

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
            TASK_STATUS_LABELS.get(row.get("status", ""), status_label(row.get("status", ""))),
            humanize_text(row.get("goal", ""), item_labels=item_labels, evidence_assets=evidence_assets),
            humanize_text(row.get("result", ""), item_labels=item_labels, evidence_assets=evidence_assets),
            humanize_text(row.get("evidence", ""), item_labels=item_labels, evidence_assets=evidence_assets)
            or public_evidence_summary(row.get("evidence_refs"), context, item_labels=item_labels),
        ]
        for index, row in enumerate(context.get("tasks", []), start=1)
    ]
    capability_table_rows = capability_rows(context, item_labels=item_labels, evidence_assets=evidence_assets)
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
    routing_html = (
        table_html(["Review area", "Decision", "Reason"], route_table_rows)
        if route_table_rows else '<p class="quiet">No routing ledger is present in this legacy context.</p>'
    )
    assumptions_html = (
        table_html(["Assumption", "Status", "Basis", "Risk if wrong", "Evidence needed", "Decision affected"], assumption_table_rows)
        if assumption_table_rows else '<p class="quiet">No consequential assumptions recorded.</p>'
    )
    referrals_html = (
        table_html(["Review area", "Question", "Status", "Why it was referred", "Claim boundary", "Supporting records", "Verified specialist result"], referral_table_rows)
        if referral_table_rows else '<p class="quiet">No specialist referrals recorded.</p>'
    )
    score_table_rows = score_rows(context, item_labels=item_labels, evidence_assets=evidence_assets)
    reconciliation_rows = [
        [
            item_labels.get(item["id"], "Review item"),
            humanize_text(item["title"], item_labels=item_labels, evidence_assets=evidence_assets),
            status_label(item["status"]),
            disposition_label(item["revision_disposition"]),
            item_labels.get(item.get("destination_id"), "—") if item.get("destination_id") else "—",
            humanize_text(item["disposition_reason"] or "New in this review.", item_labels=item_labels, evidence_assets=evidence_assets),
        ]
        for item in items
    ]
    work_rows = []
    for index, order in enumerate(context.get("work_orders", []), start=1):
        related_items = ", ".join(item_labels.get(item_id, "Review item") for item_id in order.get("item_ids", [])) or "None"
        work_rows.append(
            f'<li><div><strong>Work package {index} · {esc(humanize_text(order.get("title", ""), item_labels=item_labels, evidence_assets=evidence_assets))}</strong>'
            f'<p>{esc(humanize_text(order.get("summary", ""), item_labels=item_labels, evidence_assets=evidence_assets))}</p>'
            f'<p class="meta">Related items: {esc(related_items)} · How to verify: {esc(humanize_text(order.get("verification", ""), item_labels=item_labels, evidence_assets=evidence_assets))}</p>'
            f'{humanized_list_html(order.get("acceptance_checks", []), item_labels=item_labels, evidence_assets=evidence_assets, empty="No verification steps recorded.")}</div></li>'
        )

    registry_json = json.dumps(registry, ensure_ascii=False).replace("</", "<\\/")
    decisions_json = json.dumps(decision_doc, ensure_ascii=False).replace("</", "<\\/")
    title = context.get("title", "Scruffy audit")
    target = registry.get("target", "")
    storage_key = f"anti-slop:{registry['audit_id']}:decisions:v2"
    # The handoff has to name a real bundle directory and a real target, or the
    # agent that receives it has to guess where to write verification.json.
    handoff_json = json.dumps(
        {
            "target": str(registry.get("target") or "the audited product"),
            "bundle": str(context_path.parent),
        },
        ensure_ascii=False,
    ).replace("</", "<\\/")

    severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3, "none": 4}
    additional_findings.sort(key=lambda i: (i["category"], severity_rank.get(i["severity"], 9)))
    additional_enhancements.sort(key=lambda i: (i["category"], severity_rank.get(i["severity"], 9)))
    capability_counts: dict[str, int] = {}
    for row in context.get("capabilities", []):
        capability_counts[row.get("status", "?")] = capability_counts.get(row.get("status", "?"), 0) + 1
    capability_summary = " · ".join(
        f"{CAPABILITY_STATUS_LABELS.get(key, status_label(key))}: {value}"
        for key, value in sorted(capability_counts.items())
    )
    open_findings = sum(1 for i in items if i["kind"] == "finding" and i["status"] in {"open", "needs-verification"})
    open_enhancements = sum(1 for i in items if i["kind"] == "enhancement" and i["status"] in {"open", "needs-verification"})
    strength_count = sum(1 for i in items if i["kind"] == "strength")
    cleared_count = sum(1 for i in items if i["status"] in {"cleared", "fixed"})
    carried_count = sum(1 for i in items if i.get("revision_disposition") == "carried")
    numeric_scores = [(row.get("category"), score_number(row.get("score"))) for row in context.get("scores", [])
                      if score_number(row.get("score")) is not None]
    worst = max(numeric_scores, key=lambda pair: pair[1], default=None)
    worst_label = f"{plain_category_label(worst[0])} · {worst[1]} of 3" if worst else "—"
    hero = next((i for i in prioritized_findings if i["status"] in {"open", "needs-verification"}), None)
    if hero:
        hero_html = (
            f'<p class="eyebrow">Independent product review · '
            f'{open_findings + open_enhancements} items awaiting decision</p>'
            f'<h1>{esc(humanize_text(hero["title"], item_labels=item_labels, evidence_assets=evidence_assets))}</h1>'
            f'<p class="target">{esc(item_labels.get(hero["id"], "Finding"))} · {esc(plain_category_label(hero["category"]))} · '
            f'{esc(severity_label(hero))} · decide this first, then review <a href="#findings">the remaining items below</a>.</p>'
        )
    else:
        hero_html = (
            '<p class="eyebrow">Independent product review</p>'
            f'<h1>{esc(humanize_text(title, item_labels=item_labels, evidence_assets=evidence_assets))}</h1>'
        )
    strip_html = (
        f'<div class="strip num" aria-label="Review counts">'
        f'<div><span>Open findings</span><b>{open_findings}</b></div>'
        f'<div><span>Optional enhancements</span><b>{open_enhancements}</b></div>'
        f'<div><span>Strengths</span><b>{strength_count}</b></div>'
        f'<div><span>Cleared</span><b>{cleared_count}</b></div>'
        f'<div><span>Still present from prior review</span><b>{carried_count}</b></div>'
        f'<div><span>Highest concern</span><b>{esc(worst_label)}</b></div>'
        f'<div class="strip-target"><span>Target</span><b class="tgt">{esc(target)}</b></div></div>'
    )
    if enhancement_priority or additional_enhancements:
        enhancement_html = (
            section_items('Highest priority', 'Up to five optional enhancements with the strongest expected value.', enhancement_priority, decision_map, context, context_path.parent, item_labels)
            + section_items('Other enhancements', 'Useful optional enhancements outside the first-priority group.', additional_enhancements, decision_map, context, context_path.parent, item_labels)
        )
    else:
        enhancement_html = (
            '<p class="quiet">No optional enhancements were identified. '
            'Corrective changes remain listed under Findings and Recommended work sequence.</p>'
        )
    additional_visual_evidence = unattached_screenshot_html(registry, context, context_path.parent, item_labels)
    humanized_checks_not_run = [
        humanize_text(
            f"{row.get('check', '')} — {row.get('reason', '')} Impact: {row.get('impact', '')}" if isinstance(row, dict) else row,
            item_labels=item_labels,
            evidence_assets=evidence_assets,
        )
        for row in context.get("checks_not_run", [])
    ]

    return f"""<!doctype html>
<html lang="en" data-theme="light">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(humanize_text(title, item_labels=item_labels, evidence_assets=evidence_assets))}</title>
  <style>
    :root{{--paper:#e9eaec;--surface:#fff;--lane:#f2f3f4;--ink:#14161a;--ink2:#4d525c;--ink3:#6d6b69;--rule:#dcdee1;
      --brand:#d40f2e;--action-on:#fff;--link:#2a53d8;--critical:#b42318;--critical-soft:#fdeceb;--ok:#1f6b3f;--ok-soft:#e7f2ec;
      --warn:#8a5a06;--warn-soft:#f6efe2;--violet:#6f42c1;--violet-soft:#f0eafd;--radius:8px;
      --shadow:0 1px 2px rgb(20 22 26/.06),0 8px 24px rgb(20 22 26/.05);color-scheme:light;
      font-family:-apple-system,"Helvetica Neue",Arial,sans-serif;color:var(--ink);background:var(--paper)}}
    *{{box-sizing:border-box}} body{{margin:0;min-height:100vh;background:var(--paper)}} a{{color:var(--link);text-underline-offset:3px}}
    button,select,input{{font:inherit}} :focus-visible{{outline:3px solid var(--link);outline-offset:3px}}
    .num,.item-id,.strip b{{font-variant-numeric:tabular-nums}}
    .wrap{{width:min(1220px,calc(100% - 40px));margin:0 auto}}
    .mast{{background:var(--surface);border-bottom:3px solid var(--brand)}}
    .mast .wrap{{padding:36px 0 30px;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:28px;align-items:end}}
    .eyebrow{{margin:0 0 10px;color:var(--brand);font:700 11px/1.4 Arial,sans-serif;letter-spacing:.14em;text-transform:uppercase}}
    h1{{margin:0;font:500 clamp(1.7rem,3.2vw,2.8rem)/1.1 Georgia,"Times New Roman",serif;max-width:920px}}
    .target{{margin:12px 0 0;color:var(--ink3);font:.88rem/1.55 Arial,sans-serif;overflow-wrap:anywhere;max-width:820px}}
    .verdict{{max-width:300px;padding:16px 19px;color:var(--action-on);background:var(--brand);border-radius:var(--radius);font:.82rem/1.35 Arial,sans-serif;box-shadow:var(--shadow)}}
    .verdict strong{{display:block;margin-top:5px;font:600 1.25rem/1.2 Georgia,serif}}
    .strip{{display:flex;gap:30px;flex-wrap:wrap;padding:16px 0;border-bottom:1px solid var(--rule);background:var(--lane)}}
    .strip>div>span{{display:block;color:var(--ink3);font:700 10.5px/1.4 Arial,sans-serif;letter-spacing:.11em;text-transform:uppercase}}
    .strip b{{font:600 1.7rem/1.15 "Helvetica Neue",Arial,sans-serif}}
    .strip .strip-target{{margin-left:auto;max-width:360px;min-width:0}} .strip .tgt{{font:400 .78rem/1.45 Arial,sans-serif;color:var(--ink3);overflow-wrap:anywhere}}
    .strip-holder{{background:var(--lane)}}
    main.wrap{{padding:34px 0 72px}}
    section{{padding:0 0 8px}} section+section{{border-top:1px solid var(--rule);margin-top:36px}}
    h2{{margin:34px 0 12px;color:var(--ink);font:700 12px/1.4 Arial,sans-serif;letter-spacing:.15em;text-transform:uppercase}}
    h2:after{{content:"";display:block;margin-top:10px;width:44px;border-top:2px solid var(--brand)}}
    .subhead{{margin:24px 0 4px;color:var(--ink);font:500 1.15rem/1.3 Georgia,serif}}
    .section-note,.quiet,.meta{{color:var(--ink3);font:.88rem/1.55 Arial,sans-serif}}
    .lede{{font:400 clamp(1.05rem,1.8vw,1.3rem)/1.6 Georgia,serif;max-width:920px;color:var(--ink)}}
    .table-wrap{{overflow:auto;border:1px solid var(--rule);border-radius:var(--radius);background:var(--surface);box-shadow:var(--shadow)}}
    table{{width:100%;border-collapse:collapse;font:.86rem/1.5 Arial,sans-serif}}
    th{{color:var(--ink3);background:var(--lane);text-align:left;font:700 10.5px/1.4 Arial,sans-serif;letter-spacing:.1em;text-transform:uppercase}}
    th,td{{padding:11px 13px;border-bottom:1px solid var(--rule);vertical-align:top}} td{{overflow-wrap:anywhere}} tr:last-child td{{border-bottom:0}}
    .toolbar{{position:sticky;top:0;z-index:9;display:flex;flex-wrap:wrap;gap:9px;margin:20px 0;padding:12px 14px;background:rgba(255,255,255,.96);border:1px solid var(--rule);border-radius:var(--radius);box-shadow:var(--shadow)}}
    .toolbar button,.toolbar label{{border:1px solid var(--rule);background:var(--lane);color:var(--ink);padding:9px 13px;cursor:pointer;font:700 .78rem/1 Arial,sans-serif;border-radius:var(--radius)}}
    .toolbar button.primary{{background:var(--brand);border-color:var(--brand);color:var(--action-on)}}
    .toolbar input{{position:absolute;inline-size:1px;block-size:1px;opacity:.01}}
    .registry-item{{display:grid;grid-template-columns:118px minmax(0,1fr);gap:24px;padding:26px 0;border-top:1px solid var(--rule)}}
    .registry-item>*{{min-width:0}}
    .item-rail{{display:flex;flex-direction:column;align-items:flex-start;gap:9px}}
    .item-id{{color:var(--brand);font:800 1.05rem/1 "Helvetica Neue",Arial,sans-serif}}
    .badge,.severity{{padding:5px 9px;border-radius:6px;font:800 .64rem/1 Arial,sans-serif;letter-spacing:.08em;text-transform:uppercase}}
    .severity:before,.badge:before{{content:"●";margin-right:6px;font-size:.7em;vertical-align:1px}}
    .severity.critical,.severity.high{{background:var(--critical-soft);color:var(--critical)}}
    .severity.medium{{background:var(--warn-soft);color:var(--warn)}}
    .severity.low{{background:var(--ok-soft);color:var(--ok)}} .severity.none{{background:#edf3ff;color:var(--link)}}
    .badge.open{{background:var(--warn-soft);color:var(--warn)}} .badge.needs-verification{{background:var(--violet-soft);color:var(--violet)}}
    .badge.fixed,.badge.cleared{{background:var(--ok-soft);color:var(--ok)}} .badge.merged,.badge.superseded{{background:var(--lane);color:var(--ink3)}}
    .item-body h3{{margin:0 0 6px;font:500 1.3rem/1.3 Georgia,serif}}
    .item-body p,.item-body li{{line-height:1.6;overflow-wrap:anywhere}}
    .item-body h4{{margin:18px 0 4px;color:var(--ink3);font:800 .68rem/1.4 Arial,sans-serif;letter-spacing:.1em;text-transform:uppercase}}
    .item-body ul{{margin:5px 0;padding-left:21px}}
    .item-columns{{display:grid;grid-template-columns:1fr 1fr;gap:24px}} .item-columns>*{{min-width:0}}
    .dependency{{font:.82rem/1.5 Arial,sans-serif;color:var(--ink3);overflow-wrap:anywhere}}
    .cat-chip{{padding:5px 9px;border-radius:6px;border:1px solid var(--rule);color:var(--ink3);font:800 .64rem/1 Arial,sans-serif;letter-spacing:.08em;text-transform:uppercase}}
    .decision-row{{display:grid;grid-template-columns:170px 1fr;gap:11px;margin-top:19px;padding:15px 16px;background:var(--surface);border:1px solid var(--rule);border-radius:var(--radius);box-shadow:var(--shadow)}}
    .decision-row>*{{min-width:0}}
    .decision-row label{{color:var(--ink3);font:700 .72rem/1.3 Arial,sans-serif;letter-spacing:.06em;text-transform:uppercase}}
    .decision-row select,.decision-row input{{width:100%;margin-top:5px;padding:9px;color:var(--ink);background:var(--surface);border:1px solid var(--rule);border-radius:var(--radius)}}
    .evidence-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,360px),1fr));gap:18px;margin:18px 0}}
    .evidence-grid>*{{min-width:0}}
    figure{{margin:0;min-width:0;background:var(--surface);border:1px solid var(--rule);border-radius:var(--radius);padding:8px 8px 12px;box-shadow:var(--shadow)}}
    .evidence-grid>figure:only-child{{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(280px,.7fr);gap:12px;align-items:start}}
    .evidence-grid>figure:only-child figcaption{{padding:3px 4px 0 0}}
    .evidence-image{{position:relative;overflow:hidden;background:#d8d2c2}}
    figure img{{display:block;width:100%;border:1px solid #d8d2c2}}
    .evidence-annotation{{position:absolute;border:3px solid var(--brand);background:rgba(212,15,46,.12);box-shadow:0 0 0 1px rgba(255,255,255,.8) inset;pointer-events:none}}
    .evidence-annotation>span{{position:absolute;left:-3px;top:-3px;max-width:min(260px,80vw);padding:4px 7px;background:var(--brand);color:#fff;font:800 10px/1.25 Arial,sans-serif;letter-spacing:.02em;white-space:normal}}
    figcaption{{padding:8px 3px 0;color:#26322c;font:.76rem/1.5 Arial,sans-serif;overflow-wrap:anywhere}}
    .evidence-receipt{{margin:0 0 8px;font:600 .78rem/1.45 Georgia,serif}}
    .evidence-context{{display:grid;gap:7px;margin:0}}
    .evidence-context>div{{display:grid;grid-template-columns:74px minmax(0,1fr);gap:8px;padding-top:7px;border-top:1px solid #d8d2c2}}
    .evidence-context dt{{color:#6c766f;font:800 9.5px/1.35 Arial,sans-serif;letter-spacing:.08em;text-transform:uppercase}}
    .evidence-context dd{{margin:0;font-weight:600}}
    .whole-frame{{margin:9px 0 0;padding:8px 9px;background:var(--lane);border-left:3px solid var(--brand)}}
    .status{{min-height:1.3em;color:var(--ok);font:700 .82rem/1.4 Arial,sans-serif}}
    .work-list{{counter-reset:work;list-style:none;margin:0;padding:0}}
    .work-list>li{{counter-increment:work;display:grid;grid-template-columns:44px minmax(0,1fr);gap:12px;padding:15px 0;border-bottom:1px solid var(--rule)}}
    .work-list>li>*{{min-width:0}}
    .work-list>li:before{{content:counter(work,decimal-leading-zero);color:var(--brand);font:800 1rem/1.5 "Helvetica Neue",Arial,sans-serif}}
    footer{{color:var(--ink3);background:var(--lane);border-top:1px solid var(--rule)}} footer .wrap{{padding:22px 0;font:.8rem/1.5 Arial,sans-serif}}
    [hidden]{{display:none!important}}
    @media(max-width:760px){{.mast .wrap,.registry-item,.item-columns,.decision-row,.evidence-grid>figure:only-child{{grid-template-columns:1fr}} .toolbar{{position:static}} .evidence-grid>figure:only-child figcaption{{padding:8px 3px 0}} .verdict{{max-width:none}} .registry-item{{gap:11px}} .item-rail{{flex-direction:row;align-items:center;flex-wrap:wrap}} .strip{{gap:18px}} .strip .strip-target{{margin-left:0}}}}
    @media print{{
      :root{{color:#141414;background:#fff;font-family:Georgia,"Times New Roman",serif}}
      body,.mast,.strip,.strip-holder,footer{{background:#fff!important;color:#141414}}
      .toolbar,.decision-row{{display:none}}
      .mast{{border-bottom:3px double #141414}} .eyebrow,.target,.strip>div>span,.section-note,.meta,.quiet{{color:#5c5c56}}
      h1,.item-body h3,.subhead{{color:#141414}} h2{{color:#141414}} h2:after{{border-color:#141414}}
      .verdict{{background:#fff;border:1.5px solid #141414;box-shadow:none;color:#141414;border-radius:0}}
      .strip{{border-bottom:1px solid #141414}} .strip b{{color:#141414}}
      .registry-item{{break-inside:avoid;border-top:1px solid #d9d9d2}}
      .item-id{{color:#c8102e}}
      .badge,.severity{{border:1.5px solid #141414;background:#fff!important;color:#141414!important;border-radius:0}}
      .severity.critical,.severity.high{{background:#c8102e!important;border-color:#c8102e;color:#fff!important}}
      table,th,td{{color:#141414}} th{{background:#fff;border-bottom:1.5px solid #141414}}
      figure{{box-shadow:none;border:1px solid #d9d9d2}} a{{color:#141414}}
    }}
  
/* The plain lead is the finding for a reader who does not know the taxonomy.
   It gets the type, and the title drops to a subhead. Added, never substituted:
   every other field still renders below. */
      .registry-item .plain-lead{{font-size:1.24rem;line-height:1.4;margin:0 0 .35rem;font-weight:600;max-width:62ch}}
      .registry-item h3{{font-size:.94rem;font-weight:600;opacity:.72;margin:0 0 .3rem}}

/* The fix packet is the executable form of the acceptance checks. It renders
   inside the item so approving a change and reading the change are the same
   act. Manual checks are dimmed because nothing runs them. */
      .fix-packet{{margin:.75rem 0 0;padding:.7rem .85rem;border-left:3px solid #141414;background:rgba(20,20,20,.035);min-width:0}}
      .fix-packet h4{{margin:0 0 .35rem}}
      .fix-packet p{{margin:.2rem 0;overflow-wrap:anywhere}}
      .fix-checks{{margin:.3rem 0 0;padding-left:1.1rem}}
      .fix-checks li{{margin:.2rem 0;overflow-wrap:anywhere}}
      .fix-checks .check-kind{{display:inline-block;font-size:.7rem;letter-spacing:.06em;text-transform:uppercase;border:1px solid currentColor;border-radius:2px;padding:0 .3rem;margin-right:.35rem;opacity:.75}}
      .fix-checks li.check-manual{{opacity:.62}}
      .fix-checks .check-manual{{font-style:italic;opacity:.8}}
</style>
</head>
<body>
  <header class="mast"><div class="wrap"><div>{hero_html}</div><div class="verdict">Overall result<strong>{esc(humanize_text(outcome.get('label','Insufficient evidence'), item_labels=item_labels, evidence_assets=evidence_assets))}</strong></div></div></header>
  <div class="strip-holder"><div class="wrap">{strip_html}</div></div>
  <main class="wrap">
    <section id="outcome"><h2>Outcome</h2><p class="lede">{esc(humanize_text(outcome.get('summary',''), item_labels=item_labels, evidence_assets=evidence_assets))}</p><p class="section-note"><strong>Confidence:</strong> {esc(str(outcome.get('confidence','unknown')).title())}</p></section>
    <section id="product-frame"><h2>What this product is meant to do</h2>{table_html(['Question','Answer','How we know'],product_table_rows)}</section>
    <section id="task-ledger"><h2>Did real journeys work?</h2><p class="section-note">Each row shows a task we performed, what happened, and the supporting records.</p>{table_html(['Journey','Outcome','Goal','What happened','Supporting records'],task_table_rows)}</section>
    {additional_visual_evidence}
    <section id="capability-ledger"><h2>What we could and could not test</h2><p class="section-note">{esc(capability_summary)}. Anything not tested includes the reason and what that limits.</p>{table_html(['Test area','Status','What was covered'],capability_table_rows)}</section>
    <section id="routing"><h2>Review routing</h2><p class="section-note">Every review area is accounted for, including areas excluded or referred to specialists.</p>{routing_html}</section>
    <section id="assumptions"><h2>Assumptions that could change the result</h2>{assumptions_html}</section>
    <section id="referrals"><h2>Specialist referrals</h2>{referrals_html}</section>
    <section id="score"><h2>Quality scores, highest concern first</h2><p class="section-note">Zero means clear; three means a major problem. “Not scored” means the review did not have enough evidence.</p>{table_html(['Area','Result','Why'],score_table_rows)}</section>
    <section id="findings"><h2>Findings</h2><div class="toolbar" aria-label="Review controls"><button data-filter="all" class="primary">All open items</button><button data-filter="open">Open</button><button data-filter="needs-verification">Needs more evidence</button><button id="download-findings">Download full audit data</button><button id="download-decisions">Download decisions</button><button id="copy-decisions">Copy decisions</button><button id="copy-handoff">Copy AI handoff</button><label>Import decisions<input id="import-decisions" type="file" accept="application/json"></label></div><p id="ui-status" class="status" aria-live="polite"></p>{section_items('Address first','The highest-priority findings are shown first; all findings remain available below.',prioritized_findings,decision_map,context,context_path.parent,item_labels)}{section_items('Other active findings','Confirmed findings and items that still need more evidence.',additional_findings,decision_map,context,context_path.parent,item_labels)}</section>
    <section id="enhancements"><h2>Optional enhancements</h2>{enhancement_html}</section>
    <section id="strengths"><h2>Strengths to preserve</h2>{section_items('Preserve','These existing qualities should survive any repair work.',strengths,decision_map,context,context_path.parent,item_labels)}</section>
    <section id="resolved"><h2>Closed concerns</h2>{section_items('Resolved items','Earlier concerns remain visible so the review history stays complete.',resolved,decision_map,context,context_path.parent,item_labels)}</section>
    <section id="reconciliation"><h2>Review history</h2>{table_html(['Item','Current title','Status','What changed','Replaced by','Reason'],reconciliation_rows,'reconciliation')}</section>
    <section id="work-orders"><h2>Recommended work sequence</h2><ol class="work-list">{''.join(work_rows) or '<li><div>No work packages recorded.</div></li>'}</ol></section>
    <section id="checks-not-run"><h2>What was not tested</h2>{list_html(humanized_checks_not_run,'Everything in scope was tested.')}</section>
  </main>
  <footer><div class="wrap">Complete review: {len(items)} items · Findings to address first: {len(prioritized_findings)} · Optional enhancements to consider first: {len(enhancement_priority)}.</div></footer>
  <script>
    const registry={registry_json};
    const embeddedDecisions={decisions_json};
    const storageKey={json.dumps(storage_key)};
    const itemRows=[...document.querySelectorAll('[data-item-id]')];
    const clone=value=>JSON.parse(JSON.stringify(value));
    const baseRows=Object.fromEntries(embeddedDecisions.decisions.map(row=>[row.item_id,clone(row)]));
    const decisionItems=new Map(registry.items.filter(item=>['finding','enhancement'].includes(item.kind)).map(item=>[item.id,item]));
    const choices=new Set(['pending','approve','defer','reject']);
    const object=value=>value!==null&&typeof value==='object'&&!Array.isArray(value);
    const validRecord=row=>object(row)&&choices.has(row.decision)&&typeof row.note==='string'&&(row.updated_at===null||typeof row.updated_at==='string');
    const validateDecisionState=incoming=>{{
      if(!object(incoming))throw new Error('decision data must be an object');
      for(const key of ['schema_version','audit_id','revision_id','baseline_revision_id']){{
        if(incoming[key]!==registry[key])throw new Error(`decision ${{key}} does not match this review`);
      }}
      if(!Array.isArray(incoming.decisions)||incoming.decisions.length!==decisionItems.size)throw new Error('decisions must contain every review item exactly once');
      const seen=new Set();
      for(const row of incoming.decisions){{
        if(!validRecord(row)||typeof row.item_id!=='string'||!decisionItems.has(row.item_id)||seen.has(row.item_id))throw new Error('decision rows must be unique known items with valid choices and notes');
        if(!Array.isArray(row.history)||!row.history.every(validRecord))throw new Error('decision history must contain valid records');
        const item=decisionItems.get(row.item_id);
        if(row.destination_id!==item.destination_id)throw new Error('decision destination does not match this review');
        if(!['open','needs-verification'].includes(item.status)){{
          const base=baseRows[row.item_id];
          if(row.decision!==base.decision||row.note!==base.note||row.updated_at!==base.updated_at||JSON.stringify(row.history)!==JSON.stringify(base.history))throw new Error('resolved decisions are read-only');
        }}
        seen.add(row.item_id);
      }}
      return clone(incoming);
    }};
    const loadLocal=()=>{{
      try{{
        const raw=localStorage.getItem(storageKey);
        return raw===null?null:validateDecisionState(JSON.parse(raw));
      }}catch(error){{document.getElementById('ui-status').textContent=`Saved decisions rejected: ${{error.message}}`;return null}}
    }};
    let state=loadLocal()||clone(embeddedDecisions);
    const rowFor=id=>state.decisions.find(row=>row.item_id===id);
    const persist=()=>{{try{{localStorage.setItem(storageKey,JSON.stringify(state));return true}}catch{{return false}}}};
    const hydrate=()=>{{document.querySelectorAll('[data-decision-for]').forEach(control=>{{const row=rowFor(control.dataset.decisionFor);control.value=row?.decision||'pending'}});document.querySelectorAll('[data-note-for]').forEach(control=>{{const row=rowFor(control.dataset.noteFor);control.value=row?.note||''}})}};
    document.querySelectorAll('[data-decision-for]').forEach(control=>control.addEventListener('change',()=>{{const row=rowFor(control.dataset.decisionFor);if(!row||!['open','needs-verification'].includes(decisionItems.get(row.item_id)?.status)||!choices.has(control.value))return;row.history=row.history||[];row.history.push({{decision:row.decision,note:row.note,updated_at:row.updated_at}});row.decision=control.value;row.updated_at=new Date().toISOString();persist()}}));
    document.querySelectorAll('[data-note-for]').forEach(control=>control.addEventListener('input',()=>{{const row=rowFor(control.dataset.noteFor);if(!row||!['open','needs-verification'].includes(decisionItems.get(row.item_id)?.status))return;row.note=control.value;row.updated_at=new Date().toISOString();persist()}}));
    const download=(name,value)=>{{const blob=new Blob([JSON.stringify(value,null,2)],{{type:'application/json'}});const link=document.createElement('a');link.href=URL.createObjectURL(blob);link.download=name;link.click();URL.revokeObjectURL(link.href)}};
    document.getElementById('download-findings').addEventListener('click',()=>download(`${{registry.audit_id}}-findings.json`,registry));
    document.getElementById('download-decisions').addEventListener('click',()=>download(`${{registry.audit_id}}-decisions.json`,state));
    document.getElementById('copy-decisions').addEventListener('click',async()=>{{try{{await navigator.clipboard.writeText(JSON.stringify(state,null,2));document.getElementById('ui-status').textContent='Decisions copied.'}}catch{{document.getElementById('ui-status').textContent='Clipboard unavailable; use Download decisions.'}}}});
    const handoffMeta={handoff_json};
    // Copying decisions gives an agent the data but no instruction, so the
    // approvals sat unimplemented. This builds the instruction with them.
    const buildHandoff=()=>{{
      const titles=Object.fromEntries(registry.items.map(item=>[item.id,item.title]));
      const active=new Set(registry.items.filter(item=>['open','needs-verification'].includes(item.status)).map(item=>item.id));
      const approved=state.decisions.filter(row=>row.decision==='approve'&&active.has(row.item_id));
      const list=approved.length?approved.map(row=>`- ${{row.item_id}}: ${{titles[row.item_id]||'(untitled item)'}}`).join('\\n'):'- (nothing is approved yet)';
      return [
        `Run Scruffy in redesign mode with source-write authority on ${{handoffMeta.target}}. Implement only the approve items below, author missing fix packets, run scripts/verify_fixes.py --execute, write verification.json into ${{handoffMeta.bundle}}, do not change item status.`,
        '',
        `Approved items (${{approved.length}}):`,
        list,
        '',
        'decisions.json:',
        '```json',
        JSON.stringify(state,null,2),
        '```'
      ].join('\\n');
    }};
    document.getElementById('copy-handoff').addEventListener('click',async()=>{{
      const text=buildHandoff();
      try{{await navigator.clipboard.writeText(text);document.getElementById('ui-status').textContent='Handoff copied. Paste it into your AI task.'}}
      catch{{download(`${{registry.audit_id}}-decisions.json`,state);document.getElementById('ui-status').textContent='Clipboard unavailable; decisions downloaded instead. Tell your AI to implement only the approved items, run scripts/verify_fixes.py --execute, and write verification.json into the bundle.'}}
    }});
    document.getElementById('import-decisions').addEventListener('change',async event=>{{const file=event.target.files[0];if(!file)return;try{{const incoming=JSON.parse(await file.text());state=validateDecisionState(incoming);hydrate();persist();document.getElementById('ui-status').textContent='Decisions imported and matched to the correct review items.'}}catch(error){{document.getElementById('ui-status').textContent=`Import rejected: ${{error.message}}`}}event.target.value=''}});
    document.querySelectorAll('[data-filter]').forEach(button=>button.addEventListener('click',()=>{{const filter=button.dataset.filter;document.querySelectorAll('[data-filter]').forEach(candidate=>candidate.classList.toggle('primary',candidate===button));itemRows.forEach(row=>{{const active=['open','needs-verification'].includes(row.dataset.status);row.hidden=filter==='all'?!active:row.dataset.status!==filter}})}}));
    hydrate();
  </script>
</body>
</html>"""


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
    rendered = render(registry, context, decisions, args.context)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"PASS: rendered {len(registry.get('items', []))} registry items to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
