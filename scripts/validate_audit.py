#!/usr/bin/env python3
"""Validate durable Scruffy registries, decisions, and HTML dashboards."""

from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from audit_contract import load_contract, mode_map
from report_contract import evidence_by_id, humanize_text, item_label_map
from taxonomy_contract import canonical_category_keys, canonical_facet_keys, load_taxonomy


AUDIT_CONTRACT = load_contract()
TAXONOMY = load_taxonomy()
CURRENT_SCHEMA_VERSION = AUDIT_CONTRACT["current_registry_schema"]
LEGACY_SCHEMA_VERSIONS = set(AUDIT_CONTRACT["legacy_registry_schemas"])
SUPPORTED_SCHEMA_VERSIONS = {CURRENT_SCHEMA_VERSION, *LEGACY_SCHEMA_VERSIONS}
RUN_MODES = mode_map(AUDIT_CONTRACT)
CANONICAL_CATEGORIES = set(canonical_category_keys(TAXONOMY))
CANONICAL_FACETS = set(canonical_facet_keys(TAXONOMY))
CATEGORY_FACETS = {row["key"]: set(row["applicable_facets"]) for row in TAXONOMY["categories"]}
LEGACY_CATEGORY_ALIASES = TAXONOMY["legacy_category_aliases"]
CONTEXT_CONTRACT = AUDIT_CONTRACT["context"]
CURRENT_CONTEXT_SCHEMA = CONTEXT_CONTRACT["schema_version"]
LEGACY_CONTEXT_SCHEMAS = set(CONTEXT_CONTRACT.get("legacy_schema_versions", []))
SUPPORTED_CONTEXT_SCHEMAS = {CURRENT_CONTEXT_SCHEMA, *LEGACY_CONTEXT_SCHEMAS}
CONTEXT_FEATURE_SCHEMAS = {
    feature: set(versions)
    for feature, versions in CONTEXT_CONTRACT["feature_schema_versions"].items()
}
VISUAL_CONTEXT_SCHEMAS = CONTEXT_FEATURE_SCHEMAS["visual_evidence"]
ROUTING_CONTEXT_SCHEMAS = CONTEXT_FEATURE_SCHEMAS["routing"]
REVIEW_LANES = {row["key"]: row for row in CONTEXT_CONTRACT["review_lanes"]}
SPECIALIST_LANES = {key for key, row in REVIEW_LANES.items() if row["owner"] == "specialist"}
VISUAL_ANNOTATION_STATUSES = set(CONTEXT_CONTRACT["visual_annotation_statuses"])
VISUAL_ANNOTATION_MAX_REGIONS = CONTEXT_CONTRACT["visual_annotation_max_regions"]
EDITORIAL_CONTRACT = AUDIT_CONTRACT["editorial_review"]
KINDS = {"finding", "enhancement", "strength"}
STATUSES = {"open", "fixed", "cleared", "needs-verification", "merged", "superseded"}
DISPOSITIONS = {"new", "carried", "reopened", "fixed", "cleared", "merged", "superseded"}
DECISIONS = {"pending", "approve", "defer", "reject"}
CONFIDENCE = {"high", "moderate", "low", "unknown"}
FINDING_SEVERITIES = {"critical", "high", "medium", "low"}
NON_FINDING_SEVERITIES = {"high", "medium", "low", "none"}
# Preserve legacy public IDs such as ENH-1; continuity outranks cosmetic padding.
ITEM_ID = re.compile(r"^[A-Z][A-Z0-9]{1,5}-\d{1,4}$")
IDENTITY_KEY = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
EVIDENCE_ID = re.compile(r"^EV-[A-Z0-9][A-Z0-9-]{0,31}$")
ROUTING_ID = re.compile(r"^ROUTE-[A-Z0-9][A-Z0-9-]{0,31}$")
ASSUMPTION_ID = re.compile(r"^ASM-[A-Z0-9][A-Z0-9-]{0,31}$")
REFERRAL_ID = re.compile(r"^REF-[A-Z0-9][A-Z0-9-]{0,31}$")
ACTIVE_FINDING_STATUSES = {"open", "needs-verification"}
RUNTIME_EVIDENCE_KINDS = {"runtime_trace", "measurement"}
RENDERED_EVIDENCE_KINDS = {"screenshot", "task_observation"}
ACCESSIBILITY_CRITERION = re.compile(
    r"\b(?:WCAG|SC)\s*\d+\.\d+\.\d+\b|\bEN\s*301\s*549\b|\bSection\s*508\b",
    re.IGNORECASE,
)
REQUIRED_ITEM_FIELDS = {
    "id",
    "identity_key",
    "kind",
    "title",
    "category",
    "severity",
    "confidence",
    "status",
    "revision_disposition",
    "first_seen_revision",
    "last_observed_revision",
    "observation",
    "user_impact",
    "evidence",
    "cause",
    "recommendation",
    "acceptance_checks",
    "depends_on",
    "disposition_reason",
    "destination_id",
}
# `plain` joined schema 2.1 on 2026-08-17. A registry whose every reader-facing
# field is correct can still be unreadable, because correctness and legibility
# are different properties and only one of them was ever checked.
CURRENT_ITEM_FIELDS = {"facets", "evidence_refs", "editorial_review", "plain"}
REQUIRED_RUN_FIELDS = {
    "requested_mode",
    "effective_mode",
    "mode_selection_basis",
    "repository_write_authority",
    "authority_basis_type",
    "authority_basis",
    "repository_writes_performed",
    "repository_write_paths",
    "live_demonstration_performed",
    "blind_status",
    "blind_artifact_refs",
}
REQUIRED_DASHBOARD_SECTIONS = {
    "outcome",
    "product-frame",
    "task-ledger",
    "capability-ledger",
    "score",
    "findings",
    "enhancements",
    "strengths",
    "resolved",
    "reconciliation",
    "work-orders",
    "checks-not-run",
}
ROUTING_REPORT_SECTIONS = {"routing", "assumptions", "referrals"}
LEDGER_REVISION_FIELDS = {
    "first_seen_revision",
    "last_observed_revision",
    "revision_disposition",
    "disposition_reason",
}


def fail(message: str) -> None:
    raise ValueError(message)


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"{path}: unreadable JSON: {error}")
    if not isinstance(data, dict):
        fail(f"{path}: root must be an object")
    return data


def require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        fail(f"{label} must be a non-empty string")
    return value


def require_specific_visual_text(value: Any, label: str) -> str:
    text = require_text(value, label)
    words = re.findall(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)?", text)
    if len(words) < 5:
        fail(f"{label} must identify a specific visible state or claim connection")
    return text


def require_bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        fail(f"{label} must be a boolean")
    return value


def require_unique_text_list(value: Any, label: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(row, str) or not row.strip() for row in value):
        fail(f"{label} must be an array of non-empty strings")
    if len(value) != len(set(value)):
        fail(f"{label} must not contain duplicates")
    if not allow_empty and not value:
        fail(f"{label} cannot be empty")
    return value


def validate_evidence_id(value: Any, label: str) -> str:
    evidence_id = require_text(value, label)
    if not EVIDENCE_ID.fullmatch(evidence_id):
        fail(f"{label} must match {EVIDENCE_ID.pattern}")
    return evidence_id


def validate_ledger_revision(
    row: dict[str, Any],
    label: str,
    *,
    revision_id: str,
    baseline_revision_id: str | None,
) -> None:
    first_seen = require_text(row.get("first_seen_revision"), f"{label}.first_seen_revision")
    last_observed = require_text(row.get("last_observed_revision"), f"{label}.last_observed_revision")
    if last_observed != revision_id:
        fail(f"{label}.last_observed_revision must equal context.revision_id")
    disposition = row.get("revision_disposition")
    if disposition not in CONTEXT_CONTRACT["ledger_revision_dispositions"]:
        fail(f"{label}.revision_disposition is invalid")
    require_text(row.get("disposition_reason"), f"{label}.disposition_reason")
    if baseline_revision_id is None:
        if disposition != "new":
            fail(f"{label}.revision_disposition must be new in a baseline context")
        if first_seen != revision_id:
            fail(f"{label}.first_seen_revision must equal context.revision_id for a new ledger row")
    elif disposition == "new" and first_seen != revision_id:
        fail(f"{label}.first_seen_revision must equal context.revision_id for a new ledger row")


