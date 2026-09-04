#!/usr/bin/env python3
"""Regressions for the scan entry and shareable one-pager."""
from __future__ import annotations

import hashlib
from html import escape
import json
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


def assert_audit_dashboard_handoff() -> None:
    """The audit dashboard must emit an instruction, not only the decisions.

    Copying decisions hands an agent data with no task attached, which is how
    approvals accumulated without anything implementing them. The handoff names
    the verifier and the artifact so the receiving session knows what proof it
    owes.
    """
    source = (ROOT / "scripts" / "render_dashboard.py").read_text(encoding="utf-8")
    for fragment in (
        'id="copy-handoff"',
        "Copy AI handoff",
        "scripts/verify_fixes.py --execute",
        "write verification.json into",
        "do not change item status",
    ):
        assert fragment in source, f"audit dashboard handoff lost: {fragment}"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, *args], capture_output=True, text=True)


def main() -> int:
    assert_archetype_registry()
    assert_audit_dashboard_handoff()
    if "--archetypes-only" in sys.argv:
        print("PASS: archetype registry headings and probe coverage resolve, including universal, lookup, ingestion, and multi-channel service modules")
        return 0
    with tempfile.TemporaryDirectory(prefix="scruffy-product-") as directory:
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
        findings = ROOT / "evals" / "continuity" / "revision.json"
        context = ROOT / "evals" / "continuity" / "context.json"
        result = run(str(ROOT / "scripts" / "render_onepager.py"), str(findings), str(context), str(pager))
        assert result.returncode == 0, result.stderr
        html = pager.read_text()
        digest = hashlib.sha256(findings.read_bytes()).hexdigest()
        assert digest in html, "receipt must embed the real registry hash"
        assert "REGISTRY SUMMARY" in html and "does not certify" in html
        assert "validator-enforced" not in html and "nothing hidden" not in html
        from render_onepager import score_order
        mixed = [{"score": "0 · clear"}, {"score": "N/A"}, {"score": 3}, {"score": "2 · material"}]
        assert [r["score"] for r in sorted(mixed, key=score_order)] == [3, "2 · material", "0 · clear", "N/A"]
        assert html.index("2 · material") < html.index("0 · clear")
        for fragment in ("Strengths worth preserving", "worst first", "overflow-wrap:anywhere"):
            assert fragment in html, fragment
        # A low-severity item first in source must not crowd out a critical one.
        data = json.loads(findings.read_text())
        active = [i for i in data["items"] if i["kind"] == "finding" and i["status"] in {"open", "needs-verification"}]
        active[0]["severity"], active[-1]["severity"] = "low", "critical"
        source = base / "findings.json"
        source.write_text(json.dumps(data))
        result = run(str(ROOT / "scripts" / "render_onepager.py"), str(source), str(context), str(pager))
        assert result.returncode == 0, result.stderr
        html = pager.read_text()
        assert escape(active[-1]["title"]) in html
        # A malformed registry must not produce a new summary or clobber an old one.
        source.write_text(json.dumps({"audit_id": "fake", "revision_id": "fake", "items": []}))
        result = run(str(ROOT / "scripts" / "render_onepager.py"), str(source), str(context), str(pager))
        assert result.returncode != 0
        assert pager.read_text() == html
        for malformed in ([], None):
            source.write_text(json.dumps(malformed))
            result = run(str(ROOT / "scripts" / "render_onepager.py"), str(source), str(context), str(pager))
            assert result.returncode != 0 and "root must be an object" in result.stderr
            assert "Traceback" not in result.stderr and pager.read_text() == html
            result = run(str(ROOT / "scripts" / "render_onepager.py"), str(findings), str(source), str(pager))
            assert result.returncode != 0 and "root must be an object" in result.stderr
            assert "Traceback" not in result.stderr and pager.read_text() == html
    print("PASS: scan leads and operated checks; shipped one-pager fixture, ordering, truthful receipt, invalid-input refusal")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        sys.exit(1)
