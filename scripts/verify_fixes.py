#!/usr/bin/env python3
"""Run the executable acceptance checks for approved registry items.

This is the half of the loop an audit alone never closes: an approved item is
not value until its fix is applied and its acceptance checks pass. The script
reads the registry and decisions, selects approved open or needs-verification
items that carry a `fix_packet`, executes every check it can, and writes
`verification.json`. It never edits the registry: a status only changes in the
next revision, where `verification.json` is the evidence for a `fixed`
disposition.

Check kinds:
  command      run a shell command from --cwd; pass when exit code is 0 (or
               `expect.exit_code`) and, when given, stdout contains
               `expect.stdout_contains`. Runs only with --execute.
  dom_state    a selector plus expected state. Needs a browser; supply results
               through --results, otherwise recorded as not_run.
  measurement  a metric name plus threshold. Same rule as dom_state.
  manual       a human must confirm. Recorded as manual, never pass.

`--results` is a JSON object keyed "ITEM-ID:index" -> {"result": "pass"|"fail",
"detail": "..."} for checks an agent or browser session ran out of band.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from validate_audit import ACTIVE_STATUSES as ACTIVE, load_json, validate_decisions


def load(path: Path | None) -> dict[str, Any]:
    return {} if path is None else load_json(path)


def decision_map(decisions: dict[str, Any]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for row in decisions.get("decisions", []) or []:
        item_id = row.get("item_id") or row.get("finding_id")
        if item_id:
            mapping[str(item_id)] = str(row.get("decision") or "pending")
    return mapping


def run_command(check: dict[str, Any], cwd: Path, execute: bool) -> tuple[str, str]:
    command = str(check.get("run") or "")
    if not execute:
        return "not_run", "command checks run only with --execute"
    try:
        completed = subprocess.run(
            command, shell=True, cwd=cwd, text=True, capture_output=True, timeout=int(check.get("timeout", 120))
        )
    except subprocess.TimeoutExpired:
        return "fail", "timed out"
    except OSError as error:
        return "fail", f"could not run command: {error}"
    expect = check.get("expect") or {}
    wanted_code = int(expect.get("exit_code", 0)) if isinstance(expect, dict) else 0
    if completed.returncode != wanted_code:
        return "fail", f"exit {completed.returncode}; {(completed.stderr or completed.stdout).strip()[:300]}"
    needle = expect.get("stdout_contains") if isinstance(expect, dict) else None
    if needle and needle not in completed.stdout:
        return "fail", f"stdout lacked {needle!r}"
    return "pass", f"exit {completed.returncode}"


def evaluate(item: dict[str, Any], packet: dict[str, Any], results: dict[str, Any], cwd: Path, execute: bool) -> dict[str, Any]:
    checks_out: list[dict[str, Any]] = []
    for index, check in enumerate(packet.get("acceptance") or []):
        kind = str(check.get("kind") or "manual")
        key = f"{item['id']}:{index}"
        supplied = results.get(key)
        if kind == "command":
            result, detail = run_command(check, cwd, execute)
        elif kind == "manual":
            result, detail = "manual", "needs a human confirmation"
        else:
            if isinstance(supplied, dict) and supplied.get("result") in {"pass", "fail"}:
                result, detail = str(supplied["result"]), str(supplied.get("detail") or "supplied result")
            else:
                result, detail = "not_run", f"{kind} check needs a runtime result supplied with --results"
        checks_out.append(
            {
                "index": index,
                "kind": kind,
                "summary": str(check.get("summary") or check.get("run") or check.get("expect") or ""),
                "result": result,
                "detail": detail,
            }
        )
    outcomes = {c["result"] for c in checks_out}
    if not checks_out:
        overall = "not_run"
    elif "fail" in outcomes:
        overall = "failed"
    elif outcomes <= {"pass"}:
        overall = "verified"
    elif "not_run" in outcomes:
        overall = "not_run"
    else:
        overall = "manual"
    return {"id": item["id"], "title": item.get("title"), "result": overall, "checks": checks_out}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("registry", type=Path)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--results", type=Path, help="out-of-band check results JSON")
    parser.add_argument("--cwd", type=Path, default=Path.cwd(), help="working directory for command checks")
    parser.add_argument("--execute", action="store_true", help="actually run command checks")
    parser.add_argument("--output", type=Path, default=Path("verification.json"))
    parser.add_argument("--include-pending", action="store_true", help="preview undecided items; incompatible with --execute")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.execute and args.include_pending:
        raise SystemExit("FAIL: --include-pending is preview-only and cannot be combined with --execute")
    registry = load(args.registry)
    decision_document = load(args.decisions)
    # Validate the entire bundle before the first command or receipt write.
    validate_decisions(decision_document, registry)
    decisions = decision_map(decision_document)
    results = load(args.results)
    if not args.cwd.is_dir():
        raise SystemExit("FAIL: --cwd must be an existing directory")
    inputs = [path.resolve() for path in (args.registry, args.decisions, args.results) if path is not None]
    if args.output.resolve() in inputs:
        raise SystemExit("FAIL: --output must not overwrite an input artifact")
    if args.output.exists() and not args.output.is_file():
        raise SystemExit("FAIL: --output must name a file")
    # Reserve a writable sibling before execution, then atomically publish the
    # receipt. A misspelled/unwritable parent must fail before side effects.
    with tempfile.TemporaryDirectory(prefix=".scruffy-verification-", dir=args.output.parent) as staging:
        items_out: list[dict[str, Any]] = []
        skipped: list[dict[str, str]] = []
        for item in registry.get("items", []):
            if item.get("kind") not in {"finding", "enhancement"} or item.get("status") not in ACTIVE:
                continue
            decision = decisions.get(str(item["id"]), "pending")
            if decision != "approve" and not (args.include_pending and decision == "pending"):
                continue
            packet = item.get("fix_packet")
            if not isinstance(packet, dict):
                skipped.append({"id": item["id"], "reason": "no fix_packet; acceptance is prose only"})
                continue
            row = evaluate(item, packet, results, args.cwd, args.execute)
            row["decision"] = decision
            items_out.append(row)

        report = {
            "schema_version": "1.0",
            "audit_id": registry.get("audit_id"),
            "revision_id": registry.get("revision_id"),
            "verified_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
            "executed_commands": bool(args.execute),
            "items": items_out,
            "skipped": skipped,
        }
        receipt = Path(staging) / "verification.json"
        receipt.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        receipt.replace(args.output)
        counts = {k: sum(1 for r in items_out if r["result"] == k) for k in ("verified", "failed", "manual", "not_run")}
        status = "FAIL" if counts["failed"] else ("PASS" if items_out and counts["verified"] == len(items_out) and not skipped else "INCOMPLETE")
        print(
            f"{status}: {len(items_out)} selected items evaluated — "
            f"{counts['verified']} verified, {counts['failed']} failed, {counts['manual']} manual, "
            f"{counts['not_run']} not run; {len(skipped)} skipped without a fix packet -> {args.output}"
        )
        return 1 if counts["failed"] else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        raise SystemExit(f"FAIL: {error}")
