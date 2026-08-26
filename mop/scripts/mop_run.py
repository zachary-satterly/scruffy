#!/usr/bin/env python3
"""One-command Mop session: preflight -> gates -> directions -> dashboard.

This is the required entry point for every Scruffy repair session. It guarantees
the run always looks the same: capabilities are probed and disclosed, the
bundle's authority and approval gates are applied, a directions.json exists for
every design-lane group (scaffolded if missing, with template imagery when a
--templates dir is given), and a self-contained decision dashboard is rendered
for the human to pick directions and decisions. Implementation never starts
from this command — it only prepares and renders the decision surface.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mop_bundle import InteropError, build_plan, load_bundle, load_interop
from mop_dashboard import render
from mop_directions import check_directions, scaffold_directions
from mop_preflight import build_preflight, to_handoff_augmentations


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", help="Scruffy audit bundle directory")
    parser.add_argument(
        "--baseline-bundle",
        help="prior Scruffy bundle directory required by a repeat context-1.2 audit",
    )
    parser.add_argument("--templates", help="reference/template image dir (Mobbin exports, taste library)")
    parser.add_argument("--assets", help="assets manifest JSON (screenshots with captions and item_ids, references, preflight)")
    parser.add_argument("--impeccable", choices=("available", "absent", "not_run"), default=None)
    parser.add_argument("--impeccable-reason", default=None)
    parser.add_argument("--design-reference-search", choices=("available", "absent", "not_run"), default=None)
    parser.add_argument("--design-reference-search-reason", default=None)
    parser.add_argument("--authorized", action="store_true", help="explicit user grant for implementation authority")
    parser.add_argument("--out", help="dashboard output path (default: <bundle>/mop-dashboard.html)")
    args = parser.parse_args(argv)

    bundle_dir = Path(args.bundle)
    interop = load_interop()
    bundle = load_bundle(
        bundle_dir,
        interop,
        baseline_source=args.baseline_bundle,
    )
    plan = build_plan(bundle, interop, args.authorized)

    # 1. Preflight — always disclosed, never assumed.
    attest = {}
    for cap in ("impeccable", "design_reference_search"):
        status = getattr(args, cap)
        reason = getattr(args, f"{cap}_reason")
        if status is not None or reason is not None:
            attest[cap] = {"status": status, "reason": reason}
    preflight = build_preflight(attest)
    augmentations = to_handoff_augmentations(preflight)
    (bundle_dir / "mop-preflight.json").write_text(
        json.dumps(preflight, indent=1) + "\n", encoding="utf-8"
    )

    # 2. Directions — scaffold when missing; validate when present.
    directions_path = bundle_dir / "directions.json"
    if directions_path.exists():
        directions = json.loads(directions_path.read_text(encoding="utf-8"))
        notes = check_directions(directions, plan, bundle=bundle, bundle_dir=bundle_dir)
        directions_state = "checked"
    else:
        directions = scaffold_directions(
            plan, preflight.get("augmentations"), bundle=bundle, templates_dir=args.templates
        )
        directions_path.write_text(json.dumps(directions, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        notes = [f"scaffolded {len(directions['groups'])} design group(s); fill TODOs before selecting"]
        directions_state = "scaffolded"

    # 3. Dashboard — the decision surface is always rendered.
    out = args.out or str(bundle_dir / "mop-dashboard.html")
    render(
        bundle_dir,
        args.assets,
        out,
        authorized=args.authorized,
        baseline_source=args.baseline_bundle,
    )

    gate = plan["gate"]
    print("Scruffy repair session prepared")
    print(f"  bundle: {plan['audit_id']} rev {plan['revision_id']}")
    print(f"  gate: {'permissible' if gate['permissible'] else 'BLOCKED'}"
          + ("" if gate["permissible"] else " — " + "; ".join(gate["reasons"])))
    print(f"  approved: {plan['approved_count']}  actionable: {plan['actionable_count']}")
    print(f"  augmentations: " + ", ".join(f"{k}={v}" for k, v in augmentations.items()))
    print(f"  directions: {directions_state} ({len(directions.get('groups', []))} design group(s))")
    for note in notes:
        print(f"    note: {note}")
    print(f"  dashboard: {out}")
    print("Next: pick directions and decisions in the dashboard, export the JSON files, "
          "then implement selected work and hand off via mop_handoff.py.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except InteropError as exc:
        print(f"REFUSED (fail closed): {exc}", file=sys.stderr)
        raise SystemExit(2)