def validate_run(registry: dict[str, Any], source: str) -> dict[str, Any]:
    run = registry.get("run")
    if not isinstance(run, dict):
        fail(f"{source}.run must be an object for schema {CURRENT_SCHEMA_VERSION}")
    missing = sorted(REQUIRED_RUN_FIELDS - set(run))
    if missing:
        fail(f"{source}.run missing fields: {missing}")

    requested = run.get("requested_mode")
    effective = run.get("effective_mode")
    if requested not in RUN_MODES:
        fail(f"{source}.run.requested_mode is invalid")
    if effective not in RUN_MODES:
        fail(f"{source}.run.effective_mode is invalid")
    if run.get("mode_selection_basis") not in AUDIT_CONTRACT["run"]["mode_selection_basis"]:
        fail(f"{source}.run.mode_selection_basis is invalid")
    authority = run.get("repository_write_authority")
    if authority not in AUDIT_CONTRACT["run"]["authority_states"]:
        fail(f"{source}.run.repository_write_authority is invalid")
    authority_basis_type = run.get("authority_basis_type")
    if authority_basis_type not in AUDIT_CONTRACT["run"]["authority_basis_types"]:
        fail(f"{source}.run.authority_basis_type is invalid")
    require_text(run.get("authority_basis"), f"{source}.run.authority_basis")
    writes = require_bool(run.get("repository_writes_performed"), f"{source}.run.repository_writes_performed")
    paths = require_unique_text_list(run.get("repository_write_paths"), f"{source}.run.repository_write_paths")
    live_demo = require_bool(run.get("live_demonstration_performed"), f"{source}.run.live_demonstration_performed")
    blind_status = run.get("blind_status")
    if blind_status not in AUDIT_CONTRACT["run"]["blind_statuses"]:
        fail(f"{source}.run.blind_status is invalid")
    blind_refs = require_unique_text_list(run.get("blind_artifact_refs"), f"{source}.run.blind_artifact_refs")
    for index, evidence_id in enumerate(blind_refs):
        validate_evidence_id(evidence_id, f"{source}.run.blind_artifact_refs[{index}]")

    mode = RUN_MODES[effective]
    if requested != effective and not (
        requested in {"redesign", "design"}
        and effective == "audit"
        and authority == "not_authorized"
    ):
        fail(f"{source}.run: requested and effective mode conflict without a valid no-authority downgrade")
    if authority == "authorized" and authority_basis_type != "explicit_request":
        fail(f"{source}.run: authorized writes require an explicit_request authority basis")
    if authority == "not_authorized" and authority_basis_type != "not_granted":
        fail(f"{source}.run: not_authorized must use a not_granted authority basis")
    if effective in {"audit", "demonstrate_fix"} and authority != "not_authorized":
        fail(f"{source}.run: mode {effective} cannot carry repository-write authority")
    if writes and not mode["repository_writes_allowed"]:
        fail(f"{source}.run: mode {effective} forbids repository writes")
    if writes and authority != "authorized":
        fail(f"{source}.run: repository writes occurred without authorization")
    if writes != bool(paths):
        fail(f"{source}.run: repository_write_paths must be present exactly when writes occurred")
    if effective in {"redesign", "design"} and authority != "authorized":
        fail(f"{source}.run: mode {effective} requires explicit repository-write authority")
    if live_demo and not mode["live_demonstration_allowed"]:
        fail(f"{source}.run: mode {effective} does not permit a live demonstration")
    if blind_status == "verified" and len(blind_refs) < 3:
        fail(f"{source}.run: verified blindness requires manifest, discovery, and freeze evidence")
    if blind_status == "not_run" and blind_refs:
        fail(f"{source}.run: blind_artifact_refs must be empty when blindness was not run")
    return run


def validate_editorial_review(review: Any, label: str, *, kind: str, status: str) -> set[str]:
    if not isinstance(review, dict):
        fail(f"{label} must be an object for copy findings and enhancements")
    required = {
        "review_type",
        "sample_adequacy",
        "analysis_language_scope",
        "language_review_basis",
        "analyzer_evidence_ref",
        "independent_signal_families",
        "manual_checks",
        "consequence",
        "counterexample_tested",
        "authorship_assessment",
    }
    missing = sorted(required - set(review))
    if missing:
        fail(f"{label} missing fields: {missing}")
    review_type = review.get("review_type")
    if review_type not in EDITORIAL_CONTRACT["review_types"]:
        fail(f"{label}.review_type is invalid")
    adequacy = review.get("sample_adequacy")
    if adequacy not in EDITORIAL_CONTRACT["sample_adequacy"]:
        fail(f"{label}.sample_adequacy is invalid")
    language_scope = review.get("analysis_language_scope")
    if language_scope not in EDITORIAL_CONTRACT["analysis_language_scopes"]:
        fail(f"{label}.analysis_language_scope is invalid")
    language_basis = review.get("language_review_basis")
    if language_basis not in EDITORIAL_CONTRACT["language_review_bases"]:
        fail(f"{label}.language_review_basis is invalid")
    if review.get("authorship_assessment") != EDITORIAL_CONTRACT["authorship_assessment"]:
        fail(f"{label}.authorship_assessment must be not_performed")
    require_text(review.get("consequence"), f"{label}.consequence")
    require_text(review.get("counterexample_tested"), f"{label}.counterexample_tested")
    families = require_unique_text_list(
        review.get("independent_signal_families"),
        f"{label}.independent_signal_families",
    )
    unknown_families = sorted(set(families) - set(EDITORIAL_CONTRACT["sentence_signal_families"]))
    if unknown_families:
        fail(f"{label}.independent_signal_families contains unknown values: {unknown_families}")
    analyzer_ref = review.get("analyzer_evidence_ref")
    evidence_refs: set[str] = set()
    if analyzer_ref is not None:
        evidence_refs.add(validate_evidence_id(analyzer_ref, f"{label}.analyzer_evidence_ref"))

    checks = review.get("manual_checks")
    if not isinstance(checks, list) or not checks:
        fail(f"{label}.manual_checks must be a non-empty array")
    by_code: dict[str, dict[str, Any]] = {}
    allowed_codes = set(EDITORIAL_CONTRACT["sentence_manual_checks"]) | set(EDITORIAL_CONTRACT["editorial_manual_checks"])
    for index, check in enumerate(checks):
        check_label = f"{label}.manual_checks[{index}]"
        if not isinstance(check, dict):
            fail(f"{check_label} must be an object")
        code = check.get("code")
        if code not in allowed_codes:
            fail(f"{check_label}.code is invalid")
        if code in by_code:
            fail(f"{label}.manual_checks repeats {code}")
        result = check.get("result")
        if result not in EDITORIAL_CONTRACT["manual_check_results"]:
            fail(f"{check_label}.result is invalid")
        require_text(check.get("evidence"), f"{check_label}.evidence")
        evidence_ref = check.get("evidence_ref")
        if evidence_ref is None:
            fail(f"{check_label}.evidence_ref must link the manual conclusion to typed evidence")
        evidence_refs.add(validate_evidence_id(evidence_ref, f"{check_label}.evidence_ref"))
        by_code[code] = check

    sentence_review = review_type in {"sentence_pattern", "mixed"}
    if sentence_review:
        if adequacy not in {"adequate", "limited"}:
            fail(f"{label}: sentence-pattern review requires an adequate or limited sample")
        if analyzer_ref is None:
            fail(f"{label}: sentence-pattern review requires an analyzer evidence receipt")
        expected_basis = {
            "en": "verified_english_analyzer",
            "non_en": "language_competent_human",
        }.get(language_scope)
        if expected_basis is None:
            fail(f"{label}: sentence-pattern review requires verified en or non_en language scope")
        if language_basis != expected_basis:
            fail(f"{label}: {language_scope} sentence review requires {expected_basis}")
        if len(families) < 2:
            fail(f"{label}: sentence-pattern review requires two independent signal families")
        missing_sentence_checks = sorted(set(EDITORIAL_CONTRACT["sentence_manual_checks"]) - set(by_code))
        if missing_sentence_checks:
            fail(f"{label}: sentence-pattern review is missing {missing_sentence_checks}")
        incomplete = [
            code
            for code in EDITORIAL_CONTRACT["sentence_manual_checks"]
            if by_code[code]["result"] in {"not_run", "not_applicable"}
        ]
        if incomplete:
            fail(f"{label}: sentence manual checks are incomplete: {incomplete}")
        if review_type == "mixed":
            missing_editorial_checks = sorted(set(EDITORIAL_CONTRACT["editorial_manual_checks"]) - set(by_code))
            if missing_editorial_checks:
                fail(f"{label}: mixed editorial review is missing {missing_editorial_checks}")
            incomplete_editorial = [
                code
                for code in EDITORIAL_CONTRACT["editorial_manual_checks"]
                if by_code[code]["result"] == "not_run"
            ]
            if incomplete_editorial and kind == "finding" and status in {"open", "needs-verification"}:
                fail(f"{label}: active mixed editorial finding has not-run checks: {incomplete_editorial}")
    else:
        if adequacy not in {"not_applicable", "insufficient"}:
            fail(f"{label}: non-sentence editorial review must use not_applicable or insufficient sampling")
        if language_scope != "not_applicable" or language_basis != "not_applicable":
            fail(f"{label}: non-sentence editorial review must use not_applicable language fields")
        if families:
            fail(f"{label}: non-sentence editorial review cannot claim sentence signal families")
        if analyzer_ref is not None:
            fail(f"{label}: non-sentence editorial review cannot attach a sentence analyzer receipt")
        missing_editorial_checks = sorted(set(EDITORIAL_CONTRACT["editorial_manual_checks"]) - set(by_code))
        if missing_editorial_checks:
            fail(f"{label}: editorial review is missing {missing_editorial_checks}")
        incomplete = [code for code in EDITORIAL_CONTRACT["editorial_manual_checks"] if by_code[code]["result"] == "not_run"]
        if incomplete and kind == "finding" and status in {"open", "needs-verification"}:
            fail(f"{label}: active editorial finding has not-run checks: {incomplete}")
    return evidence_refs


