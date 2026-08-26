#!/usr/bin/env python3
"""Regressions for the scan entry (B1) and one-pager (B2)."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def assert_archetype_registry() -> None:
    reference = (ROOT / "references" / "archetypes.md").read_text(encoding="utf-8")
    payload = json.loads((ROOT / "evals" / "archetypes.json").read_text(encoding="utf-8"))
    cases = payload.get("cases")
    assert isinstance(cases, list) and cases, "archetype registry must contain cases"
    keys = [case.get("archetype") for case in cases]
    assert len(keys) == len(set(keys)), "archetype keys must be unique"
    for case in cases:
        heading = case.get("reference_heading")
        probes = case.get("required_probes")
        assert isinstance(heading, str) and f"## {heading}" in reference, (
            f"archetype heading is absent from references/archetypes.md: {heading}"
        )
        assert isinstance(probes, list) and len(probes) >= 6 and len(probes) == len(set(probes)), (
            f"archetype needs at least six unique probes: {case.get('archetype')}"
        )
    for required in (
        "universal-web-interface",
        "lookup-identity-resolution",
        "file-media-ingestion",
        "multi-channel-service-blueprint",
    ):
        assert required in keys, f"missing product-surface regression: {required}"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, *args], capture_output=True, text=True)


def main() -> int:
    assert_archetype_registry()
    if "--archetypes-only" in sys.argv:
        print("PASS: archetype registry headings and probe coverage resolve, including universal, lookup, ingestion, and multi-channel service modules")
        return 0
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    badge = re.search(
        r'<a href="([^"]+)"><img[^>]+alt="README AI-slop reviewed"',
        readme,
    )
    assert badge, "README review badge must link to its current receipt"
    receipt_path = Path(badge.group(1))
    assert receipt_path.parent == Path("evals/sentence-slop") and ".." not in receipt_path.parts
    receipt = (ROOT / receipt_path).read_text(encoding="utf-8")
    match = re.search(r"Target SHA-256: `([a-f0-9]{64})`", receipt)
    assert match, "README review receipt must bind the target hash"
    assert match.group(1) == hashlib.sha256((ROOT / "README.md").read_bytes()).hexdigest(), (
        "README changed after its badge-linked review receipt"
    )

    with tempfile.TemporaryDirectory(prefix="scruffy-product-") as directory:
        onepager_checked = False
        base = Path(directory)
        out = base / "scan.json"
        result = run(str(ROOT / "scripts" / "scan.py"),
                     str(ROOT / "evals" / "web-fixtures" / "settings-form.html"),
                     "--output", str(out))
        assert result.returncode == 0, result.stderr
        payload = json.loads(out.read_text())
        assert payload["lead_count"] >= 3, "settings fixture must yield static leads"
        assert payload["operated_checklist"], "checklist must ship with every scan"
        assert payload["authorship_assessment"] == "not_performed"
        assert "cannot click" in payload["honesty"]
        lead_ids = {l["rule_id"] for l in payload["leads"]}
        assert "OP-UNLABELED-INPUT" in lead_ids and "OP-DIV-BUTTON" in lead_ids, lead_ids
        assert not lead_ids & {c["rule_id"] for c in payload["operated_checklist"]}

        pager = base / "onepager.html"
        findings = ROOT.parent / "one-more-photo-audit" / "findings-r2.json"
        context = ROOT.parent / "one-more-photo-audit" / "context-r2.json"
        if findings.is_file():
            onepager_checked = True
            result = run(str(ROOT / "scripts" / "render_onepager.py"), str(findings), str(context), str(pager))
            assert result.returncode == 0, result.stderr
            html = pager.read_text()
            digest = hashlib.sha256(findings.read_bytes()).hexdigest()
            assert digest in html, "badge must embed the real registry hash"
            assert "PROCESS CLAIM ONLY" in html and "asserts nothing about quality" in html
            for fragment in ("Strengths worth preserving", "worst first", "overflow-wrap:anywhere"):
                assert fragment in html, fragment
            for banned in ("/100", "grade", "score:"):
                assert banned not in html.lower(), f"fake-score artifact: {banned}"
    suffix = (
        "one-pager carries a process-only badge with the real registry hash"
        if onepager_checked
        else "SKIP: optional external one-pager fixture was unavailable"
    )
    print(
        "PASS: README review badge resolves to its current hash-bound receipt; "
        f"scan entry yields honest leads plus operated checklist; {suffix}"
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        sys.exit(1)
