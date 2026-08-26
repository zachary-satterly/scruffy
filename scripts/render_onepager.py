#!/usr/bin/env python3
"""Shareable one-pager (bet B2): verdict, worst-first ledger, strengths, process badge.

The badge asserts process, never quality: audited, revision, registry hash.
Single self-contained file; no fake scores anywhere.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from report_contract import referral_rows, score_row_label


def esc(value: object) -> str:
    return (str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("findings", type=Path)
    parser.add_argument("context", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    registry = json.loads(args.findings.read_text(encoding="utf-8"))
    context = json.loads(args.context.read_text(encoding="utf-8"))
    digest = hashlib.sha256(args.findings.read_bytes()).hexdigest()
    outcome = context.get("outcome", {})
    scores = list(context.get("scores", []))
    scores.sort(key=lambda row: (0, -row["score"]) if isinstance(row.get("score"), int) else (1, 0))
    strengths = [i for i in registry["items"] if i["kind"] == "strength"]
    open_findings = [i for i in registry["items"] if i["kind"] == "finding" and i["status"] in {"open", "needs-verification"}]
    open_assumptions = [row for row in context.get("assumptions", []) if row.get("status") == "open"]
    rows = "".join(
        f'<tr><td>{esc(score_row_label(row.get("category")))}</td>'
        f'<td class="num">{esc(row.get("score"))}</td><td>{esc(row.get("evidence", ""))}</td></tr>'
        for row in scores
    )
    strength_list = "".join(f"<li><b>{esc(s['id'])}</b> {esc(s['title'])}</li>" for s in strengths[:3])
    finding_list = "".join(f"<li><b>{esc(f['id'])}</b> {esc(f['title'])} · {esc(f['severity'])}</li>" for f in open_findings[:3])
    referral_list = "".join(
        f"<li><b>{esc(row[0])}</b> {esc(row[1])} Boundary: {esc(row[4])} "
        f"Supporting records: {esc(row[5])} Specialist result: {esc(row[6])}</li>"
        for row in referral_rows(context)
    )
    assumption_list = "".join(
        f"<li>{esc(row.get('statement', ''))} Evidence needed: {esc(row.get('evidence_needed', ''))}</li>"
        for row in open_assumptions
    )
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(context.get('title','Scruffy audit'))}</title>
<style>
*{{box-sizing:border-box;margin:0}}:root{{--ink:#141414;--mut:#5c5c56;--accent:#c8102e;--line:#d9d9d2}}
body{{font:15px/1.55 Georgia,serif;color:var(--ink);background:#fcfcfa;max-width:820px;margin:0 auto;padding:34px 22px}}
.micro{{font:700 10.5px/1.4 "Helvetica Neue",Arial,sans-serif;letter-spacing:.14em;text-transform:uppercase;color:var(--mut)}}
h1{{font:600 clamp(22px,4vw,34px)/1.12 Georgia,serif;margin:8px 0 12px;border-bottom:3px double var(--ink);padding-bottom:14px}}
table{{width:100%;border-collapse:collapse;font:13.5px/1.5 "Helvetica Neue",Arial,sans-serif;margin:14px 0}}
th{{text-align:left;font:700 10.5px/1.4 Arial;letter-spacing:.1em;text-transform:uppercase;border-bottom:1.5px solid var(--ink);padding:6px 8px}}
td{{padding:7px 8px;border-bottom:1px solid var(--line);vertical-align:top;overflow-wrap:anywhere}}td.num{{font-weight:700;min-width:0}}
h2{{font:700 11px/1.4 Arial;letter-spacing:.14em;text-transform:uppercase;margin:20px 0 6px}}
ul{{padding-left:20px}}li{{margin:4px 0}}
.badge{{margin-top:26px;padding:13px 15px;border:1.5px solid var(--ink);font:12.5px/1.6 "Helvetica Neue",Arial,sans-serif}}
.badge b{{letter-spacing:.05em}} .badge code{{font:11px/1 ui-monospace,monospace;overflow-wrap:anywhere}}
@media print{{body{{padding:0}}}}
</style></head><body>
<p class="micro">Scruffy audit · {esc(registry['audit_id'])} · revision {esc(registry['revision_id'])} · nothing hidden</p>
<h1>{esc(outcome.get('label',''))} — {esc(outcome.get('summary','').split('.')[0])}.</h1>
<h2>The eight slop categories, worst first</h2>
<table><tr><th>Category</th><th>Score</th><th>Evidence</th></tr>{rows}</table>
<h2>Top open findings</h2><ul>{finding_list or '<li>None open.</li>'}</ul>
<h2>Strengths worth preserving</h2><ul>{strength_list or '<li>None recorded.</li>'}</ul>
<h2>Open assumptions</h2><ul>{assumption_list or '<li>None recorded.</li>'}</ul>
<h2>Specialist boundaries</h2><ul>{referral_list or '<li>No specialist referrals recorded.</li>'}</ul>
<div class="badge"><b>SCRUFFY-AUDITED · PROCESS CLAIM ONLY</b><br>
This badge asserts that a durable, validator-enforced audit registry exists for this
target and that no prior item was silently dropped. It asserts nothing about quality.
Registry SHA-256: <code>{digest}</code></div>
</body></html>"""
    args.output.write_text(html, encoding="utf-8")
    print(f"PASS: one-pager written to {args.output} (registry sha256 {digest[:12]}…)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