def validate_registry(registry: dict[str, Any], source: str = "registry") -> dict[str, dict[str, Any]]:
    schema_version = registry.get("schema_version")
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        fail(f"{source}: schema_version must be one of {sorted(SUPPORTED_SCHEMA_VERSIONS)}")
    if schema_version == CURRENT_SCHEMA_VERSION:
        validate_run(registry, source)
    audit_id = require_text(registry.get("audit_id"), f"{source}.audit_id")
    require_text(registry.get("target"), f"{source}.target")
    revision_id = require_text(registry.get("revision_id"), f"{source}.revision_id")
    baseline_revision = registry.get("baseline_revision_id")
    if baseline_revision is not None and (not isinstance(baseline_revision, str) or not baseline_revision.strip()):
        fail(f"{source}.baseline_revision_id must be null or a non-empty string")

    items = registry.get("items")
    if not isinstance(items, list):
        fail(f"{source}.items must be an array")

    by_id: dict[str, dict[str, Any]] = {}
    by_identity: dict[str, str] = {}
    for index, item in enumerate(items):
        label = f"{source}.items[{index}]"
        if not isinstance(item, dict):
            fail(f"{label} must be an object")
        required_fields = REQUIRED_ITEM_FIELDS | (CURRENT_ITEM_FIELDS if schema_version == CURRENT_SCHEMA_VERSION else set())
        missing = sorted(required_fields - set(item))
        if missing:
            fail(f"{label} missing fields: {missing}")
        item_id = require_text(item["id"], f"{label}.id")
        identity = require_text(item["identity_key"], f"{label}.identity_key")
        if not ITEM_ID.fullmatch(item_id):
            fail(f"{label}.id is invalid: {item_id}")
        if not IDENTITY_KEY.fullmatch(identity):
            fail(f"{label}.identity_key is invalid: {identity}")
        if item_id in by_id:
            fail(f"{source}: duplicate item id {item_id}")
        if identity in by_identity:
            fail(f"{source}: identity_key {identity} reused by {by_identity[identity]} and {item_id}")
        by_id[item_id] = item
        by_identity[identity] = item_id

        kind = item["kind"]
        status = item["status"]
        disposition = item["revision_disposition"]
        if kind not in KINDS:
            fail(f"{label}.kind must be one of {sorted(KINDS)}")
        if status not in STATUSES:
            fail(f"{label}.status must be one of {sorted(STATUSES)}")
        if disposition not in DISPOSITIONS:
            fail(f"{label}.revision_disposition must be one of {sorted(DISPOSITIONS)}")
        if item["confidence"] not in CONFIDENCE:
            fail(f"{label}.confidence must be one of {sorted(CONFIDENCE)}")
        allowed_severity = FINDING_SEVERITIES if kind == "finding" else NON_FINDING_SEVERITIES
        if item["severity"] not in allowed_severity:
            fail(f"{label}.severity is invalid for kind {kind}")
        if kind == "strength" and item["severity"] != "none":
            fail(f"{label}: strengths must use severity none")
        for field in ("title", "category", "first_seen_revision", "last_observed_revision"):
            require_text(item[field], f"{label}.{field}")
        category = item["category"]
        if schema_version == CURRENT_SCHEMA_VERSION:
            if category not in CANONICAL_CATEGORIES:
                legacy_target = LEGACY_CATEGORY_ALIASES.get(category)
                suffix = f"; use canonical key {legacy_target}" if legacy_target else ""
                fail(f"{label}.category is not canonical{suffix}")
            facets = require_unique_text_list(item["facets"], f"{label}.facets")
            unknown_facets = sorted(set(facets) - CANONICAL_FACETS)
            if unknown_facets:
                fail(f"{label}.facets contains unknown values: {unknown_facets}")
            incompatible_facets = sorted(set(facets) - CATEGORY_FACETS[category])
            if incompatible_facets:
                fail(f"{label}.facets are not applicable to {category}: {incompatible_facets}")
            for provenance_field in ("principle_refs", "detector_refs"):
                if provenance_field in item and item[provenance_field] is not None:
                    require_unique_text_list(item[provenance_field], f"{label}.{provenance_field}", allow_empty=True)
            evidence_refs = require_unique_text_list(
                item["evidence_refs"],
                f"{label}.evidence_refs",
                allow_empty=False,
            )
            for evidence_index, evidence_id in enumerate(evidence_refs):
                validate_evidence_id(evidence_id, f"{label}.evidence_refs[{evidence_index}]")
            if category == "copy" and kind in {"finding", "enhancement"}:
                validate_editorial_review(
                    item["editorial_review"],
                    f"{label}.editorial_review",
                    kind=kind,
                    status=status,
                )
            elif item["editorial_review"] is not None:
                fail(f"{label}.editorial_review must be null outside copy findings and enhancements")
        for field in ("evidence", "acceptance_checks", "depends_on"):
            if not isinstance(item[field], list):
                fail(f"{label}.{field} must be an array")
        if not item["evidence"] and kind != "strength":
            fail(f"{label}.evidence cannot be empty")
        if not item["acceptance_checks"] and kind != "strength":
            fail(f"{label}.acceptance_checks cannot be empty")
        if disposition != "new":
            require_text(item["disposition_reason"], f"{label}.disposition_reason")
        destination = item["destination_id"]
        if disposition in {"merged", "superseded"} or status in {"merged", "superseded"}:
            require_text(destination, f"{label}.destination_id")
        elif destination is not None:
            fail(f"{label}.destination_id must be null unless merged or superseded")
        expected_status = {"fixed": "fixed", "cleared": "cleared", "merged": "merged", "superseded": "superseded"}
        if disposition in expected_status and status != expected_status[disposition]:
            fail(f"{label}: disposition {disposition} requires status {expected_status[disposition]}")
        if disposition == "reopened" and status not in {"open", "needs-verification"}:
            fail(f"{label}: reopened requires open or needs-verification status")

    for item_id, item in by_id.items():
        destination = item["destination_id"]
        if destination is not None:
            if destination == item_id:
                fail(f"{source}: {item_id} cannot point to itself")
            if destination not in by_id:
                fail(f"{source}: {item_id} points to missing destination {destination}")
        for dependency in item["depends_on"]:
            if dependency not in by_id:
                fail(f"{source}: {item_id} depends on missing item {dependency}")

    presentation = registry.get("presentation")
    if not isinstance(presentation, dict):
        fail(f"{source}.presentation must be an object")
    expected_lists = {
        "prioritized_finding_ids",
        "prioritized_enhancement_ids",
        "strength_ids",
        "cleared_ids",
    }
    missing_lists = sorted(expected_lists - set(presentation))
    if missing_lists:
        fail(f"{source}.presentation missing lists: {missing_lists}")
    for name in expected_lists:
        values = presentation[name]
        if not isinstance(values, list) or len(values) != len(set(values)):
            fail(f"{source}.presentation.{name} must be a unique array")
        unknown = [item_id for item_id in values if item_id not in by_id]
        if unknown:
            fail(f"{source}.presentation.{name} has unknown IDs: {unknown}")
    if len(presentation["prioritized_finding_ids"]) > 8:
        fail(f"{source}: prioritized findings exceed eight")
    if len(presentation["prioritized_enhancement_ids"]) > 5:
        fail(f"{source}: prioritized enhancements exceed five")
    for item_id in presentation["prioritized_finding_ids"]:
        if by_id[item_id]["kind"] != "finding" or by_id[item_id]["status"] not in {"open", "needs-verification"}:
            fail(f"{source}: prioritized finding {item_id} is not an active finding")
    for item_id in presentation["prioritized_enhancement_ids"]:
        if by_id[item_id]["kind"] != "enhancement" or by_id[item_id]["status"] not in {"open", "needs-verification"}:
            fail(f"{source}: prioritized enhancement {item_id} is not active")
    for item_id in presentation["strength_ids"]:
        if by_id[item_id]["kind"] != "strength":
            fail(f"{source}: strength list contains non-strength {item_id}")
    for item_id in presentation["cleared_ids"]:
        if by_id[item_id]["status"] not in {"fixed", "cleared", "merged", "superseded"}:
            fail(f"{source}: cleared list contains active item {item_id}")

    registry["audit_id"] = audit_id
    registry["revision_id"] = revision_id
    return by_id


def validate_baseline(current: dict[str, Any], baseline: dict[str, Any]) -> None:
    current_items = validate_registry(current, "current")
    baseline_items = validate_registry(baseline, "baseline")
    if current["audit_id"] != baseline["audit_id"]:
        fail("current and baseline audit_id differ")
    if current.get("baseline_revision_id") != baseline["revision_id"]:
        fail("current.baseline_revision_id must equal baseline.revision_id")
    missing = sorted(set(baseline_items) - set(current_items))
    if missing:
        fail(f"current registry silently dropped baseline IDs: {missing}")
    baseline_identity = {item["identity_key"]: item_id for item_id, item in baseline_items.items()}
    for item_id, prior in baseline_items.items():
        now = current_items[item_id]
        if now["identity_key"] != prior["identity_key"]:
            fail(f"{item_id} reused for a new identity: {prior['identity_key']} -> {now['identity_key']}")
        if now["first_seen_revision"] != prior["first_seen_revision"]:
            fail(f"{item_id}.first_seen_revision changed")
        if now["revision_disposition"] == "new":
            fail(f"baseline item {item_id} cannot have disposition new")
        if prior["status"] in {"fixed", "cleared"} and now["status"] in {"open", "needs-verification"} and now["revision_disposition"] != "reopened":
            fail(f"resolved item {item_id} became active without disposition reopened")
    for item_id, item in current_items.items():
        if item_id not in baseline_items and item["identity_key"] in baseline_identity:
            fail(f"new ID {item_id} reuses baseline identity from {baseline_identity[item['identity_key']]}")
        if item_id not in baseline_items and item["revision_disposition"] != "new":
            fail(f"new item {item_id} must have disposition new")


