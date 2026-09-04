#!/usr/bin/env python3
"""Exercise the fix loop: brief -> fix packet -> verify -> outcomes."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
FIXTURE = ROOT / "evals" / "continuity"


def run(*arguments: str, succeeds: bool = True, contains: str | None = None) -> str:
    result = subprocess.run([PYTHON, *arguments], cwd=ROOT, text=True, capture_output=True, check=False)
    output = result.stdout + result.stderr
    if succeeds and result.returncode != 0:
        raise SystemExit(f"FAIL: {' '.join(arguments)}\n{output}")
    if not succeeds and result.returncode == 0:
        raise SystemExit(f"FAIL: expected failure: {' '.join(arguments)}\n{output}")
    if contains and contains not in output:
        raise SystemExit(f"FAIL: expected {contains!r} in output of {' '.join(arguments)}\n{output}")
    return output


def packet(run_command: str) -> dict:
    return {
        "target": [{"kind": "file", "value": "index.html"}, {"kind": "route", "value": "/lessons/:slug"}],
        "change": "Read the lesson slug from the address on load and write it on navigation.",
        "effort": "M",
        "rollback": "Revert the routing commit; stored progress is untouched.",
        "acceptance": [
            {"kind": "command", "run": run_command, "summary": "routing test passes", "check_ref": 0},
            {"kind": "dom_state", "selector": "main h1", "expect": {"text_contains": "Lesson 3"}, "summary": "/lessons/3 shows lesson 3"},
            {"kind": "manual", "summary": "a shared link opens the same lesson for a colleague"},
        ],
    }


def main() -> int:
    registry = json.loads((FIXTURE / "revision.json").read_text(encoding="utf-8"))
    decisions = json.loads((FIXTURE / "decisions.json").read_text(encoding="utf-8"))
    context = FIXTURE / "context.json"

    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)

        # 1. Brief renders within budget and leads with the plain sentence, not the taxonomy.
        brief = tmp / "brief.md"
        run("scripts/render_brief.py", str(FIXTURE / "revision.json"), "--context", str(context), "--decisions", str(FIXTURE / "decisions.json"), "--output", str(brief), contains="PASS: brief rendered")
        text = brief.read_text(encoding="utf-8")
        for heading in ("**Verdict:**", "## Decide now", "## Cleared", "## Not tested"):
            if heading not in text:
                raise SystemExit(f"FAIL: brief lacks {heading}")
        if "identity_key" in text or "revision_disposition" in text:
            raise SystemExit("FAIL: brief leaks machine vocabulary")
        if text.count("\n1. **") != 1 or "\n4. **" in text:
            raise SystemExit("FAIL: brief must list at most three items to decide")
        run("scripts/render_brief.py", str(FIXTURE / "revision.json"), "--context", str(context), "--max-words", "20", succeeds=False, contains="budget")

        # 2. Fix packets validate, and a malformed one fails closed.
        good = copy.deepcopy(registry)
        for item in good["items"]:
            if item["id"] == "AS-02":
                item["fix_packet"] = packet("true")
            if item["id"] == "AS-01":
                item["fix_packet"] = packet("false")
        good_path = tmp / "findings.json"
        good_path.write_text(json.dumps(good), encoding="utf-8")
        run("scripts/validate_audit.py", str(good_path), "--context", str(context), contains="PASS")

        bad = copy.deepcopy(good)
        for item in bad["items"]:
            if item["id"] == "AS-02":
                item["fix_packet"]["acceptance"] = [{"kind": "command"}]
        bad_path = tmp / "bad.json"
        bad_path.write_text(json.dumps(bad), encoding="utf-8")
        run("scripts/validate_audit.py", str(bad_path), succeeds=False, contains="fix_packet.acceptance[0].run")

        strength_bad = copy.deepcopy(good)
        for item in strength_bad["items"]:
            if item["kind"] == "strength":
                item["fix_packet"] = packet("true")
                break
        strength_path = tmp / "strength.json"
        strength_path.write_text(json.dumps(strength_bad), encoding="utf-8")
        run("scripts/validate_audit.py", str(strength_path), succeeds=False, contains="not allowed on a strength")

        # 3. Verify runs only approved items; dry run never executes; --execute does.
        approved = copy.deepcopy(decisions)
        key = "item_id" if approved["decisions"] and "item_id" in approved["decisions"][0] else "finding_id"
        for row in approved["decisions"]:
            if row[key] in {"AS-01", "AS-02"}:
                row["decision"] = "approve"
        decisions_path = tmp / "decisions.json"
        decisions_path.write_text(json.dumps(approved), encoding="utf-8")
        results_path = tmp / "results.json"
        results_path.write_text(json.dumps({"AS-02:1": {"result": "pass", "detail": "h1 read Lesson 3"}}), encoding="utf-8")
        verification = tmp / "verification.json"

        run("scripts/verify_fixes.py", str(good_path), "--decisions", str(decisions_path), "--output", str(verification), contains="2 not run")
        dry = json.loads(verification.read_text(encoding="utf-8"))
        if dry["executed_commands"] or any(c["result"] == "pass" for i in dry["items"] for c in i["checks"]):
            raise SystemExit("FAIL: dry run must not execute or pass commands")

        run("scripts/verify_fixes.py", str(good_path), "--decisions", str(decisions_path), "--results", str(results_path), "--execute", "--output", str(verification), succeeds=False, contains="1 failed, 1 manual")
        failure_output = run("scripts/verify_fixes.py", str(good_path), "--decisions", str(decisions_path), "--execute", "--output", str(verification), succeeds=False)
        if not failure_output.startswith("FAIL:"):
            raise SystemExit("FAIL: failed verification must not print a PASS banner")
        run("scripts/verify_fixes.py", str(good_path), "--decisions", str(decisions_path), "--results", str(results_path), "--execute", "--output", str(verification), succeeds=False)
        executed = json.loads(verification.read_text(encoding="utf-8"))
        by_id = {row["id"]: row for row in executed["items"]}
        if by_id["AS-01"]["result"] != "failed" or by_id["AS-02"]["result"] != "manual":
            raise SystemExit(f"FAIL: unexpected verification results {by_id}")
        if [c["result"] for c in by_id["AS-02"]["checks"]] != ["pass", "pass", "manual"]:
            raise SystemExit("FAIL: supplied dom_state result was not honored")
        if any(row["id"] not in {"AS-01", "AS-02"} for row in executed["items"]):
            raise SystemExit("FAIL: verify evaluated an unapproved item")

        # 4. Outcomes counts each item once across revisions and reports rates.
        outcomes = tmp / "outcomes.json"
        run(
            "scripts/outcomes.py",
            str(FIXTURE / "baseline.json"),
            f"{good_path}:{decisions_path}:{verification}",
            "--output",
            str(outcomes),
            contains="TOTAL",
        )
        report = json.loads(outcomes.read_text(encoding="utf-8"))
        ids = [row["id"] for row in report["items"]]
        if len(ids) != len(set(ids)):
            raise SystemExit("FAIL: outcomes counted an item twice")
        if report["total"]["approved"] != 2 or report["total"]["failed"] != 1:
            raise SystemExit(f"FAIL: outcome totals wrong: {report['total']}")

        # 5. --require-fix-packets is opt-in and catches the serious bare finding.
        #    Default-off is the whole point: registries published before packets
        #    existed keep validating.
        bare = copy.deepcopy(registry)
        for item in bare["items"]:
            if item["id"] == "AS-01":
                item["kind"] = "finding"
                item["status"] = "open"
                item["severity"] = "critical"
                item.pop("fix_packet", None)
        bare_path = tmp / "bare.json"
        bare_path.write_text(json.dumps(bare), encoding="utf-8")
        run("scripts/validate_audit.py", str(bare_path), "--context", str(context), contains="PASS")
        run(
            "scripts/validate_audit.py",
            str(bare_path),
            "--context",
            str(context),
            "--require-fix-packets",
            succeeds=False,
            contains="open critical or major findings without a fix_packet: AS-01",
        )
        packed = copy.deepcopy(bare)
        for item in packed["items"]:
            if item["id"] == "AS-01":
                item["fix_packet"] = packet("true")
        packed_path = tmp / "packed.json"
        packed_path.write_text(json.dumps(packed), encoding="utf-8")
        run(
            "scripts/validate_audit.py",
            str(packed_path),
            "--context",
            str(context),
            "--require-fix-packets",
            contains="fix-packet coverage",
        )

        # 6. migrate_decisions records what proved the fix, not just the choice.
        migrated = tmp / "migrated-decisions.json"
        run(
            "scripts/migrate_decisions.py",
            str(decisions_path),
            str(good_path),
            str(migrated),
            "--verification",
            str(verification),
            contains="PASS: migrated",
        )
        migrated_rows = {row["item_id"]: row for row in json.loads(migrated.read_text(encoding="utf-8"))["decisions"]}
        reference = migrated_rows["AS-01"].get("verification_ref")
        if not isinstance(reference, dict) or reference.get("result") != "failed":
            raise SystemExit(f"FAIL: migrated decision lost its verification_ref: {reference}")
        if "verification_ref" in migrated_rows.get("AS-03", {}):
            raise SystemExit("FAIL: verification_ref attached to an item with no verification entry")

        # 7. The dashboard renders the packet and emits an instruction, not just data.
        dashboard = tmp / "dashboard.html"
        run(
            "scripts/render_dashboard.py",
            str(good_path),
            str(context),
            str(decisions_path),
            str(dashboard),
            contains="PASS: rendered",
        )
        html = dashboard.read_text(encoding="utf-8")
        for fragment in (
            "Executable fix packet",
            "Read the lesson slug from the address",
            "Revert the routing commit",
            "needs a person; no tool can pass it",
            'id="copy-handoff"',
            "Copy AI handoff",
            "scripts/verify_fixes.py --execute",
            "verification.json",
        ):
            if fragment not in html:
                raise SystemExit(f"FAIL: dashboard lost {fragment!r}")

        markdown = tmp / "audit.md"
        run(
            "scripts/render_markdown.py",
            str(good_path),
            str(context),
            str(decisions_path),
            str(markdown),
            contains="PASS",
        )
        report_text = markdown.read_text(encoding="utf-8")
        for fragment in ("**Executable fix packet**", "- Undo: Revert the routing commit", "**Manual:**", "needs a person"):
            if fragment not in report_text:
                raise SystemExit(f"FAIL: Markdown report lost {fragment!r}")

    print(
        "PASS: brief budget, fix-packet validation and coverage gate, verify dry/execute, "
        "migrated verification refs, rendered fix packets, dashboard handoff, outcomes ledger"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
