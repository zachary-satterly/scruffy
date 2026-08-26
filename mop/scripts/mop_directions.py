#!/usr/bin/env python3
"""Direction picker for design-lane findings: scaffold, validate, and gate.

For approved findings in the design lanes (visual, product,
information_architecture, interaction), Scruffy proposes three
structurally distinct directions per work group — following Scruffy's ladder
(paradigm, then material, then composition) — marks exactly one as
``recommended``, and implements ONLY a direction a human selected. The
``recommended`` flag is advice; it is never auto-selected.

The craft engine per group is disclosed from the preflight: ``impeccable`` when
the runtime has it, otherwise the built-in craft ``floor`` — the free-tier path
is the contract, not a degraded mode. Grounding is ``design_reference_search``
(for example Mobbin) when available, otherwise ``internal`` (Scruffy archetypes
plus impeccable anti-patterns). An absence is disclosed, never a defect.

A UI recommendation cannot be made with text alone. Every direction must cite
the principle(s) that motivated the finding (``principle_refs`` into Scruffy's
principles corpus — Kole Jain [KJ], Refactoring UI [RUI], Butterick, NN/g, …),
and a **visual-category direction is not selectable without at least one image
anchor**: a reference/template image (Mobbin export, taste-library entry, local
mockup) or an annotated baseline screenshot. When the runtime cannot supply
imagery, the group is emitted ``imagery: "unavailable"`` and stays advisory —
Scruffy refuses the selection instead of pretending prose is a design.

Dependency-free (Python 3 stdlib only). Consumes Scruffy's bundle read-only;
owns exactly one artifact: ``directions.json`` (schema 1.1), written beside
``decisions.json`` in the bundle directory.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mop_bundle import InteropError, build_plan, load_bundle, load_interop

DESIGN_CATEGORIES = {"visual", "product", "information_architecture", "interaction"}
IMAGERY_REQUIRED_CATEGORIES = {"visual"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}

# Every image anchor must declare where it comes from. Cross-product leakage —
# another audited product's evidence appearing as "reference" — is a provenance
# breach, not a style choice.
ANCHOR_ORIGINS = {
    "target_baseline",      # a screenshot receipt from THIS audit's evidence
    "design_reference",     # an external published pattern (e.g. Mobbin), source named
    "taste_library",        # user-curated reference explicitly designated for reuse
    "mockup",               # produced for this work, stored inside the bundle
}
CRAFT_ENGINES = {"impeccable", "floor"}
GROUNDING_TIERS = {"design_reference_search", "internal"}
DIRECTIONS_PER_GROUP = 3

# Finding category -> impeccable commands worth reaching for when the engine is
# present. Advisory routing; the floor checklist below always applies.
IMPECCABLE_ROUTES = {
    "visual": ("polish", "bolder", "quieter", "typeset", "layout", "colorize"),
    "product": ("critique", "shape"),
    "information_architecture": ("shape", "distill"),
    "interaction": ("animate", "harden", "onboard"),
}

# The built-in craft floor: applied verbatim when impeccable is absent, and as a
# final pass even when it is present.
CRAFT_FLOOR = (
    "Preserve the product's real identity and content; no template swaps.",
    "Change the structural cause, not the cosmetic symptom.",
    "Keep type, spacing, and color changes on the existing token scale; propose token deltas, never inline overrides.",
    "Keyboard, focus-visible, and reduced-motion behavior must survive the change.",
    "Re-run the item's acceptance checks and the repo's own gates before handoff.",
)


def _preflight_states(augmentations: dict | None) -> tuple[str, str]:
    """Map preflight augmentations to (craft_engine, grounding_tier)."""
    aug = augmentations or {}
    def status(key: str) -> str:
        rec = aug.get(key)
        if isinstance(rec, dict):
            return str(rec.get("status", "not_run"))
        return str(rec or "not_run")
    engine = "impeccable" if status("impeccable") in {"available", "used"} else "floor"
    grounding = (
        "design_reference_search"
        if status("design_reference_search") in {"available", "used"}
        else "internal"
    )
    return engine, grounding


def design_groups(plan: dict, bundle: dict | None = None) -> list[dict]:
    """Group actionable design-lane steps by work order (or singleton by item)."""
    items_by_id = {}
    if bundle:
        items_by_id = {i["id"]: i for i in bundle.get("findings", {}).get("items", [])}
    groups: dict[str, dict] = {}
    for step in plan["steps"]:
        if step.get("category") not in DESIGN_CATEGORIES:
            continue
        key = step.get("work_order_id") or step["item_id"]
        group = groups.setdefault(
            key, {"work_order_id": step.get("work_order_id"), "item_ids": [], "categories": [], "principle_refs": []}
        )
        group["item_ids"].append(step["item_id"])
        if step.get("category") not in group["categories"]:
            group["categories"].append(step["category"])
        for ref in (items_by_id.get(step["item_id"], {}).get("principle_refs") or []):
            if ref not in group["principle_refs"]:
                group["principle_refs"].append(ref)
    return [
        {"id": f"GRP-{index}", **group}
        for index, group in enumerate(groups.values(), start=1)
    ]


def _collect_template_images(templates_dir: str | Path | None) -> list[dict]:
    """Curated taste-library images offered as a pool; never auto-attached to directions."""
    if not templates_dir:
        return []
    base = Path(templates_dir)
    if not base.is_dir():
        raise InteropError(f"templates dir does not exist: {base}")
    anchors = []
    for path in sorted(base.rglob("*")):
        if path.suffix.lower() in IMAGE_SUFFIXES:
            anchors.append({
                "source": path.stem.replace("-", " "),
                "image": str(path),
                "origin": "taste_library",
                "note": "",
            })
    return anchors


def _baseline_screenshots(bundle: dict | None) -> list[dict]:
    """Screenshot receipts already captured by the Scruffy audit, usable as before-images."""
    if not bundle:
        return []
    assets = bundle.get("context", {}).get("evidence_assets") or []
    return [
        {
            "source": f"audit baseline {a['id']}",
            "image": a["locator"],
            "origin": "target_baseline",
            "note": a.get("description", ""),
        }
        for a in assets
        if a.get("kind") == "screenshot"
    ]


def scaffold_directions(
    plan: dict,
    augmentations: dict | None = None,
    bundle: dict | None = None,
    templates_dir: str | Path | None = None,
) -> dict:
    """Emit a directions.json skeleton: three TODO directions per design group."""
    engine, grounding = _preflight_states(augmentations)
    template_anchors = _collect_template_images(templates_dir)
    baseline_anchors = _baseline_screenshots(bundle)
    groups = []
    for group in design_groups(plan, bundle):
        reference_pool = template_anchors + baseline_anchors
        needs_imagery = bool(set(group.get("categories", [])) & IMAGERY_REQUIRED_CATEGORIES)
        imagery = "available" if (reference_pool or not needs_imagery) else "unavailable"
        directions = []
        for letter in ("A", "B", "C"):
            directions.append({
                "id": f"{group['id']}-{letter}",
                "title": f"TODO direction {letter}",
                "paradigm": f"TODO-distinct-paradigm-{letter}",
                "material": "TODO material system",
                "thesis": "TODO: one-paragraph thesis tied to the product frame.",
                "principle_refs": list(group.get("principle_refs", [])) or ["TODO: cite the principle that fired, e.g. [KJ §n] / [RUI] / PRINCIPLES §n"],
                "grounding": [],
                "tokens_delta": [],
                "risk": "TODO: what this direction could break.",
                "impeccable_route": list(IMPECCABLE_ROUTES.get("visual", ())) if engine == "impeccable" else [],
                "recommended": letter == "A",
            })
        groups.append({
            **group,
            "craft_engine": engine,
            "grounding_tier": grounding,
            "imagery": imagery,
            "reference_pool": reference_pool,
            "directions": directions,
            "selected": None,
        })
    return {
        "schema_version": "1.1",
        "producer": "scruffys-mop",
        "reference_sources": ([str(Path(templates_dir).resolve())] if templates_dir else []),
        "audit_id": plan["audit_id"],
        "revision_id": plan["revision_id"],
        "craft_floor": list(CRAFT_FLOOR),
        "note": (
            "A human selects a direction per group; 'recommended' is advice and is "
            "never auto-selected. Groups without a selection are not implemented."
        ),
        "groups": groups,
    }


def _anchor_path_allowed(image: str, directions: dict, plan_bundle_dir: Path | None, bundle: dict | None) -> bool:
    """An image path is legitimate only if it lives in a declared reference source,
    inside the bundle itself (mockups, captured evidence), or matches one of this
    audit's screenshot receipt locators. Anything else is cross-product leakage."""
    path = Path(image)
    declared = [Path(src) for src in directions.get("reference_sources", [])]
    if plan_bundle_dir is not None:
        declared.append(plan_bundle_dir)
    try:
        resolved = path.resolve()
    except OSError:
        return False
    for base in declared:
        try:
            resolved.relative_to(base.resolve())
            return True
        except ValueError:
            continue
    if bundle:
        for asset in bundle.get("context", {}).get("evidence_assets") or []:
            if asset.get("kind") == "screenshot" and asset.get("locator") == image:
                return True
    return False


