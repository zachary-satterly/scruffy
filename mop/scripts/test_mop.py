#!/usr/bin/env python3
"""Tests for Scruffy repair bundle ingestion, gating, planning, and handoff.

Dependency-free. Run directly: ``python3 scripts/test_mop.py``.
"""
from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
from pathlib import Path

from mop_bundle import (
    InteropError,
    approved_item_ids,
    build_plan,
    gate_state,
    load_bundle,
    load_interop,
)
from mop_handoff import build_handoff

REPO = Path(__file__).resolve().parent.parent
FIXTURE = REPO / "fixtures" / "sample-audit"
INTEROP = load_interop()


def _bundle():
    return load_bundle(FIXTURE, INTEROP)


def _write_json(path: Path, document: dict) -> None:
    path.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")


def _repeat_bundle(directory: Path) -> Path:
    """Derive a legitimate r2 bundle from the shipped canonical r1 fixture."""
    current = directory / "current"
    shutil.copytree(FIXTURE, current)

    findings_path = current / "findings.json"
    findings = json.loads(findings_path.read_text(encoding="utf-8"))
    findings["revision_id"] = "r2"
    findings["baseline_revision_id"] = "r1"
    for item in findings["items"]:
        item["last_observed_revision"] = "r2"
        item["revision_disposition"] = "carried"
        item["disposition_reason"] = "Unchanged from the validated r1 baseline."
    _write_json(findings_path, findings)

    context_path = current / "context.json"
    context = json.loads(context_path.read_text(encoding="utf-8"))
    context["revision_id"] = "r2"
    context["baseline_revision_id"] = "r1"
    for ledger_name in ("routing", "assumptions", "referrals"):
        for row in context[ledger_name]:
            row["last_observed_revision"] = "r2"
            row["revision_disposition"] = "carried"
            row["disposition_reason"] = "Unchanged from the validated r1 baseline."
    _write_json(context_path, context)

    decisions_path = current / "decisions.json"
    decisions = json.loads(decisions_path.read_text(encoding="utf-8"))
    decisions["revision_id"] = "r2"
    decisions["baseline_revision_id"] = "r1"
    _write_json(decisions_path, decisions)
    return current


def test_load_and_validate_fixture():
    b = _bundle()
    assert b["findings"]["audit_id"] == "acme-billing"
    assert b["context"]["schema_version"] == "1.2"
    assert b["tokens"] is not None, "optional tokens.json should load when present"


def test_reject_unknown_major_schema():
    b = _bundle()
    b = copy.deepcopy(b)
    b["findings"]["schema_version"] = "3.0"
    try:
        from mop_bundle import validate_versions
        validate_versions(b, INTEROP)
    except InteropError as exc:
        assert "major" in str(exc)
        return
    raise AssertionError("unknown major schema must fail closed")


def test_reject_unknown_minor_schema():
    from mop_bundle import validate_versions
    b = copy.deepcopy(_bundle())
    b["context"]["schema_version"] = "1.9"
    try:
        validate_versions(b, INTEROP)
    except InteropError:
        return
    raise AssertionError("unrecognized minor schema must fail closed")


def test_legacy_schema_is_readable_with_note():
    from mop_bundle import validate_versions
    b = copy.deepcopy(_bundle())
    b["findings"]["schema_version"] = "2.0"  # legacy, readable
    notes = validate_versions(b, INTEROP)
    assert any("legacy" in n for n in notes), "legacy schema should produce a note"


def test_context_1_1_remains_readable_with_note():
    from mop_bundle import validate_versions
    b = copy.deepcopy(_bundle())
    b["context"]["schema_version"] = "1.1"
    notes = validate_versions(b, INTEROP)
    assert any("context.json is legacy schema 1.1" in n for n in notes), notes


def test_malformed_context_1_2_fails_scruffy_canonical_validation():
    with tempfile.TemporaryDirectory(prefix="scruffy-mop-context-") as directory:
        copied = Path(directory) / "bundle"
        shutil.copytree(FIXTURE, copied)
        context_path = copied / "context.json"
        context = json.loads(context_path.read_text(encoding="utf-8"))
        context["routing"].pop()
        context_path.write_text(json.dumps(context), encoding="utf-8")
        try:
            load_bundle(copied, INTEROP)
        except InteropError as exc:
            assert "canonical context-1.2 validation" in str(exc), exc
            assert "routing must cover exactly" in str(exc), exc
            return
    raise AssertionError("Mop accepted a malformed current Scruffy context")


def test_repeat_context_1_2_load_check_and_plan_accept_r1_baseline():
    import subprocess

    with tempfile.TemporaryDirectory(prefix="scruffy-mop-repeat-") as directory:
        current = _repeat_bundle(Path(directory))
        bundle = load_bundle(current, INTEROP, baseline_source=FIXTURE)
        assert bundle["findings"]["revision_id"] == "r2"
        assert bundle["context"]["baseline_revision_id"] == "r1"

        script = REPO / "scripts" / "mop_bundle.py"
        for command in ("check", "plan"):
            argv = [
                sys.executable,
                str(script),
                command,
                str(current),
                "--baseline-bundle",
                str(FIXTURE),
            ]
            if command == "plan":
                argv.append("--json")
            result = subprocess.run(argv, text=True, capture_output=True, check=False)
            assert result.returncode == 0, result.stdout + result.stderr
            assert "r2" in result.stdout, result.stdout


