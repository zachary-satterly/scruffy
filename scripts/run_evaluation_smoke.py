#!/usr/bin/env python3
"""Development smoke harness for the evaluation and verification code paths.

This is a harness-integrity check, not a benchmark and not proof of audit
accuracy. It drives three inexpensive deterministic workflows through the same
public code the runtime uses, and it preserves the actual status each real tool
reports rather than asserting a hoped-for one:

1. Detection — the deterministic rule engine (`rule_engine.evaluate_page`) must
   raise leads on a fixture with clear, reproducible defects and must stay
   silent on an adjacent legitimate-pattern control whose false-positive guards
   are all satisfied.
2. Repair verification — the real verifier (`verify_fixes.py`) runs a fix
   packet's executable acceptance checks against four target variants: the
   original broken behavior fails, an authorized valid repair passes, a
   plausible wrong repair fails a neighboring invariant, and an alternative
   valid implementation passes.
3. False-closure guards — a skipped (`--execute` withheld) command check and a
   manual check cannot report `verified` through the actual verifier, and the
   closure gate (`validate_audit.validate_fix_verification`) refuses to mark an
   item fixed when a promised check was skipped or failed.

Limitations this harness does NOT cover are printed with its report and listed
in `evals/smoke/README.md`. It authors no browser receipts and is never blind.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

import rule_engine
from validate_audit import validate_fix_verification

ROOT = Path(__file__).resolve().parents[1]
SMOKE_DIR = ROOT / "evals" / "smoke"
CONTINUITY = ROOT / "evals" / "continuity"
DURABILITY = ROOT / "evals" / "durability"
VERIFY_FIXES = ROOT / "scripts" / "verify_fixes.py"

# Expected leads on the defect fixture. The engine may raise more (it does), so
# the workflow asserts these are a subset rather than an exact set — a lead is a
# suspicion to confirm, and the clear defects here must at least surface.
EXPECTED_DEFECT_LEADS = {
    "A11Y-IMG-NO-ALT",
    "A11Y-EMPTY-CONTROL",
    "A11Y-HTML-NO-LANG",
    "OP-UNLABELED-INPUT",
    "OP-NO-STATE-URL",
}

# Four candidate repairs for one finding: "lesson state is not addressable".
# route_for maps a page key to a shareable address; "home" must stay "/".
ROUTER_VARIANTS: dict[str, str] = {
    "original_broken": (
        "def route_for(page):\n"
        "    # Every page collapses to the root: no lesson has its own address.\n"
        "    return '/'\n"
    ),
    "valid_repair": (
        "def route_for(page):\n"
        "    if page == 'home':\n"
        "        return '/'\n"
        "    if page.startswith('lesson-'):\n"
        "        return '/lesson/' + page.split('-', 1)[1]\n"
        "    return '/' + page\n"
    ),
    "wrong_repair": (
        "def route_for(page):\n"
        "    # Addresses lessons, but silently rewrites 'home' to '/home',\n"
        "    # regressing the neighboring default-route invariant.\n"
        "    return '/' + page.replace('-', '/')\n"
    ),
    "alternative_valid": (
        "import re\n\n"
        "def route_for(page):\n"
        "    if page == 'home':\n"
        "        return '/'\n"
        "    match = re.fullmatch(r'lesson-(\\d+)', page)\n"
        "    if match:\n"
        "        return '/lesson/' + match.group(1)\n"
        "    return '/' + page\n"
    ),
}

# The oracle checks the two declared inputs only — that 'lesson-3' gains a
# shareable address and the 'home' default is preserved. It makes no claim that
# the valid and alternative implementations are equivalent across all page
# strings; they deliberately differ on other inputs.
CHECK_ADDRESS = "import router, sys; sys.exit(0 if router.route_for('lesson-3') == '/lesson/3' else 1)"
CHECK_DEFAULT = "import router, sys; sys.exit(0 if router.route_for('home') == '/' else 1)"

# Bound each verifier subprocess so a hung run surfaces as an actionable failure.
SUBPROCESS_TIMEOUT = 60


def _leads_for(path: Path) -> set[str]:
    """Return the set of rule ids the real engine raises for one page."""
    packs = rule_engine.load_packs(rule_engine.DEFAULT_RULES_DIR, [])
    rule_engine.validate_packs(packs)
    return {lead["rule_id"] for lead in rule_engine.evaluate_page(path, packs)}


def run_detection_smoke() -> dict[str, Any]:
    """Workflow 1 and 2: a clear defect raises leads; a clean control stays silent."""
    defect_leads = _leads_for(SMOKE_DIR / "defect-page.html")
    clean_leads = _leads_for(SMOKE_DIR / "clean-control.html")
    missing = sorted(EXPECTED_DEFECT_LEADS - defect_leads)
    defect_ok = not missing
    control_ok = not clean_leads
    return {
        "defect_leads": sorted(defect_leads),
        "clean_leads": sorted(clean_leads),
        "missing_expected": missing,
        "defect_ok": defect_ok,
        "control_ok": control_ok,
        "ok": defect_ok and control_ok,
    }


def _fix_packet(router_check: str, default_check: str, *, extra: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    acceptance: list[dict[str, Any]] = [
        {"kind": "command", "argv": [sys.executable, "-c", router_check],
         "summary": "lesson-3 resolves to the shareable address /lesson/3"},
        {"kind": "command", "argv": [sys.executable, "-c", default_check],
         "summary": "neighboring invariant: home still resolves to /"},
    ]
    if extra:
        acceptance.extend(extra)
    return {
        "target": [{"kind": "file", "value": "router.py"}],
        "change": "Give each lesson a stable address while preserving the default route.",
        "effort": "S",
        "rollback": "Revert router.py to the prior revision.",
        "acceptance": acceptance,
    }


def _registry_with_packet(packet: dict[str, Any], item_id: str = "AS-02") -> tuple[dict[str, Any], dict[str, Any]]:
    registry = json.loads((CONTINUITY / "revision.json").read_text(encoding="utf-8"))
    decisions = json.loads((CONTINUITY / "decisions.json").read_text(encoding="utf-8"))
    next(item for item in registry["items"] if item["id"] == item_id)["fix_packet"] = packet
    next(row for row in decisions["decisions"] if row["item_id"] == item_id)["decision"] = "approve"
    return registry, decisions


def _infra_failure(detail: str) -> dict[str, Any]:
    """A verifier invocation that could not produce trustworthy evidence.

    Preserved as an actionable non-pass rather than silently accepted: stale or
    absent data must never masquerade as a verified result.
    """
    return {"ok_infra": False, "exit_code": None, "result": "infrastructure_failure",
            "checks": [], "detail": detail}


VALID_RESULTS = {"verified", "failed", "manual", "not_run"}


def _verify(registry: dict[str, Any], decisions: dict[str, Any], router_src: str,
            work: Path | None = None, *, execute: bool) -> dict[str, Any]:
    """Run the real verifier against one target variant in an isolated directory.

    Each invocation runs in its own fresh temp directory, so a failed run can
    never read another variant's stale `verification.json`, and per-variant
    `router.py` bytecode is never reused. When `work` is given it is used only as
    the parent for that fresh directory (never reused directly); otherwise the
    default temp root is used. A launch error, a timeout, an exit code outside
    the verifier's {0, 1} contract, or a missing, unreadable, or structurally
    malformed receipt is surfaced as an infrastructure failure, not a pass.
    """
    parent = str(work) if work is not None else None
    with tempfile.TemporaryDirectory(prefix="scruffy-smoke-verify-", dir=parent) as raw:
        run_dir = Path(raw)
        (run_dir / "router.py").write_text(router_src, encoding="utf-8")
        registry_path = run_dir / "findings.json"
        decisions_path = run_dir / "decisions.json"
        output = run_dir / "verification.json"
        registry_path.write_text(json.dumps(registry), encoding="utf-8")
        decisions_path.write_text(json.dumps(decisions), encoding="utf-8")
        command = [sys.executable, str(VERIFY_FIXES), str(registry_path),
                   "--decisions", str(decisions_path), "--cwd", str(run_dir), "--output", str(output)]
        if execute:
            command.append("--execute")
        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT)
        except subprocess.TimeoutExpired:
            return _infra_failure(f"verifier timed out after {SUBPROCESS_TIMEOUT}s")
        except OSError as error:
            return _infra_failure(f"verifier could not be launched: {error}")
        # verify_fixes.py returns 0 (nothing failed) or 1 (a check failed or a
        # handled preflight error). Anything else is not its contract.
        if completed.returncode not in (0, 1):
            return _infra_failure(f"verifier exited {completed.returncode}: {(completed.stderr or completed.stdout).strip()[:200]}")
        if not output.exists():
            return _infra_failure("verifier produced no receipt for this invocation")
        try:
            receipt = json.loads(output.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            return _infra_failure(f"verifier receipt is unreadable: {error}")
        # Guard every shape the receipt could take before indexing into it.
        if not isinstance(receipt, dict):
            return _infra_failure("verifier receipt is not a JSON object")
        rows = receipt.get("items")
        if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
            return _infra_failure("verifier receipt evaluated no well-formed items")
        result = rows[0].get("result")
        # Guard the type before membership: a parsed JSON [] or {} is unhashable
        # and would raise TypeError against the VALID_RESULTS set.
        if not isinstance(result, str) or result not in VALID_RESULTS:
            return _infra_failure(f"verifier receipt result {result!r} is not a known status")
        checks = rows[0].get("checks")
        if not isinstance(checks, list):
            return _infra_failure("verifier receipt checks are not a list")
        expected_exit = 1 if result == "failed" else 0
        if completed.returncode != expected_exit:
            return _infra_failure(f"exit {completed.returncode} disagrees with receipt result {result!r}")
        return {"ok_infra": True, "exit_code": completed.returncode,
                "result": result, "checks": checks, "detail": ""}


def run_repair_smoke() -> dict[str, Any]:
    """Workflow 3: original fails, valid passes, wrong fails, alternative passes.

    Every verifier invocation runs in its own isolated directory (see _verify),
    so no result is ever read from another variant's stale receipt.
    """
    registry, decisions = _registry_with_packet(_fix_packet(CHECK_ADDRESS, CHECK_DEFAULT))

    variants = {name: _verify(registry, decisions, src, execute=True)
                for name, src in ROUTER_VARIANTS.items()}

    # Skipped: the same valid repair, but command checks never run.
    skipped = _verify(registry, decisions, ROUTER_VARIANTS["valid_repair"], execute=False)

    # Manual: append a manual check; a passing command run cannot upgrade it.
    manual_registry, manual_decisions = _registry_with_packet(
        _fix_packet(CHECK_ADDRESS, CHECK_DEFAULT,
                    extra=[{"kind": "manual", "summary": "a person confirms a shared link reopens the lesson"}]))
    manual = _verify(manual_registry, manual_decisions, ROUTER_VARIANTS["valid_repair"], execute=True)

    expected = {"original_broken": "failed", "valid_repair": "verified",
                "wrong_repair": "failed", "alternative_valid": "verified"}
    all_rows = [*variants.values(), skipped, manual]
    infra_ok = all(row["ok_infra"] for row in all_rows)
    variants_ok = all(variants[name]["ok_infra"] and variants[name]["result"] == want
                      for name, want in expected.items())
    # The wrong repair must fail specifically on the neighboring-invariant check.
    wrong_checks = variants["wrong_repair"]["checks"]
    neighbor_ok = (len(wrong_checks) == 2 and wrong_checks[0]["result"] == "pass"
                   and wrong_checks[1]["result"] == "fail")
    skipped_ok = skipped["ok_infra"] and skipped["result"] == "not_run"
    manual_ok = manual["ok_infra"] and manual["result"] == "manual"
    return {
        "variants": {name: row["result"] for name, row in variants.items()},
        "expected": expected,
        "infrastructure_ok": infra_ok,
        "neighbor_invariant_caught_wrong_repair": neighbor_ok,
        "skipped_result": skipped["result"],
        "manual_result": manual["result"],
        "ok": infra_ok and variants_ok and neighbor_ok and skipped_ok and manual_ok,
    }


def _closure(mutate: Callable[[dict[str, Any]], None] | None) -> tuple[bool, str]:
    """Run the fixed-transition closure gate with an optionally mutated receipt."""
    baseline = json.loads((DURABILITY / "baseline.json").read_text(encoding="utf-8"))
    current = json.loads((DURABILITY / "revision-valid-fixed-with-verification.json").read_text(encoding="utf-8"))
    receipt = json.loads((DURABILITY / "verification-fixed.json").read_text(encoding="utf-8"))
    receipt["revision_id"] = baseline["revision_id"]
    if mutate:
        mutate(receipt)
    try:
        validate_fix_verification(current, baseline, receipt)
        return True, "accepted"
    except ValueError as error:
        return False, str(error)


def _skip_command(receipt: dict[str, Any]) -> None:
    receipt["items"][0]["checks"][0]["result"] = "not_run"
    receipt["items"][0]["result"] = "not_run"


def _fail_command(receipt: dict[str, Any]) -> None:
    receipt["items"][0]["checks"][0]["result"] = "fail"
    receipt["items"][0]["result"] = "failed"


def run_closure_smoke() -> dict[str, Any]:
    """Prove skipped or failed checks cannot relabel an item as fixed."""
    valid_accepted, _ = _closure(None)
    skipped_accepted, skipped_reason = _closure(_skip_command)
    failed_accepted, failed_reason = _closure(_fail_command)
    return {
        "valid_receipt_accepted": valid_accepted,
        "skipped_rejected": not skipped_accepted,
        "failed_rejected": not failed_accepted,
        "skipped_reason": skipped_reason,
        "failed_reason": failed_reason,
        "ok": valid_accepted and not skipped_accepted and not failed_accepted,
    }


LIMITATIONS = (
    "Deterministic static leads and executable command checks only; no live "
    "browser, screenshot, DOM, contrast, or performance runtime was exercised.",
    "Leads are suspicions, not confirmed findings; the detection workflow proves "
    "discrimination between a defect and an adjacent control, not audit accuracy.",
    "This run is not blind and authors no browser or specialist receipts.",
)


def main() -> int:
    detection = run_detection_smoke()
    repair = run_repair_smoke()
    closure = run_closure_smoke()

    print("== Detection (workflows 1 and 2) ==")
    print(f"  defect leads raised: {detection['defect_leads']}")
    print(f"  clean-control leads: {detection['clean_leads']} (expected none)")
    if detection["missing_expected"]:
        print(f"  MISSING expected defect leads: {detection['missing_expected']}")

    print("== Repair verification (workflow 3) ==")
    print(f"  every verifier invocation produced fresh, coherent evidence: {repair['infrastructure_ok']}")
    for name, result in repair["variants"].items():
        print(f"  {name}: {result} (expected {repair['expected'][name]})")
    print(f"  neighboring invariant caught the wrong repair: {repair['neighbor_invariant_caught_wrong_repair']}")
    print(f"  skipped command check reported: {repair['skipped_result']} (never 'verified')")
    print(f"  manual check reported: {repair['manual_result']} (never 'verified')")

    print("== False-closure guards ==")
    print(f"  valid receipt accepted as fixed: {closure['valid_receipt_accepted']}")
    print(f"  skipped check rejected: {closure['skipped_rejected']}")
    print(f"  failed check rejected: {closure['failed_rejected']}")

    print("== Limitations ==")
    for note in LIMITATIONS:
        print(f"  - {note}")

    ok = detection["ok"] and repair["ok"] and closure["ok"]
    print(f"\n{'PASS' if ok else 'FAIL'}: evaluation smoke harness")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
