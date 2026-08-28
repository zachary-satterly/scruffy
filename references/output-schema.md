# Output contract

For durable or repeated audits, [references/durability.md](durability.md) is binding. Keep stable IDs and identity keys across revisions. Never remove a prior item or assign its identity to another problem.

## Required artifact set

For a substantial file-backed audit, produce:

1. `findings.json` — complete registry, revision lineage, presentation lists, and run receipt
2. `context.json` — product frame, tasks, capabilities, routing, assumptions, specialist referrals, category scores, typed evidence, work orders, and checks not run
3. `decisions.json` — one decision record per finding/enhancement plus history
4. Markdown report — complete human-readable audit
5. Self-contained HTML dashboard when a viewer is available
6. `tokens.json` only when observed token changes are proposed

Chat-only work emits the same registry as a JSON block when files are unavailable.

## Markdown and dashboard order

1. Outcome and evidence boundary
2. Product framing and representative tasks
3. Capability and coverage ledger
4. Routing, assumptions, and specialist referrals
5. Category scores and verbal result
6. Prioritized findings (maximum eight)
7. Additional open and needs-verification findings
8. Prioritized and additional enhancements
9. Strengths to preserve
10. Fixed, cleared, merged, and superseded items
11. Revision reconciliation table
12. Work orders and acceptance checks
13. Checks not run

Every registry item must be present in the Markdown report and HTML dashboard. Collapsing resolved items is allowed; omission is not.

Interactive controls follow lifecycle, not merely the presence of a durable
decision row. Only open and needs-verification findings or enhancements may
offer approve, defer, reject, bulk-approval, or design-direction controls.
Fixed, cleared, merged, and superseded items retain their complete decision
history in exports and remain visible in the resolved section, but render as
read-only lifecycle history. A prior `approve` value never makes a terminal
item actionable again.

## Registry and run receipt

New audits emit registry schema `2.1`. Schema `2.0` remains readable for revision durability, but it is not a template for new reports. Mode names and authority rules come only from [audit-contract.md](audit-contract.md); categories and facets come only from [taxonomy.md](taxonomy.md).

```json
{
  "schema_version": "2.1",
  "audit_id": "stable-product-id",
  "target": "https://example.com",
  "revision_id": "r2",
  "baseline_revision_id": "r1",
  "scruffy_applicability": "applicable",
  "run": {
    "requested_mode": "audit",
    "effective_mode": "audit",
    "mode_selection_basis": "explicit",
    "repository_write_authority": "not_authorized",
    "authority_basis_type": "not_granted",
    "authority_basis": "The request authorized inspection and reporting only.",
    "repository_writes_performed": false,
    "repository_write_paths": [],
    "live_demonstration_performed": false,
    "blind_status": "not_run",
    "blind_artifact_refs": []
  },
  "items": [],
  "presentation": {}
}
```

Validation rejects writes in `audit` or `demonstrate_fix`, writes without authority, missing mutation paths, impossible live-demonstration combinations, and unsupported blind claims.

## Registry item