def check_directions(
    directions: dict,
    plan: dict,
    bundle: dict | None = None,
    bundle_dir: str | Path | None = None,
) -> list[str]:
    """Validate a directions document against the plan. Raises InteropError."""
    notes: list[str] = []
    if directions.get("schema_version") not in {"1.0", "1.1"}:
        raise InteropError("directions.schema_version must be 1.0 or 1.1")
    for field in ("audit_id", "revision_id"):
        if directions.get(field) != plan.get(field):
            raise InteropError(f"directions.{field} does not match the plan")
    plan_design_items = {
        step["item_id"] for step in plan["steps"] if step.get("category") in DESIGN_CATEGORIES
    }
    covered: set[str] = set()
    for group in directions.get("groups", []):
        gid = group.get("id") or "<missing id>"
        if group.get("craft_engine") not in CRAFT_ENGINES:
            raise InteropError(f"{gid}: craft_engine must be one of {sorted(CRAFT_ENGINES)}")
        if group.get("grounding_tier") not in GROUNDING_TIERS:
            raise InteropError(f"{gid}: grounding_tier must be one of {sorted(GROUNDING_TIERS)}")
        dirs = group.get("directions", [])
        if len(dirs) < DIRECTIONS_PER_GROUP:
            raise InteropError(f"{gid}: needs at least {DIRECTIONS_PER_GROUP} directions, got {len(dirs)}")
        paradigms = [d.get("paradigm", "").strip().lower() for d in dirs]
        if len(set(paradigms)) != len(paradigms):
            raise InteropError(f"{gid}: directions must be structurally distinct (paradigms repeat)")
        recommended = [d for d in dirs if d.get("recommended") is True]
        if len(recommended) != 1:
            raise InteropError(f"{gid}: exactly one direction must be recommended, got {len(recommended)}")
        direction_ids = {d.get("id") for d in dirs}
        if len(direction_ids) != len(dirs):
            raise InteropError(f"{gid}: direction IDs repeat")
        for d in dirs:
            refs = d.get("principle_refs") or []
            if not refs or any(str(r).startswith("TODO") for r in refs):
                raise InteropError(
                    f"{gid}/{d.get('id')}: every direction must cite the principle(s) it serves "
                    "(principle_refs into Scruffy's corpus, e.g. [KJ §n], [RUI], PRINCIPLES §n)"
                )
            for ref in d.get("grounding", []):
                if not ref.get("image"):
                    continue
                origin = ref.get("origin")
                if origin not in ANCHOR_ORIGINS:
                    raise InteropError(
                        f"{gid}/{d.get('id')}: image anchor {ref.get('source')!r} must declare an origin "
                        f"in {sorted(ANCHOR_ORIGINS)} — untyped imagery is a provenance breach"
                    )
                if origin == "design_reference" and not (ref.get("source") or "").strip():
                    raise InteropError(f"{gid}/{d.get('id')}: design_reference anchors must name their source")
        base_dir = Path(bundle_dir) if bundle_dir else None
        for d in dirs:
            for ref in d.get("grounding", []):
                image = ref.get("image")
                if image and not _anchor_path_allowed(image, directions, base_dir, bundle):
                    raise InteropError(
                        f"{gid}/{d.get('id')}: image {image!r} is outside every declared reference source "
                        "and is not this audit's evidence — refusing cross-product imagery. Declare a curated "
                        "taste library via reference_sources/--templates or use this bundle's own screenshots."
                    )
        needs_imagery = bool(set(group.get("categories", [])) & IMAGERY_REQUIRED_CATEGORIES)
        selected = group.get("selected")
        if selected is not None and selected not in direction_ids:
            raise InteropError(f"{gid}: selected {selected!r} is not a direction in this group")
        if needs_imagery and selected is not None:
            chosen = next(d for d in dirs if d.get("id") == selected)
            image_anchors = [ref for ref in chosen.get("grounding", []) if ref.get("image")]
            if not image_anchors:
                raise InteropError(
                    f"{gid}: visual direction {selected!r} has no image anchor — a UI recommendation "
                    "cannot be made with text alone. Attach a template/reference image or an "
                    "annotated baseline screenshot, or leave the group unselected (advisory)."
                )
        if group.get("imagery") == "unavailable" and selected is not None:
            raise InteropError(
                f"{gid}: imagery is unavailable in this runtime; the group is advisory-only and "
                "cannot be selected until reference or screenshot imagery exists"
            )
        if selected is None:
            notes.append(f"{gid}: no selection — group will not be implemented")
        unknown = set(group.get("item_ids", [])) - plan_design_items
        if unknown:
            raise InteropError(f"{gid}: item_ids not in the plan's design lanes: {sorted(unknown)}")
        covered.update(group.get("item_ids", []))
    uncovered = plan_design_items - covered
    if uncovered:
        notes.append(f"design items without a directions group: {sorted(uncovered)}")
    return notes