def test_repeat_context_1_2_without_baseline_fails_closed():
    with tempfile.TemporaryDirectory(prefix="scruffy-mop-repeat-") as directory:
        current = _repeat_bundle(Path(directory))
        try:
            load_bundle(current, INTEROP)
        except InteropError as exc:
            assert "repeat context-1.2 bundle requires" in str(exc), exc
            assert "--baseline-bundle" in str(exc), exc
            return
    raise AssertionError("Mop accepted a repeat context-1.2 bundle without its baseline")


def test_repeat_context_1_2_malformed_with_baseline_still_fails_closed():
    with tempfile.TemporaryDirectory(prefix="scruffy-mop-repeat-") as directory:
        current = _repeat_bundle(Path(directory))
        context_path = current / "context.json"
        context = json.loads(context_path.read_text(encoding="utf-8"))
        context["routing"].pop()
        _write_json(context_path, context)
        try:
            load_bundle(current, INTEROP, baseline_source=FIXTURE)
        except InteropError as exc:
            assert "canonical context-1.2 validation" in str(exc), exc
            assert "routing must cover exactly" in str(exc), exc
            return
    raise AssertionError("Mop accepted a malformed repeat context with a baseline")


def test_missing_required_artifact_fails():
    try:
        load_bundle({"findings.json": FIXTURE / "findings.json",
                     "context.json": FIXTURE / "context.json"}, INTEROP)
    except InteropError as exc:
        assert "decisions.json" in str(exc)
        return
    raise AssertionError("missing decisions.json must fail")


def test_approved_selection_excludes_defer_and_reject():
    approved = approved_item_ids(_bundle())
    assert approved == {"AS-04", "AS-02", "AS-05", "AS-01"}, approved
    assert "AS-03" not in approved  # deferred
    assert "AS-06" not in approved  # rejected


def test_plan_order_respects_depends_on_and_lanes():
    plan = build_plan(_bundle(), INTEROP)
    order = [s["item_id"] for s in plan["steps"]]
    assert order == ["AS-04", "AS-02", "AS-05", "AS-01"], order
    # AS-04 (structural blocker) precedes its dependents.
    assert order.index("AS-04") < order.index("AS-02")
    assert order.index("AS-04") < order.index("AS-05")


def test_enhancement_included_when_approved():
    b = copy.deepcopy(_bundle())
    for d in b["decisions"]["decisions"]:
        if d["item_id"] == "AS-06":
            d["decision"] = "approve"
    plan = build_plan(b, INTEROP)
    assert "AS-06" in [s["item_id"] for s in plan["steps"]]


def test_explicit_work_orders_are_honored():
    b = copy.deepcopy(_bundle())
    b["context"]["work_orders"] = [
        {"id": "WO-2", "lane": 3, "item_ids": ["AS-05", "AS-02"]},
        {"id": "WO-1", "lane": 1, "item_ids": ["AS-04"]},
        {"id": "WO-5", "lane": 5, "item_ids": ["AS-01"]},
    ]
    plan = build_plan(b, INTEROP)
    assert plan["ordering_basis"] == "explicit_work_orders"
    order = [s["item_id"] for s in plan["steps"]]
    # Lane 1 order before lane 3 before lane 5; within WO-2 the given order holds.
    assert order == ["AS-04", "AS-05", "AS-02", "AS-01"], order


def test_dependency_on_nonapproved_is_flagged_not_dropped():
    b = copy.deepcopy(_bundle())
    # Make AS-01 depend on the deferred AS-03.
    for it in b["findings"]["items"]:
        if it["id"] == "AS-01":
            it["depends_on"] = ["AS-03"]
    plan = build_plan(b, INTEROP)
    assert any("AS-03" in w for w in plan["warnings"]), plan["warnings"]


def test_cycle_is_rejected():
    b = copy.deepcopy(_bundle())
    ids = {"AS-04": "AS-02", "AS-02": "AS-04"}
    for it in b["findings"]["items"]:
        if it["id"] in ids:
            it["depends_on"] = [ids[it["id"]]]
    try:
        build_plan(b, INTEROP)
    except InteropError as exc:
        assert "cycle" in str(exc)
        return
    raise AssertionError("a depends_on cycle must be rejected")


def test_approved_but_terminal_item_is_skipped():
    b = copy.deepcopy(_bundle())
    # Approve AS-03 but mark it already fixed: it must be skipped, with a warning.
    for it in b["findings"]["items"]:
        if it["id"] == "AS-03":
            it["status"] = "fixed"
    for d in b["decisions"]["decisions"]:
        if d["item_id"] == "AS-03":
            d["decision"] = "approve"
    plan = build_plan(b, INTEROP)
    ids = [s["item_id"] for s in plan["steps"]]
    assert "AS-03" not in ids, ids
    assert any("AS-03" in w and "already fixed" in w for w in plan["warnings"]), plan["warnings"]


def test_gate_fails_closed_without_authority():
    b = copy.deepcopy(_bundle())
    b["findings"]["run"]["repository_write_authority"] = "not_authorized"
    gate = gate_state(b, INTEROP)
    assert not gate["permissible"]
    # Explicit user grant re-opens it.
    assert gate_state(b, INTEROP, authorized_override=True)["permissible"]


