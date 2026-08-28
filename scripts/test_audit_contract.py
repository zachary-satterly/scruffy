#!/usr/bin/env python3
"""Regression tests for canonical categories, authority, evidence, and editorial receipts."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

from audit_contract import load_contract
from render_dashboard import decision_control, render as render_dashboard
from render_markdown import render as render_markdown
from report_contract import humanize_text
from taxonomy_contract import load_taxonomy
from validate_audit import (
    validate_baseline,
    validate_context,
    validate_dashboard,
    validate_decisions,
    validate_editorial_review,
    validate_markdown,
    validate_registry,
)


def expect_failure(registry: dict, context: dict | None, base: Path, contains: str) -> None:
    try:
        validate_registry(registry)
        if context is not None:
            validate_context(context, registry, base_path=base)
    except ValueError as error:
        if contains not in str(error):
            raise AssertionError(f"expected failure containing {contains!r}; got {error!r}") from error
        return
    raise AssertionError(f"expected failure containing {contains!r}")


def expect_dashboard_failure(
    path: Path,
    registry: dict,
    context: dict,
    contains: str,
) -> None:
    try:
        validate_dashboard(path, registry, context)
    except ValueError as error:
        if contains not in str(error):
            raise AssertionError(f"expected dashboard failure containing {contains!r}; got {error!r}") from error
        return
    raise AssertionError(f"expected dashboard failure containing {contains!r}")


class ReaderTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.hidden_tags: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.hidden_tags.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if self.hidden_tags and self.hidden_tags[-1] == tag:
            self.hidden_tags.pop()

    def handle_data(self, data: str) -> None:
        if not self.hidden_tags:
            self.parts.append(data)


def reader_text(document: str) -> str:
    parser = ReaderTextParser()
    parser.feed(document)
    return " ".join(" ".join(parser.parts).split())


def build_fixture(base: Path) -> tuple[dict, dict]:
    taxonomy = load_taxonomy()
    contract = load_contract()
    copy_path = base / "copy.txt"
    analyzer_path = base / "sentence-analysis.json"
    copy_path.write_text("Reader-facing copy sample.", encoding="utf-8")
    analyzer_path.write_text(json.dumps({"authorship_assessment": "not_performed"}), encoding="utf-8")

    evidence = [
        {
            "id": "EV-COPY",
            "kind": "copy_sample",
            "locator": copy_path.name,
            "description": "Verified reader-facing product prose.",
            "verification": "captured",
        },
        {
            "id": "EV-ANALYZER",
            "kind": "analysis_receipt",
            "locator": analyzer_path.name,
            "description": "Deterministic sentence-analysis receipt.",
            "verification": "captured",
        },
        {
            "id": "EV-TASK",
            "kind": "task_observation",
            "locator": "T1-T3",
            "description": "Three representative task observations.",
            "verification": "observed",
        },
        {
            "id": "EV-SCORE",
            "kind": "measurement",
            "locator": "all-category-scores",
            "description": "Evidence boundary for the category score ledger.",
            "verification": "observed",
        },
    ]
    manual_checks = [
        {
            "code": code,
            "result": "candidate" if code == "sentence_portability" else "clear",
            "evidence": "The passage was reviewed against the named procedure.",
            "evidence_ref": "EV-COPY",
        }
        for code in contract["editorial_review"]["sentence_manual_checks"]
    ]
    item = {
        "id": "AS-01",
        "identity_key": "portable-editorial-claim",
        "kind": "finding",
        "plain": "The homepage claims could belong to any product, so a reader cannot tell what this one does.",
        "title": "Portable claims hide the product outcome",
        "category": "copy",
        "facets": ["trust_integrity"],
        "severity": "medium",
        "confidence": "high",
        "status": "open",
        "revision_disposition": "new",
        "first_seen_revision": "r1",
        "last_observed_revision": "r1",
        "observation": "Two independent passage patterns recur without naming the product outcome.",
        "user_impact": "Readers cannot determine what changes after using the product.",
        "evidence": ["EV-COPY quotes the affected reader-facing passage."],
        "evidence_refs": ["EV-COPY", "EV-ANALYZER"],
        "cause": "The copy substitutes rhetorical structure for a concrete product claim.",
        "recommendation": "Name the actor, changed state, constraint, and observable result.",
        "acceptance_checks": ["A reader can state the product outcome from the revised passage."],
        "depends_on": [],
        "disposition_reason": "New baseline finding.",
        "destination_id": None,
        "editorial_review": {
            "review_type": "sentence_pattern",
            "sample_adequacy": "adequate",
            "analysis_language_scope": "en",
            "language_review_basis": "verified_english_analyzer",
            "analyzer_evidence_ref": "EV-ANALYZER",
            "independent_signal_families": ["rhetorical_structure", "specificity"],
            "manual_checks": manual_checks,
            "consequence": "The reader cannot identify the promised product outcome.",
            "counterexample_tested": "Intentional parallelism was rejected because the repeated structure adds no distinct information.",
            "authorship_assessment": "not_performed",
        },
    }
    registry = {
        "schema_version": "2.1",
        "audit_id": "contract-fixture",
        "target": "fixture://editorial",
        "revision_id": "r1",
        "baseline_revision_id": None,
        "run": {
            "requested_mode": "audit",
            "effective_mode": "audit",
            "mode_selection_basis": "explicit",
            "repository_write_authority": "not_authorized",
            "authority_basis_type": "not_granted",
            "authority_basis": "The request authorized inspection and reporting only.",
            "repository_writes_performed": False,
            "repository_write_paths": [],
            "live_demonstration_performed": False,
            "blind_status": "not_run",
            "blind_artifact_refs": [],
        },
        "items": [item],
        "presentation": {
            "prioritized_finding_ids": ["AS-01"],
            "prioritized_enhancement_ids": [],
            "strength_ids": [],
            "cleared_ids": [],
        },
    }
    question_rows = [
        {"key": row["key"], "answer": f"Fixture answer for {row['key']}.", "basis": "supplied"}
        for row in contract["context"]["product_frame_questions"]
    ]
    tasks = [
        {
            "id": f"T{index}",
            "goal": f"Representative task {index}",
            "result": "Observed result.",
            "status": "pass",
            "evidence_refs": ["EV-TASK"],
        }
        for index in range(1, 4)
    ]
    capability_status = {"source_write": "not_authorized", "screenshots": "not_run"}
    capabilities = [
        {
            "key": row["key"],
            "status": capability_status.get(row["key"], "available"),
            "scope": "Synthetic contract fixture.",
        }
        for row in contract["context"]["capabilities"]
    ]
    scores = [
        {
            "category": row["key"],
            "score": 2 if row["key"] == "copy" else 0,
            "evidence": "Bounded fixture score.",
            "evidence_refs": ["EV-SCORE"],
        }
        for row in taxonomy["categories"]
    ]
    context = {
        "schema_version": contract["context"]["schema_version"],
        "audit_id": registry["audit_id"],
        "revision_id": registry["revision_id"],
        "baseline_revision_id": None,
        "scruffy_applicability": "applicable",
        "title": "Audit-contract fixture",
        "outcome": {"label": "Sound with material gaps", "summary": "One editorial finding.", "confidence": "high"},
        "product_frame": question_rows,
        "tasks": tasks,
        "capabilities": capabilities,
        "routing": [
            {
                "id": f"ROUTE-{row['key'].replace('_', '-').upper()}",
                "lane": row["key"],
                "disposition": (
                    "selected" if row["key"] == "core_interface"
                    else "referred" if row["key"] == "security"
                    else "not_applicable"
                ),
                "reason": (
                    "The fixture exercises Scruffy's core interface contract."
                    if row["key"] == "core_interface"
                    else "The fixture routes security severity outside Scruffy."
                    if row["key"] == "security"
                    else "This bounded fixture does not require the lane."
                ),
                "evidence_refs": ["EV-TASK"] if row["key"] in {"core_interface", "security"} else [],
                "referral_ids": ["REF-SECURITY-1"] if row["key"] == "security" else [],
                "first_seen_revision": registry["revision_id"],
                "last_observed_revision": registry["revision_id"],
                "revision_disposition": "new",
                "disposition_reason": "Baseline routing decision.",
            }
            for row in contract["context"]["review_lanes"]
        ],
        "assumptions": [
            {
                "id": "ASM-AUDIENCE-1",
                "statement": "The supplied task observations represent the primary reader journey.",
                "basis": "inferred",
                "confidence": "moderate",
                "risk_if_wrong": "The audit could prioritize a secondary journey over the primary one.",
                "evidence_needed": "Representative usage evidence from the product owner or runtime.",
                "decision_affected": "Which journey receives first-priority repair work.",
                "status": "open",
                "evidence_refs": ["EV-TASK"],
                "first_seen_revision": registry["revision_id"],
                "last_observed_revision": registry["revision_id"],
                "revision_disposition": "new",
                "disposition_reason": "Baseline assumption.",
            }
        ],
        "referrals": [
            {
                "id": "REF-SECURITY-1",
                "lane": "security",
                "summary": "Validate any exploitability or security-severity claims separately.",
                "reason": "Scruffy can inspect interface consequences but does not perform vulnerability validation.",
                "review_status": "not_run",
                "claim_boundary": "This audit makes no claim that the fixture is secure.",
                "evidence_refs": ["EV-TASK"],
                "specialist_artifact_refs": [],
                "first_seen_revision": registry["revision_id"],
                "last_observed_revision": registry["revision_id"],
                "revision_disposition": "new",
                "disposition_reason": "Baseline specialist referral.",
            }
        ],
        "scores": scores,
        "work_orders": [
            {
                "id": "WO-01",
                "title": "Replace portable claims",
                "item_ids": ["AS-01"],
                "summary": "Write concrete, supported product outcomes.",
                "acceptance_checks": ["The outcome is specific and verifiable."],
                "verification": "Reader task plus editorial review.",
            }
        ],
        "checks_not_run": [],
        "evidence_assets": evidence,
        "visual_evidence": [],
    }
    return registry, context


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="scruffy-contract-") as directory:
        base = Path(directory)
        registry, context = build_fixture(base)
        active_control = decision_control(registry["items"][0], {"decision": "approve", "note": "repair it"})
        if 'data-decision-for="AS-01"' not in active_control:
            raise AssertionError("active audit finding lost its decision control")
        for terminal_status in ("fixed", "cleared", "merged", "superseded"):
            terminal_item = copy.deepcopy(registry["items"][0])
            terminal_item["status"] = terminal_status
            if decision_control(terminal_item, {"decision": "approve"}):
                raise AssertionError(f"{terminal_status} audit history was rendered as actionable")
        validate_registry(registry)
        validate_context(context, registry, base_path=base)
        decisions = {
            "schema_version": "2.1",
            "audit_id": registry["audit_id"],
            "revision_id": registry["revision_id"],
            "baseline_revision_id": None,
            "decisions": [
                {
                    "item_id": "AS-01",
                    "decision": "pending",
                    "note": "",
                    "updated_at": None,
                    "decision_source": "current",
                    "destination_id": None,
                    "history": [],
                }
            ],
        }
        validate_decisions(decisions, registry)

        prior_decisions_path = base / "decisions-r1.json"
        current_registry_path = base / "findings-r2.json"
        migrated_decisions_path = base / "decisions-r2.json"
        prior_decisions_path.write_text(json.dumps(decisions), encoding="utf-8")
        current_registry = copy.deepcopy(registry)
        current_registry["revision_id"] = "r2"
        current_registry["baseline_revision_id"] = "r1"
        current_registry["items"][0]["last_observed_revision"] = "r2"
        current_registry["items"][0]["revision_disposition"] = "carried"
        current_registry["items"][0]["disposition_reason"] = "Reproduced in the schema-2.1 revision."
        current_registry_path.write_text(json.dumps(current_registry), encoding="utf-8")
        migration = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).with_name("migrate_decisions.py")),
                str(prior_decisions_path),
                str(current_registry_path),
                str(migrated_decisions_path),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        if migration.returncode:
            raise AssertionError(f"schema-2.1 decision migration failed: {migration.stdout}{migration.stderr}")
        migrated_decisions = json.loads(migrated_decisions_path.read_text(encoding="utf-8"))
        if migrated_decisions["schema_version"] != "2.1":
            raise AssertionError("decision migration did not preserve the current registry schema")
        validate_decisions(migrated_decisions, current_registry, baseline_decisions=decisions)

        context_path = base / "context.json"
        context_path.write_text(json.dumps(context), encoding="utf-8")
        markdown_path = base / "report.md"
        dashboard_path = base / "dashboard.html"
        markdown_path.write_text(render_markdown(registry, context, decisions), encoding="utf-8")
        dashboard_path.write_text(render_dashboard(registry, context, decisions, context_path), encoding="utf-8")
        validate_markdown(markdown_path, registry, context)
        validate_dashboard(dashboard_path, registry, context)

        dashboard_html = dashboard_path.read_text(encoding="utf-8")
        dashboard_reader_text = reader_text(dashboard_html)
        for brand_token in (
            '--paper:#e9eaec',
            '--surface:#fff',
            '--ink:#14161a',
            '--brand:#d40f2e',
            'color-scheme:light',
            '<html lang="en" data-theme="light">',
        ):
            if brand_token not in dashboard_html:
                raise AssertionError(f"audit dashboard lost the canonical white/red brand token {brand_token!r}")
        for retired_theme_marker in (
            '--ink:#0c1210',
            '--gold:#e4c56a',
            'linear-gradient(160deg',
            'prefers-color-scheme:dark',
            'data-theme=dark',
        ):
            if retired_theme_marker in dashboard_html:
                raise AssertionError(f"audit dashboard restored retired theme behavior {retired_theme_marker!r}")
        if ".toolbar{position:static}" not in dashboard_html:
            raise AssertionError("dashboard keeps its large control toolbar sticky on narrow screens")
        for machine_term in ("AS-01", "EV-COPY", "EV-ANALYZER", "WO-01", "T1", "ASM-AUDIENCE-1", "REF-SECURITY-1", "trust_integrity", "schema-v2", "Receipts:"):
            if machine_term in dashboard_reader_text:
                raise AssertionError(f"dashboard exposes machine-facing term {machine_term}")
        for plain_term in ("Finding 1", "Journey 1", "Work package 1", "Core interface audit", "Security review", "Assumptions that could change the result", "Specialist referrals", "Copy sample", "Trust and content integrity", "Supporting records"):
            if plain_term not in dashboard_reader_text:
                raise AssertionError(f"dashboard omits plain-language term {plain_term}")
        for empty_state_term in (
            "Optional enhancements",
            "No optional enhancements were identified",
            "Corrective changes remain listed under Findings and Recommended work sequence",
        ):
            if empty_state_term not in dashboard_reader_text:
                raise AssertionError(f"dashboard enhancement empty state omits {empty_state_term!r}")
        for misleading_term in ("Suggested improvements", "Other improvements"):
            if misleading_term in dashboard_reader_text:
                raise AssertionError(f"dashboard still presents optional enhancements as {misleading_term!r}")

        markdown_reader_text = "\n".join(
            line for line in markdown_path.read_text(encoding="utf-8").splitlines()
            if not line.lstrip().startswith("<!--")
        )
        for machine_term in ("AS-01", "EV-COPY", "EV-ANALYZER", "WO-01", "T1", "ASM-AUDIENCE-1", "REF-SECURITY-1", "trust_integrity"):
            if machine_term in markdown_reader_text:
                raise AssertionError(f"Markdown report exposes machine-facing term {machine_term}")

        translated = humanize_text(
            "MJ-01 uses EV-AXE to check WCAG 1.4.3 at a URL; DOM, LCP, CLS, RUM, CSS, and NVDA are technical terms.",
            item_labels={"MJ-01": "Finding 1"},
            evidence_assets={"EV-AXE": {"kind": "accessibility_observation"}},
        )
        for machine_term in ("MJ-01", "EV-AXE", "WCAG", "URL", "DOM", "LCP", "CLS", "RUM", "CSS", "NVDA"):
            if machine_term in translated:
                raise AssertionError(f"plain-language translation leaves unexplained term {machine_term}")
        for plain_term in ("Finding 1", "Accessibility review", "minimum text-contrast requirement", "web address", "page structure", "main-content load time"):
            if plain_term not in translated:
                raise AssertionError(f"plain-language translation omits {plain_term}")
        accessibility_translation = humanize_text(
            "WCAG 2.4.2 (Page Titled), WCAG 3.1.1 (Language of Page), WCAG 1.3.1, "
            "WCAG 4.1.2 name/role/value/state contract, WCAG 4.1.3 support, and browser/OS."
        )
        for machine_term in ("WCAG", "OS", "2.4.2", "3.1.1", "1.3.1", "4.1.2", "4.1.3"):
            if machine_term in accessibility_translation:
                raise AssertionError(f"accessibility translation leaves unexplained term {machine_term}")
        for plain_term in ("page-title accessibility requirement", "page-language accessibility requirement", "operating system"):
            if plain_term not in accessibility_translation:
                raise AssertionError(f"accessibility translation omits {plain_term}")

        invalid_category = copy.deepcopy(registry)
        invalid_category["items"][0]["category"] = "writing-ish"
        expect_failure(invalid_category, None, base, "not canonical")

        unauthorized = copy.deepcopy(registry)
        unauthorized["run"]["repository_writes_performed"] = True
        unauthorized["run"]["repository_write_paths"] = ["README.md"]
        expect_failure(unauthorized, None, base, "forbids repository writes")

        invented_authority = copy.deepcopy(registry)
        invented_authority["run"]["requested_mode"] = "redesign"
        invented_authority["run"]["effective_mode"] = "redesign"
        invented_authority["run"]["repository_write_authority"] = "authorized"
        expect_failure(invented_authority, None, base, "explicit_request authority basis")

        escalation = copy.deepcopy(registry)
        escalation["run"]["effective_mode"] = "redesign"
        escalation["run"]["repository_write_authority"] = "authorized"
        escalation["run"]["authority_basis_type"] = "explicit_request"
        expect_failure(escalation, None, base, "requested and effective mode conflict")

        audit_with_authority = copy.deepcopy(registry)
        audit_with_authority["run"]["repository_write_authority"] = "authorized"
        audit_with_authority["run"]["authority_basis_type"] = "explicit_request"
        expect_failure(audit_with_authority, None, base, "cannot carry repository-write authority")

        missing_review = copy.deepcopy(registry)
        missing_review["items"][0]["editorial_review"] = None
        expect_failure(missing_review, None, base, "must be an object")

        one_family = copy.deepcopy(registry)
        one_family["items"][0]["editorial_review"]["independent_signal_families"] = ["specificity"]
        expect_failure(one_family, None, base, "two independent signal families")

        invented_families = copy.deepcopy(registry)
        invented_families["items"][0]["editorial_review"]["independent_signal_families"] = ["vibes", "roboticness"]
        expect_failure(invented_families, None, base, "unknown values")

        unlinked_manual_check = copy.deepcopy(registry)
        unlinked_manual_check["items"][0]["editorial_review"]["manual_checks"][0]["evidence_ref"] = None
        expect_failure(unlinked_manual_check, None, base, "typed evidence")

        authorship = copy.deepcopy(registry)
        authorship["items"][0]["editorial_review"]["authorship_assessment"] = "probably_ai"
        expect_failure(authorship, None, base, "must be not_performed")

        broader_editorial_review = {
            "review_type": "claims_provenance",
            "sample_adequacy": "not_applicable",
            "analysis_language_scope": "not_applicable",
            "language_review_basis": "not_applicable",
            "analyzer_evidence_ref": None,
            "independent_signal_families": [],
            "manual_checks": [
                {
                    "code": code,
                    "result": "candidate" if code == "claim_support_and_provenance" else "clear",
                    "evidence": "The claim was traced to its visible support and surface context.",
                    "evidence_ref": "EV-COPY",
                }
                for code in load_contract()["editorial_review"]["editorial_manual_checks"]
            ],
            "consequence": "The unsupported claim prevents a reader from verifying the promised outcome.",
            "counterexample_tested": "A supplied source was sought and not found in the bounded evidence set.",
            "authorship_assessment": "not_performed",
        }
        validate_editorial_review(broader_editorial_review, "broader editorial fixture", kind="finding", status="open")

        non_english_sentence_review = copy.deepcopy(registry["items"][0]["editorial_review"])
        non_english_sentence_review["analysis_language_scope"] = "non_en"
        non_english_sentence_review["language_review_basis"] = "language_competent_human"
        validate_editorial_review(non_english_sentence_review, "non-English sentence fixture", kind="finding", status="open")

        unknown_language = copy.deepcopy(registry)
        unknown_language["items"][0]["editorial_review"]["analysis_language_scope"] = "unknown"
        unknown_language["items"][0]["editorial_review"]["language_review_basis"] = "not_run"
        expect_failure(unknown_language, None, base, "requires verified en or non_en")

        missing_capability = copy.deepcopy(context)
        missing_capability["capabilities"].pop()
        expect_failure(registry, missing_capability, base, "must cover exactly")

        missing_route = copy.deepcopy(context)
        missing_route["routing"].pop()
        expect_failure(registry, missing_route, base, "routing must cover exactly")

        non_interface_registry = copy.deepcopy(registry)
        non_interface_registry["items"] = []
        non_interface_registry["presentation"] = {
            "prioritized_finding_ids": [],
            "prioritized_enhancement_ids": [],
            "strength_ids": [],
            "cleared_ids": [],
        }
        stop_and_refer = copy.deepcopy(context)
        stop_and_refer["scruffy_applicability"] = "not_applicable"
        stop_and_refer["work_orders"] = []
        for task in stop_and_refer["tasks"]:
            task["status"] = "not_run"
            task["result"] = "Scruffy stopped because the supplied target is not an interface."
        for score in stop_and_refer["scores"]:
            score["score"] = "N/A"
            score["evidence"] = "No interface score is claimed for a non-interface target."
        for route in stop_and_refer["routing"]:
            if route["lane"] in {"core_interface", "service_journey", "media_ingestion", "shared_output"}:
                route["disposition"] = "not_applicable"
                route["reason"] = "The supplied target is not a web interface."
                route["evidence_refs"] = []
        validate_registry(non_interface_registry)
        validate_context(stop_and_refer, non_interface_registry, base_path=base)

        contradictory_stop = copy.deepcopy(stop_and_refer)
        next(
            row for row in contradictory_stop["routing"] if row["lane"] == "core_interface"
        )["disposition"] = "selected"
        expect_failure(
            non_interface_registry,
            contradictory_stop,
            base,
            "core_interface must be not_applicable",
        )

        missed_interface = copy.deepcopy(context)
        next(row for row in missed_interface["routing"] if row["lane"] == "core_interface")["disposition"] = "not_applicable"
        expect_failure(registry, missed_interface, base, "core_interface must be selected")

        selected_specialist = copy.deepcopy(context)
        security_route = next(row for row in selected_specialist["routing"] if row["lane"] == "security")
        security_route["disposition"] = "selected"
        security_route["referral_ids"] = []
        expect_failure(registry, selected_specialist, base, "cannot select specialist-owned lane")

        unlinked_referral = copy.deepcopy(context)
        unlinked_referral["referrals"].append(
            {
                "id": "REF-PRIVACY-1",
                "lane": "privacy",
                "summary": "Validate privacy consequences independently.",
                "reason": "The bounded interface audit cannot prove privacy compliance.",
                "review_status": "not_run",
                "claim_boundary": "No privacy-compliance claim is made.",
                "evidence_refs": ["EV-TASK"],
                "specialist_artifact_refs": [],
                "first_seen_revision": registry["revision_id"],
                "last_observed_revision": registry["revision_id"],
                "revision_disposition": "new",
                "disposition_reason": "Baseline specialist referral.",
            }
        )
        expect_failure(registry, unlinked_referral, base, "contains unlinked referrals")

        unsupported_completion = copy.deepcopy(context)
        unsupported_completion["referrals"][0]["review_status"] = "complete"
        expect_failure(registry, unsupported_completion, base, "cannot be empty when review_status is complete")

        generic_completion = copy.deepcopy(context)
        generic_completion["referrals"][0]["review_status"] = "complete"
        generic_completion["referrals"][0]["specialist_artifact_refs"] = ["EV-TASK"]
        expect_failure(registry, generic_completion, base, "typed specialist_review receipt")

        verified_completion = copy.deepcopy(context)
        verified_completion["evidence_assets"].append(
            {
                "id": "EV-SPECIALIST",
                "kind": "specialist_review",
                "locator": "https://example.com/security-review-v1",
                "description": "Independent security review receipt covering the bounded fixture.",
                "verification": "observed",
                "specialist_review": {
                    "discipline": "security",
                    "reviewer_or_authority": "Independent security reviewer",
                    "scope": "Hostile-input and exploitability review for the bounded fixture.",
                    "result": "No critical exploitability finding was validated within the stated scope.",
                    "reviewed_at": "2026-08-25",
                    "artifact_version": None,
                    "verification_state": "verified",
                },
            }
        )
        verified_completion["referrals"][0]["review_status"] = "complete"
        verified_completion["referrals"][0]["evidence_refs"].append("EV-SPECIALIST")
        verified_completion["referrals"][0]["specialist_artifact_refs"] = ["EV-SPECIALIST"]
        validate_context(verified_completion, registry, base_path=base)
        completed_markdown = render_markdown(registry, verified_completion, decisions)
        completed_dashboard = render_dashboard(
            registry,
            verified_completion,
            decisions,
            context_path,
        )
        for rendered in (completed_markdown, completed_dashboard):
            for expected_text in (
                "Specialist review: Independent security review receipt",
                "Independent security reviewer",
                "No critical exploitability finding was validated",
                "2026-08-25",
                "Verification: verified",
            ):
                if expected_text not in rendered:
                    raise AssertionError(
                        f"completed specialist referral omits inspectable evidence {expected_text!r}"
                    )

        wrong_specialist_discipline = copy.deepcopy(verified_completion)
        wrong_specialist_discipline["evidence_assets"][-1]["specialist_review"]["discipline"] = "privacy"
        expect_failure(registry, wrong_specialist_discipline, base, "does not match referral lane")

        unverified_completion = copy.deepcopy(verified_completion)
        unverified_completion["evidence_assets"][-1]["specialist_review"]["verification_state"] = "not_verified"
        expect_failure(registry, unverified_completion, base, "requires a verified specialist_review receipt")

        ungrounded_assumption = copy.deepcopy(context)
        ungrounded_assumption["assumptions"][0]["evidence_refs"] = []
        expect_failure(registry, ungrounded_assumption, base, "grounded or resolved assumption")

        missing_evidence = copy.deepcopy(context)
        missing_evidence["evidence_assets"] = [row for row in missing_evidence["evidence_assets"] if row["id"] != "EV-COPY"]
        expect_failure(registry, missing_evidence, base, "missing evidence EV-COPY")

        missing_file = copy.deepcopy(context)
        missing_file["evidence_assets"][0]["locator"] = "does-not-exist.txt"
        expect_failure(registry, missing_file, base, "does not exist")

        wrong_analyzer_kind = copy.deepcopy(context)
        wrong_analyzer_kind["evidence_assets"][1]["kind"] = "measurement"
        expect_failure(registry, wrong_analyzer_kind, base, "kind analysis_receipt")

        # --- evidence-kind enforcement: performance ---
        perf = copy.deepcopy(registry)
        perf["items"][0]["category"] = "performance"
        perf["items"][0]["facets"] = ["resilience_recovery"]
        perf["items"][0]["editorial_review"] = None
        expect_failure(perf, context, base, "performance finding without runtime evidence")

        perf_guarded = copy.deepcopy(perf)
        perf_context = copy.deepcopy(context)
        perf_context["evidence_assets"].append(
            {
                "id": "EV-TRACE",
                "kind": "runtime_trace",
                "locator": "devtools-performance-trace",
                "description": "Recorded interaction trace with elapsed timings.",
                "verification": "observed",
            }
        )
        perf_guarded["items"][0]["evidence_refs"] = ["EV-TRACE"]
        validate_registry(perf_guarded)
        validate_context(perf_context, perf_guarded, base_path=base)

        # --- evidence-kind enforcement: accessibility ---
        axe = copy.deepcopy(registry)
        axe["items"][0]["category"] = "accessibility"
        axe["items"][0]["facets"] = ["resilience_recovery"]
        axe["items"][0]["editorial_review"] = None
        expect_failure(axe, context, base, "without an accessibility_observation receipt")

        axe_context = copy.deepcopy(context)
        axe_context["evidence_assets"].append(
            {
                "id": "EV-AXE",
                "kind": "accessibility_observation",
                "locator": "focus-order-walkthrough",
                "description": "Keyboard walkthrough recording focus order and announcements.",
                "verification": "observed",
            }
        )
        axe_named = copy.deepcopy(axe)
        axe_named["items"][0]["evidence_refs"] = ["EV-AXE"]
        expect_failure(axe_named, axe_context, base, "without a named criterion")

        axe_guarded = copy.deepcopy(axe_named)
        axe_guarded["items"][0]["observation"] = (
            "Focus order skips the dialog close control, failing WCAG 2.4.3 focus order."
        )
        validate_registry(axe_guarded)
        validate_context(axe_context, axe_guarded, base_path=base)

        # --- evidence-kind enforcement: visual must be rendered ---
        vis = copy.deepcopy(registry)
        vis["items"][0]["category"] = "visual"
        vis["items"][0]["facets"] = ["trust_integrity"]
        vis["items"][0]["editorial_review"] = None
        vis["items"][0]["evidence_refs"] = ["EV-SCORE"]
        expect_failure(vis, context, base, "without rendered evidence")

        vis_guarded = copy.deepcopy(vis)
        vis_guarded["items"][0]["evidence_refs"] = ["EV-TASK"]
        validate_registry(vis_guarded)
        validate_context(context, vis_guarded, base_path=base)

        # Guard: a cleared visual suspicion may keep source-only evidence.
        vis_cleared = copy.deepcopy(vis)
        vis_cleared["items"][0]["status"] = "cleared"
        vis_cleared["items"][0]["revision_disposition"] = "cleared"
        vis_cleared["presentation"]["prioritized_finding_ids"] = []
        vis_cleared["presentation"]["cleared_ids"] = ["AS-01"]
        validate_registry(vis_cleared)
        validate_context(context, vis_cleared, base_path=base)

        # --- capability/evidence reconciliation: screenshots ---
        shot_claimed = copy.deepcopy(context)
        for row in shot_claimed["capabilities"]:
            if row["key"] == "screenshots":
                row["status"] = "available"
        expect_failure(registry, shot_claimed, base, "captured no screenshot evidence asset")

        shot_file = base / "capture.png"
        shot_file.write_bytes(b"synthetic")
        shot_context = copy.deepcopy(context)
        shot_context["evidence_assets"].append(
            {
                "id": "EV-SHOT",
                "kind": "screenshot",
                "locator": shot_file.name,
                "description": "Synthetic capture for reconciliation tests.",
                "verification": "captured",
            }
        )
        shot_context["visual_evidence"].append(
            {
                "evidence_id": "EV-SHOT",
                "item_id": None,
                "state": "The synthetic fixture shows the complete captured test frame.",
                "look_at": "Use the entire frame as the screenshot embedding receipt.",
                "connection": "This frame proves that unlinked captured evidence remains visible.",
                "annotation": {
                    "status": "not_needed",
                    "reason": "The whole synthetic frame is the evidence under test here.",
                    "regions": [],
                },
            }
        )
        expect_failure(registry, shot_context, base, "contradicts the screenshots capability status")

        shot_guarded = copy.deepcopy(shot_context)
        for row in shot_guarded["capabilities"]:
            if row["key"] == "screenshots":
                row["status"] = "available"
        validate_registry(registry)
        validate_context(shot_guarded, registry, base_path=base)

        missing_visual_context = copy.deepcopy(shot_guarded)
        missing_visual_context["visual_evidence"] = []
        expect_failure(registry, missing_visual_context, base, "omits captured screenshot placements")

        context_1_1_visual_guard = copy.deepcopy(missing_visual_context)
        context_1_1_visual_guard["schema_version"] = "1.1"
        for field in ("routing", "assumptions", "referrals"):
            context_1_1_visual_guard.pop(field)
        expect_failure(registry, context_1_1_visual_guard, base, "omits captured screenshot placements")

        generic_visual_context = copy.deepcopy(shot_guarded)
        generic_visual_context["visual_evidence"][0]["look_at"] = "See image here."
        expect_failure(registry, generic_visual_context, base, "specific visible state or claim connection")

        empty_annotation = copy.deepcopy(shot_guarded)
        empty_annotation["visual_evidence"][0]["annotation"] = {
            "status": "provided",
            "reason": "The highlighted region should isolate the exact visible evidence.",
            "regions": [],
        }
        expect_failure(registry, empty_annotation, base, "must contain one to")

        contradictory_whole_frame = copy.deepcopy(shot_guarded)
        contradictory_whole_frame["visual_evidence"][0]["annotation"]["regions"] = [
            {"x": 10, "y": 10, "width": 40, "height": 40, "label": "Unexpected region"}
        ]
        expect_failure(registry, contradictory_whole_frame, base, "must be empty when status is not_needed")

        # A captured screenshot that is not item-linked remains visible in the
        # dashboard's additional visual-evidence index.
        unattached_dashboard_path = base / "dashboard-unattached-screenshot.html"
        unattached_dashboard = render_dashboard(registry, shot_guarded, decisions, context_path)
        unattached_dashboard_path.write_text(unattached_dashboard, encoding="utf-8")
        if 'id="visual-evidence"' not in unattached_dashboard:
            raise AssertionError("unattached screenshots were omitted instead of receiving a visual-evidence index")
        validate_dashboard(unattached_dashboard_path, registry, shot_guarded)

        # An item-linked screenshot is embedded as a data URI beside that item
        # and carries machine-readable receipt and association markers.
        shot_registry = copy.deepcopy(registry)
        shot_registry["items"][0]["evidence_refs"].append("EV-SHOT")
        linked_shot_context = copy.deepcopy(shot_guarded)
        linked_shot_context["visual_evidence"][0] = {
            "evidence_id": "EV-SHOT",
            "item_id": "AS-01",
            "state": "The synthetic fixture shows the item-linked evidence state.",
            "look_at": "The highlighted center marks the claim-specific evidence region.",
            "connection": "This region visibly connects the screenshot receipt to AS-01.",
            "annotation": {
                "status": "provided",
                "reason": "The center region isolates the evidence tied to this item.",
                "regions": [
                    {"x": 20, "y": 20, "width": 60, "height": 60, "label": "Claim-specific region"}
                ],
            },
        }
        validate_context(linked_shot_context, shot_registry, base_path=base)
        shot_dashboard_path = base / "dashboard-screenshot.html"
        shot_dashboard = render_dashboard(shot_registry, linked_shot_context, decisions, context_path)
        shot_dashboard_path.write_text(shot_dashboard, encoding="utf-8")
        for marker in (
            'data-evidence-id="EV-SHOT"',
            'data-evidence-for="AS-01"',
            'data-evidence-caption="EV-SHOT"',
            'data-evidence-context="state"',
            'data-evidence-context="look_at"',
            'data-evidence-context="connection"',
            'data-evidence-annotation="0"',
            'data-evidence-label="Claim-specific region"',
            'src="data:image/png;base64,',
        ):
            if marker not in shot_dashboard:
                raise AssertionError(f"rendered screenshot is missing {marker}")
        validate_dashboard(shot_dashboard_path, shot_registry, linked_shot_context)

        contextless_dashboard_path = base / "dashboard-contextless-screenshot.html"
        contextless_dashboard_path.write_text(
            shot_dashboard.replace(
                "The highlighted center marks the claim-specific evidence region.",
                "A nearby image appears here.",
            ),
            encoding="utf-8",
        )
        expect_dashboard_failure(
            contextless_dashboard_path,
            shot_registry,
            linked_shot_context,
            "does not render visual context look_at",
        )

        unannotated_dashboard_path = base / "dashboard-unannotated-screenshot.html"
        unannotated_dashboard_path.write_text(
            shot_dashboard.replace('data-evidence-annotation="0"', 'data-hidden-annotation="0"', 1),
            encoding="utf-8",
        )
        expect_dashboard_failure(
            unannotated_dashboard_path,
            shot_registry,
            linked_shot_context,
            "does not render the declared annotations",
        )

        external_dashboard_path = base / "dashboard-external-screenshot.html"
        external_dashboard_path.write_text(
            shot_dashboard.replace('src="data:image/png;base64,', 'src="capture.png#', 1),
            encoding="utf-8",
        )
        expect_dashboard_failure(
            external_dashboard_path,
            shot_registry,
            linked_shot_context,
            "is not a self-contained image data URI",
        )

        detached_dashboard_path = base / "dashboard-detached-screenshot.html"
        detached_dashboard_path.write_text(
            shot_dashboard.replace(' data-evidence-for="AS-01"', ""),
            encoding="utf-8",
        )
        expect_dashboard_failure(
            detached_dashboard_path,
            shot_registry,
            linked_shot_context,
            "does not render captured screenshot evidence beside each registry item",
        )

        uncaptioned_dashboard_path = base / "dashboard-uncaptioned-screenshot.html"
        uncaptioned_dashboard_path.write_text(
            shot_dashboard.replace('data-evidence-caption="EV-SHOT"', 'data-hidden-caption="EV-SHOT"'),
            encoding="utf-8",
        )
        expect_dashboard_failure(
            uncaptioned_dashboard_path,
            shot_registry,
            linked_shot_context,
            "lacks a visible evidence caption",
        )

        hidden_dashboard_path = base / "dashboard-hidden-screenshot.html"
        hidden_dashboard_path.write_text(
            shot_dashboard.replace(
                '<img data-evidence-id="EV-SHOT"',
                '<img data-hidden-evidence-id="EV-SHOT"',
            ),
            encoding="utf-8",
        )
        expect_dashboard_failure(
            hidden_dashboard_path,
            shot_registry,
            linked_shot_context,
            "does not embed captured screenshot evidence",
        )

        legacy = copy.deepcopy(registry)
        legacy["schema_version"] = "2.0"
        legacy.pop("run")
        legacy["items"][0]["category"] = "implementation-shape"
        for field in ("facets", "evidence_refs", "editorial_review"):
            legacy["items"][0].pop(field)
        validate_registry(legacy)

        legacy_baseline = copy.deepcopy(legacy)
        legacy_baseline["revision_id"] = "r0"
        legacy_baseline["items"][0]["category"] = "copy"
        legacy_baseline["items"][0]["first_seen_revision"] = "r0"
        legacy_baseline["items"][0]["last_observed_revision"] = "r0"
        legacy_baseline["items"][0]["revision_disposition"] = "new"
        current_revision = copy.deepcopy(registry)
        current_revision["baseline_revision_id"] = "r0"
        current_revision["items"][0]["first_seen_revision"] = "r0"
        current_revision["items"][0]["revision_disposition"] = "carried"
        current_revision["items"][0]["disposition_reason"] = "Reconciled from the schema-2.0 baseline."
        validate_baseline(current_revision, legacy_baseline)

    print("PASS: canonical taxonomy, run authority, evidence links, screenshot dashboard embedding, evidence-kind enforcement, capability reconciliation, editorial receipts, and legacy compatibility")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AssertionError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        sys.exit(1)