def validate_decisions(decisions: dict[str, Any], registry: dict[str, Any], baseline_decisions: dict[str, Any] | None = None) -> None:
    items = validate_registry(registry, "registry")
    if decisions.get("schema_version") != registry.get("schema_version"):
        fail("decisions.schema_version must match the registry schema_version")
    for field in ("audit_id", "revision_id", "baseline_revision_id"):
        if decisions.get(field) != registry.get(field):
            fail(f"decisions.{field} does not match registry")
    rows = decisions.get("decisions")
    if not isinstance(rows, list):
        fail("decisions.decisions must be an array")
    required_ids = {item_id for item_id, item in items.items() if item["kind"] in {"finding", "enhancement"}}
    by_id: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows):
        label = f"decisions[{index}]"
        if not isinstance(row, dict):
            fail(f"{label} must be an object")
        item_id = row.get("item_id")
        if item_id in by_id:
            fail(f"duplicate decision for {item_id}")
        if item_id not in required_ids:
            fail(f"orphan decision for {item_id}")
        if row.get("decision") not in DECISIONS:
            fail(f"{label}.decision is invalid")
        if not isinstance(row.get("note"), str):
            fail(f"{label}.note must be a string")
        if row.get("updated_at") is not None and not isinstance(row.get("updated_at"), str):
            fail(f"{label}.updated_at must be null or a string")
        if not isinstance(row.get("history"), list):
            fail(f"{label}.history must be an array")
        destination = row.get("destination_id")
        if destination is not None and destination not in items:
            fail(f"{label}.destination_id is unknown")
        by_id[item_id] = row
    missing = sorted(required_ids - set(by_id))
    if missing:
        fail(f"decisions missing item IDs: {missing}")

    if baseline_decisions is not None:
        prior_rows = baseline_decisions.get("decisions")
        if not isinstance(prior_rows, list):
            fail("baseline decisions are invalid")
        prior_by_id = {(row.get("item_id") or row.get("finding_id")): row for row in prior_rows if isinstance(row, dict)}
        for item_id in set(prior_by_id) & set(by_id):
            prior = prior_by_id[item_id]
            now = by_id[item_id]
            if prior.get("decision") != "pending" and now.get("decision_source") == "migrated":
                if now.get("decision") != prior.get("decision"):
                    fail(f"migrated decision changed for {item_id}")