def selected_item_ids(directions: dict) -> set[str]:
    """Item IDs whose group has a human selection."""
    chosen: set[str] = set()
    for group in directions.get("groups", []):
        if group.get("selected"):
            chosen.update(group.get("item_ids", []))
    return chosen


def implementable_steps(plan: dict, directions: dict | None) -> list[dict]:
    """Plan steps Scruffy may implement now.

    Non-design steps pass through (their contract is the item recommendation).
    Design-lane steps additionally require a selected direction; without one
    they are withheld — nothing is built that a human did not pick.
    """
    if directions is None:
        chosen: set[str] = set()
    else:
        chosen = selected_item_ids(directions)
    steps = []
    for step in plan["steps"]:
        if step.get("category") in DESIGN_CATEGORIES and step["item_id"] not in chosen:
            continue
        steps.append(step)
    return steps


def _cmd_scaffold(args) -> int:
    interop = load_interop()
    bundle = load_bundle(
        args.bundle,
        interop,
        baseline_source=args.baseline_bundle,
    )
    plan = build_plan(bundle, interop, args.authorized)
    augmentations = json.loads(Path(args.preflight).read_text(encoding="utf-8")).get("augmentations") if args.preflight else None
    doc = scaffold_directions(plan, augmentations, bundle=bundle, templates_dir=args.templates)
    out = Path(args.out or (Path(args.bundle) / "directions.json"))
    if out.exists() and not args.force:
        raise InteropError(f"{out} exists; pass --force to overwrite")
    out.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {out}: {len(doc['groups'])} design group(s); fill TODOs, then run check")
    return 0


