#!/usr/bin/env python3
"""Ingest, validate, gate, and plan a Scruffy audit bundle.

Scruffy owns the audit contract; its repair stage consumes it read-only. This module
loads the artifacts Scruffy emits, checks their schema versions against the
consumer compatibility key in ``schema/interop.json``, applies the authority and
approval gates, and builds the dependency-ordered implementation plan.

Dependency-free (Python 3 stdlib only). It never writes to the bundle and never
assigns a finding a fixed/cleared status — clearing is Scruffy's job.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INTEROP_PATH = REPO_ROOT / "schema" / "interop.json"

# Artifact filename -> (json key holding the version, interop.consumes key).
ARTIFACTS = {
    "findings.json": "findings.json",
    "context.json": "context.json",
    "decisions.json": "decisions.json",
    "tokens.json": "tokens.json",
}


class InteropError(Exception):
    """A bundle violates the consumer compatibility key or is unreadable."""


def resolve_scruffy_root() -> Path:
    """Resolve the canonical installation; never copy its audit schema into Mop."""
    configured = os.environ.get("SCRUFFY_ROOT")
    root = Path(configured).expanduser().resolve() if configured else REPO_ROOT.parent
    required = ("SKILL.md", "schema/audit-contract.json", "scripts/validate_audit.py", "scripts/verify_fixes.py")
    if not all((root / name).is_file() for name in required):
        raise InteropError("Scruffy canonical installation is unavailable; set SCRUFFY_ROOT to the Scruffy repository/plugin root containing SKILL.md, schema/audit-contract.json, scripts/validate_audit.py and scripts/verify_fixes.py")
    return root


def canonical_verification(path: Path, findings: dict, decisions: dict) -> dict:
    """Ask Scruffy to validate receipt integrity; this never executes checks."""
    root = resolve_scruffy_root()
    command = [sys.executable, "-c", "import sys,json;sys.path.insert(0,sys.argv[1]);from validate_audit import validate_verification_receipt;data=json.load(sys.stdin);print(json.dumps(validate_verification_receipt(data['receipt'],data['findings'],data['decisions'])))", str(root / "scripts")]
    result = subprocess.run(command, input=json.dumps({"receipt": _read_json(path), "findings": findings, "decisions": decisions}), text=True, capture_output=True)
    if result.returncode:
        raise InteropError("verification receipt failed canonical validation: " + " ".join((result.stdout + result.stderr).split()))
    return json.loads(result.stdout)


# A finding already in one of these states has nothing left to implement.
TERMINAL_STATUSES = {"fixed", "cleared", "merged", "superseded"}


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def load_interop(path: Path = INTEROP_PATH) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:  # pragma: no cover - config error
        raise InteropError(f"Cannot read interop contract at {path}: {exc}") from exc


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise InteropError(f"Cannot read {path.name}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise InteropError(f"{path.name} is not valid JSON: {exc}") from exc


def _paths_for_source(source, *, label: str) -> dict[str, Path]:
    """Resolve a bundle directory or explicit artifact-path mapping."""
    if isinstance(source, dict):
        return {name: Path(path) for name, path in source.items()}
    base = Path(source)
    if not base.is_dir():
        raise InteropError(f"{label} path is not a directory: {base}")
    return {name: base / name for name in ARTIFACTS}


def _baseline_paths(source) -> dict[str, Path] | None:
    """Resolve the canonical baseline pair required for context-1.2 continuity."""
    if source is None:
        return None
    paths = _paths_for_source(source, label="Baseline bundle")
    for required in ("findings.json", "context.json"):
        path = paths.get(required)
        if path is None or not path.is_file():
            raise InteropError(
                f"Baseline bundle is missing required artifact: {required}"
            )
    return paths


def load_bundle(
    source,
    interop: dict | None = None,
    *,
    baseline_source=None,
) -> dict:
    """Load a Scruffy audit bundle from a directory (or a dict of paths).

    Returns a dict with keys ``findings``, ``context``, ``decisions`` and, when
    present, ``tokens``. ``tokens.json`` is optional; the other three are
    required. Schema versions are validated against the interop contract.

    A repeat context-1.2 audit must also supply the prior Scruffy bundle through
    ``baseline_source``. Mop passes that bundle's ``findings.json`` and
    ``context.json`` to Scruffy's canonical validator; it does not interpret or
    copy the parent schema.
    """
    interop = interop or load_interop()
    paths = _paths_for_source(source, label="Bundle")
    baseline_paths = _baseline_paths(baseline_source)

    bundle: dict = {}
    for required in ("findings.json", "context.json", "decisions.json"):
        p = paths.get(required)
        if p is None or not p.exists():
            raise InteropError(f"Bundle is missing required artifact: {required}")
        bundle[required[:-5]] = _read_json(p)

    tokens_path = paths.get("tokens.json")
    if tokens_path is not None and tokens_path.exists():
        bundle["tokens"] = _read_json(tokens_path)
    else:
        bundle["tokens"] = None

    validate_versions(bundle, interop)
    _validate_canonical_current_context(bundle, paths, interop, baseline_paths)
    _check_cross_references(bundle)
    return bundle


# ---------------------------------------------------------------------------
# Version validation (fail closed)
# ---------------------------------------------------------------------------
def _accepted_versions(consume_spec: dict) -> tuple[str, list[str]]:
    """Return (current, [current, *legacy]) from a consumes entry."""
    current = (
        consume_spec.get("current_registry_schema")
        or consume_spec.get("current_schema")
    )
    legacy = (
        consume_spec.get("legacy_registry_schemas_readable")
        or consume_spec.get("legacy_schemas_readable")
        or []
    )
    if current is None:
        raise InteropError("interop contract is missing a current schema version")
    return current, [current, *legacy]


def _major(version: str) -> str:
    return str(version).split(".", 1)[0]


def validate_versions(bundle: dict, interop: dict) -> list[str]:
    """Validate each artifact's schema_version against the interop contract.

    Returns a list of human-readable notes (e.g. legacy-schema warnings).
    Raises InteropError, fail-closed, on any unrecognized version.
    """
    consumes = interop["consumes"]
    notes: list[str] = []
    present = [
        ("findings.json", bundle["findings"]),
        ("context.json", bundle["context"]),
        ("decisions.json", bundle["decisions"]),
    ]
    if bundle.get("tokens") is not None:
        present.append(("tokens.json", bundle["tokens"]))

    for name, doc in present:
        spec = consumes[name]
        current, accepted = _accepted_versions(spec)
        if not isinstance(doc, dict):
            raise InteropError(f"{name} must be a JSON object")
        version = str(doc.get("schema_version", "")).strip()
        if not version:
            raise InteropError(f"{name} has no schema_version")
        if version in accepted:
            if version != current:
                notes.append(
                    f"{name} is legacy schema {version} (read-only; current is {current})"
                )
            continue
        # Not recognized: distinguish unknown major from unknown minor for the
        # message, but both fail closed per compatibility_policy.
        kind = "major" if _major(version) != _major(current) else "minor"
        raise InteropError(
            f"{name} schema {version} is an unrecognized {kind} version "
            f"(Scruffy repair consumes {accepted}). Disclose the gap and stop; "
            f"do not coerce an unrecognized schema."
        )
    return notes


def _validate_canonical_current_context(
    bundle: dict,
    paths: dict[str, Path],
    interop: dict,
    baseline_paths: dict[str, Path] | None,
) -> None:
    """Delegate current-context validation to Scruffy's canonical validator.

    Mop deliberately owns no context schema. Legacy contexts retain their
    documented read-only compatibility path; the current context must satisfy
    the exact validator shipped by the parent Scruffy repository.
    """
    current_context, _ = _accepted_versions(interop["consumes"]["context.json"])
    if str(bundle["context"].get("schema_version", "")).strip() != current_context:
        if baseline_paths is not None:
            raise InteropError(
                "--baseline-bundle is only valid for the current context schema; "
                "legacy contexts retain their read-only compatibility path"
            )
        return
    validator = resolve_scruffy_root() / "scripts" / "validate_audit.py"
    if not validator.is_file():
        raise InteropError(
            "Scruffy canonical context validator is unavailable; disclose the gap and stop"
        )
    command = [
        sys.executable,
        str(validator),
        str(paths["findings.json"]),
        "--context",
        str(paths["context.json"]),
        "--decisions",
        str(paths["decisions.json"]),
    ]
    baseline_revision = bundle["context"].get("baseline_revision_id")
    if baseline_revision is not None and baseline_paths is None:
        raise InteropError(
            "repeat context-1.2 bundle requires its prior Scruffy artifacts; "
            "pass --baseline-bundle <prior-bundle-dir> (or baseline_source to load_bundle)"
        )
    if baseline_paths is not None:
        command.extend(
            [
                "--baseline",
                str(baseline_paths["findings.json"]),
                "--baseline-context",
                str(baseline_paths["context.json"]),
            ]
        )
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode:
        detail = " ".join((result.stdout + result.stderr).split())
        raise InteropError(
            "context.json failed Scruffy's canonical context-1.2 validation: "
            + (detail or "validator returned no diagnostic")
        )


def _check_cross_references(bundle: dict) -> None:
    """Every decision must reference a real registry item."""
    items = bundle["findings"].get("items")
    decisions = bundle["decisions"].get("decisions")
    if not isinstance(items, list) or any(not isinstance(it, dict) or not isinstance(it.get("id"), str) for it in items):
        raise InteropError("findings.items must contain objects with string IDs")
    item_ids = {it["id"] for it in items}
    if not isinstance(decisions, list):
        raise InteropError("decisions.json decisions must be an array")
    seen = set()
    for dec in decisions:
        if not isinstance(dec, dict) or not isinstance(dec.get("item_id"), str):
            raise InteropError("decisions entries must contain a string item_id")
        if not isinstance(dec.get("decision"), str) or dec["decision"] not in {"approve", "pending", "defer", "reject"}:
            raise InteropError("decisions entry has an invalid decision")
        if dec["item_id"] in seen:
            raise InteropError(f"duplicate decision for {dec['item_id']}")
        seen.add(dec["item_id"])
        if dec["item_id"] not in item_ids:
            raise InteropError(f"decisions.json references unknown item {dec['item_id']!r}")


# ---------------------------------------------------------------------------
# Gates
# ---------------------------------------------------------------------------
def gate_state(bundle: dict, interop: dict, authorized_override: bool = False) -> dict:
    """Report whether the bundle permits implementation.

    Authority is inherited from Scruffy's run, but the *user* is what actually
    grants Scruffy repair write access. ``authorized_override`` represents that
    explicit grant when the recorded run does not already carry it.
    """
    gate = interop["authority_gate"]
    run = bundle["findings"].get("run", {})
    mode = run.get("effective_mode")
    write_authority = run.get("repository_write_authority")

    # SKILL.md: write authority comes from Scruffy's redesign/design mode with
    # source_write, OR an explicit user grant. An explicit grant therefore
    # satisfies the mode requirement too — the grant is recorded in the gate
    # state and the handoff, so the re-audit sees exactly what happened.
    mode_ok = mode in gate["required_scruffy_mode"] or authorized_override
    authority_ok = write_authority == "authorized" or authorized_override

    reasons = []
    if not mode_ok:
        reasons.append(
            f"effective_mode {mode!r} is not one of {gate['required_scruffy_mode']} "
            "and no explicit user grant (--authorized) was given"
        )
    if not authority_ok:
        reasons.append(
            "repository_write_authority is not 'authorized' and no explicit "
            "user grant (--authorized) was given"
        )
    return {
        "effective_mode": mode,
        "repository_write_authority": write_authority,
        "authorized_override": authorized_override,
        "permissible": mode_ok and authority_ok,
        "reasons": reasons,
    }


def approved_item_ids(bundle: dict) -> set[str]:
    return {
        d["item_id"]
        for d in bundle["decisions"].get("decisions", [])
        if d.get("decision") == "approve"
    }


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------
def _items_by_id(bundle: dict) -> dict:
    return {it["id"]: it for it in bundle["findings"].get("items", [])}


def _lane_for(item: dict, ordering: dict) -> int:
    default = ordering["category_default_lane"].get(item.get("category"), 5)
    # Verification-only items would go to lane 6; none exist as categories, so
    # the default map is authoritative.
    return default


def _severity_rank(item: dict, ordering: dict) -> int:
    ranks = ordering["severity_rank"]
    sev = item.get("severity", "low")
    return ranks.index(sev) if sev in ranks else len(ranks)


def _tokens_for(bundle: dict, item_id: str) -> list[dict]:
    tokens = bundle.get("tokens") or {}
    return [
        t for t in tokens.get("tokens", []) if item_id in t.get("finding_ids", [])
    ]


def build_plan(bundle: dict, interop: dict, authorized_override: bool = False) -> dict:
    """Build the dependency-ordered implementation plan for approved items."""
    ordering = interop["ordering"]
    gate = gate_state(bundle, interop, authorized_override)
    approved = approved_item_ids(bundle)
    items = _items_by_id(bundle)

    # Approved findings and enhancements only. Strengths are never actioned, and
    # an item already in a terminal status has nothing left to implement even if
    # it was approved — skip it with a warning rather than re-doing settled work.
    warnings: list[str] = []
    actionable = []
    for item_id in sorted(approved):
        it = items[item_id]
        if it.get("kind") not in ("finding", "enhancement"):
            continue
        if it.get("status") in TERMINAL_STATUSES:
            warnings.append(
                f"{item_id} is approved but already {it['status']}; skipped "
                f"(nothing to implement — re-audit if you disagree)"
            )
            continue
        actionable.append(it)
    actionable_ids = {it["id"] for it in actionable}

    explicit_orders = bundle["context"].get("work_orders") or []

    if explicit_orders:
        steps, wo_warn = _plan_from_work_orders(
            explicit_orders, items, actionable_ids, ordering
        )
        warnings.extend(wo_warn)
        basis = "explicit_work_orders"
    else:
        steps, syn_warn = _synthesize_plan(actionable, actionable_ids, ordering)
        warnings.extend(syn_warn)
        basis = "synthesized"

    for step in steps:
        step["tokens"] = _tokens_for(bundle, step["item_id"])

    return {
        "audit_id": bundle["findings"].get("audit_id"),
        "revision_id": bundle["findings"].get("revision_id"),
        "ordering_basis": basis,
        "gate": gate,
        "approved_count": len(approved),
        "actionable_count": len(actionable),
        "steps": steps,
        "warnings": warnings,
    }


def _step(item: dict, lane: int, work_order_id=None) -> dict:
    return {
        "item_id": item["id"],
        "title": item.get("title"),
        "category": item.get("category"),
        "severity": item.get("severity"),
        "lane": lane,
        "depends_on": list(item.get("depends_on", [])),
        "recommendation": item.get("recommendation"),
        "acceptance_checks": list(item.get("acceptance_checks", [])),
        "work_order_id": work_order_id,
    }


def _synthesize_plan(actionable: list, actionable_ids: set, ordering: dict):
    """Topological sort by depends_on; tie-break by (lane, severity, id)."""
    warnings: list[str] = []
    by_id = {it["id"]: it for it in actionable}

    # Edges: a depends_on b  =>  b must precede a. Only keep edges within the
    # actionable set; a dependency on a non-approved item is flagged, not dropped
    # silently.
    remaining_deps: dict[str, set] = {}
    for it in actionable:
        deps = set()
        for dep in it.get("depends_on", []):
            if dep in actionable_ids:
                deps.add(dep)
            else:
                warnings.append(
                    f"{it['id']} depends on {dep}, which is not in the approved "
                    f"set; implement or re-audit that dependency first"
                )
        remaining_deps[it["id"]] = deps

    def sort_key(item_id):
        it = by_id[item_id]
        return (_lane_for(it, ordering), _severity_rank(it, ordering), item_id)

    ordered: list[str] = []
    ready = sorted(
        (i for i, d in remaining_deps.items() if not d), key=sort_key
    )
    ready = list(dict.fromkeys(ready))
    while ready:
        node = ready.pop(0)
        ordered.append(node)
        for other, deps in remaining_deps.items():
            if node in deps:
                deps.discard(node)
                if not deps and other not in ordered and other not in ready:
                    ready.append(other)
        ready.sort(key=sort_key)

    if len(ordered) != len(actionable):
        cycle = [i for i in remaining_deps if i not in ordered]
        raise InteropError(
            f"depends_on cycle among approved items: {sorted(cycle)}"
        )

    return [_step(by_id[i], _lane_for(by_id[i], ordering)) for i in ordered], warnings


def _plan_from_work_orders(orders: list, items: dict, actionable_ids: set, ordering: dict):
    """Apply explicit order only among nodes whose prerequisites are ready."""
    ranks = {}
    for order in sorted(orders, key=lambda o: o.get("lane", 99)):
        for item_id in order.get("item_ids", []):
            if item_id in actionable_ids and item_id not in ranks:
                ranks[item_id] = (len(ranks), order)
    warnings = []
    dependencies = {}
    for item_id in actionable_ids:
        deps = set(items[item_id].get("depends_on", []))
        dependencies[item_id] = deps & actionable_ids
        for dep in sorted(deps - actionable_ids):
            warnings.append(f"{item_id} depends on {dep}, which is not in the approved set; implement or re-audit that dependency first")
    def priority(item_id):
        return (0, ranks[item_id][0]) if item_id in ranks else (1, _lane_for(items[item_id], ordering), _severity_rank(items[item_id], ordering), item_id)
    steps = []
    while dependencies:
        ready = [item_id for item_id, deps in dependencies.items() if not deps]
        if not ready:
            raise InteropError(f"depends_on cycle among approved items: {sorted(dependencies)}")
        item_id = min(ready, key=priority)
        order = ranks.get(item_id, (None, {}))[1]
        steps.append(_step(items[item_id], order.get("lane", _lane_for(items[item_id], ordering)), order.get("id")))
        del dependencies[item_id]
        for deps in dependencies.values():
            deps.discard(item_id)
    uncovered = actionable_ids - ranks.keys()
    if uncovered:
        warnings.append(f"{len(uncovered)} approved item(s) were not in any work order; dependency-ordered with synthesized priorities")
    return steps, warnings


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def plan_to_markdown(plan: dict) -> str:
    lines = [
        f"# Scruffy — repair implementation plan",
        "",
        f"- Audit: `{plan['audit_id']}` revision `{plan['revision_id']}`",
        f"- Ordering basis: {plan['ordering_basis']}",
        f"- Approved items: {plan['approved_count']}  |  actionable: {plan['actionable_count']}",
        f"- Authority: {'PERMISSIBLE' if plan['gate']['permissible'] else 'BLOCKED — plan is advisory only'}",
    ]
    if not plan["gate"]["permissible"]:
        for r in plan["gate"]["reasons"]:
            lines.append(f"  - blocked: {r}")
    lines.append("")
    for n, step in enumerate(plan["steps"], 1):
        lines.append(
            f"## Step {n} — {step['title']} ({step['item_id']}, lane {step['lane']})"
        )
        lines.append(f"- Category: {step['category']}  |  Severity: {step['severity']}")
        if step["depends_on"]:
            lines.append(f"- Depends on: {', '.join(step['depends_on'])}")
        lines.append(f"- Do: {step['recommendation']}")
        lines.append("- Acceptance checks:")
        for c in step["acceptance_checks"]:
            lines.append(f"  - [ ] {c}")
        for t in step["tokens"]:
            lines.append(
                f"- Token: `{t['name']}` {t['current']} → {t['proposed']} ({t['reason']})"
            )
        lines.append("")
    for w in plan["warnings"]:
        lines.append(f"> warning: {w}")
    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _cmd_check(args) -> int:
    interop = load_interop()
    bundle = load_bundle(args.bundle, interop, baseline_source=args.baseline_bundle)
    notes = validate_versions(bundle, interop)
    gate = gate_state(bundle, interop, args.authorized)
    approved = approved_item_ids(bundle)
    print(f"bundle OK: {bundle['findings'].get('audit_id')} "
          f"rev {bundle['findings'].get('revision_id')}")
    print(f"items: {len(bundle['findings'].get('items', []))}  approved: {len(approved)}")
    print(f"authority: {'permissible' if gate['permissible'] else 'BLOCKED'}")
    for r in gate["reasons"]:
        print(f"  - {r}")
    for note in notes:
        print(f"  note: {note}")
    return 0


def _cmd_plan(args) -> int:
    interop = load_interop()
    bundle = load_bundle(args.bundle, interop, baseline_source=args.baseline_bundle)
    plan = build_plan(bundle, interop, args.authorized)
    if args.json:
        print(json.dumps(plan, indent=2))
    else:
        print(plan_to_markdown(plan))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Scruffy repair bundle tool")
    sub = parser.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="Validate a bundle and report the gate state")
    c.add_argument("bundle", help="Path to a directory of Scruffy audit artifacts")
    c.add_argument(
        "--baseline-bundle",
        help="Prior Scruffy bundle directory required by a repeat context-1.2 audit",
    )
    c.add_argument("--authorized", action="store_true",
                   help="Explicit user grant of Scruffy repair write authority")
    c.set_defaults(func=_cmd_check)

    p = sub.add_parser("plan", help="Emit the dependency-ordered plan")
    p.add_argument("bundle", help="Path to a directory of Scruffy audit artifacts")
    p.add_argument(
        "--baseline-bundle",
        help="Prior Scruffy bundle directory required by a repeat context-1.2 audit",
    )
    p.add_argument("--authorized", action="store_true",
                   help="Explicit user grant of Scruffy repair write authority")
    p.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown")
    p.set_defaults(func=_cmd_plan)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except InteropError as exc:
        print(f"REFUSED (fail closed): {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
