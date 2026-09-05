#!/usr/bin/env python3
"""Render and validate Scruffy's run, context, and editorial contracts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "schema" / "audit-contract.json"
REFERENCE = ROOT / "references" / "audit-contract.md"
README = ROOT / "README.md"
README_START = "<!-- scruffy-modes:start -->"
README_END = "<!-- scruffy-modes:end -->"


def load_contract(path: Path = MANIFEST) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != "1.0":
        raise ValueError("audit-contract schema_version must be 1.0")
    if data.get("current_registry_schema") != "2.1":
        raise ValueError("current registry schema must be 2.1")
    modes = data.get("run", {}).get("modes")
    if not isinstance(modes, list) or len(modes) != 4:
        raise ValueError("audit contract must define four run modes")
    required_mode_fields = {
        "key", "label", "repository_writes_allowed", "live_demonstration_allowed", "description",
    }
    if any(not isinstance(row, dict) or required_mode_fields - set(row) for row in modes):
        raise ValueError("each run mode must define the complete execution contract")
    for row in modes:
        for field in ("repository_writes_allowed", "live_demonstration_allowed"):
            if type(row[field]) is not bool:
                raise ValueError(f"run mode {row['key']} {field} must be a boolean")
    mode_keys = [row.get("key") for row in modes]
    if len(mode_keys) != len(set(mode_keys)) or any(not isinstance(value, str) for value in mode_keys):
        raise ValueError("run-mode keys must be unique strings")
    run = data["run"]
    for field in ("mode_selection_basis", "blind_statuses", "authority_states", "authority_basis_types"):
        values = run.get(field)
        if not isinstance(values, list) or not values or len(values) != len(set(values)) or any(not isinstance(value, str) for value in values):
            raise ValueError(f"run.{field} must be a non-empty unique string array")
    questions = data.get("context", {}).get("product_frame_questions")
    capabilities = data.get("context", {}).get("capabilities")
    if not isinstance(questions, list) or len(questions) != 6:
        raise ValueError("audit context must define six product-frame questions")
    if not isinstance(capabilities, list) or len(capabilities) != 9:
        raise ValueError("audit context must define nine capabilities")
    capability_keys = [row.get("key") for row in capabilities if isinstance(row, dict)]
    if len(capability_keys) != 9 or len(capability_keys) != len(set(capability_keys)):
        raise ValueError("audit context repeats a capability key")
    context = data["context"]
    if context.get("schema_version") != "1.2":
        raise ValueError("current context schema must be 1.2")
    legacy_context_schemas = context.get("legacy_schema_versions")
    if (
        not isinstance(legacy_context_schemas, list)
        or not legacy_context_schemas
        or len(legacy_context_schemas) != len(set(legacy_context_schemas))
        or any(not isinstance(value, str) for value in legacy_context_schemas)
    ):
        raise ValueError("context.legacy_schema_versions must be a non-empty unique string array")
    for field in (
        "product_frame_bases", "task_statuses", "scruffy_applicability_statuses", "capability_statuses", "score_values",
        "evidence_kinds", "evidence_verification", "lane_dispositions",
        "assumption_statuses", "assumption_confidence", "referral_review_statuses",
        "ledger_revision_dispositions", "specialist_review_verification_states",
    ):
        values = context.get(field)
        if not isinstance(values, list) or not values or len(values) != len(set(map(str, values))):
            raise ValueError(f"context.{field} must be a non-empty unique array")
    if "analysis_receipt" not in context["evidence_kinds"]:
        raise ValueError("audit context must define analysis_receipt evidence")
    if "specialist_review" not in context["evidence_kinds"]:
        raise ValueError("audit context must define specialist_review evidence")
    if context["scruffy_applicability_statuses"] != ["applicable", "not_applicable", "uncertain"]:
        raise ValueError("context.scruffy_applicability_statuses must define applicable, not_applicable, and uncertain")
    if context["ledger_revision_dispositions"] != ["new", "carried", "updated"]:
        raise ValueError("context.ledger_revision_dispositions must define new, carried, and updated")
    if context["specialist_review_verification_states"] != ["verified", "not_verified"]:
        raise ValueError("context.specialist_review_verification_states must define verified and not_verified")
    annotation_statuses = context.get("visual_annotation_statuses")
    if annotation_statuses != ["provided", "not_needed"]:
        raise ValueError("context.visual_annotation_statuses must define provided and not_needed")
    max_regions = context.get("visual_annotation_max_regions")
    if not isinstance(max_regions, int) or isinstance(max_regions, bool) or max_regions < 1:
        raise ValueError("context.visual_annotation_max_regions must be a positive integer")
    supported_context_schemas = {context["schema_version"], *legacy_context_schemas}
    features = context.get("feature_schema_versions")
    if not isinstance(features, dict) or set(features) != {"visual_evidence", "routing"}:
        raise ValueError("context.feature_schema_versions must define visual_evidence and routing")
    for feature, versions in features.items():
        if (
            not isinstance(versions, list)
            or not versions
            or len(versions) != len(set(versions))
            or any(value not in supported_context_schemas for value in versions)
        ):
            raise ValueError(f"context.feature_schema_versions.{feature} must name supported unique versions")
    if features["visual_evidence"] != ["1.1", "1.2"]:
        raise ValueError("visual evidence must remain enforced for context schemas 1.1 and 1.2")
    if features["routing"] != ["1.2"]:
        raise ValueError("routing must begin with context schema 1.2")
    lanes = context.get("review_lanes")
    required_lane_fields = {"key", "label", "owner", "description"}
    if not isinstance(lanes, list) or not lanes:
        raise ValueError("context.review_lanes must be a non-empty array")
    if any(not isinstance(row, dict) or required_lane_fields - set(row) for row in lanes):
        raise ValueError("each review lane must define key, label, owner, and description")
    lane_keys = [row.get("key") for row in lanes]
    if len(lane_keys) != len(set(lane_keys)) or any(not isinstance(value, str) or not value for value in lane_keys):
        raise ValueError("context.review_lanes must use unique non-empty string keys")
    if any(row.get("owner") not in {"scruffy", "specialist"} for row in lanes):
        raise ValueError("context.review_lanes owner must be scruffy or specialist")
    if lanes[0].get("key") != "core_interface" or lanes[0].get("owner") != "scruffy":
        raise ValueError("core_interface must be the first Scruffy-owned review lane")
    required_specialists = {
        "api_contract", "security", "privacy", "reliability", "legal_compliance", "physical_testing",
    }
    actual_specialists = {row["key"] for row in lanes if row["owner"] == "specialist"}
    if actual_specialists != required_specialists:
        raise ValueError("review lanes must define the six canonical specialist referrals")
    observation = data.get("observation_manifest", {})
    if not isinstance(observation, dict):
        raise ValueError("observation_manifest must be an object")
    if observation.get("schema_version") != "1.0":
        raise ValueError("observation_manifest schema_version must be 1.0")
    supported_manifests = observation.get("supported_versions")
    if supported_manifests != ["1.0"]:
        raise ValueError("observation_manifest.supported_versions must list exactly the readable versions")
    if observation.get("digest_algorithm") != "sha256":
        raise ValueError("observation_manifest.digest_algorithm must be sha256")
    if observation.get("target_fingerprint_scopes")[:1] != ["commit_and_worktree_bytes"]:
        raise ValueError("observation_manifest.target_fingerprint_scopes must lead with the byte-level scope")
    if {"target", "target_after", "target_stable", "target_binding"} - set(observation.get("required_fields", [])):
        raise ValueError("observation_manifest.required_fields must bind identity before and after execution")
    if observation.get("result_provenance") != ["collected", "imported", "not_collected"]:
        raise ValueError("observation_manifest.result_provenance must separate collected, imported, and not_collected")
    for field in ("input_roles", "target_identity_kinds", "target_fingerprint_scopes", "target_fingerprint_exclusions", "required_fields"):
        values = observation.get(field)
        if not isinstance(values, list) or not values or len(values) != len(set(values)) or any(not isinstance(value, str) or not value for value in values):
            raise ValueError(f"observation_manifest.{field} must be a non-empty unique string array")
    editorial = data.get("editorial_review", {})
    if editorial.get("authorship_assessment") != "not_performed":
        raise ValueError("editorial contract must prohibit authorship assessment")
    if len(editorial.get("sentence_manual_checks", [])) != 4:
        raise ValueError("editorial contract must define four sentence manual checks")
    if len(editorial.get("editorial_manual_checks", [])) != 4:
        raise ValueError("editorial contract must define four broader editorial checks")
    for field in (
        "review_types", "sample_adequacy", "analysis_language_scopes", "language_review_bases",
        "sentence_signal_families", "manual_check_results",
        "sentence_manual_checks", "editorial_manual_checks",
    ):
        values = editorial.get(field)
        if not isinstance(values, list) or not values or len(values) != len(set(values)):
            raise ValueError(f"editorial_review.{field} must be a non-empty unique array")
    return data


def mode_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["key"]: row for row in data["run"]["modes"]}


def render_reference(data: dict[str, Any]) -> str:
    lines = [
        "# Audit execution contract",
        "",
        "> Generated from `schema/audit-contract.json` by `scripts/audit_contract.py`. Do not edit this file directly.",
        "",
        "This contract turns mode selection, source-write authority, capability coverage, evidence receipts, and editorial review into data that validators can enforce.",
        "",
        "## Run modes",
        "",
        "| Mode | Repository writes | Live demonstration | Contract |",
        "|---|---|---|---|",
    ]
    for row in data["run"]["modes"]:
        writes = "Allowed with explicit authority" if row["repository_writes_allowed"] else "Forbidden"
        demo = "Allowed" if row["live_demonstration_allowed"] else "Not part of the mode"
        lines.append(f"| **{row['label']}** (`{row['key']}`) | {writes} | {demo} | {row['description']} |")
    lines.extend(
        [
            "",
            "Every schema-2.1 registry records requested and effective mode, whether selection was explicit or inferred, the authority state, an `explicit_request` or `not_granted` authority basis type, the human-readable authority basis, whether repository writes or a live demonstration occurred, affected write paths, and blind status. AUDIT and DEMONSTRATE-FIX cannot carry repository-write authority and fail validation if repository writes are reported. REDESIGN and DESIGN fail validation without an explicit-request authority receipt. An unauthorized design/redesign request may only downgrade to AUDIT.",
            "",
            "## Capability contract",
            "",
            "Every substantial audit records exactly these capabilities. Missing capability is not a finding; use `not_run`, `unavailable`, `not_needed`, or `not_authorized` and explain the scope.",
            "",
        ]
    )
    for row in data["context"]["capabilities"]:
        lines.append(f"- `{row['key']}` — {row['label']}")
    lines.extend(
        [
            "",
            "## Evidence receipts",
            "",
            "Schema-2.1 context stores evidence as typed receipts with an immutable ID, kind, locator, description, and verification state. Registry items reference those IDs through `evidence_refs`. A local screenshot or source locator must exist when the validator can resolve it. URLs must use HTTP or HTTPS. A non-empty prose claim is not an evidence receipt. A `specialist_review` receipt additionally records its discipline, reviewer or authority, scope, result, date or artifact version, and a verified/not-verified state.",
            "",
            "New audits emit context schema 1.2. Every locally captured screenshot has one claim-specific visual context for each registry item that cites it, or one unlinked context when no item cites it. Each context records the operated state, a precise `look_at` instruction, the connection to the claim, and an annotation decision. `provided` annotations contain one to four percentage-based rectangles with visible labels. `not_needed` requires a reason explaining why the whole frame is the evidence or why an overlay would misrepresent a nonvisual claim. Generic asset descriptions do not satisfy this contract.",
            "",
            "## Review routing",
            "",
            "Context schema 1.2 records `scruffy_applicability` and every canonical review lane exactly once as `selected`, `rejected`, `not_applicable`, or `referred`. `core_interface` is selected when Scruffy is applicable or applicability is uncertain. A non-interface stop-and-refer records `scruffy_applicability: not_applicable`, marks `core_interface` not applicable, selects no Scruffy-owned lane, and emits no interface findings or work orders. Specialist-owned lanes cannot be selected as if Scruffy performed them: they are rejected with a reason, marked not applicable, or linked to a typed referral. A referral records its specialist lane, review status, evidence references, and the claim Scruffy will not make without that specialist evidence. `complete` requires at least one verified, lane-matched `specialist_review` receipt; `not_run` forbids specialist artifacts.",
            "",
            "The routing ledger is separate from the eight finding categories. Lane keys never appear in `items[].category`, and specialist results never leak into Scruffy's registry as improvised ninth categories.",
            "",
            "Routing, assumptions, and referrals are durable ledgers. Each row carries a stable ID, first-seen and last-observed revisions, and an explicit `new`, `carried`, or `updated` disposition. A context 1.2 revision records `baseline_revision_id` and must be validated with its baseline context; prior rows cannot disappear or be reissued under new IDs.",
            "",
            "Assumptions are durable records with an ID, basis, confidence, risk if wrong, evidence needed, affected decision, status, and evidence references. Open assumptions may lack supporting evidence; supported or refuted assumptions may not.",
            "",
            "Canonical lanes:",
            "",
        ]
    )
    for row in data["context"]["review_lanes"]:
        lines.append(f"- `{row['key']}` — {row['label']} ({row['owner']}): {row['description']}")
    lines.extend(
        [
            "",
            "## Observation manifest",
            "",
            "A tool that collects evidence by running something may attach one optional `observation_manifest` to the receipt it writes. The manifest is versioned and additive: a receipt without one stays valid, and a receipt whose manifest names an unreadable version is refused rather than downgraded.",
            "",
            "Readable manifest versions: "
            + ", ".join(f"`{value}`" for value in data["observation_manifest"]["supported_versions"])
            + f". Digests use `{data['observation_manifest']['digest_algorithm']}` over canonical JSON.",
            "",
            "A manifest records "
            + ", ".join(f"`{value}`" for value in data["observation_manifest"]["required_fields"])
            + ". `run_id` is unique per invocation, `inputs` carries a digest per "
            + "/".join(f"`{value}`" for value in data["observation_manifest"]["input_roles"])
            + " input, `checks_digest` binds the receipt to the exact promised checks it answers, and `result_counts` separates "
            + ", ".join(f"`{value}`" for value in data["observation_manifest"]["result_provenance"])
            + " results so imported out-of-band results are never presented as independently collected.",
            "",
            "`target` and `target_after` identify where the observation happened, captured before and after execution, using "
            + " or ".join(f"`{value}`" for value in data["observation_manifest"]["target_identity_kinds"])
            + " identity. `target_stable` is true only when both sides carry the same byte-level fingerprint, so a check that edits its own target cannot have an earlier pass attributed to the tree that replaced it. A `git_commit` target fingerprints the commit plus the actual bytes of every in-scope modified and untracked file; commit plus status output alone is not a content fingerprint and is never recorded as one. Fingerprint scope is one of "
            + ", ".join(f"`{value}`" for value in data["observation_manifest"]["target_fingerprint_scopes"])
            + ", and only `commit_and_worktree_bytes` is a content claim; the others record that no fingerprint was computed. Fingerprints exclude: "
            + "; ".join(data["observation_manifest"]["target_fingerprint_exclusions"])
            + ".",
            "",
            "Manifests record digests and fingerprints, never filesystem paths, captured process output, or command text. Author-written check summaries are copied through as-is and are not scrubbed.",
            "",
            "Validation refuses an unknown manifest version, a malformed or missing required field, a stored input digest that does not reproduce from the supplied document, a checks digest that no longer matches the registry the receipt claims to answer, and a target that does not match the environment a consumer is checking against. Target freshness is only checked when a consumer supplies a freshly read target: document-only validation cannot know whether the tree still matches, so it never implies that it does. An item cannot be `verified` in a run whose target changed. Manifests are evidence about collection conditions; they do not raise a result's authority.",
            "",
            "## Editorial review",
            "",
            "Every active `copy` finding carries an `editorial_review` receipt. Editorial review includes content strategy, terminology, information sequence, microcopy, claims and provenance, recovery language, voice, and sentence construction.",
            "",
            "Sentence-pattern findings require an adequate or limited reader-facing sample, a recorded language scope, an analyzer evidence receipt, all four sentence manual checks, a demonstrated consequence, a tested counterexample, and `authorship_assessment: not_performed`. English findings use `verified_english_analyzer`; non-English findings require `language_competent_human` and retain the analyzer's abstention receipt. Unknown language cannot produce a sentence-pattern finding. Other editorial findings use `not_applicable` for sentence sampling and language analysis but must complete the applicable editorial checks and prove their consequence.",
            "",
            "Allowed independent sentence-signal families are: "
            + ", ".join(f"`{value}`" for value in data["editorial_review"]["sentence_signal_families"])
            + ". A receipt cannot invent new family names to satisfy the two-family threshold.",
            "",
            "## Backward compatibility",
            "",
            "Schema 2.0 and context schemas 1.0 and 1.1 remain readable so published audit history survives. New audits emit registry schema 2.1 with context schema 1.2. Visual-evidence checks remain active for both context 1.1 and 1.2; routing checks apply only to context 1.2. A new revision may reconcile an older baseline without rewriting it, but it must supply the baseline context to the validator; ledgers introduced after a legacy context are explicitly marked `new`.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_readme(data: dict[str, Any]) -> str:
    lines = [
        README_START,
        "## Modes",
        "",
        "| Mode | Use it for | Repository authority |",
        "|---|---|---|",
    ]
    for row in data["run"]["modes"]:
        authority = "Explicit source-write authority required" if row["repository_writes_allowed"] else "Repository writes forbidden"
        lines.append(f"| **{row['label']}** | {row['description']} | {authority} |")
    lines.extend(
        [
            "",
            "New schema-2.1 reports record requested mode, effective mode, selection basis, explicit-request write authority, performed mutations, live demonstrations, and blind status. Validation fails closed when those facts conflict.",
            README_END,
        ]
    )
    return "\n".join(lines)


def replace_readme_block(text: str, rendered: str) -> str:
    generated = re.compile(rf"{re.escape(README_START)}.*?{re.escape(README_END)}", re.S)
    if generated.search(text):
        return generated.sub(lambda match: rendered, text)
    existing = re.search(r"(?ms)^## Modes\n.*?(?=^## Install\n)", text)
    if not existing:
        raise ValueError("README modes section or generated markers were not found")
    return text[: existing.start()] + rendered + "\n\n" + text[existing.end() :]


def expected_readme(data: dict[str, Any]) -> str:
    return replace_readme_block(README.read_text(encoding="utf-8"), render_readme(data))


def check(data: dict[str, Any]) -> list[str]:
    expected = render_reference(data)
    failures: list[str] = []
    if not REFERENCE.is_file() or REFERENCE.read_text(encoding="utf-8") != expected:
        failures.append("references/audit-contract.md is stale or missing")
    if README.read_text(encoding="utf-8") != expected_readme(data):
        failures.append("README run-mode projection is stale")
    return failures


def write(data: dict[str, Any]) -> None:
    REFERENCE.write_text(render_reference(data), encoding="utf-8")
    README.write_text(expected_readme(data), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true")
    action.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        data = load_contract()
        if args.write:
            write(data)
            print("PASS: audit-contract reference updated")
            return 0
        failures = check(data)
        if failures:
            for failure in failures:
                print(f"FAIL: {failure}", file=sys.stderr)
            return 1
        print("PASS: audit execution contract and reference are synchronized")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