def validate_context(
    context: dict[str, Any],
    registry: dict[str, Any],
    *,
    base_path: Path,
) -> dict[str, dict[str, Any]]:
    if registry.get("schema_version") != CURRENT_SCHEMA_VERSION:
        return {}
    required = {
        "schema_version",
        "audit_id",
        "revision_id",
        "title",
        "outcome",
        "product_frame",
        "tasks",
        "capabilities",
        "scores",
        "work_orders",
        "checks_not_run",
        "evidence_assets",
    }
    context_schema = context.get("schema_version")
    if context_schema not in SUPPORTED_CONTEXT_SCHEMAS:
        fail(f"context.schema_version must be one of {sorted(SUPPORTED_CONTEXT_SCHEMAS)}")
    if context_schema in VISUAL_CONTEXT_SCHEMAS:
        required.add("visual_evidence")
    if context_schema in ROUTING_CONTEXT_SCHEMAS:
        required.update({"baseline_revision_id", "scruffy_applicability", "routing", "assumptions", "referrals"})
    missing = sorted(required - set(context))
    if missing:
        fail(f"context missing fields: {missing}")
    for field in ("audit_id", "revision_id"):
        if context.get(field) != registry.get(field):
            fail(f"context.{field} does not match registry")
    baseline_revision_id = context.get("baseline_revision_id")
    if context_schema in ROUTING_CONTEXT_SCHEMAS:
        if baseline_revision_id is not None and (
            not isinstance(baseline_revision_id, str) or not baseline_revision_id.strip()
        ):
            fail("context.baseline_revision_id must be null or a non-empty string")
        if baseline_revision_id != registry.get("baseline_revision_id"):
            fail("context.baseline_revision_id does not match registry")
    require_text(context.get("title"), "context.title")
    scruffy_applicability = context.get("scruffy_applicability")
    if context_schema in ROUTING_CONTEXT_SCHEMAS:
        if scruffy_applicability not in CONTEXT_CONTRACT["scruffy_applicability_statuses"]:
            fail("context.scruffy_applicability is invalid")

    outcome = context.get("outcome")
    if not isinstance(outcome, dict):
        fail("context.outcome must be an object")
    for field in ("label", "summary", "confidence"):
        require_text(outcome.get(field), f"context.outcome.{field}")

    assets = context.get("evidence_assets")
    if not isinstance(assets, list):
        fail("context.evidence_assets must be an array")
    by_evidence: dict[str, dict[str, Any]] = {}
    for index, asset in enumerate(assets):
        label = f"context.evidence_assets[{index}]"
        if not isinstance(asset, dict):
            fail(f"{label} must be an object")
        evidence_id = validate_evidence_id(asset.get("id"), f"{label}.id")
        if evidence_id in by_evidence:
            fail(f"context.evidence_assets repeats {evidence_id}")
        kind = asset.get("kind")
        if kind not in CONTEXT_CONTRACT["evidence_kinds"]:
            fail(f"{label}.kind is invalid")
        locator = require_text(asset.get("locator"), f"{label}.locator")
        require_text(asset.get("description"), f"{label}.description")
        verification = asset.get("verification")
        if verification not in CONTEXT_CONTRACT["evidence_verification"]:
            fail(f"{label}.verification is invalid")
        parsed = urlparse(locator)
        explicit_uri = re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://", locator)
        if explicit_uri and parsed.scheme not in {"http", "https"}:
            fail(f"{label}.locator uses an unsupported URI scheme")
        if kind in {"screenshot", "source", "runtime_trace", "copy_sample", "analysis_receipt"} and not explicit_uri and verification == "captured":
            candidate_text = re.sub(r":\d+$", "", locator.split("#", 1)[0])
            candidate = Path(candidate_text)
            if not candidate.is_absolute():
                candidate = base_path / candidate
            if not candidate.exists():
                fail(f"{label}.locator does not exist: {locator}")
        if kind == "specialist_review":
            receipt = asset.get("specialist_review")
            if not isinstance(receipt, dict):
                fail(f"{label}.specialist_review must be an object")
            discipline = receipt.get("discipline")
            if discipline not in SPECIALIST_LANES:
                fail(f"{label}.specialist_review.discipline must name a specialist-owned review lane")
            for field in ("reviewer_or_authority", "scope", "result"):
                require_text(receipt.get(field), f"{label}.specialist_review.{field}")
            reviewed_at = receipt.get("reviewed_at")
            artifact_version = receipt.get("artifact_version")
            if reviewed_at is not None:
                require_text(reviewed_at, f"{label}.specialist_review.reviewed_at")
            if artifact_version is not None:
                require_text(artifact_version, f"{label}.specialist_review.artifact_version")
            if reviewed_at is None and artifact_version is None:
                fail(
                    f"{label}.specialist_review requires reviewed_at or artifact_version metadata"
                )
            if receipt.get("verification_state") not in CONTEXT_CONTRACT["specialist_review_verification_states"]:
                fail(f"{label}.specialist_review.verification_state is invalid")
            if verification == "not_verified" and receipt.get("verification_state") == "verified":
                fail(f"{label}.specialist_review cannot be verified when the evidence asset is not_verified")
            if not explicit_uri and verification != "not_verified":
                candidate = Path(locator.split("#", 1)[0])
                if not candidate.is_absolute():
                    candidate = base_path / candidate
                if not candidate.exists():
                    fail(f"{label}.locator does not exist: {locator}")
        by_evidence[evidence_id] = asset

    def check_refs(value: Any, label: str, *, allow_empty: bool = False) -> list[str]:
        refs = require_unique_text_list(value, label, allow_empty=allow_empty)
        for ref_index, evidence_id in enumerate(refs):
            validate_evidence_id(evidence_id, f"{label}[{ref_index}]")
            if evidence_id not in by_evidence:
                fail(f"{label} references missing evidence {evidence_id}")
        return refs

    questions = context.get("product_frame")
    if not isinstance(questions, list):
        fail("context.product_frame must be an array")
    expected_questions = {row["key"] for row in CONTEXT_CONTRACT["product_frame_questions"]}
    by_question: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(questions):
        label = f"context.product_frame[{index}]"
        if not isinstance(row, dict):
            fail(f"{label} must be an object")
        key = row.get("key")
        if key not in expected_questions:
            fail(f"{label}.key is invalid")
        if key in by_question:
            fail(f"context.product_frame repeats {key}")
        require_text(row.get("answer"), f"{label}.answer")
        if row.get("basis") not in CONTEXT_CONTRACT["product_frame_bases"]:
            fail(f"{label}.basis is invalid")
        by_question[key] = row
    if set(by_question) != expected_questions:
        fail(f"context.product_frame must cover exactly {sorted(expected_questions)}")

    tasks = context.get("tasks")
    if not isinstance(tasks, list) or not 3 <= len(tasks) <= 5:
        fail("context.tasks must contain three to five representative tasks")
    task_ids: set[str] = set()
    for index, task in enumerate(tasks):
        label = f"context.tasks[{index}]"
        if not isinstance(task, dict):
            fail(f"{label} must be an object")
        task_id = require_text(task.get("id"), f"{label}.id")
        if task_id in task_ids:
            fail(f"context.tasks repeats {task_id}")
        task_ids.add(task_id)
        for field in ("goal", "result"):
            require_text(task.get(field), f"{label}.{field}")
        if task.get("status") not in CONTEXT_CONTRACT["task_statuses"]:
            fail(f"{label}.status is invalid")
        check_refs(task.get("evidence_refs"), f"{label}.evidence_refs")
    if scruffy_applicability == "not_applicable" and any(
        task.get("status") != "not_run" for task in tasks
    ):
        fail("context.tasks must all be not_run when Scruffy is not applicable")

    capability_rows = context.get("capabilities")
    if not isinstance(capability_rows, list):
        fail("context.capabilities must be an array")
    expected_capabilities = {row["key"] for row in CONTEXT_CONTRACT["capabilities"]}
    by_capability: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(capability_rows):
        label = f"context.capabilities[{index}]"
        if not isinstance(row, dict):
            fail(f"{label} must be an object")
        key = row.get("key")
        if key not in expected_capabilities:
            fail(f"{label}.key is invalid")
        if key in by_capability:
            fail(f"context.capabilities repeats {key}")
        if row.get("status") not in CONTEXT_CONTRACT["capability_statuses"]:
            fail(f"{label}.status is invalid")
        require_text(row.get("scope"), f"{label}.scope")
        by_capability[key] = row
    if set(by_capability) != expected_capabilities:
        fail(f"context.capabilities must cover exactly {sorted(expected_capabilities)}")
    source_write_status = by_capability["source_write"]["status"]
    run = registry["run"]
    if run["repository_write_authority"] == "not_authorized" and source_write_status != "not_authorized":
        fail("context.capabilities source_write must be not_authorized when the run has no write authority")
    if run["repository_write_authority"] == "authorized" and source_write_status == "not_authorized":
        fail("context.capabilities source_write contradicts the run's write authority")
    if run["repository_writes_performed"] and source_write_status not in {"available", "partial"}:
        fail("context.capabilities source_write must be available or partial when repository writes occurred")

    if context_schema in ROUTING_CONTEXT_SCHEMAS:
        referrals = context.get("referrals")
        if not isinstance(referrals, list):
            fail("context.referrals must be an array")
        referrals_by_id: dict[str, dict[str, Any]] = {}
        referral_questions: set[tuple[str, str]] = set()
        for index, row in enumerate(referrals):
            label = f"context.referrals[{index}]"
            if not isinstance(row, dict):
                fail(f"{label} must be an object")
            referral_id = require_text(row.get("id"), f"{label}.id")
            if not REFERRAL_ID.fullmatch(referral_id):
                fail(f"{label}.id must match {REFERRAL_ID.pattern}")
            if referral_id in referrals_by_id:
                fail(f"context.referrals repeats {referral_id}")
            validate_ledger_revision(
                row,
                label,
                revision_id=context["revision_id"],
                baseline_revision_id=baseline_revision_id,
            )
            lane = row.get("lane")
            if lane not in SPECIALIST_LANES:
                fail(f"{label}.lane must name a specialist-owned review lane")
            for field in ("summary", "reason", "claim_boundary"):
                require_text(row.get(field), f"{label}.{field}")
            question_key = (lane, row["summary"])
            if question_key in referral_questions:
                fail(f"context.referrals repeats the same specialist question in lane {lane}")
            referral_questions.add(question_key)
            if row.get("review_status") not in CONTEXT_CONTRACT["referral_review_statuses"]:
                fail(f"{label}.review_status is invalid")
            evidence_refs = check_refs(row.get("evidence_refs"), f"{label}.evidence_refs", allow_empty=False)
            specialist_artifact_refs = check_refs(
                row.get("specialist_artifact_refs"),
                f"{label}.specialist_artifact_refs",
                allow_empty=True,
            )
            unattached_specialist_refs = sorted(set(specialist_artifact_refs) - set(evidence_refs))
            if unattached_specialist_refs:
                fail(f"{label}.specialist_artifact_refs must also appear in evidence_refs")
            review_status = row.get("review_status")
            if review_status == "complete" and not specialist_artifact_refs:
                fail(f"{label}.specialist_artifact_refs cannot be empty when review_status is complete")
            if review_status == "not_run" and specialist_artifact_refs:
                fail(f"{label}.specialist_artifact_refs must be empty when review_status is not_run")
            specialist_receipts = [
                by_evidence[evidence_id]
                for evidence_id in specialist_artifact_refs
                if by_evidence[evidence_id].get("kind") == "specialist_review"
            ]
            if review_status == "complete" and not specialist_receipts:
                fail(
                    f"{label}: complete specialist referral requires a typed specialist_review receipt"
                )
            for receipt_asset in specialist_receipts:
                receipt = receipt_asset["specialist_review"]
                if receipt["discipline"] != lane:
                    fail(
                        f"{label}: specialist_review discipline {receipt['discipline']} does not match referral lane {lane}"
                    )
            if review_status == "complete" and not any(
                asset["specialist_review"]["verification_state"] == "verified"
                for asset in specialist_receipts
            ):
                fail(
                    f"{label}: complete specialist referral requires a verified specialist_review receipt"
                )
            referrals_by_id[referral_id] = row

        routing = context.get("routing")
        if not isinstance(routing, list):
            fail("context.routing must be an array")
        routing_by_lane: dict[str, dict[str, Any]] = {}
        routing_ids: set[str] = set()
        linked_referral_ids: set[str] = set()
        for index, row in enumerate(routing):
            label = f"context.routing[{index}]"
            if not isinstance(row, dict):
                fail(f"{label} must be an object")
            routing_id = require_text(row.get("id"), f"{label}.id")
            if not ROUTING_ID.fullmatch(routing_id):
                fail(f"{label}.id must match {ROUTING_ID.pattern}")
            if routing_id in routing_ids:
                fail(f"context.routing repeats {routing_id}")
            routing_ids.add(routing_id)
            validate_ledger_revision(
                row,
                label,
                revision_id=context["revision_id"],
                baseline_revision_id=baseline_revision_id,
            )
            lane = row.get("lane")
            if lane not in REVIEW_LANES:
                fail(f"{label}.lane is invalid")
            if lane in routing_by_lane:
                fail(f"context.routing repeats {lane}")
            disposition = row.get("disposition")
            if disposition not in CONTEXT_CONTRACT["lane_dispositions"]:
                fail(f"{label}.disposition is invalid")
            require_text(row.get("reason"), f"{label}.reason")
            evidence_refs = check_refs(row.get("evidence_refs"), f"{label}.evidence_refs", allow_empty=True)
            referral_ids = require_unique_text_list(row.get("referral_ids"), f"{label}.referral_ids")
            unknown_referrals = sorted(set(referral_ids) - set(referrals_by_id))
            if unknown_referrals:
                fail(f"{label}.referral_ids contains unknown referrals: {unknown_referrals}")
            if lane == "core_interface":
                expected_core = "not_applicable" if scruffy_applicability == "not_applicable" else "selected"
                if disposition != expected_core:
                    fail(
                        f"context.routing core_interface must be {expected_core} when Scruffy applicability is {scruffy_applicability}"
                    )
            if REVIEW_LANES[lane]["owner"] == "specialist" and disposition == "selected":
                fail(f"{label} cannot select specialist-owned lane {lane} as Scruffy work")
            if disposition in {"selected", "referred"} and not evidence_refs:
                fail(f"{label}.evidence_refs cannot be empty when disposition is {disposition}")
            if disposition == "referred":
                if not referral_ids:
                    fail(f"{label}.referral_ids cannot be empty when disposition is referred")
                wrong_lane = sorted(
                    referral_id
                    for referral_id in referral_ids
                    if referrals_by_id[referral_id]["lane"] != lane
                )
                if wrong_lane:
                    fail(f"{label}.referral_ids belongs to another lane: {wrong_lane}")
            elif referral_ids:
                fail(f"{label}.referral_ids must be empty unless disposition is referred")
            linked_referral_ids.update(referral_ids)
            routing_by_lane[lane] = row
        if set(routing_by_lane) != set(REVIEW_LANES):
            fail(f"context.routing must cover exactly {sorted(REVIEW_LANES)}")
        if scruffy_applicability == "not_applicable":
            selected_scruffy_lanes = sorted(
                lane
                for lane, row in routing_by_lane.items()
                if REVIEW_LANES[lane]["owner"] == "scruffy" and row["disposition"] == "selected"
            )
            if selected_scruffy_lanes:
                fail(
                    "context.routing cannot select Scruffy-owned lanes when Scruffy is not applicable: "
                    f"{selected_scruffy_lanes}"
                )
            if registry.get("items"):
                fail("registry.items must be empty for a non-interface stop-and-refer result")
        orphan_referrals = sorted(set(referrals_by_id) - linked_referral_ids)
        if orphan_referrals:
            fail(f"context.referrals contains unlinked referrals: {orphan_referrals}")

        assumptions = context.get("assumptions")
        if not isinstance(assumptions, list):
            fail("context.assumptions must be an array")
        assumption_ids: set[str] = set()
        assumption_propositions: set[str] = set()
        for index, row in enumerate(assumptions):
            label = f"context.assumptions[{index}]"
            if not isinstance(row, dict):
                fail(f"{label} must be an object")
            assumption_id = require_text(row.get("id"), f"{label}.id")
            if not ASSUMPTION_ID.fullmatch(assumption_id):
                fail(f"{label}.id must match {ASSUMPTION_ID.pattern}")
            if assumption_id in assumption_ids:
                fail(f"context.assumptions repeats {assumption_id}")
            assumption_ids.add(assumption_id)
            validate_ledger_revision(
                row,
                label,
                revision_id=context["revision_id"],
                baseline_revision_id=baseline_revision_id,
            )
            for field in ("statement", "risk_if_wrong", "evidence_needed", "decision_affected"):
                require_text(row.get(field), f"{label}.{field}")
            if row["statement"] in assumption_propositions:
                fail("context.assumptions repeats the same proposition under multiple IDs")
            assumption_propositions.add(row["statement"])
            basis = row.get("basis")
            if basis not in CONTEXT_CONTRACT["product_frame_bases"]:
                fail(f"{label}.basis is invalid")
            if row.get("confidence") not in CONTEXT_CONTRACT["assumption_confidence"]:
                fail(f"{label}.confidence is invalid")
            status = row.get("status")
            if status not in CONTEXT_CONTRACT["assumption_statuses"]:
                fail(f"{label}.status is invalid")
            evidence_refs = check_refs(row.get("evidence_refs"), f"{label}.evidence_refs", allow_empty=True)
            if (basis != "unknown" or status in {"supported", "refuted"}) and not evidence_refs:
                fail(f"{label}.evidence_refs cannot be empty for a grounded or resolved assumption")

    scores = context.get("scores")
    if not isinstance(scores, list):
        fail("context.scores must be an array")
    by_score: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(scores):
        label = f"context.scores[{index}]"
        if not isinstance(row, dict):
            fail(f"{label} must be an object")
        category = row.get("category")
        if category not in CANONICAL_CATEGORIES:
            fail(f"{label}.category is not canonical")
        if category in by_score:
            fail(f"context.scores repeats {category}")
        if row.get("score") not in CONTEXT_CONTRACT["score_values"]:
            fail(f"{label}.score is invalid")
        require_text(row.get("evidence"), f"{label}.evidence")
        check_refs(row.get("evidence_refs"), f"{label}.evidence_refs")
        by_score[category] = row
    if set(by_score) != CANONICAL_CATEGORIES:
        fail(f"context.scores must cover exactly {sorted(CANONICAL_CATEGORIES)}")
    if scruffy_applicability == "not_applicable" and any(
        row.get("score") != "N/A" for row in scores
    ):
        fail("context.scores must all be N/A when Scruffy is not applicable")

    checks_not_run = context.get("checks_not_run")
    if not isinstance(checks_not_run, list):
        fail("context.checks_not_run must be an array")
    for index, row in enumerate(checks_not_run):
        label = f"context.checks_not_run[{index}]"
        if not isinstance(row, dict):
            fail(f"{label} must be an object")
        for field in ("check", "reason", "impact"):
            require_text(row.get(field), f"{label}.{field}")

    work_orders = context.get("work_orders")
    if not isinstance(work_orders, list):
        fail("context.work_orders must be an array")
    if scruffy_applicability == "not_applicable" and work_orders:
        fail("context.work_orders must be empty when Scruffy is not applicable")
    registry_ids = {item["id"] for item in registry["items"]}
    work_ids: set[str] = set()
    for index, row in enumerate(work_orders):
        label = f"context.work_orders[{index}]"
        if not isinstance(row, dict):
            fail(f"{label} must be an object")
        work_id = require_text(row.get("id"), f"{label}.id")
        if work_id in work_ids:
            fail(f"context.work_orders repeats {work_id}")
        work_ids.add(work_id)
        for field in ("title", "summary", "verification"):
            require_text(row.get(field), f"{label}.{field}")
        item_ids = require_unique_text_list(row.get("item_ids"), f"{label}.item_ids", allow_empty=False)
        unknown_items = sorted(set(item_ids) - registry_ids)
        if unknown_items:
            fail(f"{label}.item_ids contains unknown items: {unknown_items}")
        require_unique_text_list(row.get("acceptance_checks"), f"{label}.acceptance_checks", allow_empty=False)

    items = validate_registry(registry, "registry")
    for item_id, item in items.items():
        for evidence_id in item["evidence_refs"]:
            if evidence_id not in by_evidence:
                fail(f"registry item {item_id} references missing evidence {evidence_id}")
            if item["confidence"] == "high" and by_evidence[evidence_id]["verification"] == "not_verified":
                fail(f"registry item {item_id} claims high confidence from unverified evidence {evidence_id}")
        if item["category"] == "copy" and item["kind"] in {"finding", "enhancement"}:
            editorial_refs = validate_editorial_review(
                item["editorial_review"],
                f"registry item {item_id}.editorial_review",
                kind=item["kind"],
                status=item["status"],
            )
            missing_editorial = sorted(editorial_refs - set(by_evidence))
            if missing_editorial:
                fail(f"registry item {item_id} editorial review references missing evidence: {missing_editorial}")
            unattached_editorial = sorted(editorial_refs - set(item["evidence_refs"]))
            if unattached_editorial:
                fail(f"registry item {item_id} editorial review evidence is absent from item evidence_refs: {unattached_editorial}")
            analyzer_ref = item["editorial_review"].get("analyzer_evidence_ref")
            if analyzer_ref is not None and by_evidence[analyzer_ref]["kind"] != "analysis_receipt":
                fail(f"registry item {item_id} analyzer evidence must use kind analysis_receipt")

        evidence_kinds = {
            by_evidence[evidence_id]["kind"]
            for evidence_id in item["evidence_refs"]
            if evidence_id in by_evidence
        }
        if item["kind"] == "finding" and item["status"] in ACTIVE_FINDING_STATUSES:
            if item["category"] == "performance" and not evidence_kinds & RUNTIME_EVIDENCE_KINDS:
                fail(
                    f"registry item {item_id} is an active performance finding without runtime evidence"
                    " (attach a runtime_trace or measurement receipt, or mark the item needs-verification evidence)"
                )
            if item["category"] == "accessibility":
                if "accessibility_observation" not in evidence_kinds:
                    fail(
                        f"registry item {item_id} is an active accessibility finding without an"
                        " accessibility_observation receipt"
                    )
                claim_text = " ".join([item["title"], item["observation"], *item["evidence"]])
                if not ACCESSIBILITY_CRITERION.search(claim_text):
                    fail(
                        f"registry item {item_id} is an active accessibility finding without a named"
                        " criterion (for example WCAG 1.4.3)"
                    )
            if item["category"] == "visual" and not evidence_kinds & RENDERED_EVIDENCE_KINDS:
                fail(
                    f"registry item {item_id} is an active visual finding without rendered evidence"
                    " (attach a screenshot or task_observation receipt; source-only visual claims are unverified)"
                )
            if item["category"] == "interaction" and not evidence_kinds & (
                RENDERED_EVIDENCE_KINDS | RUNTIME_EVIDENCE_KINDS
            ):
                fail(
                    f"registry item {item_id} is an active interaction finding without operation evidence"
                    " (attach a task_observation, runtime_trace, screenshot, or measurement receipt)"
                )
            if item["severity"] == "critical":
                if item["confidence"] != "high":
                    fail(f"registry item {item_id}: critical findings require high confidence")
                if len(item["evidence_refs"]) < 2:
                    fail(f"registry item {item_id}: critical findings require at least two evidence receipts")
            if len((item.get("user_impact") or "").strip()) < 25:
                fail(f"registry item {item_id}: user_impact must state a concrete impact (>= 25 characters)")

    screenshots_status = by_capability["screenshots"]["status"]
    screenshot_assets = [asset for asset in by_evidence.values() if asset["kind"] == "screenshot"]
    if screenshots_status in {"available", "partial"} and not screenshot_assets:
        fail(
            "context.capabilities claims screenshots "
            f"{screenshots_status} but the run captured no screenshot evidence asset;"
            " record the capability as not_run, unavailable, or not_needed instead"
        )
    if screenshots_status in {"unavailable", "not_run", "not_authorized", "not_needed"} and any(
        asset.get("verification") == "captured" for asset in screenshot_assets
    ):
        fail("captured screenshot evidence contradicts the screenshots capability status")

    missing_blind = sorted(set(run["blind_artifact_refs"]) - set(by_evidence))
    if missing_blind:
        fail(f"registry.run.blind_artifact_refs references missing evidence: {missing_blind}")
    validate_visual_evidence(context, items, by_evidence)
    return by_evidence


