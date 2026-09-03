#!/usr/bin/env python3
"""Migrate Scruffy decisions into the supplied durable registry version."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from audit_contract import load_contract


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

    prior_rows = prior.get("decisions", [])
    if not isinstance(prior_rows, list):
        raise SystemExit("FAIL: prior decisions must contain a decisions array")
    prior_by_id = {
        row.get("item_id") or row.get("finding_id"): row
        for row in prior_rows
        if isinstance(row, dict) and (row.get("item_id") or row.get("finding_id"))
    }
    if prior_registry is not None:
        trusted_ids = {item.get("id") for item in prior_registry.get("items", []) if isinstance(item, dict)}
        unknown = sorted(set(prior_by_id) - trusted_ids)
        if unknown:
            raise SystemExit(f"FAIL: prior decisions contain IDs absent from the trusted prior registry: {unknown}")
        prior_target = prior.get("audit", {}).get("target") if isinstance(prior.get("audit"), dict) else prior.get("target")
        if prior_target and prior_target != prior_registry.get("target"):
            raise SystemExit("FAIL: prior decisions target does not match the trusted prior registry")
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
        rows.append(row)

    result = {
        "schema_version": registry["schema_version"],
        "audit_id": registry["audit_id"],
        "revision_id": registry["revision_id"],
        "baseline_revision_id": registry.get("baseline_revision_id"),
        "decisions": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"PASS: migrated {len(prior_by_id)} prior records into {len(rows)} registry decisions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