def test_explicit_grant_satisfies_mode_and_authority():
    b = _bundle()
    b = copy.deepcopy(b)
    b["findings"]["run"]["effective_mode"] = "audit"
    b["findings"]["run"]["repository_write_authority"] = "not_authorized"
    from mop_bundle import gate_state
    blocked = gate_state(b, INTEROP, authorized_override=False)
    assert not blocked["permissible"]
    granted = gate_state(b, INTEROP, authorized_override=True)
    assert granted["permissible"], granted["reasons"]
    assert granted["authorized_override"] is True


def test_gate_fails_closed_wrong_mode():
    b = copy.deepcopy(_bundle())
    b["findings"]["run"]["effective_mode"] = "audit"
    gate = gate_state(b, INTEROP)
    assert not gate["permissible"]
    assert any("effective_mode" in r for r in gate["reasons"])


def test_tokens_attach_to_their_item():
    plan = build_plan(_bundle(), INTEROP)
    step = next(s for s in plan["steps"] if s["item_id"] == "AS-02")
    assert step["tokens"] and step["tokens"][0]["name"] == "color.status.pastdue.text"


def test_handoff_never_marks_fixed():
    plan = build_plan(_bundle(), INTEROP)
    work = {
        "AS-04": {"surfaces": ["src/billing/state.ts"],
                  "self_check": [{"check": c, "result": "meets"}
                                 for c in plan["steps"][0]["acceptance_checks"]]},
    }
    handoff = build_handoff(plan, work)
    for it in handoff["items"]:
        assert it["status"] == "implemented-pending-reaudit"
        assert it["status"] not in ("fixed", "cleared")
        assert it["cleared_by"] == "pending Scruffy re-audit"
    assert "AS-02" in handoff["unimplemented"]


def test_handoff_discloses_augmentations():
    plan = build_plan(_bundle(), INTEROP)
    # Default: nothing reported, all three keys present (incl. browser).
    default = build_handoff(plan, {})
    assert default["augmentations"] == {
        "impeccable": "not_reported", "design_reference_search": "not_reported",
        "browser": "not_reported"}
    # Explicit disclosure survives, including a ':detail' suffix.
    h = build_handoff(plan, {}, {"impeccable": "used",
                                 "design_reference_search": "used:mobbin",
                                 "browser": "used"})
    assert h["augmentations"]["design_reference_search"] == "used:mobbin"
    assert h["augmentations"]["browser"] == "used"


def test_handoff_rejects_unknown_augmentation():
    from mop_handoff import _normalize_augmentations
    for bad in ({"nope": "used"}, {"impeccable": "maybe"}):
        try:
            _normalize_augmentations(bad)
        except InteropError:
            continue
        raise AssertionError(f"expected rejection for {bad}")


def test_handoff_rejects_bad_self_check_result():
    plan = build_plan(_bundle(), INTEROP)
    work = {"AS-04": {"surfaces": [], "self_check": [{"check": "x", "result": "done"}]}}
    try:
        build_handoff(plan, work)
    except InteropError:
        return
    raise AssertionError("invalid self_check result must be rejected")


def test_preflight_browser_probe_returns_status():
    from mop_preflight import probe_browser
    r = probe_browser()
    assert r["status"] in ("available", "absent")
    assert "checked" in r and isinstance(r["checked"], list)


def test_preflight_absent_requires_reason():
    from mop_preflight import build_preflight, PreflightError
    # 'absent' without a reason is refused; with a reason it is accepted.
    try:
        build_preflight({"design_reference_search": {"status": "absent"}},
                        browser={"status": "absent", "reason": "test"})
    except PreflightError:
        pass
    else:
        raise AssertionError("absent without reason must be refused")
    ok = build_preflight(
        {"design_reference_search": {"status": "absent", "reason": "MCP call failed"}},
        browser={"status": "absent", "reason": "test"})
    assert ok["augmentations"]["design_reference_search"]["status"] == "absent"


def test_preflight_omission_is_not_run():
    from mop_preflight import build_preflight
    r = build_preflight({}, browser={"status": "available", "tool": "x"})
    assert r["augmentations"]["impeccable"]["status"] == "not_run"
    assert r["augmentations"]["design_reference_search"]["status"] == "not_run"


def test_preflight_maps_to_handoff_vocabulary():
    from mop_preflight import build_preflight, to_handoff_augmentations
    r = build_preflight({"impeccable": {"status": "available"},
                         "design_reference_search": {"status": "absent", "reason": "x"}},
                        browser={"status": "available", "tool": "Chrome"})
    m = to_handoff_augmentations(r)
    assert m == {"browser": "not_reported", "impeccable": "not_reported",
                 "design_reference_search": "absent"}