def validate_context_continuity(
    current: dict[str, Any],
    baseline: dict[str, Any],
) -> None:
    """Fail closed when context-1.2 durable ledgers disappear or change identity."""
    if current.get("schema_version") not in ROUTING_CONTEXT_SCHEMAS:
        return
    if current.get("audit_id") != baseline.get("audit_id"):
        fail("current and baseline context audit_id differ")
    if current.get("baseline_revision_id") != baseline.get("revision_id"):
        fail("current context baseline_revision_id must equal baseline context revision_id")

    current_revision = current["revision_id"]
    if baseline.get("schema_version") not in ROUTING_CONTEXT_SCHEMAS:
        for ledger_name in ("routing", "assumptions", "referrals"):
            for row in current.get(ledger_name, []):
                if row.get("revision_disposition") != "new":
                    fail(
                        f"context.{ledger_name} rows introduced after a legacy baseline must use revision_disposition new"
                    )
                if row.get("first_seen_revision") != current_revision:
                    fail(
                        f"context.{ledger_name} rows introduced after a legacy baseline must start in the current revision"
                    )
        return

    ledger_specs = {
        "routing": ("id", lambda row: row.get("lane"), "routing lane"),
        "assumptions": ("id", lambda row: row.get("statement"), "assumption proposition"),
        "referrals": (
            "id",
            lambda row: (row.get("lane"), row.get("summary")),
            "specialist question",
        ),
    }
    for ledger_name, (id_field, identity, identity_label) in ledger_specs.items():
        prior_rows = baseline.get(ledger_name, [])
        current_rows = current.get(ledger_name, [])
        prior_by_id = {row[id_field]: row for row in prior_rows}
        current_by_id = {row[id_field]: row for row in current_rows}
        prior_identity = {identity(row): row[id_field] for row in prior_rows}
        for row_id, row in current_by_id.items():
            prior = prior_by_id.get(row_id)
            if prior is None:
                reused = prior_identity.get(identity(row))
                if reused:
                    fail(
                        f"context.{ledger_name} ID {row_id} reissues baseline {identity_label} from {reused}"
                    )
                if row.get("revision_disposition") != "new":
                    fail(f"new context.{ledger_name} row {row_id} must use revision_disposition new")
                if row.get("first_seen_revision") != current_revision:
                    fail(f"new context.{ledger_name} row {row_id} must start in the current revision")
                continue

            if identity(row) != identity(prior):
                fail(f"context.{ledger_name} ID {row_id} was reused for a different {identity_label}")
            if row.get("first_seen_revision") != prior.get("first_seen_revision"):
                fail(f"context.{ledger_name} row {row_id}.first_seen_revision changed")
            prior_state = {key: value for key, value in prior.items() if key not in LEDGER_REVISION_FIELDS}
            current_state = {key: value for key, value in row.items() if key not in LEDGER_REVISION_FIELDS}
            expected = "carried" if current_state == prior_state else "updated"
            if row.get("revision_disposition") != expected:
                fail(
                    f"context.{ledger_name} row {row_id} must use revision_disposition {expected}"
                )
        missing = sorted(set(prior_by_id) - set(current_by_id))
        if missing:
            fail(f"context.{ledger_name} silently dropped baseline IDs: {missing}")


