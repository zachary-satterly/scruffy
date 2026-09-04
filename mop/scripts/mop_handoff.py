#!/usr/bin/env python3
"""Build the re-audit handoff after Scruffy implements approved repairs.

The handoff maps each implemented item to the surfaces that changed and records a
self-assessment against the item's acceptance checks. It deliberately does NOT
set any finding to fixed/cleared: only a Scruffy re-audit has that authority. The
handoff's per-item status is always ``implemented-pending-reaudit``.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mop_bundle import InteropError, build_plan, load_bundle, load_interop, canonical_verification

# A self-check result an agent records per acceptance check after implementing.
SELF_CHECK_RESULTS = {"meets", "partial", "unmet"}
TERMINAL_STATUS = "implemented-pending-reaudit"

# Optional craft augmentations, disclosed so the re-audit and reader know whether
# the work was reference-grounded / impeccable-driven or produced on the free floor.
AUGMENTATION_KEYS = ("impeccable", "design_reference_search", "browser")
AUGMENTATION_STATES = {"used", "absent", "not_applicable", "not_reported"}


def _normalize_augmentations(augmentations: dict | None) -> dict:
    result = {k: "not_reported" for k in AUGMENTATION_KEYS}
    for key, state in (augmentations or {}).items():
        if key not in AUGMENTATION_KEYS:
            raise InteropError(f"unknown augmentation {key!r}")
        base = str(state).split(":", 1)[0]
        if base not in AUGMENTATION_STATES:
            raise InteropError(
                f"augmentation {key!r} state {state!r} is not one of "
                f"{sorted(AUGMENTATION_STATES)} (an optional ':detail' suffix is allowed)"
            )
        result[key] = state
    return result


def build_handoff(plan: dict, work: dict, augmentations: dict | None = None, verification: dict | None = None, verification_path: str | None = None) -> dict:
    """Combine the plan with the agent's per-item ``work`` record.

    ``work`` maps item_id -> {"surfaces": [...], "notes": str,
    "self_check": [{"check": str, "result": "meets|partial|unmet"}]}.
    ``augmentations`` discloses optional craft capabilities used or absent.
    """
    if not isinstance(work, dict):
        raise InteropError("work must be an object keyed by approved item ID")
    planned = {step["item_id"] for step in plan["steps"]}
    if set(work) - planned:
        raise InteropError(f"work references items outside the approved plan: {sorted(set(work) - planned)}")
    items = []
    for step in plan["steps"]:
        item_id = step["item_id"]
        if item_id not in work:
            continue
        record = work[item_id]
        if not isinstance(record, dict) or not isinstance(record.get("surfaces"), list) or not record["surfaces"] or any(not isinstance(surface, str) or not surface.strip() for surface in record["surfaces"]):
            raise InteropError(f"{item_id}: implemented work requires named changed surfaces")
        self_check = record.get("self_check", [])
        if not isinstance(self_check, list) or any(not isinstance(sc, dict) or not isinstance(sc.get("check"), str) for sc in self_check):
            raise InteropError(f"{item_id}: self_check must contain named checks")
        for sc in self_check:
            if not isinstance(sc.get("result"), str) or sc["result"] not in SELF_CHECK_RESULTS:
                raise InteropError(
                    f"{item_id}: self_check result {sc.get('result')!r} is not "
                    f"one of {sorted(SELF_CHECK_RESULTS)}"
                )
        items.append({
            "item_id": item_id,
            "title": step["title"],
            "category": step["category"],
            "acceptance_checks": step["acceptance_checks"],
            "changed_surfaces": record.get("surfaces", []),
            "notes": record.get("notes", ""),
            "self_assessment": self_check,
            "verification": {"result": (verification or {}).get(item_id, {}).get("result", "not_run"), "receipt": verification_path if item_id in (verification or {}) else None},
            # Never 'fixed'/'cleared'. Scruffy's re-audit decides that.
            "status": TERMINAL_STATUS,
            "cleared_by": "pending Scruffy re-audit",
        })
    unimplemented = [s["item_id"] for s in plan["steps"] if s["item_id"] not in work]
    return {
        "schema_version": "1.0",
        "role": "consumer",
        "producer": "scruffys-mop",
        "audit_id": plan["audit_id"],
        "revision_id": plan["revision_id"],
        "handoff_note": (
            "Re-audit these items in a new Scruffy revision. The repair stage does "
            "not mark its own work fixed or cleared."
        ),
        "augmentations": _normalize_augmentations(augmentations),
        "items": items,
        "unimplemented": unimplemented,
    }


def handoff_to_markdown(handoff: dict) -> str:
    lines = [
        "# Scruffy — repair re-audit handoff",
        "",
        f"Audit `{handoff['audit_id']}` revision `{handoff['revision_id']}`.",
        "",
        f"> {handoff['handoff_note']}",
        "",
        "Augmentations: "
        + ", ".join(f"{k}={v}" for k, v in handoff["augmentations"].items()),
        "",
    ]
    for it in handoff["items"]:
        lines.append(f"## {it['title']} ({it['item_id']}) — {it['status']}")
        if it["changed_surfaces"]:
            lines.append(f"- Changed: {', '.join(it['changed_surfaces'])}")
        if it["notes"]:
            lines.append(f"- Notes: {it['notes']}")
        proof = it["verification"]
        lines.append(f"- Canonical verification: {proof['result']}" + (f" ({proof['receipt']})" if proof['receipt'] else " — no receipt; implementation remains unverified"))
        lines.append("- Acceptance checks (self-assessed; Scruffy verifies):")
        results = {s["check"]: s["result"] for s in it["self_assessment"]}
        for c in it["acceptance_checks"]:
            lines.append(f"  - {results.get(c, 'not-assessed')}: {c}")
        lines.append("")
    if handoff["unimplemented"]:
        lines.append(f"> unimplemented: {', '.join(handoff['unimplemented'])}")
    return "\n".join(lines).rstrip() + "\n"


def _cmd(args) -> int:
    interop = load_interop()
    bundle = load_bundle(
        args.bundle,
        interop,
        baseline_source=args.baseline_bundle,
    )
    plan = build_plan(bundle, interop, args.authorized)
    work = json.loads(Path(args.work).read_text(encoding="utf-8")) if args.work else {}
    if args.augmentations and args.augmentations.startswith("@"):
        augmentations = json.loads(Path(args.augmentations[1:]).read_text(encoding="utf-8"))
    else:
        augmentations = json.loads(args.augmentations) if args.augmentations else None
    verification_path = Path(args.verification) if args.verification else Path(args.bundle) / "verification.json"
    if args.verification and not verification_path.is_file():
        raise InteropError("requested verification receipt does not exist")
    verification = canonical_verification(verification_path, bundle["findings"], bundle["decisions"]) if verification_path.is_file() else None
    handoff = build_handoff(plan, work, augmentations, verification, str(verification_path) if verification is not None else None)
    if args.json:
        print(json.dumps(handoff, indent=2))
    else:
        print(handoff_to_markdown(handoff))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Scruffy repair re-audit handoff")
    parser.add_argument("bundle", help="Path to the Scruffy audit bundle directory")
    parser.add_argument(
        "--baseline-bundle",
        help="prior Scruffy bundle directory required by a repeat context-1.2 audit",
    )
    parser.add_argument("--verification", help="canonical verification.json (defaults to bundle/verification.json); missing default remains not_run")
    parser.add_argument("--work", help="JSON file: item_id -> changed surfaces + self-check")
    parser.add_argument("--augmentations",
                        help='JSON string, or @file from mop_preflight --handoff-augmentations')
    parser.add_argument("--authorized", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.set_defaults(func=_cmd)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except InteropError as exc:
        print(f"REFUSED (fail closed): {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