def _tiny_png(path):
    import base64
    path.write_bytes(base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="))


def test_dashboard_is_self_contained_and_embeds_images(tmp=None):
    import tempfile
    from mop_dashboard import render
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        _tiny_png(d / "s.png")
        (d / "assets.json").write_text(json.dumps({
            "screenshots": [{"path": "s.png", "caption": "shot", "item_ids": ["AS-02"]}],
            "references": [{"path": "s.png", "app": "Linear", "url": "https://m/x",
                            "for_items": ["AS-05"]}],
            "preflight": {"augmentations": {
                "browser": {"status": "available", "tool": "Chrome"},
                "impeccable": {"status": "available"},
                "design_reference_search": {"status": "absent", "reason": "x"}}},
            "directions": {"AS-02": {"recommended": "do X", "principle": "p"}},
        }))
        out = render(FIXTURE, str(d / "assets.json"), str(d / "dash.html"),
                     authorized=True)
        doc = out.read_text()
    assert 'src="data:image/png;base64,' in doc
    import re
    external = [u for u in re.findall(r'src="([^"]+)"', doc) if not u.startswith("data:")]
    assert not external, external
    assert "Payment-status pill" in doc          # an approved item title
    assert "browser=available" in doc            # augmentation disclosure
    assert "Recommended direction" in doc        # direction overlay rendered
    # Decision surface: controls + export present, decision reflects the bundle.
    assert 'data-item-id="AS-02"' in doc
    assert "Copy AI handoff" in doc
    assert "Approve all pending" in doc
    assert "Download decisions.json" in doc
    assert 'dec-approve' in doc                   # AS-02 is approved in the fixture
    for brand_token in ('--paper:#e9eaec', '--surface:#fff', '--ink:#14161a',
                        '--brand:#d40f2e', 'color-scheme:light',
                        '<html lang="en" data-theme="light">'):
        assert brand_token in doc, f"repair dashboard lost canonical brand token {brand_token!r}"
    for retired_theme_marker in ('prefers-color-scheme:dark', 'data-theme=dark',
                                 '--paper:#0e0e10', '--brand:#ff3542'):
        assert retired_theme_marker not in doc, (
            f"repair dashboard restored implicit theme switching {retired_theme_marker!r}"
        )


def test_dashboard_shows_all_items_and_active_decisions():
    import tempfile
    from mop_dashboard import render
    with tempfile.TemporaryDirectory() as d:
        out = render(FIXTURE, None, str(Path(d) / "dash.html"), authorized=True)
        doc = out.read_text()
    # Every registry item is shown, not just approved ones.
    assert "Arbitrary hero gradient" in doc       # AS-03, deferred
    assert "Offer a dark theme" in doc            # AS-06, rejected enhancement
    # Each carries its current decision, and the loop-closing export exists.
    assert 'dec-defer' in doc and 'dec-reject' in doc and 'dec-approve' in doc
    assert 'id="dlBtn"' in doc and "decisions.json" in doc
    assert 'id="copyAllBtn"' in doc
    assert 'id="copyAllBottomBtn"' in doc
    assert 'id="approvePendingBtn"' in doc
    assert 'id="handoffStatus"' in doc
    assert 'data-decision=' in doc                # in-browser decision state
    assert "Choose here &rarr;" not in doc
    assert "Mop implements" not in doc
    assert "Toggle theme" not in doc
    assert ".tt{" not in doc


def test_dashboard_terminal_items_are_read_only_history_and_survive_export():
    from mop_dashboard import build_dashboard_html
    b, plan = _plan()
    terminal_ids = []
    for status, item in zip(("fixed", "cleared", "merged", "superseded"), b["findings"]["items"][:4]):
        item["status"] = status
        terminal_ids.append(item["id"])
    html = build_dashboard_html(b, plan, {}, FIXTURE)
    for item_id, status in zip(terminal_ids, ("Fixed", "Cleared", "Merged", "Superseded")):
        assert f'data-history-item-id="{item_id}"' in html
        assert f'data-registry-item-id="{item_id}"' in html
        assert status in html
        assert f'data-item-id="{item_id}"' not in html
        assert f'"item_id": "{item_id}"' in html
    active_id = b["findings"]["items"][4]["id"]
    assert f'data-item-id="{active_id}"' in html
    assert "var INITIAL_DECISIONS =" in html
    assert "var doc=JSON.parse(JSON.stringify(INITIAL_DECISIONS));" in html


def test_dashboard_hides_direction_groups_when_every_item_is_settled():
    from mop_dashboard import _active_direction_doc
    findings = {"items": [
        {"id": "DONE-1", "kind": "finding", "status": "fixed"},
        {"id": "LIVE-1", "kind": "finding", "status": "open"},
    ]}
    directions = {"schema_version": "1.1", "groups": [
        {"id": "GRP-DONE", "item_ids": ["DONE-1"], "directions": []},
        {"id": "GRP-MIXED", "item_ids": ["DONE-1", "LIVE-1"], "directions": []},
    ]}
    filtered = _active_direction_doc(directions, findings)
    assert [group["id"] for group in filtered["groups"]] == ["GRP-MIXED"]
    assert filtered["groups"][0]["item_ids"] == ["LIVE-1"]
    assert directions["groups"][1]["item_ids"] == ["DONE-1", "LIVE-1"]


def test_dashboard_bulk_approval_changes_only_pending_items():
    import tempfile
    from mop_dashboard import render
    with tempfile.TemporaryDirectory() as d:
        out = render(FIXTURE, None, str(Path(d) / "dash.html"), authorized=True)
        doc = out.read_text()
    assert "if((el.dataset.decision||'pending')!=='pending')return;" in doc
    assert "setDecision(el,'approve');changed+=1;" in doc
    assert "Approved '+changed+' pending item" in doc


def test_dashboard_exports_only_real_decisions_and_copies_both_artifacts_for_ai():
    import tempfile
    from mop_dashboard import render
    from mop_directions import scaffold_directions
    _, plan = _plan()
    directions = _filled(scaffold_directions(plan, None))
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        for name in ("findings.json", "context.json", "decisions.json", "tokens.json"):
            src = FIXTURE / name
            if src.exists():
                (d / name).write_text(src.read_text())
        (d / "directions.json").write_text(json.dumps(directions))
        html = render(d, None, str(d / "dash.html"), authorized=True).read_text()
    assert "document.querySelectorAll('.decide[data-item-id]')" in html
    assert "document.querySelectorAll('.decide').forEach" not in html
    assert "buildAIHandoff" in html
    assert "'decisions.json', '```json'" in html
    assert "'directions.json', '```json'" in html
    assert "Copy failed. Use the JSON downloads." in html


def test_dashboard_unknown_mime_fails_closed():
    import tempfile
    from mop_dashboard import render
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "x.bin").write_bytes(b"\x00\x01")
        (d / "a.json").write_text(json.dumps(
            {"screenshots": [{"path": "x.bin", "item_ids": []}]}))
        try:
            render(FIXTURE, str(d / "a.json"), str(d / "o.html"), authorized=True)
        except InteropError:
            return
    raise AssertionError("unknown MIME must fail closed")