```json
{
  "id": "AS-01",
  "identity_key": "portable-editorial-claim",
  "kind": "finding",
  "title": "Portable claims hide the product outcome",
  "plain": "The homepage claims could belong to any product, so a reader cannot tell what this one does.",
  "category": "copy",
  "facets": ["trust_integrity"],
  "severity": "medium",
  "confidence": "high",
  "status": "open",
  "revision_disposition": "carried",
  "first_seen_revision": "r1",
  "last_observed_revision": "r2",
  "observation": "What happened without interpretation",
  "user_impact": "Who is affected and which task becomes harder",
  "evidence": ["Human-readable summary of the observed evidence"],
  "evidence_refs": ["EV-COPY", "EV-ANALYZER"],
  "cause": "Verified or explicitly inferred cause",
  "recommendation": "Smallest coherent change",
  "acceptance_checks": ["observable pass condition"],
  "depends_on": [],
  "disposition_reason": "Why this item carried or changed state",
  "destination_id": null,
  "editorial_review": {
    "review_type": "sentence_pattern",
    "sample_adequacy": "adequate",
    "analysis_language_scope": "en",
    "language_review_basis": "verified_english_analyzer",
    "analyzer_evidence_ref": "EV-ANALYZER",
    "independent_signal_families": ["rhetorical_structure", "specificity"],
    "manual_checks": [
      {
        "code": "conceptual_coherence",
        "result": "clear",
        "evidence": "Quoted review result",
        "evidence_ref": "EV-COPY"
      },
      {
        "code": "sentence_portability",
        "result": "candidate",
        "evidence": "Representative claims remain interchangeable across unrelated products.",
        "evidence_ref": "EV-COPY"
      },
      {
        "code": "discourse_purpose",
        "result": "clear",
        "evidence": "Each paragraph's reader task was labeled.",
        "evidence_ref": "EV-COPY"
      },
      {
        "code": "voice_and_subtext",
        "result": "clear",
        "evidence": "The supplied voice and implied audience relationship were compared.",
        "evidence_ref": "EV-COPY"
      }
    ],
    "consequence": "What becomes unclear, misleading, unsupported, or harder to act on",
    "counterexample_tested": "Why the pattern is not legitimate genre, voice, safety, or accessibility-simple writing",
    "authorship_assessment": "not_performed"
  }
}
```

Every schema-2.1 item includes `plain`, `facets`, `evidence_refs`, and `editorial_review`. The `plain` lead is one or two sentences, under thirty-two words, stating the finding in the reader's words rather than the taxonomy's; see [sentence-slop.md](sentence-slop.md). It is added to the record, never substituted for it — renderers lead with it and disclose the remaining fields progressively. Use `editorial_review: null` outside Editorial slop findings and enhancements. Every active `copy` finding completes the applicable editorial contract. Sentence-pattern and mixed findings include all four sentence manual checks, as shown above.

Allowed statuses: `open`, `fixed`, `cleared`, `needs-verification`, `merged`, `superseded`.

Allowed revision dispositions: `new`, `carried`, `reopened`, `fixed`, `cleared`, `merged`, `superseded`.

`merged` and `superseded` require `destination_id`. `fixed` and `cleared` require direct revision evidence. Findings require severity `critical`, `high`, `medium`, or `low`. Strengths use `none`. Enhancements use `high`, `medium`, or `low` as priority.

## Context, routing, and typed evidence

Schema-2.1 registries require `context.json`. Use the exact product-frame, capability, score, task, and evidence keys generated in [audit-contract.md](audit-contract.md).

