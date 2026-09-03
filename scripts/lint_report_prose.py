#!/usr/bin/env python3
"""Lint reader-facing audit prose for cognitive-load slop. Leads, never verdicts.

Scans the reader-facing fields of a findings registry and its context document
against the cognitive_load signals in schema/sentence-slop-pack.json. Exit 0
unless --strict, so it informs authors without gating pipelines by default.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACK = json.loads((ROOT / "schema" / "sentence-slop-pack.json").read_text(encoding="utf-8"))
SIGNALS = {row["code"]: row for row in PACK["signals"] if row["family"] == "cognitive_load"}
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
WORD = re.compile(r"[A-Za-z0-9'’-]+")

READER_FIELDS_ITEM = ("plain", "title", "observation", "user_impact", "cause", "recommendation")

# The plain lead is the one field a reader who does not know the taxonomy can
# use. It is budgeted, not merely present: a lead that runs to four clauses has
# become the record it was supposed to introduce.
PLAIN_WORD_BUDGET = 32
# The audit's private vocabulary. A reader's own domain terms are not jargon;
# these are words that exist only because the taxonomy exists.
AUDIT_JARGON = re.compile(
    r"\b(information[_ ]architecture|backend[_ ]shape|trust[_ ]integrity"
    r"|resilience[_ ]recovery|localization[_ ]adaptability|agent[_ ]ai[_ ]behavior"
    r"|privacy[_ ]safety[_ ]ux|editorial slop|product slop|interaction slop"
    r"|visual slop|structural cause|identity[_ ]key|revision disposition"
    r"|acceptance check|evidence receipt|facet|registry item)\b",
    re.IGNORECASE,
)


def check_plain_lead(item: dict, leads: list[dict]) -> None:
    """
    The lead exists, fits its budget, and is written for the reader.

    This is the check that would have caught scruffy's own report. Every
    reader-facing field was populated and correct, and the finding was still
    unreadable, because all six fields spoke in the same register and none of
    them said the plain thing first.
    """
    base = f"items[{item.get('id','?')}]"
    if item.get("kind") not in {"finding", "enhancement", "strength"}:
        return
    text = item.get("plain")
    if not isinstance(text, str) or not text.strip():
        leads.append({"code": "missing_plain_lead", "path": f"{base}.plain",
                      "measure": "absent",
                      "snippet": str(item.get("title", ""))[:110]})
        return
    words = len(WORD.findall(text))
    if words > PLAIN_WORD_BUDGET:
        leads.append({"code": "missing_plain_lead", "path": f"{base}.plain",
                      "measure": f"{words} words, budget {PLAIN_WORD_BUDGET}",
                      "snippet": text[:110]})
    hits = sorted({m.group(0).lower() for m in AUDIT_JARGON.finditer(text)})
    if hits:
        leads.append({"code": "jargon_lead", "path": f"{base}.plain",
                      "measure": ", ".join(hits),
                      "snippet": text[:110]})
LIST_MARKER = re.compile(r"(?:^|\s)(?:\d+\)|\d+\.|·|—|-)\s")


def sentences(text: str) -> list[str]:
    return [s.strip() for s in SENTENCE_SPLIT.split(text) if s.strip()]


def check_text(path: str, text: str, leads: list[dict]) -> None:
    if not isinstance(text, str) or not text.strip():
        return
    for sentence in sentences(text):
        words = len(WORD.findall(sentence))
        enumerated = len(LIST_MARKER.findall(sentence)) >= 2 or sentence.count(",") >= 4 and ";" not in sentence and words > 35 and False
        if words > 35 and "overlong_sentence" in SIGNALS and not (len(LIST_MARKER.findall(sentence)) >= 2):
            leads.append({"code": "overlong_sentence", "path": path, "measure": f"{words} words", "snippet": sentence[:110]})
        if (sentence.count(";") >= 2 or sentence.count(",") >= 5) and "clause_pileup" in SIGNALS:
            leads.append({"code": "clause_pileup", "path": path, "measure": f"{sentence.count(';')} semicolons, {sentence.count(',')} commas", "snippet": sentence[:110]})
        if sentence.count("(") >= 2 and "parenthetical_stacking" in SIGNALS:
            leads.append({"code": "parenthetical_stacking", "path": path, "measure": f"{sentence.count('(')} parentheticals", "snippet": sentence[:110]})
    words_total = len(WORD.findall(text))
    if words_total > 90 and "\n" not in text and not LIST_MARKER.search(text) and "wall_paragraph" in SIGNALS:
        leads.append({"code": "wall_paragraph", "path": path, "measure": f"{words_total} words, no list structure", "snippet": text[:110]})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("findings", type=Path)
    parser.add_argument("--context", type=Path)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    registry = json.loads(args.findings.read_text(encoding="utf-8"))
    leads: list[dict] = []
    for item in registry.get("items", []):
        base = f"items[{item.get('id','?')}]"
        check_plain_lead(item, leads)
        for field in READER_FIELDS_ITEM:
            check_text(f"{base}.{field}", item.get(field), leads)
        for index, entry in enumerate(item.get("evidence", []) or []):
            check_text(f"{base}.evidence[{index}]", entry, leads)
    if args.context:
        context = json.loads(args.context.read_text(encoding="utf-8"))
        check_text("outcome.summary", context.get("outcome", {}).get("summary"), leads)
        check_text("outcome.confidence", context.get("outcome", {}).get("confidence"), leads)
        for task in context.get("tasks", []):
            check_text(f"tasks[{task.get('id','?')}].result", task.get("result"), leads)
        for row in context.get("capabilities", []):
            check_text(f"capabilities[{row.get('key','?')}].scope", row.get("scope"), leads)
        for index, row in enumerate(context.get("checks_not_run", [])):
            if isinstance(row, dict):
                for field in ("reason", "impact"):
                    check_text(f"checks_not_run[{index}].{field}", row.get(field), leads)
            else:
                # Legacy schema-2.0 contexts carry plain strings here.
                check_text(f"checks_not_run[{index}]", row, leads)

    for lead in leads:
        signal = SIGNALS[lead["code"]]
        lead.update({"family": "cognitive_load", "severity": "suggestion",
                     "citation": signal["citation"], "false_positive_guard": signal["false_positive_guard"]})
    payload = {"schema_version": "1.0", "tool": "lint_report_prose",
               "lead_count": len(leads), "leads": leads,
               "authorship_assessment": "not_performed",
               "note": "Cognitive-load leads on reader-facing audit prose. Rewrite or justify; never treat as verdicts."}
    rendered = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    summary = {}
    for lead in leads:
        summary[lead["code"]] = summary.get(lead["code"], 0) + 1
    verdictline = ", ".join(f"{k}×{v}" for k, v in sorted(summary.items())) or "no leads"
    print(f"{'FAIL' if (args.strict and leads) else 'PASS'}: {len(leads)} cognitive-load leads ({verdictline})")
    if not args.output and leads:
        for lead in leads[:12]:
            print(f"  {lead['code']:24} {lead['path']:34} {lead['measure']}")
    return 1 if (args.strict and leads) else 0


if __name__ == "__main__":
    sys.exit(main())