def _cmd_check(args) -> int:
    interop = load_interop()
    bundle = load_bundle(
        args.bundle,
        interop,
        baseline_source=args.baseline_bundle,
    )
    plan = build_plan(bundle, interop, args.authorized)
    path = Path(args.directions or (Path(args.bundle) / "directions.json"))
    directions = json.loads(path.read_text(encoding="utf-8"))
    notes = check_directions(directions, plan, bundle=bundle, bundle_dir=args.bundle)
    steps = implementable_steps(plan, directions)
    print(f"directions OK: {len(directions.get('groups', []))} group(s)")
    for note in notes:
        print(f"  note: {note}")
    print(f"implementable now: {len(steps)} step(s): {[s['item_id'] for s in steps]}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Scruffy repair direction picker")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, fn in (("scaffold", _cmd_scaffold), ("check", _cmd_check)):
        p = sub.add_parser(name)
        p.add_argument("bundle", help="Scruffy audit bundle directory")
        p.add_argument(
            "--baseline-bundle",
            help="prior Scruffy bundle directory required by a repeat context-1.2 audit",
        )
        p.add_argument("--authorized", action="store_true")
        if name == "scaffold":
            p.add_argument("--preflight", help="mop_preflight --json output file")
            p.add_argument("--templates", help="directory of reference/template images (Mobbin exports, taste library, mockups)")
            p.add_argument("--out", help="output path (default: <bundle>/directions.json)")
            p.add_argument("--force", action="store_true")
        else:
            p.add_argument("--directions", help="directions.json path (default: <bundle>/directions.json)")
        p.set_defaults(func=fn)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except InteropError as exc:
        print(f"REFUSED (fail closed): {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