def _plan(authorized=True):
    b = _bundle()
    return b, build_plan(b, INTEROP, authorized)


def test_directions_scaffold_covers_design_lanes_only():
    from mop_directions import DESIGN_CATEGORIES, design_groups, scaffold_directions
    _, plan = _plan()
    doc = scaffold_directions(plan, {"impeccable": {"status": "available"},
                                     "design_reference_search": {"status": "absent"}})
    grouped = {i for g in doc["groups"] for i in g["item_ids"]}
    design = {s["item_id"] for s in plan["steps"] if s["category"] in DESIGN_CATEGORIES}
    assert grouped == design, (grouped, design)
    for g in doc["groups"]:
        assert len(g["directions"]) == 3
        assert sum(1 for d in g["directions"] if d["recommended"]) == 1
        assert g["selected"] is None, "recommended must never be auto-selected"
        assert g["craft_engine"] == "impeccable"
        assert g["grounding_tier"] == "internal"


def test_directions_floor_engine_without_impeccable():
    from mop_directions import scaffold_directions
    _, plan = _plan()
    doc = scaffold_directions(plan, None)
    assert all(g["craft_engine"] == "floor" for g in doc["groups"])


def _filled(doc):
    for g in doc["groups"]:
        for d in g["directions"]:
            d["principle_refs"] = ["[KJ §3]"]
            d["title"] = "Direction " + d["id"]
            d["paradigm"] = "Structure " + d["id"]
            d["material"] = "Existing system"
            d["thesis"] = "Group related billing actions beside their current state."
            d["risk"] = "Changed grouping needs a keyboard and responsive check."
    return doc


def test_directions_check_enforces_distinct_paradigms_and_one_recommended():
    from mop_directions import check_directions, scaffold_directions
    from mop_bundle import InteropError
    _, plan = _plan()
    doc = _filled(scaffold_directions(plan, None))
    check_directions(doc, plan)  # filled scaffold must validate
    bad = copy.deepcopy(doc)
    bad["groups"][0]["directions"][1]["paradigm"] = bad["groups"][0]["directions"][0]["paradigm"]
    try:
        check_directions(bad, plan)
        raise AssertionError("repeated paradigms must fail")
    except InteropError:
        pass
    bad2 = copy.deepcopy(doc)
    bad2["groups"][0]["directions"][1]["recommended"] = True
    try:
        check_directions(bad2, plan)
        raise AssertionError("two recommended must fail")
    except InteropError:
        pass


def test_no_selection_withholds_design_steps_only():
    from mop_directions import DESIGN_CATEGORIES, implementable_steps, scaffold_directions
    _, plan = _plan()
    doc = _filled(scaffold_directions(plan, None))
    steps = implementable_steps(plan, doc)
    assert all(s["category"] not in DESIGN_CATEGORIES for s in steps), \
        "design steps must be withheld without a selection"
    doc["groups"][0]["selected"] = doc["groups"][0]["directions"][2]["id"]
    steps2 = implementable_steps(plan, doc)
    assert set(i["item_id"] for i in steps2) > set(i["item_id"] for i in steps)


def test_selection_must_reference_existing_direction():
    from mop_directions import check_directions, scaffold_directions
    from mop_bundle import InteropError
    _, plan = _plan()
    doc = _filled(scaffold_directions(plan, None))
    doc["groups"][0]["selected"] = "GRP-999-Z"
    try:
        check_directions(doc, plan)
        raise AssertionError("unknown selection must fail")
    except InteropError:
        pass


def test_todo_principle_refs_fail_check():
    from mop_directions import check_directions, scaffold_directions
    from mop_bundle import InteropError
    _, plan = _plan()
    doc = scaffold_directions(plan, None)  # unfilled: TODO principle refs
    try:
        check_directions(doc, plan)
        raise AssertionError("TODO principle refs must fail check")
    except InteropError:
        pass


def _plan_with_visual():
    b = copy.deepcopy(_bundle())
    for dec in b["decisions"]["decisions"]:
        if dec["item_id"] == "AS-03":
            dec["decision"] = "approve"
    return b, build_plan(b, INTEROP, True)


