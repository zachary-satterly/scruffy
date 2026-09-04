"""Shared display projections for Scruffy Markdown and dashboard renderers."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from audit_contract import load_contract
from taxonomy_contract import load_taxonomy


AUDIT_CONTRACT = load_contract()
TAXONOMY = load_taxonomy()
QUESTION_LABELS = {row["key"]: row["label"] for row in AUDIT_CONTRACT["context"]["product_frame_questions"]}
CAPABILITY_LABELS = {row["key"]: row["label"] for row in AUDIT_CONTRACT["context"]["capabilities"]}
CATEGORY_LABELS = {row["key"]: row["public_label"] for row in TAXONOMY["categories"]}
SCORE_LABELS = {row["key"]: row["score_label"] for row in TAXONOMY["categories"]}
FACET_LABELS = {row["key"]: row["label"] for row in TAXONOMY["facets"]}
REVIEW_LANE_LABELS = {row["key"]: row["label"] for row in AUDIT_CONTRACT["context"]["review_lanes"]}

PLAIN_CATEGORY_LABELS = {
    "product": "Product clarity",
    "information_architecture": "Navigation and organization",
    "interaction": "Interaction and feedback",
    "accessibility": "Accessibility",
    "visual": "Visual design",
    "copy": "Content and copy",
    "backend_shape": "Reliability and maintainability",
    "performance": "Performance",
}
STATUS_LABELS = {
    "open": "Open",
    "fixed": "Fixed",
    "cleared": "Cleared",
    "needs-verification": "Needs more evidence",
    "merged": "Combined",
    "superseded": "Replaced",
}
DISPOSITION_LABELS = {
    "new": "New in this review",
    "carried": "Still present",
    "reopened": "Returned",
    "fixed": "Fixed",
    "cleared": "Cleared after review",
    "merged": "Combined with another item",
    "superseded": "Replaced by a clearer item",
}
CAPABILITY_STATUS_LABELS = {
    "available": "Available",
    "partial": "Partially available",
    "unavailable": "Unavailable",
    "not_needed": "Not needed",
    "not_run": "Not tested",
    "not_authorized": "Not authorized",
}
PRODUCT_BASIS_LABELS = {
    "observed": "Observed in the product",
    "supplied": "Provided by the owner",
    "inferred": "Inferred from available evidence",
    "mixed": "Mixed evidence",
    "unknown": "Unknown",
}
EVIDENCE_KIND_LABELS = {
    "task_observation": "Interaction test",
    "screenshot": "Screenshot",
    "source": "Source review",
    "measurement": "Measurement",
    "analysis_receipt": "Analysis record",
    "specialist_review": "Specialist review",
    "runtime_trace": "Performance measurement",
    "accessibility_observation": "Accessibility review",
    "copy_sample": "Copy sample",
    "supplied": "Provided evidence",
}
LANE_DISPOSITION_LABELS = {
    "selected": "Included in this review",
    "rejected": "Considered and excluded",
    "not_applicable": "Not applicable",
    "referred": "Referred to a specialist",
}
REFERRAL_STATUS_LABELS = {
    "not_run": "Not performed",
    "partial": "Partially performed",
    "complete": "Completed by a specialist",
}
ASSUMPTION_STATUS_LABELS = {
    "open": "Open",
    "supported": "Supported",
    "refuted": "Refuted",
}

PLAIN_TERM_REPLACEMENTS = (
    (r"\bWCAG\s+(?:SC\s+)?1\.4\.3\s+4\.5:1\s+threshold\b", "the 4.5:1 minimum text-contrast threshold"),
    (r"\bWCAG\s+(?:SC\s+)?1\.4\.3\s+contrast\b", "the minimum text-contrast requirement"),
    (r"\bWCAG\s+(?:SC\s+)?1\.4\.3\b", "the minimum text-contrast requirement"),
    (r"\bWCAG\s+(?:SC\s+)?1\.4\.10\b", "the narrow-screen reflow requirement"),
    (r"\bWCAG\s+(?:SC\s+)?2\.4\.3\b", "the keyboard focus-order requirement"),
    (r"\bWCAG\s+2\.4\.2\s*\(Page Titled\)", "the page-title accessibility requirement"),
    (r"\bWCAG\s+3\.1\.1\s*\(Language of Page\)", "the page-language accessibility requirement"),
    (r"\bWCAG\s+1\.3\.1\b", "the semantic page-structure requirement"),
    (r"\bWCAG\s+4\.1\.2\s+name/role/value/state contract\b", "the accessible control-name, role, and state requirement"),
    (r"\bWCAG\s+4\.1\.3\s+support\b", "the announced-status requirement"),
    (r"\bWCAG\s+large-text definition\b", "the accessibility standard's large-text definition"),
    (r"\bWCAG\s+reflow-equivalent width\b", "the standard narrow-screen test width"),
    (r"\bWCAG-named\b", "standards-based"),
    (r"\bWCAG\b", "Web Content Accessibility Guidelines"),
    (r"\bVoiceOver\s*/\s*NVDA\b", "representative screen readers"),
    (r"\bVoiceOver\b", "an Apple screen reader"),
    (r"\bNVDA\b", "a Windows screen reader"),
    (r"\bNMJL-style\b", "National Mah Jongg League-style"),
    (r"\bCSS[ -]pixels?\b", "browser pixels"),
    (r"\bCSS\b", "page styling"),
    (r"\bURLs\b", "web addresses"),
    (r"\bURL\b", "web address"),
    (r"\bDOM\b", "page structure"),
    (r"\bLCP\b", "main-content load time"),
    (r"\bCLS\b", "layout-shift score"),
    (r"\bRUM\b", "real-user performance data"),
    (r"\bH1\b", "main page heading"),
    (r"\bUI\s*/\s*UX\b", "interface and usability"),
    (r"\bUI\b", "interface"),
    (r"\bUX\b", "usability"),
    (r"\bQA\b", "quality review"),
    (r"\bJSON\b", "data file"),
    (r"\bOS\b", "operating system"),
    (r"\bN/A\b", "Not scored"),
    (r"\bAI\b", "artificial intelligence"),
)


def evidence_by_id(context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    assets = context.get("evidence_assets", [])
    if not isinstance(assets, list):
        return {}
    return {
        row["id"]: row
        for row in assets
        if isinstance(row, dict) and isinstance(row.get("id"), str)
    }


def evidence_summary(refs: Any, context: dict[str, Any]) -> str:
    if not isinstance(refs, list):
        return ""
    assets = evidence_by_id(context)
    values = []
    for evidence_id in refs:
        asset = assets.get(evidence_id, {})
        description = asset.get("description")
        values.append(f"{evidence_id}: {description}" if description else str(evidence_id))
    return "; ".join(values)


def item_label_map(items: list[dict[str, Any]]) -> dict[str, str]:
    counters: defaultdict[str, int] = defaultdict(int)
    labels: dict[str, str] = {}
    for item in items:
        if item.get("status") in {"fixed", "cleared", "merged", "superseded"}:
            group = "Cleared concern" if item.get("status") == "cleared" else "Resolved item"
        elif item.get("kind") == "enhancement":
            group = "Improvement"
        elif item.get("kind") == "strength":
            group = "Strength"
        else:
            group = "Finding"
        counters[group] += 1
        labels[str(item.get("id", ""))] = f"{group} {counters[group]}"
    return labels


def evidence_public_label(asset: dict[str, Any]) -> str:
    return EVIDENCE_KIND_LABELS.get(str(asset.get("kind", "")), "Supporting evidence")


def humanize_text(
    value: Any,
    *,
    item_labels: dict[str, str] | None = None,
    evidence_assets: dict[str, dict[str, Any]] | None = None,
) -> str:
    text = str(value or "")
    replacements: dict[str, str] = {}
    if item_labels:
        replacements.update(item_labels)
    if evidence_assets:
        replacements.update(
            {
                evidence_id: evidence_public_label(asset)
                for evidence_id, asset in evidence_assets.items()
            }
        )
    for machine_value in sorted(replacements, key=len, reverse=True):
        text = re.sub(
            rf"(?<![A-Za-z0-9]){re.escape(machine_value)}(?![A-Za-z0-9])",
            replacements[machine_value],
            text,
        )
    text = text.replace("Playwright chromium.connectOverCDP", "the supplied automated browser connection")
    text = text.replace("componentDidMount", "startup code")
    text = text.replace("localStorage", "browser storage")
    text = text.replace("SpeechSynthesisUtterance", "browser speech playback")
    text = text.replace("cache-disabled", "tested without browser caching")
    text = text.replace("html lang", "page language declaration")
    text = text.replace("header/nav/main/footer landmarks", "header, navigation, main-content, and footer regions")
    text = text.replace("aria-expanded/aria-controls", "an announced open or closed state and control relationship")
    text = text.replace("aria-pressed/aria-checked", "an announced selected or checked state")
    text = text.replace("status/live semantics", "an announced status message")
    text = text.replace("live region", "announced update region")
    for pattern, replacement in PLAIN_TERM_REPLACEMENTS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE if pattern == r"\bN/A\b" else 0)
    return text


def public_evidence_summary(
    refs: Any,
    context: dict[str, Any],
    *,
    item_labels: dict[str, str] | None = None,
) -> str:
    if not isinstance(refs, list):
        return ""
    assets = evidence_by_id(context)
    values: list[str] = []
    for evidence_id in refs:
        asset = assets.get(evidence_id, {})
        label = evidence_public_label(asset)
        description = humanize_text(
            asset.get("description", ""),
            item_labels=item_labels,
            evidence_assets=assets,
        )
        values.append(f"{label}: {description}" if description else label)
    return "; ".join(values)


def plain_category_label(key: str) -> str:
    # Canonical keys receive a reader-facing label. Legacy schema-2.0 contexts
    # already contain display strings, so preserve unknown values verbatim.
    return PLAIN_CATEGORY_LABELS.get(TAXONOMY["legacy_category_aliases"].get(key, key), str(key))


def facet_labels(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [FACET_LABELS.get(str(value), str(value).replace("_", " ").title()) for value in values]


def status_label(value: Any) -> str:
    return STATUS_LABELS.get(str(value), str(value).replace("_", " ").replace("-", " ").title())


def disposition_label(value: Any) -> str:
    return DISPOSITION_LABELS.get(str(value), str(value).replace("_", " ").replace("-", " ").title())


def severity_label(item: dict[str, Any]) -> str:
    severity = str(item.get("severity", ""))
    if item.get("kind") == "strength":
        return "Preserve"
    suffix = "priority" if item.get("kind") == "enhancement" else "impact"
    return f"{severity.title()} {suffix}"


def score_display(value: Any) -> str:
    labels = {0: "0 — Clear", 1: "1 — Minor issue", 2: "2 — Material issue", 3: "3 — Major problem", "N/A": "Not scored"}
    return labels.get(value, str(value))


TASK_STATUS_LABELS = {"pass": "Pass", "fail": "Fail", "partial": "Partial",
                      "needs_verification": "Needs verification", "not_run": "Not run"}


def capability_rows(context: dict[str, Any], **humanize_options: Any) -> list[list[Any]]:
    return [
        [
            CAPABILITY_LABELS.get(row.get("key"), row.get("capability") or str(row.get("key", "")).replace("_", " ").title()),
            CAPABILITY_STATUS_LABELS.get(row.get("status"), status_label(row.get("status", ""))),
            humanize_text(row.get("scope", ""), **humanize_options),
        ]
        for row in context.get("capabilities", [])
    ]


def routing_rows(context: dict[str, Any]) -> list[list[Any]]:
    return [
        [
            REVIEW_LANE_LABELS.get(row.get("lane"), str(row.get("lane", "")).replace("_", " ").title()),
            LANE_DISPOSITION_LABELS.get(row.get("disposition"), status_label(row.get("disposition"))),
            row.get("reason", ""),
        ]
        for row in context.get("routing", [])
    ]


def assumption_rows(context: dict[str, Any]) -> list[list[Any]]:
    return [
        [
            row.get("statement", ""),
            ASSUMPTION_STATUS_LABELS.get(row.get("status"), status_label(row.get("status"))),
            PRODUCT_BASIS_LABELS.get(row.get("basis"), status_label(row.get("basis"))),
            row.get("risk_if_wrong", ""),
            row.get("evidence_needed", ""),
            row.get("decision_affected", ""),
        ]
        for row in context.get("assumptions", [])
    ]


def referral_rows(context: dict[str, Any]) -> list[list[Any]]:
    assets = evidence_by_id(context)
    rows: list[list[Any]] = []
    for row in context.get("referrals", []):
        specialist_summaries: list[str] = []
        for evidence_id in row.get("specialist_artifact_refs", []):
            asset = assets.get(evidence_id, {})
            receipt = asset.get("specialist_review")
            if not isinstance(receipt, dict):
                continue
            date_or_version = receipt.get("reviewed_at") or receipt.get("artifact_version") or ""
            specialist_summaries.append(
                f"{receipt.get('reviewer_or_authority', '')}. Scope: {receipt.get('scope', '')} "
                f"Result: {receipt.get('result', '')} Date or version: {date_or_version}. "
                f"Verification: {receipt.get('verification_state', '')}."
            )
        rows.append(
            [
                REVIEW_LANE_LABELS.get(row.get("lane"), str(row.get("lane", "")).replace("_", " ").title()),
                row.get("summary", ""),
                REFERRAL_STATUS_LABELS.get(row.get("review_status"), status_label(row.get("review_status"))),
                row.get("reason", ""),
                row.get("claim_boundary", ""),
                public_evidence_summary(row.get("evidence_refs"), context),
                " ".join(specialist_summaries) or "No completed specialist receipt.",
            ]
        )
    return rows


def score_row_label(key: Any) -> str:
    """Name the canonical slop category first so a reader can map a score to the
    public category, then the measurement framing used for the score itself.
    When the measurement framing adds no words beyond the public label
    ("Accessibility slop · Accessibility"), show the public label alone."""
    key = TAXONOMY["legacy_category_aliases"].get(key, key)
    public = CATEGORY_LABELS.get(key)
    scored = SCORE_LABELS.get(key)
    if public and scored:
        if scored.lower() == public.lower().removesuffix(" slop"):
            return public
        return f"{public} · {scored}"
    return public or scored or str(key or "")


def score_number(value: Any) -> int | None:
    """Read canonical scores and the numeric prefix of legacy display strings."""
    if type(value) is int and 0 <= value <= 3:
        return value
    if isinstance(value, str):
        match = re.match(r"^([0-3])(?:\s*[·—-]|\s*$)", value)
        if match:
            return int(match.group(1))
    return None


def score_order(row: dict[str, Any]) -> tuple[int, int]:
    number = score_number(row.get("score"))
    return (0, -number) if number is not None else (1, 0)


def score_rows(context: dict[str, Any], **humanize_options: Any) -> list[list[Any]]:
    return [
        [
            plain_category_label(row.get("category", "")),
            score_display(row.get("score", "")),
            humanize_text(row.get("evidence", ""), **humanize_options),
        ]
        for row in sorted(context.get("scores", []), key=score_order)
    ]


def checks_not_run(context: dict[str, Any]) -> list[str]:
    output: list[str] = []
    for row in context.get("checks_not_run", []):
        if isinstance(row, str):
            output.append(row)
        elif isinstance(row, dict):
            output.append(f"{row.get('check', '')} — {row.get('reason', '')} Impact: {row.get('impact', '')}".strip())
    return output