def validate_visual_evidence(
    context: dict[str, Any],
    items: dict[str, dict[str, Any]],
    by_evidence: dict[str, dict[str, Any]],
) -> dict[tuple[str, str | None], dict[str, Any]]:
    """Validate claim-specific context for every captured screenshot placement."""
    if context.get("schema_version") not in VISUAL_CONTEXT_SCHEMAS:
        return {}

    rows = context.get("visual_evidence")
    if not isinstance(rows, list):
        fail("context.visual_evidence must be an array")

    captured_ids = {
        evidence_id
        for evidence_id, asset in by_evidence.items()
        if asset.get("kind") == "screenshot" and asset.get("verification") == "captured"
    }
    referenced_by: dict[str, set[str]] = {evidence_id: set() for evidence_id in captured_ids}
    for item_id, item in items.items():
        for evidence_id in item.get("evidence_refs", []):
            if evidence_id in referenced_by:
                referenced_by[evidence_id].add(item_id)
    expected_pairs = {
        (evidence_id, item_id)
        for evidence_id, item_ids in referenced_by.items()
        for item_id in (item_ids or {None})
    }

    by_pair: dict[tuple[str, str | None], dict[str, Any]] = {}
    for index, row in enumerate(rows):
        label = f"context.visual_evidence[{index}]"
        if not isinstance(row, dict):
            fail(f"{label} must be an object")
        evidence_id = validate_evidence_id(row.get("evidence_id"), f"{label}.evidence_id")
        item_id = row.get("item_id")
        if item_id is not None:
            item_id = require_text(item_id, f"{label}.item_id")
            if item_id not in items:
                fail(f"{label}.item_id names unknown registry item {item_id}")
        pair = (evidence_id, item_id)
        if pair in by_pair:
            fail(f"context.visual_evidence repeats {item_id or 'unlinked'}:{evidence_id}")
        if evidence_id not in captured_ids:
            fail(f"{label} references screenshot evidence that is not captured: {evidence_id}")

        require_specific_visual_text(row.get("state"), f"{label}.state")
        require_specific_visual_text(row.get("look_at"), f"{label}.look_at")
        require_specific_visual_text(row.get("connection"), f"{label}.connection")
        annotation = row.get("annotation")
        if not isinstance(annotation, dict):
            fail(f"{label}.annotation must be an object")
        status = annotation.get("status")
        if status not in VISUAL_ANNOTATION_STATUSES:
            fail(f"{label}.annotation.status is invalid")
        require_specific_visual_text(annotation.get("reason"), f"{label}.annotation.reason")
        regions = annotation.get("regions")
        if not isinstance(regions, list):
            fail(f"{label}.annotation.regions must be an array")
        if status == "provided" and not 1 <= len(regions) <= VISUAL_ANNOTATION_MAX_REGIONS:
            fail(
                f"{label}.annotation.regions must contain one to "
                f"{VISUAL_ANNOTATION_MAX_REGIONS} regions when status is provided"
            )
        if status == "not_needed" and regions:
            fail(f"{label}.annotation.regions must be empty when status is not_needed")
        for region_index, region in enumerate(regions):
            region_label = f"{label}.annotation.regions[{region_index}]"
            if not isinstance(region, dict):
                fail(f"{region_label} must be an object")
            coordinates: dict[str, float] = {}
            for field in ("x", "y", "width", "height"):
                value = region.get(field)
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    fail(f"{region_label}.{field} must be a number")
                coordinates[field] = float(value)
            if coordinates["x"] < 0 or coordinates["y"] < 0:
                fail(f"{region_label} x and y must be at least zero")
            if coordinates["width"] <= 0 or coordinates["height"] <= 0:
                fail(f"{region_label} width and height must be greater than zero")
            if coordinates["x"] + coordinates["width"] > 100 or coordinates["y"] + coordinates["height"] > 100:
                fail(f"{region_label} must remain within percentage bounds 0 through 100")
            require_text(region.get("label"), f"{region_label}.label")
        by_pair[pair] = row

    missing = sorted(
        f"{item_id or 'unlinked'}:{evidence_id}"
        for evidence_id, item_id in expected_pairs - set(by_pair)
    )
    extra = sorted(
        f"{item_id or 'unlinked'}:{evidence_id}"
        for evidence_id, item_id in set(by_pair) - expected_pairs
    )
    if missing:
        fail(f"context.visual_evidence omits captured screenshot placements: {missing}")
    if extra:
        fail(f"context.visual_evidence contains non-rendered screenshot placements: {extra}")
    return by_pair


class DashboardParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.section_ids: set[str] = set()
        self.item_ids: list[str] = []
        self.decision_ids: set[str] = set()
        self.screenshot_images: list[dict[str, str | None]] = []
        self.screenshot_captions: set[tuple[str, str | None]] = set()
        self.visual_context: dict[tuple[str, str | None, str], list[str]] = {}
        self.annotation_markers: list[tuple[str, str | None, str]] = []
        self.whole_frame_markers: set[tuple[str, str | None]] = set()
        self._text_captures: list[dict[str, Any]] = []
        self.visible_text_parts: list[str] = []
        self._nonvisible_tags: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag in {"script", "style"}:
            self._nonvisible_tags.append(tag)
        element_id = values.get("id")
        if element_id:
            self.section_ids.add(element_id)
        item_id = values.get("data-item-id")
        if item_id:
            self.item_ids.append(item_id)
        decision_for = values.get("data-decision-for")
        if decision_for:
            self.decision_ids.add(decision_for)
        if tag == "img" and values.get("data-evidence-id"):
            self.screenshot_images.append(
                {
                    "evidence_id": values.get("data-evidence-id"),
                    "item_id": values.get("data-evidence-for"),
                    "src": values.get("src"),
                    "alt": values.get("alt"),
                }
            )
        caption_id = values.get("data-evidence-caption")
        if caption_id:
            self.screenshot_captions.add((caption_id, values.get("data-evidence-for")))
        context_kind = values.get("data-evidence-context")
        context_evidence = values.get("data-evidence-id")
        if context_kind and context_evidence:
            self._text_captures.append(
                {
                    "tag": tag,
                    "key": (context_evidence, values.get("data-evidence-for"), context_kind),
                    "parts": [],
                }
            )
        annotation_index = values.get("data-evidence-annotation")
        if annotation_index is not None and context_evidence:
            self.annotation_markers.append(
                (context_evidence, values.get("data-evidence-for"), values.get("data-evidence-label") or "")
            )
        if values.get("data-evidence-whole-frame") is not None and context_evidence:
            self.whole_frame_markers.add((context_evidence, values.get("data-evidence-for")))

    def handle_data(self, data: str) -> None:
        if not self._nonvisible_tags:
            self.visible_text_parts.append(data)
        for capture in self._text_captures:
            capture["parts"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._nonvisible_tags and self._nonvisible_tags[-1] == tag:
            self._nonvisible_tags.pop()
        for index in range(len(self._text_captures) - 1, -1, -1):
            capture = self._text_captures[index]
            if capture["tag"] != tag:
                continue
            text = " ".join("".join(capture["parts"]).split())
            self.visual_context.setdefault(capture["key"], []).append(text)
            self._text_captures.pop(index)
            break


def validate_dashboard(
    path: Path,
    registry: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> None:
    items = validate_registry(registry, "registry")
    parser = DashboardParser()
    try:
        parser.feed(path.read_text(encoding="utf-8"))
    except OSError as error:
        fail(f"dashboard unreadable: {error}")
    required_sections = set(REQUIRED_DASHBOARD_SECTIONS)
    if context is not None and context.get("schema_version") in ROUTING_CONTEXT_SCHEMAS:
        required_sections.update(ROUTING_REPORT_SECTIONS)
    missing_sections = sorted(required_sections - parser.section_ids)
    if missing_sections:
        fail(f"dashboard missing required sections: {missing_sections}")
    duplicates = sorted({item_id for item_id in parser.item_ids if parser.item_ids.count(item_id) > 1})
    if duplicates:
        fail(f"dashboard repeats item IDs: {duplicates}")
    missing_items = sorted(set(items) - set(parser.item_ids))
    extra_items = sorted(set(parser.item_ids) - set(items))
    if missing_items:
        fail(f"dashboard omits registry items: {missing_items}")
    if extra_items:
        fail(f"dashboard has unregistered items: {extra_items}")
    decision_required = {
        item_id
        for item_id, item in items.items()
        if item["kind"] in {"finding", "enhancement"} and item["status"] in {"open", "needs-verification"}
    }
    missing_controls = sorted(decision_required - parser.decision_ids)
    if missing_controls:
        fail(f"dashboard lacks decision controls for active items: {missing_controls}")

    if registry.get("schema_version") != CURRENT_SCHEMA_VERSION:
        return
    if context is None:
        fail(f"schema {CURRENT_SCHEMA_VERSION} dashboard validation requires context")
    raw_assets = context.get("evidence_assets")
    if not isinstance(raw_assets, list):
        fail("dashboard validation requires context.evidence_assets")
    screenshot_assets = {
        asset.get("id"): asset
        for asset in raw_assets
        if isinstance(asset, dict) and asset.get("kind") == "screenshot" and isinstance(asset.get("id"), str)
    }
    captured_ids = {
        evidence_id
        for evidence_id, asset in screenshot_assets.items()
        if asset.get("verification") == "captured"
    }
    rendered_ids: set[str] = set()
    rendered_pairs: set[tuple[str, str | None]] = set()
    for image in parser.screenshot_images:
        evidence_id = image["evidence_id"]
        item_id = image["item_id"]
        if evidence_id not in screenshot_assets:
            fail(f"dashboard embeds undeclared screenshot evidence {evidence_id}")
        if item_id is not None and item_id not in items:
            fail(f"dashboard screenshot {evidence_id} names unknown registry item {item_id}")
        source = image["src"] or ""
        if not source.startswith("data:image/") or ";base64," not in source:
            fail(f"dashboard screenshot {evidence_id} is not a self-contained image data URI")
        if not (image["alt"] or "").strip():
            fail(f"dashboard screenshot {evidence_id} lacks alt text")
        pair = (evidence_id, item_id)
        if pair not in parser.screenshot_captions:
            fail(f"dashboard screenshot {evidence_id} lacks a visible evidence caption")
        rendered_ids.add(evidence_id)
        rendered_pairs.add(pair)

    missing_captured = sorted(captured_ids - rendered_ids)
    if missing_captured:
        fail(f"dashboard does not embed captured screenshot evidence: {missing_captured}")
    missing_item_pairs: list[str] = []
    for item_id, item in items.items():
        for evidence_id in item.get("evidence_refs", []):
            asset = screenshot_assets.get(evidence_id)
            if asset and asset.get("verification") == "captured" and (evidence_id, item_id) not in rendered_pairs:
                missing_item_pairs.append(f"{item_id}:{evidence_id}")
    if missing_item_pairs:
        fail(
            "dashboard does not render captured screenshot evidence beside each registry item: "
            f"{sorted(missing_item_pairs)}"
        )

    if context.get("schema_version") in VISUAL_CONTEXT_SCHEMAS:
        all_evidence_assets = evidence_by_id(context)
        public_item_labels = item_label_map(list(items.values()))
        visual_by_pair = validate_visual_evidence(context, items, screenshot_assets)
        for (evidence_id, item_id), visual in visual_by_pair.items():
            for field in ("state", "look_at", "connection"):
                rendered = parser.visual_context.get((evidence_id, item_id, field), [])
                expected = " ".join(
                    humanize_text(
                        visual[field],
                        item_labels=public_item_labels,
                        evidence_assets=all_evidence_assets,
                    ).split()
                )
                if expected not in rendered:
                    fail(
                        f"dashboard does not render visual context {field} for "
                        f"{item_id or 'unlinked'}:{evidence_id}"
                    )
            annotation = visual["annotation"]
            marker_labels = [
                label
                for marker_evidence, marker_item, label in parser.annotation_markers
                if (marker_evidence, marker_item) == (evidence_id, item_id)
            ]
            expected_labels = [
                humanize_text(
                    region["label"],
                    item_labels=public_item_labels,
                    evidence_assets=all_evidence_assets,
                )
                for region in annotation["regions"]
            ]
            if annotation["status"] == "provided" and marker_labels != expected_labels:
                fail(f"dashboard does not render the declared annotations for {item_id or 'unlinked'}:{evidence_id}")
            if annotation["status"] == "not_needed":
                if (evidence_id, item_id) not in parser.whole_frame_markers:
                    fail(f"dashboard omits the whole-frame evidence decision for {item_id or 'unlinked'}:{evidence_id}")
                rendered_reason = parser.visual_context.get((evidence_id, item_id, "annotation_reason"), [])
                expected_reason = " ".join(
                    humanize_text(
                        annotation["reason"],
                        item_labels=public_item_labels,
                        evidence_assets=all_evidence_assets,
                    ).split()
                )
                if expected_reason not in rendered_reason:
                    fail(f"dashboard does not render the whole-frame reason for {item_id or 'unlinked'}:{evidence_id}")

        visible_text = " ".join(" ".join(parser.visible_text_parts).split())
        machine_references = {
            *items,
            *all_evidence_assets,
            *(str(row.get("id")) for row in context.get("tasks", []) if isinstance(row, dict) and row.get("id")),
            *(str(row.get("id")) for row in context.get("work_orders", []) if isinstance(row, dict) and row.get("id")),
            *(str(row.get("id")) for row in context.get("routing", []) if isinstance(row, dict) and row.get("id")),
            *(str(row.get("id")) for row in context.get("assumptions", []) if isinstance(row, dict) and row.get("id")),
            *(str(row.get("id")) for row in context.get("referrals", []) if isinstance(row, dict) and row.get("id")),
        }
        exposed_references = sorted(
            reference
            for reference in machine_references
            if re.search(rf"(?<![A-Za-z0-9]){re.escape(reference)}(?![A-Za-z0-9])", visible_text)
        )
        if exposed_references:
            fail(
                "dashboard exposes machine references in reader-facing text instead of plain-language labels: "
                f"{exposed_references}"
            )


def validate_markdown(
    path: Path,
    registry: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> None:
    items = validate_registry(registry, "registry")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        fail(f"Markdown report unreadable: {error}")
    section_ids = set(re.findall(r"<!--\s*anti-slop-section:([a-z-]+)\s*-->", text))
    item_ids = re.findall(r"<!--\s*anti-slop-item:([A-Z][A-Z0-9-]+)\s*-->", text)
    required_sections = set(REQUIRED_DASHBOARD_SECTIONS)
    if context is not None and context.get("schema_version") in ROUTING_CONTEXT_SCHEMAS:
        required_sections.update(ROUTING_REPORT_SECTIONS)
    missing_sections = sorted(required_sections - section_ids)
    if missing_sections:
        fail(f"Markdown report missing required sections: {missing_sections}")
    duplicates = sorted({item_id for item_id in item_ids if item_ids.count(item_id) > 1})
    if duplicates:
        fail(f"Markdown report repeats item IDs: {duplicates}")
    missing_items = sorted(set(items) - set(item_ids))
    extra_items = sorted(set(item_ids) - set(items))
    if missing_items:
        fail(f"Markdown report omits registry items: {missing_items}")
    if extra_items:
        fail(f"Markdown report has unregistered items: {extra_items}")


def run_prose_lint(findings: Path, context: Path | None, *, strict: bool) -> int | None:
    """
    Run the cognitive-load lint over the report's own reader-facing prose.

    Scruffy holds every interface it audits to a legibility standard and held
    its own output to none. `lint_report_prose.py` was written for exactly this
    and was never wired to a caller, which is the same failure shape as a check
    that exists in a file nobody imports.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from lint_report_prose import main as prose_main
    except ImportError:  # pragma: no cover - the linter ships beside this file
        print("note: lint_report_prose.py not importable; reader-facing prose NOT CHECKED")
        return None
    argv = [str(findings)]
    if context:
        argv += ["--context", str(context)]
    if strict:
        argv.append("--strict")
    code = prose_main(argv)
    if code != 0:
        fail("reader-facing prose failed the cognitive-load lint under --strict-prose")
    return code


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("registry", type=Path)
    parser.add_argument("--context", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--baseline-context", type=Path)
    parser.add_argument("--decisions", type=Path)
    parser.add_argument("--baseline-decisions", type=Path)
    parser.add_argument("--dashboard", type=Path)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument(
        "--strict-prose",
        action="store_true",
        help="Fail when reader-facing prose carries cognitive-load leads.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    registry = load_json(args.registry)
    validate_registry(registry)
    if registry.get("schema_version") == CURRENT_SCHEMA_VERSION and not args.context:
        fail(f"schema {CURRENT_SCHEMA_VERSION} registries require --context")
    context = load_json(args.context) if args.context else None
    if context is not None:
        validate_context(context, registry, base_path=args.context.parent)
    if args.baseline_context and not args.baseline:
        fail("--baseline-context requires --baseline")
    if (
        context is not None
        and context.get("schema_version") in ROUTING_CONTEXT_SCHEMAS
        and registry.get("baseline_revision_id") is not None
        and not args.baseline_context
    ):
        fail("context 1.2 revisions require --baseline-context to validate durable ledger continuity")
    baseline_registry = None
    if args.baseline:
        baseline_registry = load_json(args.baseline)
        validate_baseline(registry, baseline_registry)
    if args.baseline_context:
        if context is None or baseline_registry is None:
            fail("--baseline-context requires current --context and --baseline artifacts")
        baseline_context = load_json(args.baseline_context)
        if baseline_registry.get("schema_version") == CURRENT_SCHEMA_VERSION:
            validate_context(
                baseline_context,
                baseline_registry,
                base_path=args.baseline_context.parent,
            )
        validate_context_continuity(context, baseline_context)
    if args.decisions:
        baseline_decisions = load_json(args.baseline_decisions) if args.baseline_decisions else None
        validate_decisions(load_json(args.decisions), registry, baseline_decisions)
    if args.dashboard:
        validate_dashboard(args.dashboard, registry, context)
    if args.markdown:
        validate_markdown(args.markdown, registry, context)
    # The prose lint existed and nothing called it, so a report could be
    # schema-perfect and unreadable and still pass. Leads are informational by
    # design; --strict-prose promotes them to a gate.
    prose_leads = run_prose_lint(args.registry, args.context, strict=args.strict_prose)
    checks = ["registry"]
    if args.context:
        checks.append("context and evidence")
    if args.baseline:
        checks.append("baseline continuity")
    if args.baseline_context:
        checks.append("context ledger continuity")
    if args.decisions:
        checks.append("decisions")
    if prose_leads is not None:
        checks.append("reader-facing prose")
    if args.dashboard:
        checks.append("dashboard completeness")
    if args.markdown:
        checks.append("Markdown completeness")
    print("PASS: " + ", ".join(checks))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ValueError as error:
        raise SystemExit(f"FAIL: {error}")