def test_visual_selection_requires_image_anchor():
    from mop_directions import check_directions, scaffold_directions
    from mop_bundle import InteropError
    _, plan = _plan_with_visual()
    doc = _filled(scaffold_directions(plan, None))
    visual = next((g for g in doc["groups"] if "visual" in g.get("categories", [])), None)
    assert visual is not None, "fixture must contain a visual design group"
    assert visual["imagery"] == "unavailable", "no templates/screenshots supplied"
    visual["selected"] = visual["directions"][0]["id"]
    try:
        check_directions(doc, plan)
        raise AssertionError("text-only visual selection must be refused")
    except InteropError as exc:
        assert "image" in str(exc) or "imagery" in str(exc)


def test_visual_selection_passes_with_template_image():
    import tempfile
    from mop_directions import check_directions, scaffold_directions
    b, plan = _plan_with_visual()
    with tempfile.TemporaryDirectory() as td:
        _tiny_png(Path(td) / "linear-board-reference.png")
        doc = _filled(scaffold_directions(plan, None, bundle=b, templates_dir=td))
        visual = next(g for g in doc["groups"] if "visual" in g.get("categories", []))
        assert visual["imagery"] == "available"
        assert visual["reference_pool"], "pool must carry the taste-library anchors"
        assert not any(d["grounding"] for d in visual["directions"]), \
            "scaffold must never auto-attach imagery to directions"
        # deliberate assignment from the pool is required
        visual["directions"][0]["grounding"] = [visual["reference_pool"][0]]
        visual["selected"] = visual["directions"][0]["id"]
        check_directions(doc, plan)


def test_untyped_image_anchor_is_refused():
    import tempfile
    from mop_directions import check_directions, scaffold_directions
    from mop_bundle import InteropError
    b, plan = _plan_with_visual()
    with tempfile.TemporaryDirectory() as td:
        _tiny_png(Path(td) / "ref.png")
        doc = _filled(scaffold_directions(plan, None, bundle=b, templates_dir=td))
        visual = next(g for g in doc["groups"] if "visual" in g.get("categories", []))
        anchor = dict(visual["reference_pool"][0]); anchor.pop("origin", None)
        visual["directions"][0]["grounding"] = [anchor]
        try:
            check_directions(doc, plan)
            raise AssertionError("untyped image anchor must be refused")
        except InteropError as exc:
            assert "origin" in str(exc)


def test_cross_product_imagery_is_refused():
    import tempfile
    from mop_directions import check_directions, scaffold_directions
    from mop_bundle import InteropError
    b, plan = _plan_with_visual()
    with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as foreign:
        _tiny_png(Path(td) / "ref.png")
        _tiny_png(Path(foreign) / "other-products-audit-evidence.png")
        doc = _filled(scaffold_directions(plan, None, bundle=b, templates_dir=td))
        visual = next(g for g in doc["groups"] if "visual" in g.get("categories", []))
        visual["directions"][0]["grounding"] = [{
            "source": "another product's audit",
            "image": str(Path(foreign) / "other-products-audit-evidence.png"),
            "origin": "taste_library",
            "note": "",
        }]
        try:
            check_directions(doc, plan)
            raise AssertionError("imagery outside declared reference sources must be refused")
        except InteropError as exc:
            assert "cross-product" in str(exc) or "reference source" in str(exc)


def test_dashboard_renders_direction_picker_and_export():
    import tempfile
    from mop_directions import scaffold_directions
    from mop_dashboard import render
    b, plan = _plan()
    doc = _filled(scaffold_directions(plan, None))
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        for name in ("findings.json", "context.json", "decisions.json", "tokens.json"):
            src = FIXTURE / name
            if src.exists():
                (d / name).write_text(src.read_text())
        (d / "directions.json").write_text(json.dumps(doc))
        out = render(d, None, str(d / "dash.html"), authorized=True)
        html = out.read_text()
    assert "Design directions" in html
    assert "Copy AI handoff" in html
    assert "Download directions.json" in html
    assert 'data-group-id="GRP-1"' in html
    assert html.count('type="radio"') >= 3


def test_dashboard_names_target_and_discloses_missing_screenshots():
    import tempfile
    from mop_dashboard import render
    with tempfile.TemporaryDirectory() as td:
        td = Path(td) / "fixtures" / "sample-audit"
        td.mkdir(parents=True)
        for name in ("findings.json", "context.json", "decisions.json", "tokens.json"):
            src = FIXTURE / name
            if src.exists():
                (td / name).write_text(src.read_text())
        out = render(td, None, str(td / "dash.html"), authorized=True)
        html = out.read_text()
    assert "Every item below judges one product" in html
    assert "DEMO FIXTURE" in html, "fixture bundles must be visibly labeled as demos"
    assert "No rendered image in this bundle" in html or "No screenshot receipt" in html, \
        "missing rendered evidence must be disclosed, not silent"


def test_dashboard_voice_categories_and_credits():
    import tempfile
    from mop_dashboard import render
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        for name in ("findings.json", "context.json", "decisions.json", "tokens.json"):
            src = FIXTURE / name
            if src.exists():
                (td / name).write_text(src.read_text())
        # give one item a principle ref so the credit line renders
        f = json.loads((td / "findings.json").read_text())
        f["items"][0]["principle_refs"] = ["PRINCIPLES §12 [Lp6ey4AyDzA 3:06]"]
        (td / "findings.json").write_text(json.dumps(f))
        out = render(td, None, str(td / "dash.html"), authorized=True)
        html = out.read_text()
    assert "text-transform:uppercase" not in html, "all-caps microlabels are a slop tell; sentence case only"
    assert "Editorial slop (copy)" in html or "Structure slop (backend_shape)" in html, \
        "cards must name the slop category explicitly, not just the schema key"
    assert "Kole Jain" in html, "principle citations must credit the human source"
    assert "Principle behind this finding" in html
    assert 'data-tab="provenance"' in html and "Rules applied (and their sources)" in html \
        and "Detector packs and signals" in html and "Evidence receipts" in html, \
        "every finding needs a Provenance tab with the standardized Source/Rule/Pack/Signal chain"