```json
{
  "schema_version": "1.2",
  "audit_id": "stable-product-id",
  "revision_id": "r2",
  "baseline_revision_id": "r1",
  "title": "Example audit",
  "outcome": {"label": "Sound with material gaps", "summary": "...", "confidence": "high"},
  "product_frame": [{"key": "audience", "answer": "...", "basis": "observed"}],
  "tasks": [{"id": "T1", "goal": "...", "result": "...", "status": "pass", "evidence_refs": ["EV-TASK"]}],
  "capabilities": [{"key": "source_read", "status": "available", "scope": "..."}],
  "routing": [
    {
      "id": "ROUTE-CORE-INTERFACE",
      "lane": "core_interface",
      "disposition": "selected",
      "reason": "The request is an interface audit.",
      "evidence_refs": ["EV-TASK"],
      "referral_ids": [],
      "first_seen_revision": "r1",
      "last_observed_revision": "r2",
      "revision_disposition": "carried",
      "disposition_reason": "The interface-audit boundary is unchanged."
    },
    {
      "id": "ROUTE-SECURITY",
      "lane": "security",
      "disposition": "referred",
      "reason": "The target processes untrusted uploads, but exploitability was outside this interface review.",
      "evidence_refs": ["EV-SOURCE"],
      "referral_ids": ["REF-SECURITY-1"],
      "first_seen_revision": "r1",
      "last_observed_revision": "r2",
      "revision_disposition": "carried",
      "disposition_reason": "The specialist boundary remains open."
    }
  ],
  "assumptions": [
    {
      "id": "ASM-AUDIENCE-1",
      "statement": "Most guests will arrive by scanning a printed code on a phone.",
      "basis": "supplied",
      "confidence": "moderate",
      "risk_if_wrong": "The representative task set may omit the dominant entry path.",
      "evidence_needed": "Current event plan and real-device entry-path observations.",
      "decision_affected": "Which guest journey receives first-priority acceptance testing.",
      "status": "open",
      "evidence_refs": ["EV-SUPPLIED"],
      "first_seen_revision": "r1",
      "last_observed_revision": "r2",
      "revision_disposition": "carried",
      "disposition_reason": "The operating assumption remains unresolved."
    }
  ],
  "referrals": [
    {
      "id": "REF-SECURITY-1",
      "lane": "security",
      "summary": "Validate hostile-upload attack paths and severity.",
      "reason": "Scruffy can report visible upload consequences but does not perform vulnerability validation.",
      "review_status": "complete",
      "claim_boundary": "No claim is made that upload processing is secure.",
      "evidence_refs": ["EV-SOURCE", "EV-SECURITY-REVIEW"],
      "specialist_artifact_refs": ["EV-SECURITY-REVIEW"],
      "first_seen_revision": "r1",
      "last_observed_revision": "r2",
      "revision_disposition": "carried",
      "disposition_reason": "The specialist review completed in this revision."
    }
  ],
  "scores": [{"category": "product", "score": 0, "evidence": "...", "evidence_refs": ["EV-TASK"]}],
  "work_orders": [],
  "checks_not_run": [{"check": "Runtime performance", "reason": "No trace access", "impact": "Performance score is N/A"}],
  "evidence_assets": [
    {
      "id": "EV-TASK",
      "kind": "task_observation",
      "locator": "T1",
      "description": "Observed primary-task result",
      "verification": "observed"
    },
    {
      "id": "EV-SOURCE",
      "kind": "source",
      "locator": "https://example.com/source-boundary",
      "description": "Supplied source boundary that triggered specialist review",
      "verification": "supplied"
    },
    {
      "id": "EV-SUPPLIED",
      "kind": "supplied",
      "locator": "https://example.com/product-brief",
      "description": "Owner-supplied product and audience brief",
      "verification": "supplied"
    },
    {
      "id": "EV-SECURITY-REVIEW",
      "kind": "specialist_review",
      "locator": "evidence/security-review-v1.md",
      "description": "Independent security review receipt and bounded result.",
      "verification": "observed",
      "specialist_review": {
        "discipline": "security",
        "reviewer_or_authority": "Named independent security reviewer or authoritative reviewing body",
        "scope": "Hostile-upload attack paths and exploitability within the named build.",
        "result": "The review's bounded conclusion, including unresolved questions.",
        "reviewed_at": "2026-08-25",
        "artifact_version": "review-v1",
        "verification_state": "verified"
      }
    }
  ],
  "visual_evidence": [
    {
      "evidence_id": "EV-SHOT",
      "item_id": "AS-01",
      "state": "After the user completed the primary task at desktop width.",
      "look_at": "The highlighted result panel contains no completion value or recovery action.",
      "connection": "This visible dead end is the user impact described by AS-01.",
      "annotation": {
        "status": "provided",
        "reason": "The result panel is the smallest region that demonstrates the visible claim.",
        "regions": [
          {"x": 20, "y": 25, "width": 60, "height": 35, "label": "Result panel without an outcome"}
        ]
      }
    }
  ]
}
```

The complete document contains every required product-frame question, capability, canonical category score, and routing lane. Registry, task, score, routing, assumption, referral, blind, and editorial references resolve to typed evidence IDs. Captured local screenshots, source files, traces, copy samples, and analysis receipts must exist relative to `context.json` or at their absolute path. Context schemas 1.1 and 1.2 contain one `visual_evidence` record for every captured screenshot/item pair. A captured screenshot not cited by any item receives one record with `item_id: null`.

