#!/usr/bin/env python3
"""Migrate Scruffy decisions into the supplied durable registry version."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from audit_contract import load_contract
from validate_audit import validate_registry, validate_decisions, validate_baseline, validate_verification_receipt


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"FAIL: {path} must contain a JSON object")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prior_decisions", type=Path)
    parser.add_argument("registry", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--prior-registry",
        type=Path,
        help="Required for legacy decisions that do not carry immutable identity keys.",
    )
    parser.add_argument(
        "--verification",
        type=Path,
        help="verification.json from verify_fixes.py; records what proved each approved fix.",
    )
    args = parser.parse_args()

    prior = load(args.prior_decisions)
    registry = load(args.registry)
    contract = load_contract()
    supported_registry_versions = {
        contract["current_registry_schema"],
        *contract["legacy_registry_schemas"],
    }
    if registry.get("schema_version") not in supported_registry_versions:
        raise SystemExit(f"FAIL: registry must use one of {sorted(supported_registry_versions)}")

    validate_registry(registry, "registry")
    prior_registry: dict[str, Any] | None = None
    if args.prior_registry:
        prior_registry = load(args.prior_registry)
        if prior_registry.get("schema_version") not in supported_registry_versions:
            raise SystemExit(f"FAIL: prior registry must use one of {sorted(supported_registry_versions)}")
        if prior_registry.get("audit_id") != registry.get("audit_id"):
            raise SystemExit("FAIL: prior and current registries have different audit_id values")
        if registry.get("baseline_revision_id") != prior_registry.get("revision_id"):
            raise SystemExit("FAIL: current baseline_revision_id does not match the prior registry revision_id")

    if prior.get("schema_version") not in supported_registry_versions and prior_registry is None:
        raise SystemExit(
            "FAIL: legacy decisions lack immutable identity keys; provide --prior-registry so IDs can be bound to a trusted baseline"
        )

    modern = prior.get("schema_version") in supported_registry_versions
    same_revision = prior.get("revision_id") == registry.get("revision_id")
    if modern:
        if prior.get("audit_id") != registry.get("audit_id"):
            raise SystemExit("FAIL: prior decisions audit_id does not match registry")
        expected_revision = registry.get("revision_id") if same_revision else registry.get("baseline_revision_id")
        if not expected_revision or prior.get("revision_id") != expected_revision:
            raise SystemExit("FAIL: prior decisions revision does not match current or baseline revision")
        if not same_revision and prior_registry is None:
            raise SystemExit("FAIL: cross-revision decisions require --prior-registry to verify immutable identity")
        validate_decisions(prior, registry if same_revision else prior_registry)
    if prior_registry is not None:
        validate_registry(prior_registry, "prior registry")
        validate_baseline(registry, prior_registry)

    prior_rows = prior.get("decisions", [])
    if not isinstance(prior_rows, list):
        raise SystemExit("FAIL: prior decisions must contain a decisions array")
    prior_by_id = {}
    for row in prior_rows:
        if not isinstance(row, dict):
            raise SystemExit("FAIL: prior decision rows must be objects")
        item_id = row.get("item_id") or row.get("finding_id")
        if not isinstance(item_id, str) or not item_id or item_id in prior_by_id:
            raise SystemExit("FAIL: prior decisions contain missing or duplicate item IDs")
        if row.get("decision") not in {"approve", "defer", "reject", "pending"}:
            raise SystemExit("FAIL: prior decision is invalid")
        prior_by_id[item_id] = row
    if prior_registry is not None:
        trusted_ids = {item.get("id") for item in prior_registry.get("items", []) if isinstance(item, dict)}
        unknown = sorted(set(prior_by_id) - trusted_ids)
        if unknown:
            raise SystemExit(f"FAIL: prior decisions contain IDs absent from the trusted prior registry: {unknown}")
        prior_target = prior.get("audit", {}).get("target") if isinstance(prior.get("audit"), dict) else prior.get("target")
        if prior_target and prior_target != prior_registry.get("target"):
            raise SystemExit("FAIL: prior decisions target does not match the trusted prior registry")
    # A decision history that records the choice but not the proof loses the
    # only fact that distinguishes an approved fix from a shipped one.
    verification: dict[str, Any] = {}
    verification_by_id: dict[str, dict[str, Any]] = {}
    if args.verification:
        verification = load(args.verification)
        verification_by_id = validate_verification_receipt(
            verification, prior_registry or registry, prior if modern else None
        )

    def verification_ref(item_id: str) -> dict[str, Any] | None:
        row = verification_by_id.get(item_id)
        if row is None:
            return None
        return {
            "source": str(args.verification),
            "verified_at": verification.get("verified_at"),
            "revision_id": verification.get("revision_id"),
            "result": row.get("result"),
            "executed_commands": verification.get("executed_commands"),
        }

    migrated_at = datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, Any]] = []
    for item in registry.get("items", []):
        if item.get("kind") not in {"finding", "enhancement"}:
            continue
        item_id = item["id"]
        old = prior_by_id.get(item_id)
        if old:
            history = list(old.get("history", [])) if isinstance(old.get("history", []), list) else []
            history.append(
                {
                    "decision": old.get("decision", "pending"),
                    "note": old.get("note", ""),
                    "updated_at": old.get("updated_at"),
                    "migrated_at": migrated_at,
                    "migrated_from_schema": prior.get("schema_version", "unknown"),
                }
            )
            row = {
                "item_id": item_id,
                "decision": old.get("decision", "pending"),
                "note": old.get("note", ""),
                "updated_at": old.get("updated_at"),
                "decision_source": "migrated",
                "destination_id": item.get("destination_id"),
                "history": history,
            }
        else:
            row = {
                "item_id": item_id,
                "decision": "pending",
                "note": "",
                "updated_at": None,
                "decision_source": "current",
                "destination_id": item.get("destination_id"),
                "history": [],
            }
        if old and isinstance(old.get("verification_ref"), dict):
            row["verification_ref"] = old["verification_ref"]
        reference = verification_ref(item_id)
        if reference is not None:
            row["verification_ref"] = reference
        rows.append(row)

    result = {
        "schema_version": registry["schema_version"],
        "audit_id": registry["audit_id"],
        "revision_id": registry["revision_id"],
        "baseline_revision_id": registry.get("baseline_revision_id"),
        "decisions": rows,
    }
    validate_decisions(result, registry)
    protected = [args.prior_decisions, args.registry, args.prior_registry, args.verification]
    if any(path and path.resolve() == args.output.resolve() for path in protected):
        raise SystemExit("FAIL: output must not overwrite a migration input")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"PASS: migrated {len(prior_by_id)} prior records into {len(rows)} registry decisions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