def test_mop_run_prepares_full_session():
    import subprocess, tempfile
    root = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        for name in ("findings.json", "context.json", "decisions.json", "tokens.json"):
            src = FIXTURE / name
            if src.exists():
                (td / name).write_text(src.read_text())
        proc = subprocess.run(
            [sys.executable, str(root / "mop_run.py"), str(td), "--authorized",
             "--impeccable", "absent", "--impeccable-reason", "probe failed in test",
             "--design-reference-search", "absent", "--design-reference-search-reason", "probe failed in test"],
            capture_output=True, text=True)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert (td / "directions.json").exists(), "directions must always exist after a run"
        assert (td / "mop-dashboard.html").exists(), "dashboard must always be rendered"
        assert (td / "mop-preflight.json").exists(), "preflight must always be recorded"
        assert "gate:" in proc.stdout and "augmentations:" in proc.stdout


def test_handoff_absent_work_is_not_implemented():
    plan = build_plan(_bundle(), INTEROP)
    h = build_handoff(plan, {})
    assert not h["items"]
    assert set(h["unimplemented"]) == {s["item_id"] for s in plan["steps"]}
    item_id = plan["steps"][0]["item_id"]
    h = build_handoff(plan, {item_id: {"surfaces": ["src/example.ts"], "self_check": []}})
    assert [i["item_id"] for i in h["items"]] == [item_id]
    assert h["items"][0]["verification"]["result"] == "not_run"
    for work in ({"unknown": {}}, {item_id: {}}, []):
        try:
            build_handoff(plan, work)
        except InteropError:
            continue
        raise AssertionError("malformed or out-of-plan work must refuse")


def test_explicit_orders_preserve_prerequisites_and_partial_coverage():
    from mop_bundle import _plan_from_work_orders
    items = {"A": {"id": "A", "category": "interaction", "depends_on": ["B"]},
             "B": {"id": "B", "category": "backend_shape", "depends_on": []}}
    for orders in ([{"id": "one", "lane": 1, "item_ids": ["A"]}, {"id": "two", "lane": 2, "item_ids": ["B"]}],
                   [{"id": "one", "lane": 1, "item_ids": ["B"]}]):
        steps, warnings = _plan_from_work_orders(orders, items, set(items), INTEROP["ordering"])
        assert [step["item_id"] for step in steps] == ["B", "A"]
    items["B"]["depends_on"] = ["A"]
    try:
        _plan_from_work_orders(orders, items, set(items), INTEROP["ordering"])
    except InteropError:
        return
    raise AssertionError("real cycle must refuse")


def test_legacy_malformed_decisions_refuse_cleanly():
    from mop_bundle import _check_cross_references
    bundle = _bundle()
    for decisions in (None, {}, [None], [{}], [{"item_id": []}], [{"item_id": "AS-01", "decision": "bogus"}], [{"item_id": "AS-01", "decision": []}],
                      [{"item_id": "AS-01", "decision": "approve"}] * 2):
        bundle["decisions"]["decisions"] = decisions
        try:
            _check_cross_references(bundle)
        except InteropError:
            continue
        raise AssertionError(f"malformed decisions accepted: {decisions}")


def test_standalone_installation_uses_explicit_scruffy_root():
    import os, subprocess
    with tempfile.TemporaryDirectory() as td:
        standalone = Path(td) / "repair"
        shutil.copytree(REPO, standalone, ignore=shutil.ignore_patterns("__pycache__"))
        env = dict(os.environ)
        env.pop("SCRUFFY_ROOT", None)
        command = [sys.executable, str(standalone / "scripts/mop_bundle.py"), "check", str(standalone / "fixtures/sample-audit")]
        refused = subprocess.run(command, env=env, text=True, capture_output=True)
        assert refused.returncode != 0 and "SCRUFFY_ROOT" in refused.stderr, refused.stderr
        env["SCRUFFY_ROOT"] = str(REPO.parent)
        valid = subprocess.run(command, env=env, text=True, capture_output=True)
        assert valid.returncode == 0, valid.stdout + valid.stderr
        env["SCRUFFY_ROOT"] = td
        invalid = subprocess.run(command, env=env, text=True, capture_output=True)
        assert invalid.returncode != 0 and "SCRUFFY_ROOT" in invalid.stderr


def test_draft_direction_controls_disabled():
    import re
    from mop_directions import scaffold_directions
    from mop_dashboard import build_dashboard_html
    bundle = _bundle()
    plan = build_plan(bundle, INTEROP)
    html = build_dashboard_html(bundle, plan, {}, FIXTURE, scaffold_directions(plan, bundle=bundle), FIXTURE)
    radios = re.findall(r'<input type="radio"[^>]*>', html)
    assert radios and all("disabled" in radio for radio in radios)