Context 1.2 records `scruffy_applicability` as `applicable`, `not_applicable`, or `uncertain`, then records each canonical lane exactly once as `selected`, `rejected`, `not_applicable`, or `referred`. The core interface lane is selected when Scruffy applies or applicability is uncertain. A non-interface stop-and-refer marks Scruffy and the core lane not applicable, selects no Scruffy-owned lane, emits no interface items or work orders, records representative tasks as not run, and leaves every category score as `N/A`. Specialist-owned lanes cannot be selected as Scruffy work. A referred lane links to one or more referral records for the same lane; every referral is linked from the routing ledger. Routing keys never appear in `items[].category`.

Routing, assumption, and referral IDs are durable within an audit. Every row records `first_seen_revision`, `last_observed_revision`, `revision_disposition`, and `disposition_reason`. Use `new` only for a genuinely new row, `carried` when its substantive data is unchanged, and `updated` when its status, evidence, boundary, or routing decision changed. Prior rows remain present even after an assumption is supported or refuted or a referral is completed. Context 1.2 also records `baseline_revision_id`; a revision must be validated with `--baseline-context` so stable IDs cannot silently disappear or be reissued.

Open assumptions may omit evidence only when their basis is `unknown`; grounded, supported, and refuted assumptions cite evidence. Specialist referrals use `not_run`, `partial`, or `complete` to disclose the actual review boundary and state what Scruffy will not claim. `specialist_artifact_refs` is empty for `not_run`. A `complete` referral must cite a lane-matched `specialist_review` receipt whose metadata names the discipline, reviewer or authority, scope, result, a date or artifact version, and `verification_state: verified`. Human reports render an inspectable summary of the supporting receipts instead of showing a bare completion label.

## Decisions

```json
{
  "schema_version": "2.1",
  "audit_id": "stable-product-id",
  "revision_id": "r2",
  "baseline_revision_id": "r1",
  "decisions": [
    {
      "item_id": "AS-01",
      "decision": "pending",
      "note": "",
      "updated_at": null,
      "decision_source": "current",
      "destination_id": null,
      "history": []
    }
  ]
}
```

Allowed decisions are `pending`, `approve`, `defer`, and `reject`. Preserve history append-only. A merged or superseded source retains its decision; never transfer approval to the destination automatically.

The decisions schema version must match its registry. Validate a new audit with:

```sh
python3 scripts/validate_audit.py findings.json --context context.json --decisions decisions.json --dashboard dashboard.html --markdown report.md
```

Validate a context-1.2 revision against both baselines:

```sh
python3 scripts/validate_audit.py findings.json --context context.json --baseline prior-findings.json --baseline-context prior-context.json --decisions decisions.json --baseline-decisions prior-decisions.json --dashboard dashboard.html --markdown report.md
```

## Token data

Create `tokens.json` only from observed current values:

```json
{
  "schema_version": "1.0",
  "tokens": [
    {
      "name": "color.text.muted",
      "current": "#777777",
      "proposed": "#555555",
      "reason": "Measured contrast correction",
      "finding_ids": ["AS-11"]
    }
  ]
}
```

If no token layer exists, label current values as observed literals and make token extraction part of the work order.

## Interactive HTML report

Include:

- All twelve required sections in the prescribed order
- Every registry item, keyed by immutable ID
- Filterable status/kind/severity views
- Evidence and acceptance checks without hover dependence
- Approve/defer/reject plus notes for open or needs-verification findings and enhancements
- Read-only lifecycle state and preserved prior decisions for terminal items
- Copy/download of schema-v2 decisions and findings
- Prior-decision import or explicit migration instructions
- Print-friendly styling and keyboard-operable controls
- No external runtime dependency unless requested

Every locally captured screenshot receipt must be visible in the self-contained dashboard, not merely present on disk or named by evidence ID. Render a screenshot referenced by a registry item beside that item. Render any remaining captured screenshot in an additional visual-evidence index so the dashboard does not hide collected evidence. Embed image bytes as `data:image/...;base64,...`, provide meaningful alt text, and show a caption that names the evidence receipt. The caption must visibly render the claim-specific state, `look_at` instruction, and connection from `context.json`. A `provided` annotation renders its labeled rectangles over the image. A `not_needed` annotation renders the whole-frame reason instead. Mark the image with `data-evidence-id="EV-..."`; when it supports an item, also mark it with `data-evidence-for="ITEM-ID"`. The validator rejects missing images, external or relative image sources, absent captions, generic or missing visual context, unrendered context, missing annotations, and screenshot-to-item associations that exist only in JSON.

