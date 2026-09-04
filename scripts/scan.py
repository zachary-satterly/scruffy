#!/usr/bin/env python3
"""Instant scan (bet B1): URL or file -> static leads + operated checklist + feedback.

The 60-second front door. Honest by construction: static leads are suspicions,
and the output names the checks that only an operated audit can run.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import urllib.request
from contextlib import contextmanager
from collections.abc import Iterator
from pathlib import Path

from rule_engine import DEFAULT_RULES_DIR, evaluate_page, load_packs, validate_packs

SEVERITY_ORDER = {"error": 0, "warning": 1, "suggestion": 2}


MAX_HTML_BYTES = 10 * 1024 * 1024


@contextmanager
def acquire(target: str) -> Iterator[tuple[Path, str]]:
    if target.startswith(("http://", "https://")):
        request = urllib.request.Request(target, headers={"User-Agent": "scruffy-scan"})
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read(MAX_HTML_BYTES + 1)
        if len(raw) > MAX_HTML_BYTES:
            raise ValueError(f"HTML exceeds {MAX_HTML_BYTES} bytes")
        with tempfile.TemporaryDirectory(prefix="scruffy-scan-") as directory:
            path = Path(directory) / "page.html"
            path.write_text(raw.decode("utf-8", errors="replace"), encoding="utf-8")
            yield path, target
    else:
        path = Path(target)
        if not path.is_file():
            raise ValueError(f"{target} is neither a URL nor a file")
        if path.stat().st_size > MAX_HTML_BYTES:
            raise ValueError(f"HTML exceeds {MAX_HTML_BYTES} bytes")
        yield path, str(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="URL or local HTML file")
    parser.add_argument("--rules-dir", type=Path, default=DEFAULT_RULES_DIR)
    parser.add_argument("--pack", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    packs = load_packs(args.rules_dir, args.pack)
    validate_packs(packs)
    if args.output and not args.target.startswith(("http://", "https://")) and args.output.resolve() == Path(args.target).resolve():
        parser.error("--output must not overwrite the scanned file")
    try:
        with acquire(args.target) as (page, origin):
            leads = evaluate_page(page, packs)
    except (OSError, ValueError) as error:
        parser.exit(1, f"FAIL: could not scan target: {error}\n")
    checklist = [
        {"rule_id": r["id"], "category": r["category"], "instruction": r["predicate"]["instruction"],
         "citation": r["citation"]}
        for p in packs for r in p["rules"] if r["predicate"]["type"] == "operated_check"
    ]
    leads = [l for l in leads if l["rule_id"] not in {c["rule_id"] for c in checklist}]
    leads.sort(key=lambda l: SEVERITY_ORDER.get(l["severity"], 9))
    payload = {
        "schema_version": "1.0", "tool": "scan", "target": origin,
        "lead_count": len(leads), "leads": leads,
        "operated_checklist": checklist,
        "authorship_assessment": "not_performed",
        "honesty": ("A scan reads markup. It cannot click, submit, reload, or recover. "
                    f"The {len(checklist)} checks above require operating the interface — that is the audit."),
    }
    if args.output:
        args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    counts: dict[str, int] = {}
    for lead in leads:
        counts[lead["severity"]] = counts.get(lead["severity"], 0) + 1
    mix = ", ".join(f"{v} {k}" for k, v in sorted(counts.items(), key=lambda i: SEVERITY_ORDER[i[0]])) or "none"
    print(f"PASS: scanned {origin} — {len(leads)} leads ({mix}); {len(checklist)} operated checks pending")
    for lead in leads[:10]:
        print(f"  {lead['severity']:10} {lead['rule_id']:26} {lead['snippet'][:70]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