def test_complete_direction_mentions_todo_and_remains_selectable():
    import re
    from mop_directions import scaffold_directions, check_directions, direction_is_draft
    from mop_dashboard import build_dashboard_html
    bundle = _bundle()
    plan = build_plan(bundle, INTEROP)
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        _tiny_png(base / "reference.png")
        doc = _filled(scaffold_directions(plan, bundle=bundle))
        for group in doc["groups"]:
            group["imagery"] = "available"
            group["selected"] = group["directions"][0]["id"]
            for direction in group["directions"]:
                direction["title"] = "TODOList product " + direction["id"]
                direction["thesis"] = "Place the TODO column beside the active work queue."
                direction["grounding"] = [{"source": "TODO-123 reference", "image": "reference.png", "origin": "mockup"}]
                assert not direction_is_draft(direction)
        check_directions(doc, plan, bundle=bundle, bundle_dir=base)
        html = build_dashboard_html(bundle, plan, {}, base, doc, base)
        radios = re.findall(r'<input type="radio"[^>]*>', html)
        assert radios and all("disabled" not in radio for radio in radios)
        assert any("checked" in radio for radio in radios)
        bad = copy.deepcopy(doc)
        bad["groups"][0]["directions"][0]["thesis"] = "TODO: explain the product task."
        try:
            check_directions(bad, plan, bundle=bundle, bundle_dir=base)
        except InteropError as error:
            assert "draft" in str(error)
        else:
            raise AssertionError("a selected scaffold placeholder must still refuse")


def test_image_evidence_rejects_spoofing_and_escape():
    from mop_dashboard import _data_uri
    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / "assets"
        base.mkdir()
        valid = base / "ok.png"
        _tiny_png(valid)
        assert _data_uri(valid, None, base).startswith("data:image/png;")
        fake = base / "fake.png"
        fake.write_text("<svg onload='alert(1)'></svg>")
        outside = Path(td) / "outside.png"
        _tiny_png(outside)
        link = base / "escape.png"
        link.symlink_to(outside)
        for path, mime in ((fake, None), (valid, "image/svg+xml"), (link, None)):
            try:
                _data_uri(path, mime, base)
            except InteropError:
                continue
            raise AssertionError("invalid evidence accepted")


def test_handoff_canonical_receipt_retains_states_and_refuses_mismatch():
    from mop_bundle import canonical_verification
    bundle = _bundle()
    plan = build_plan(bundle, INTEROP)
    item_id = plan["steps"][0]["item_id"]
    item = next(i for i in bundle["findings"]["items"] if i["id"] == item_id)
    work = {item_id: {"surfaces": ["src/example.ts"], "self_check": []}}
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "verification.json"
        for kind, check_result, overall in (("command", "pass", "verified"), ("command", "fail", "failed"), ("command", "not_run", "not_run"), ("manual", "manual", "manual")):
            item["fix_packet"] = {"target": [{"kind": "file", "value": "src/example.ts"}], "change": "Restore accepted behavior", "effort": "S", "rollback": "Revert scoped patch", "acceptance": [{"kind": kind, "run": "true", "summary": "Check accepted behavior"}]}
            receipt = {"schema_version": "1.0", "audit_id": plan["audit_id"], "revision_id": plan["revision_id"], "executed_commands": kind == "command" and check_result != "not_run", "items": [{"id": item_id, "decision": "approve", "result": overall, "checks": [{"index": 0, "kind": kind, "result": check_result}]}]}
            _write_json(path, receipt)
            validated = canonical_verification(path, bundle["findings"], bundle["decisions"])
            handoff = build_handoff(plan, work, verification=validated, verification_path=str(path))
            assert handoff["items"][0]["verification"]["result"] == overall
            assert handoff["items"][0]["status"] == "implemented-pending-reaudit"
        receipt["revision_id"] = "wrong"
        _write_json(path, receipt)
        try:
            canonical_verification(path, bundle["findings"], bundle["decisions"])
        except InteropError:
            return
        raise AssertionError("mismatched receipt must refuse")


def test_mop_run_reopens_unselected_draft_without_rewriting():
    import subprocess, re
    with tempfile.TemporaryDirectory() as td:
        bundle_dir = Path(td) / "sample-audit"
        shutil.copytree(FIXTURE, bundle_dir)
        command = [sys.executable, str(REPO / "scripts/mop_run.py"), str(bundle_dir), "--authorized"]
        first = subprocess.run(command, text=True, capture_output=True)
        assert first.returncode == 0, first.stdout + first.stderr
        directions = bundle_dir / "directions.json"
        original = directions.read_bytes()
        second = subprocess.run(command, text=True, capture_output=True)
        assert second.returncode == 0, second.stdout + second.stderr
        assert directions.read_bytes() == original
        assert "draft; supply principle references" in second.stdout
        radios = re.findall(r'<input type="radio"[^>]*>', (bundle_dir / "mop-dashboard.html").read_text())
        assert radios and all("disabled" in radio for radio in radios)
        doc = json.loads(original)
        doc["groups"][0]["selected"] = doc["groups"][0]["directions"][0]["id"]
        _write_json(directions, doc)
        selected_bytes = directions.read_bytes()
        refused = subprocess.run(command, text=True, capture_output=True)
        assert refused.returncode != 0 and "draft" in refused.stderr
        assert directions.read_bytes() == selected_bytes


def _run():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ok  {t.__name__}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL  {t.__name__}: {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_run())