Human-facing Markdown and HTML are decision surfaces, not schema viewers. Translate stable item IDs into ordinal labels such as `Finding 1`, evidence IDs into their evidence type such as `Screenshot` or `Accessibility review`, work-order IDs into `Work package 1`, and task IDs into `Journey 1`. Render canonical categories, facets, statuses, dispositions, severity, confidence, standards, and measurements in plain language. Translate or expand technical abbreviations such as WCAG, URL, DOM, LCP, CLS, and RUM wherever they would otherwise require specialist knowledge. Keep the original values unchanged in JSON, `data-*` attributes, embedded downloads, and invisible Markdown continuity comments. A reader must be able to understand and decide every item without learning the audit schema or opening a glossary.

Use the complete registry as the rendering source. Do not hand-maintain a separate HTML findings list.

## Implementation work orders

Order approved work by dependency:

1. Shared structural blockers
2. Routing, data, and state contracts
3. Semantic and interaction primitives
4. Visual tokens and responsive composition
5. Page-specific cleanup
6. Verification and regression tests

Each work order names affected surfaces, registry IDs, dependencies, acceptance checks, and verification method. An audit or dashboard decision is not source-edit authorization unless the user requested implementation.


## Provenance vocabulary (standardized)

One chain, four words, used everywhere in Scruffy and its consumers:

| Term | Meaning | Lives in | Cited as |
|---|---|---|---|
| **Source** | Origin material: a person, paper, video, or standard | `principles/SOURCES.md` | alias — `[KJ]`, `[RUI]`, `[GOVUK-CLEAR]` |
| **Rule** | A distilled, falsifiable statement from a source | `principles/PRINCIPLES.md` §n; reference contracts | `PRINCIPLES §12 [Lp6ey4AyDzA 3:06]` |
| **Detector pack** | Deterministic code operationalizing rules — analyzer packs, the sentence-slop pack manifest, or a target's own CI gate | `scripts/analyze_sentence_slop.py` PACKS; `schema/sentence-slop-pack.json`; target repo gates | pack id — `recovery-cues`; `target gate: contrast-checks` |
| **Signal** | What a detector emits: a lead needing human judgement | analyzer output `leads[].code` | `missing_recovery_information` |

A finding may record rules in `principle_refs` and packs/signals in `detector_refs` (both optional, validated when present); typed receipts stay in `evidence_refs`. "Principle" and "policy" are not separate terms; a principle *is* a rule.

## Category evidence gates (summary)

Active performance findings require runtime evidence; accessibility findings require an `accessibility_observation` receipt and a named criterion; visual findings require rendered evidence; interaction findings require operation evidence. Critical findings require high confidence and two receipts, and `user_impact` has a 25-character concrete-consequence floor. Enforced in `validate_audit.py`; regression-locked by `scripts/test_category_gates.py`.

## Starting a new bundle

Run `python3 scripts/scaffold_audit.py --audit-id <id> --target <desc> --title <title> --out <dir>` to emit a pre-valid findings/context/decisions trio (TODO placeholders, one `needs-verification` seed item). Select an explicit contract-safe run receipt with `--mode` and `--repository-write-authority`; authorized writes are accepted only for `redesign` and `design`, while an unauthorized write-capable mode safely downgrades its effective mode to `audit`. Repeat `--supplied-screenshot <path>` to copy recognized PNG, JPEG, GIF, or WebP evidence into the bundle and seed typed, renderer-compatible screenshot receipts. Explicit `--item-prefix` values must be two to six uppercase alphanumeric characters beginning with a letter, and invalid inputs fail before the output directory is created. Edit from green instead of negotiating with the validator.
