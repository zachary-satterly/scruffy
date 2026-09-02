#!/usr/bin/env python3
"""Render the human decision brief from Scruffy registry data.

The brief is the first thing a human reads. It is rendered from the registry,
never authored freehand, so every run reads the same way: a verdict, at most
three items to decide now, what was cleared, what was not tested. Everything
else stays in the full report and dashboard.

Body budget is 150 words by default; the renderer fails rather than exceed it.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from report_contract import (
    evidence_by_id,
    humanize_text,
    item_label_map,
    plain_category_label,
    severity_label,
)

ACTIVE = {"open", "needs-verification"}
SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
EFFORT_LABELS = {"S": "small", "M": "medium", "L": "large"}


def load(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"FAIL: {path} must contain an object")
    return data


def first_sentence(text: str) -> str:
    text = " ".join(str(text or "").split())
    match = re.match(r"(.+?[.!?])(?:\s|$)", text)
    return (match.group(1) if match else text).strip()


def clip(text: str, limit: int) -> str:
    words = text.split()
    if len(words) <= limit:
        return text
    head = words[:limit]
    # Prefer a clause boundary so the cut reads as a phrase, not a stump.
    for index in range(len(head) - 1, max(2, limit // 2) - 1, -1):
        if head[index].endswith((",", ";", ":")):
            head = head[: index + 1]
            break
    return " ".join(head).rstrip(",;:") + "…"


def strip_period(text: str) -> str:
    return text.rstrip(". ")


def category_text(key: Any) -> str:
    label = plain_category_label(str(key or ""))
    return label.replace("_", " ").replace("-", " ")


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'’-]*", text))


def decision_for(decisions: dict[str, Any], item_id: str) -> str | None:
    for row in decisions.get("decisions", []) or []:
        if row.get("finding_id") == item_id:
            return str(row.get("decision") or "") or None
    return None


def prioritized(registry: dict[str, Any]) -> list[dict[str, Any]]:
    by_id = {item["id"]: item for item in registry.get("items", [])}
    ordered: list[dict[str, Any]] = []
    for item_id in registry.get("presentation", {}).get("prioritized_finding_ids", []) or []:
        item = by_id.get(item_id)
        if item and item.get("status") in ACTIVE:
            ordered.append(item)
    seen = {item["id"] for item in ordered}
    rest = [
        item
        for item in by_id.values()
        if item.get("kind") == "finding" and item.get("status") in ACTIVE and item["id"] not in seen
    ]
    rest.sort(key=lambda item: (SEVERITY_RANK.get(str(item.get("severity")), 9), item["id"]))
    return ordered + rest


def effort_label(item: dict[str, Any]) -> str:
    packet = item.get("fix_packet")
    if isinstance(packet, dict) and packet.get("effort") in EFFORT_LABELS:
        return EFFORT_LABELS[packet["effort"]]
    return "not estimated"


def evidence_hint(item: dict[str, Any], assets: dict[str, dict[str, Any]]) -> str:
    for ref in item.get("evidence_refs") or []:
        asset = assets.get(ref) or {}
        if asset.get("kind") == "screenshot":
            caption = asset.get("caption") or asset.get("description") or ""
            return first_sentence(caption)
    return ""


def render(registry: dict[str, Any], context: dict[str, Any], decisions: dict[str, Any], *, limit: int) -> str:
    items = registry.get("items", [])
    labels = item_label_map(items)
    assets = evidence_by_id(context) if context else {}
    plain = lambda value: humanize_text(value, item_labels=labels, evidence_assets=assets)  # noqa: E731

    active_findings = [i for i in items if i.get("kind") == "finding" and i.get("status") in ACTIVE]
    active_enh = [i for i in items if i.get("kind") == "enhancement" and i.get("status") in ACTIVE]
    cleared = [i for i in items if i.get("status") == "cleared"]
    fixed = [i for i in items if i.get("status") == "fixed"]
    not_run = [str(v) for v in (context.get("checks_not_run") or [])]
    outcome = context.get("outcome") or {}
    target = str(registry.get("target") or context.get("title") or "the target")
    revision = str(registry.get("revision_id") or "")

    lines: list[str] = []
    title = f"# Audit brief — {target}"
    if revision:
        title += f" ({revision})"
    lines.append(title)
    lines.append("")
    verdict = plain(outcome.get("label") or ("Findings need a decision" if active_findings else "No open findings"))
    counts = f"{len(active_findings)} finding{'s' if len(active_findings) != 1 else ''} to decide"
    if active_enh:
        counts += f", {len(active_enh)} optional improvement{'s' if len(active_enh) != 1 else ''}"
    if fixed:
        counts += f", {len(fixed)} fixed since last time"
    lines.append(f"**Verdict:** {verdict}. {counts}.")
    lines.append("")

    top = prioritized(registry)[:limit]
    lines.append("## Decide now")
    lines.append("")
    if not top:
        lines.append("Nothing is waiting on you.")
    for index, item in enumerate(top, start=1):
        lead = clip(plain(item.get("plain") or item.get("title") or ""), 20)
        fix = clip(strip_period(first_sentence(plain(item.get("recommendation") or ""))), 14)
        decided = decision_for(decisions, item["id"])
        tail = f" Already {decided}d." if decided in {"approve", "defer", "reject"} else ""
        hint = evidence_hint(item, assets)
        hint_text = f" Look at: {hint}" if hint else ""
        effort = effort_label(item)
        effort_text = f" Effort: {effort}." if effort != "not estimated" else ""
        lines.append(
            f"{index}. **{strip_period(lead)}** — {severity_label(item)}, {category_text(item.get('category'))}. "
            f"Fix: {fix}{'' if fix.endswith('…') else '.'}{effort_text}{tail}{hint_text}"
        )
    lines.append("")

    lines.append("## Cleared")
    lines.append("")
    if cleared:
        names = [clip(strip_period(plain(i.get("plain") or i.get("title") or "")), 9) for i in cleared[:2]]
        more = f" and {len(cleared) - 2} more" if len(cleared) > 2 else ""
        lines.append(f"{len(cleared)} suspicion{'s' if len(cleared) != 1 else ''} checked and dismissed: " + "; ".join(names) + more + ".")
    else:
        lines.append("No suspicions were cleared this run.")
    lines.append("")

    lines.append("## Not tested")
    lines.append("")
    if not_run:
        shown = [clip(strip_period(first_sentence(plain(v))), 9) for v in not_run[:2]]
        more = f" and {len(not_run) - 2} more" if len(not_run) > 2 else ""
        lines.append("; ".join(shown) + more + ".")
    else:
        lines.append("Every planned check ran.")
    lines.append("")
    lines.append("_Full findings, evidence, and history are in the report and dashboard._")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("registry", type=Path)
    parser.add_argument("--context", type=Path)
    parser.add_argument("--decisions", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--limit", type=int, default=3, help="items in Decide now (max 3)")
    parser.add_argument("--max-words", type=int, default=150, help="body word budget")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    limit = max(1, min(3, args.limit))
    text = render(load(args.registry), load(args.context), load(args.decisions), limit=limit)
    body = "\n".join(
        line for line in text.splitlines() if not line.startswith("#") and not line.startswith("_Full findings")
    )
    words = word_count(body)
    if words > args.max_words:
        raise SystemExit(f"FAIL: brief body is {words} words; budget is {args.max_words}")
    if args.output:
        args.output.write_text(text, encoding="utf-8")
        print(f"PASS: brief rendered to {args.output} ({words} words)")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
