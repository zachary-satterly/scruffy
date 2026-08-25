#!/usr/bin/env python3
"""Emit a pre-valid Scruffy audit bundle (findings/context/decisions) to edit in place.

The emitted trio passes validate_audit.py as-is, so an audit session starts from
green and every subsequent edit is a small diff against a valid document instead
of a multi-round negotiation with the validator. Placeholders are marked TODO.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from audit_contract import load_contract, mode_map

ROOT = Path(__file__).resolve().parents[1]
AUDIT_CONTRACT = load_contract()
RUN_MODES = mode_map(AUDIT_CONTRACT)
AUTHORITY_STATES = tuple(AUDIT_CONTRACT["run"]["authority_states"])
# Keep this aligned with validate_audit.ITEM_ID. The generated numeric suffix
# consumes the final hyphen and digit segment.
ITEM_PREFIX = re.compile(r"^[A-Z][A-Z0-9]{1,5}$")
MAX_SCREENSHOT_BYTES = 25 * 1024 * 1024

FRAME = [
    ("audience", "Who is it for?"),
    ("job", "What job does it perform?"),
    ("primary_action", "What is the primary action?"),
    ("differentiator", "What makes it meaningfully different?"),
    ("return_reason", "Why would someone return?"),
    ("success_signal", "What observable result means it succeeded?"),
]
CAPABILITY_KEYS = [
    "source_read", "rendered_page", "interaction_keyboard", "screenshots",
    "console_network_accessibility_performance", "source_write",
    "prior_audit_data", "copy_context", "design_reference_search",
]
CATEGORIES = [
    "product", "information_architecture", "interaction", "accessibility",
    "visual", "copy", "backend_shape", "performance",
]


def screenshot_extension(path: Path) -> str | None:
    """Return a browser-compatible raster extension from file bytes."""
    with path.open("rb") as handle:
        header = handle.read(16)
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if header.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if header.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return ".webp"
    return None


def preflight_screenshots(paths: list[Path]) -> list[tuple[Path, Path]]:
    prepared: list[tuple[Path, Path]] = []
    for index, supplied in enumerate(paths, start=1):
        source = supplied.expanduser().resolve()
        if not source.is_file():
            raise ValueError(f"supplied screenshot is not a readable file: {supplied}")
        size = source.stat().st_size
        if size == 0 or size > MAX_SCREENSHOT_BYTES:
            raise ValueError(
                f"supplied screenshot must be between 1 byte and {MAX_SCREENSHOT_BYTES} bytes: {supplied}"
            )
        extension = screenshot_extension(source)
        if extension is None:
            raise ValueError(
                f"supplied screenshot is not a recognized PNG, JPEG, GIF, or WebP raster image: {supplied}"
            )
        prepared.append((source, Path("evidence") / f"supplied-screenshot-{index:02d}{extension}"))
    return prepared


def validate_mode_authority(mode: str, authority: str) -> None:
    if authority == "authorized" and not RUN_MODES[mode]["repository_writes_allowed"]:
        raise ValueError(f"mode {mode} forbids repository-write authority")


def build(
    audit_id: str,
    target: str,
    title: str,
    item_prefix: str,
    mode: str,
    authority: str,
    screenshots: list[tuple[Path, Path]],
) -> tuple[dict, dict, dict]:
    today = _dt.date.today().isoformat()
    rev = f"{audit_id}-{today}-r1"
    first_id = f"{item_prefix}-1"
    effective_mode = mode
    if mode in {"redesign", "design"} and authority == "not_authorized":
        effective_mode = "audit"
    authority_basis_type = "explicit_request" if authority == "authorized" else "not_granted"
    authority_basis = (
        "TODO: cite the user's explicit repository-write authorization."
        if authority == "authorized"
        else "TODO: what the user asked for and what was authorized."
    )
    screenshot_assets = [
        {
            "id": f"EV-SCREENSHOT-{index}",
            "kind": "screenshot",
            "verification": "supplied",
            "locator": destination.as_posix(),
            "description": f"TODO: describe supplied screenshot {index} and the state it shows.",
        }
        for index, (_, destination) in enumerate(screenshots, start=1)
    ]
    seed_evidence_id = screenshot_assets[0]["id"] if screenshot_assets else "EV-1"
    evidence_assets = screenshot_assets or [
        {
            "id": "EV-1",
            "kind": "supplied",
            "verification": "observed",
            "locator": "https://example.invalid/replace-with-real-evidence",
            "description": "TODO: replace with the first typed evidence receipt.",
        }
    ]
    item = {
        "id": first_id,
        "identity_key": "todo-first-finding-identity",
        "kind": "finding",
        # The plain lead is written first and rewritten last. If it cannot be
        # said without the taxonomy, the finding is not understood yet.
        "plain": "TODO: one or two sentences, under 32 words, naming what is wrong in the reader's own words.",
        "title": "TODO: replace with the first verified finding",
        "category": "product",
        "severity": "low",
        "confidence": "low",
        "status": "needs-verification",
        "revision_disposition": "new",
        "first_seen_revision": rev,
        "last_observed_revision": rev,
        "observation": "TODO: what was observed, stated as fact.",
        "user_impact": "TODO: the concrete consequence for a user performing a real task.",
        "evidence": ["TODO: smallest evidence that proves or disproves the claim."],
        "evidence_refs": [seed_evidence_id],
        "cause": "TODO: structural cause, once known.",
        "recommendation": "TODO: smallest coherent change.",
        "acceptance_checks": ["TODO: observable check that clears this item."],
        "editorial_review": None,
        "facets": [],
        "depends_on": [],
        "disposition_reason": "Baseline item.",
        "destination_id": None,
    }
    registry = {
        "schema_version": "2.1",
        "audit_id": audit_id,
        "target": target,
        "revision_id": rev,
        "baseline_revision_id": None,
        "run": {
            "requested_mode": mode,
            "effective_mode": effective_mode,
            "mode_selection_basis": "explicit",
            "repository_write_authority": authority,
            "authority_basis_type": authority_basis_type,
            "authority_basis": authority_basis,
            "repository_writes_performed": False,
            "repository_write_paths": [],
            "live_demonstration_performed": False,
            "blind_status": "not_run",
            "blind_artifact_refs": [],
        },
        "items": [item],
        "presentation": {
            "prioritized_finding_ids": [first_id],
            "prioritized_enhancement_ids": [],
            "strength_ids": [],
            "cleared_ids": [],
        },
    }
    context = {
        "schema_version": "1.1",
        "audit_id": audit_id,
        "revision_id": rev,
        "title": title,
        "outcome": {
            "label": "TODO: one-line outcome",
            "summary": "TODO: what the audit concluded, including what was not tested.",
            "confidence": "TODO: overall confidence and why it is capped where it is.",
        },
        "product_frame": [
            {"key": key, "question": question, "answer": "TODO", "basis": "inferred"}
            for key, question in FRAME
        ],
        "tasks": [
            {"id": "T1", "goal": "TODO: primary task", "result": "TODO", "status": "partial", "evidence_refs": [seed_evidence_id]},
            {"id": "T2", "goal": "TODO: recovery or error path", "result": "TODO", "status": "partial", "evidence_refs": [seed_evidence_id]},
            {"id": "T3", "goal": "TODO: repeat-use or persistence task", "result": "TODO", "status": "partial", "evidence_refs": [seed_evidence_id]},
        ],
        "capabilities": [
            {
                "key": key,
                "status": (
                    "available" if key == "source_write" and authority == "authorized"
                    else "not_authorized" if key == "source_write"
                    else "partial" if key == "screenshots" and screenshots
                    else "not_run"
                ),
                "scope": (
                    f"{len(screenshots)} supplied screenshot(s) copied into this bundle for typed evidence and dashboard embedding."
                    if key == "screenshots" and screenshots
                    else "TODO: record what was actually possible for this capability."
                ),
            }
            for key in CAPABILITY_KEYS
        ],
        "scores": [
            {"category": category, "score": 1, "evidence": "TODO: evidence for this category's score.", "evidence_refs": [seed_evidence_id]}
            for category in CATEGORIES
        ],
        "work_orders": [],
        "checks_not_run": [
            {"check": "TODO: named check", "reason": "TODO: why it could not run", "impact": "TODO: what cannot be claimed as a result"}
        ],
        "visual_evidence": [],
        "evidence_assets": evidence_assets,
    }
    decisions = {
        "schema_version": "2.1",
        "audit_id": audit_id,
        "revision_id": rev,
        "baseline_revision_id": None,
        "decisions": [
            {"item_id": first_id, "decision": "pending", "note": "", "updated_at": None,
             "decision_source": "initial", "destination_id": None, "history": []}
        ],
    }
    return registry, context, decisions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-id", required=True, help="Stable product/target audit ID, e.g. nagops-plugin")
    parser.add_argument("--target", required=True, help="Human-readable target description")
    parser.add_argument("--title", required=True, help="Audit title")
    parser.add_argument("--item-prefix", default=None, help="Registry ID prefix (default: derived from audit ID)")
    parser.add_argument("--mode", choices=tuple(RUN_MODES), default="audit", help="Requested audit-contract mode")
    parser.add_argument(
        "--repository-write-authority",
        choices=AUTHORITY_STATES,
        default="not_authorized",
        help="Explicit target-repository write authority state",
    )
    parser.add_argument(
        "--supplied-screenshot",
        action="append",
        type=Path,
        default=[],
        help="Supplied raster screenshot to copy into typed evidence (repeatable)",
    )
    parser.add_argument("--out", type=Path, required=True, help="Output directory for the bundle")
    parser.add_argument("--no-validate", action="store_true", help="Skip the self-validation pass")
    args = parser.parse_args(argv)

    prefix = args.item_prefix or "".join(c for c in args.audit_id.upper() if c.isalnum())[:3] or "AUD"
    if not ITEM_PREFIX.fullmatch(prefix):
        parser.error(
            "--item-prefix must contain 2-6 uppercase ASCII letters or digits, start with a letter, "
            "and contain no hyphens (for example, OMPMOB)"
        )
    try:
        validate_mode_authority(args.mode, args.repository_write_authority)
        screenshots = preflight_screenshots(args.supplied_screenshot)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    registry, context, decisions = build(
        args.audit_id,
        args.target,
        args.title,
        prefix,
        args.mode,
        args.repository_write_authority,
        screenshots,
    )
    args.out.mkdir(parents=True, exist_ok=True)
    for source, destination in screenshots:
        target = args.out / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    for name, data in (("findings.json", registry), ("context.json", context), ("decisions.json", decisions)):
        (args.out / name).write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    if not args.no_validate:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "validate_audit.py"),
             str(args.out / "findings.json"),
             "--context", str(args.out / "context.json"),
             "--decisions", str(args.out / "decisions.json")],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            print(proc.stdout + proc.stderr, file=sys.stderr)
            print("FAIL: scaffold did not self-validate; this is a scaffolder bug", file=sys.stderr)
            return 1
    print(f"PASS: pre-valid audit bundle written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
