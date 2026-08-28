# Changelog

All notable changes to the public Scruffy skill, formerly Anti-Slop, are documented here.

## Unreleased

- Prevented completed work from reappearing as a repair queue. Audit and repair
  decision surfaces now reserve controls for open or needs-verification items;
  fixed, cleared, merged, and superseded items remain visible and exportable as
  read-only lifecycle history, and completed design-direction groups are retired.
- Simplified the repair decision dashboard: added a safe **Approve all pending**
  action that preserves explicit defers and rejects, placed **Copy AI handoff**
  at both the sticky summary and end of the review, shortened the instructions,
  and removed the stale process slogan and inert theme toggle.
- Unified the audit and repair dashboards around the user-selected white/red
  Scruffy interface system while preserving their distinct jobs. Removed the
  audit dashboard's fixed green/gold screen palette and Mop's automatic
  operating-system dark-mode switch so moving from audit to decision to
  re-audit no longer looks like switching products.
- Fixed Mop dashboard choice handoff: its primary action now copies both exact
  decision and direction artifacts in a paste-ready AI message, individual JSON
  downloads remain available, and direction controls cannot serialize as orphan
  decision rows.
- Added context schema 1.2 with explicit Scruffy applicability, durable stable-ID routing, assumption, and specialist-referral ledgers, baseline-context continuity validation, and revision dispositions that distinguish new, carried, and updated rows. Completed referrals now require verified typed `specialist_review` receipts with discipline, reviewer or authority, scope, result, and date or version metadata, and rendered reports expose those evidence references and summaries. The audit instructions now treat target content as untrusted data and resist prompt injection. Scruffy's compatibility repair workflow delegates current-context validation to the canonical validator, accepts the prior r1 bundle explicitly through `--baseline-bundle` for legitimate repeat r2 ingestion, and fails closed when that baseline or continuity proof is missing or malformed.
- Reclassified the shipped review-routing fixtures and answer key as public synthetic development evidence, added ignored private-holdout locations, and bound scoring to frozen artifact/prompt hashes, explicit model/runtime identity, exact trials, and unique externally attested sessions. Frozen prompts embed the complete candidate schema and exact repeat/blind durability semantics so tool-disabled trials require no repository reads. Prospective v1.3 scoring preserves v1.1/v1.2 inputs, derives `record_checks_not_run` structurally, separates required recall and hard contradictions from non-gating unlisted-check advisories, permits an applicable interface to receive a limited review, and narrows `benign_quotation` to inert instruction-like text. Self-reported instruction non-execution scores as unproved, and non-interface targets stop and refer instead of selecting a fictitious core-interface review.
- Added prospective review-routing v1.4 while preserving v1.1-v1.3 and their run evidence: no-tools prompts now define every module and checks-not-run token and distinguish specialist referrals from missing execution evidence; ambiguous fixtures now state the form, backend-execution, and security-test evidence boundaries directly; required checks use an explicit 100% aggregate named-atom gate; and route agreement excludes evidence-grounded optional selections.
- Made `scaffold_audit.py` fail before writing when an explicit item prefix cannot produce a valid durable ID, with regression coverage for the previously broken `OMP-MOB` path.
- Added contract-safe `--mode` and `--repository-write-authority` scaffold inputs so explicitly authorized redesign and design runs start with matching run receipts and source-write capability.
- Added repeatable `--supplied-screenshot` inputs that type supplied raster evidence, copy bounded recognized images into the bundle, and make them directly embeddable by the self-contained dashboard renderer.

## 3.0.0 — 2026-08-20

**Breaking.** `plain` is now a required schema-2.1 registry field and
`validate_audit.py` refuses a registry without it. Existing stored audit
registries will fail validation until each item gains a lead. Everything else in
this release is additive; this one field is why the major version moves.

Note on distribution: `plugin.json` and `marketplace.json` had reported 2.5.0
since 2026-08-10 while `main` accumulated the entire section below. A
version-keyed installer therefore could not deliver any of it, including the
deterministic rule engine and reference grounding that the 2.5.0 changelog
already described. Installs predating this release are stale regardless of the
version they report.

- **Ingested research that never produced a rule is now a build failure, and the
  record of what was ingested outlives the ignored transcript folder.**
  `transcripts/` and `frames/` are gitignored by design — creator transcripts are
  not redistributed — but nothing committed recorded what had entered. The
  consequence, found by audit: 41 distinct video IDs are cited across PRINCIPLES
  §1–20 (roughly 120 rules) and not one of their transcripts survives anywhere.
  The citations carry real timestamps and are almost certainly accurate; they are
  simply no longer auditable, so no rule sourced from them can be re-verified or
  defended against a challenge.
  - `principles/SOURCE_LEDGER.md` is the committed per-video record: 41
    evidence-lost founding rows, 35 retained pilot rows, plus queued and
    known-failing entries. Rows are never deleted; `rejected` exists so a dead
    end is not silently re-ingested.
  - `scripts/validate_sources.py` enforces it. **`ingested` is deliberately a
    failing status** — a source with a transcript and zero `[video_id t]`
    citations breaks the build. There is no longer a state in which supplied
    content sits in a folder doing nothing.
  - It splits ledger checks from evidence checks, because this file ships to
    plugin users who have no corpus. Ledger checks read only committed files and
    run everywhere, including CI. Evidence checks need transcripts and report
    `SKIP` in a consumer checkout. **A check that did not run is never reported
    as a pass** — `validate_corpus.py` still prints PASS after skipping its own
    transcript-dependent checks, which is the failure this avoids.
  - `P06RgnUKX_I` (YC / Steven Haney) ships as a known-failing row: SOURCES.md
    claims coverage at "skill §C direct", but no citation for that id exists in
    PRINCIPLES.md or SKILL.md. Recorded rather than quietly dropped.
  - Wired into `.github/workflows/validate.yml` and the CONTRIBUTING validation
    block. CONTRIBUTING now states plainly that using scruffy never requires the
    corpus, and routes most contributions to user rule packs instead of PRs.

- **Every registry item now carries a `plain` lead, and the audit's own prose is
  in scope for the sentence-slop module.** Scruffy held every interface it
  audited to a legibility standard and held its own report to none. The failure
  that forced this: a twenty-one item registry in which every reader-facing
  field was populated, accurate and evidence-backed, and which a human could not
  read — each finding rendered as seven equal-weight blocks in the same
  register, twenty-one times, with no sentence anywhere saying the plain thing.
  Nothing failed, because correctness and legibility are different properties
  and only one of them was checked.
  - `plain` is a required schema-2.1 item field: one or two sentences, under
    thirty-two words, in the reader's words rather than the taxonomy's.
    `validate_audit.py` refuses a registry without it.
  - Two `cognitive_load` signals enforce it. `missing_plain_lead` fires on an
    absent or over-budget lead; `jargon_lead` fires when the lead is written in
    the register it was meant to replace. A reader's own domain terms are never
    jargon; the audit's private vocabulary is what gets flagged.
  - `scripts/lint_report_prose.py` already existed and **nothing called it**, so
    a report could be schema-perfect and unreadable and still pass.
    `validate_audit.py` now runs it every time, with `--strict-prose` to promote
    leads from a note to a gate.
  - Detail is never traded for readability. The lead is added, not substituted:
    the dashboard and Markdown renderers lead with it and disclose every
    remaining field below, and print forces disclosure open. The plain-language
    rule at output-schema.md was already the stated intent; this makes it
    enforceable rather than aspirational.
  - Artifact emission now follows capability rather than judgement. When
    `source_write` is available the registry, context, decisions and Markdown
    report are required, and an artifact that was not produced is named with the
    capability that prevented it. A missing artifact and one nobody thought
    about look identical otherwise.

- Consolidated the public product under one name, **Scruffy**. Reference grounding,
  principles, audit, repair, and verification are now described as workflow
  stages rather than DIRT, Keys, or Mop companion brands. Repair dashboards use
  the single Scruffy hero; the obsolete two-character banner was removed.
- Rewrote the README around the evidence loop and documented the complete
  principle-admission path: source registration, attributed rule, reproducible
  lead, false-positive counterexample, validation, and unseen-target forward
  test. A fresh hash-bound AI-slop review receipt replaces the stale naming-era
  review, and validators now resolve the receipt linked by the badge instead of
  hard-coding a dated file.
- Added a cited, guarded identity-lockup composition check for ceremonial and
  multi-line titles, including connector alignment and short/long/compound/
  localized stress cases. Empty report sections now say explicitly when no
  optional enhancements were found instead of presenting misleading empty
  “Suggested improvements” groups.
- Rebuilt the sentence analyzer's lexicon detectors as a data-driven runtime pack registry (contrast-scaffolds, hook-scaffolds, transition-markers, abstract-filler, hedged-profundity, triad-density, error-states, recovery-cues) with `--list-packs`, `--disable-pack`, `analyze(disabled_packs=...)`, pack disclosure in output (schema 1.3), and an extensibility regression; merged cleanly with the cognitive-load signals and the sentence-slop pack manifest, which now registers the two new signals with §33 citations and guards.
- New signals: comma-splice negative parallelism ("you're not overwhelmed, you're overstimulated"), kicker hooks, hedged profundity ("quietly"-class modifiers), profound-but-vague filler vocabulary, and short-item triad density — each with a false-positive fixture (sentence corpus 12 → 18 cases).
- Recovery detector: honest retained-state language ("nothing changed") now counts as a recovery cue, and UI items may carry `surface_class` so badges, cells, labels, headings, and status vocabulary never flag as unrecoverable errors.
- Validator: optional `principle_refs`/`detector_refs` provenance on registry items, an interaction-category evidence gate, critical-severity calibration (high confidence, two receipts), and a concrete `user_impact` floor — extending the existing category gates; regression suite `scripts/test_category_gates.py`.
- Added `scripts/scaffold_audit.py` (+ regression) emitting a pre-valid nine-capability, context-1.1 bundle so audits start from green.
- Standardized the provenance vocabulary (Source → Rule → Detector pack → Signal → Finding) in the output-schema reference.
- Repair workflow: direction picker with per-group `directions.json` (three structurally distinct, rule-cited directions, one recommended, human selection gate), imagery provenance origins with cross-product leakage refusal, provenance tab on every dashboard finding, target-identity header and missing-screenshot disclosure, browser probing, `mop_run.py` compatibility entry point, and self-labeling fixtures ([FIXTURE] titles).

- Gave scripts/annotate.html a complete keyboard authoring path (WCAG 2.1.1),
  closing the one open finding from the tool's first self-audit: the stage is
  now a focusable application region where Enter opens the file chooser, B adds
  a box, arrows move it, Shift+arrows resize it, Enter hands focus to the label
  input, Delete removes it, and every change is announced through a status live
  region with a visible focus outline. Re-verified keyboard-only end to end in
  a rendered session. Also collapsed the redundant one-pager score row label
  ("Accessibility slop · Accessibility" now renders as "Accessibility slop"),
  with a regression in test_durability.py.

- Fixed an innocent-substring false positive in the blind-freeze contamination
  scan: forbidden markers now match as whole tokens (marker "keys" no longer
  flags "monkeys"), with a regression covering both the benign and the
  real-mention case in scripts/test_blind_protocol.py. Documented the
  previously implicit blind-discovery JSON shape (top-level candidates /
  cleared_suspicions / checks_not_run lists keyed by sample_id, CAND-NNN ids,
  two-signal minimum) and the do-not-name-forbidden-paths rule in
  references/blind-audit.md. The web-fixtures contamination rule now also
  forbids evals/web-fixtures/runs/, which archives scored past runs (first
  entry: web-fixtures-blind-20260810, 11/12 disposition agreement, blindness
  verified).

- Implemented the first two product bets as reference CLIs: scripts/scan.py
  (B1: URL or file to static leads plus the operated checklist, honesty note
  built in) and scripts/render_onepager.py (B2: shareable broadsheet one-pager
  whose badge asserts process only — audited, revision, registry SHA-256 —
  never quality). Regressions in scripts/test_product_surfaces.py forbid
  fake-score artifacts and verify the embedded hash. Design agents restyle
  these; the contracts and honesty language are canonical.

## 2.5.0 — 2026-08-10

- Added the operated_check rule class: checklist rules with no static executor
  that the engine queues for the task walkthrough (8 starter checks from NN/g and
  Baymard distillations), plus a session_feedback block in engine output — a
  summary and per-rule next actions printed back to the invoking session so the
  lead-to-fix loop closes without opening the JSON. Dogfooded on Scruffy's own
  rendered dashboard: 20 static leads, all cleared by their own recorded guards
  (self-contained reports inline payloads and size figures by CSS by design).
- Added four source-backed baseline packs (30 rules total across 6 packs) and six
  new engine predicate types. Performance statics distilled from web.dev/Lighthouse
  (unsized images, head-blocking scripts, missing viewport, inline megapayloads);
  accessibility statics mapped from axe-core/WCAG with named criteria (missing alt,
  missing lang, empty controls, positive tabindex, duplicate ids); plain-language
  patterns from the public-domain US Federal Plain Language Guidelines and GOV.UK
  style guide; and generator-residue detection of unmodified builder defaults
  (scaffold titles, generator metas, built-with badges, TODO residue, silent empty
  catch blocks) informed by the public tell-catalogs of kill-ai-slop, SlopCop, and
  Slopdar — framed strictly as skipped decisions, never authorship claims. Every
  rule cites a corpus section and carries a false-positive guard; synthetic
  regressions cover each predicate, and all six packs stay silent on the
  known-answer fixture guards.
- Added the cognitive_load sentence-signal family with a cited pack listing
  (schema/sentence-slop-pack.json) covering all fifteen deterministic signals, a
  pack-parity regression so no analyzer code can ship uncited or unguarded, three
  new analyzer detectors (overlong_sentence, clause_pileup, parenthetical_stacking),
  and scripts/lint_report_prose.py, which turns the detector on our own audit
  artifacts. Dashboards gained plain-language section titles and explainers, task
  outcomes moved to the second column, scores sort worst-first, and every registry
  item carries a category chip in its rail.
- Redesigned the dashboard renderer around a docket architecture selected through
  a five-paradigm, five-material design round against real audit data: the masthead
  now leads with the top prioritized finding and a decision count, a stats strip
  carries open/enhancement/strength/cleared/carried counts with the worst category,
  severity chips gain a non-color lamp indicator, evidence figures take framed
  captions, print output becomes a broadsheet with red reserved for high severity,
  and text-containment rules (min-width:0, overflow-wrap:anywhere) prevent long
  hashes and URLs from painting over adjacent content, with a rendering regression.
- Added reference grounding: an optional design-reference search capability
  (reference implementation: Mobbin MCP — `search_screens`, `search_flows`, and
  `search_sections`) plus the user taste overlay restored from the Anti-Slop
  lineage, with precedence rules and popularity/deviation false-positive guards
  in `references/reference-grounding.md`. Absence is disclosed, never a finding.

## 2.4.0 — 2026-08-10

- Enforced four evidence rules that previously existed only as prose. Schema-2.1
  validation now fails closed when an active performance finding lacks a
  runtime_trace or measurement receipt, an active accessibility finding lacks an
  accessibility_observation receipt or a named criterion (for example WCAG 2.4.3),
  an active visual finding carries no rendered evidence (screenshot or
  task_observation), or the capability ledger claims screenshots while the run
  captured no screenshot evidence; captured screenshots likewise contradict a
  not-run screenshot capability. Cleared and legacy schema-2.0 items are exempt,
  preserving falsified-suspicion records and existing registries.
- Renamed the golden reconciliation fixture to evals/continuity/ and anonymized
  its target, prose, and identifiers; the seventeen-record structure, dispositions,
  and regression value are unchanged.
- Score tables now name the canonical slop category beside the score framing
  (for example "Structure slop · Implementation shape"), with a regression, an
  unknown-key fallback guard, and a legacy display-string passthrough guard.
- Added a deterministic rule engine (`scripts/rule_engine.py`) with rules as data
  in `schema/rules/*.json`. Every rule carries a canonical category, a severity on
  the suggestion/warning/error ratchet, a citation into the reconciled principles
  corpus, an explicit false-positive guard, and a narrow predicate. The engine
  emits leads, never findings: every lead requires confirmation by operating the
  interface, and output records `authorship_assessment: not_performed`. Two
  baseline packs ship (interaction/IA/semantic controls and editorial/synthetic
  proof, 11 rules); user packs load with `--pack`, require source attribution, and
  carry credit into every lead. Against the known-answer fixtures the baseline
  packs surface four of six planted defects statically with zero guard false
  positives; the remaining two are operation-only by design.
- Added `evals/web-fixtures/`: three deterministic, self-contained pages with six
  planted defects and six adjacent legitimate patterns across interaction,
  information architecture, copy, visual, and accessibility, plus a hidden
  discrimination key consumed by `scripts/evaluate_blind_outputs.py`. A new
  `scripts/test_web_fixtures.py` suite enforces page/key agreement, determinism,
  self-containment, per-page defect/guard pairing, and the no-authorship boundary.
  Detection quality on these fixtures is now a measured number rather than a claim.
- Known residual: kind-level checks cannot distinguish a static measurement from
  a runtime one; a measurement receipt derived from source alone still satisfies
  the performance predicate. Closing this requires a runtime attribute on
  measurement receipts in a future schema revision.

## 2.3.1 — 2026-08-10

- Added an agent-neutral root `AGENTS.md` maintainer contract and a thin
  `CLAUDE.md` import that turns the checkout into a Claude-priority project
  without duplicating the runtime skill.
- Mapped canonical sources to generated projections and made package validation
  enforce the DRY edit routes, no-authorship boundary, and blind-test separation.
- Added a paste-ready Claude maintenance prompt and completed the documented
  validation suite.

## 2.3.0 — 2026-08-10

- Made **Editorial slop** a first-class public category spanning content strategy, terminology, microcopy, sentence and passage construction, claims, provenance, information sequence, recovery language, and voice while preserving `copy` as the durable compatibility key.
- Replaced drifting layer, category, facet, run-mode, authority, capability, evidence, and editorial-review definitions with two canonical machine-readable manifests and generated documentation projections.
- Added schema-2.1 run receipts, write-authority enforcement, exact capability and score coverage, typed evidence resolution, captured-file checks, and mandatory editorial review receipts.
- Added current-to-legacy revision compatibility, decision migration across supported registry versions, current and legacy report rendering, and regression tests for invalid categories, unauthorized writes, missing evidence, weak sentence predicates, authorship claims, and missing audit coverage.
- Added explicit English language scope to the sentence analyzer; non-English and unknown-language inputs now abstain and require language-competent editorial review.
- Clarified that Claude and Codex share a source-compatible skill but require independent behavioral testing; compatibility is not a claim of identical output.
- Added a generated `skills/scruffy/SKILL.md` discovery adapter so Claude Code plugins expose `/scruffy:scruffy` while root `SKILL.md` remains the single runtime source of truth.

## 2.2.0 — 2026-08-10

- Rebuilt sentence-slop analysis around verified reader-facing prose extraction so README HTML, badges, tables, URLs, and install commands no longer inflate sentence counts or specificity markers.
- Added independent signal families, dependency collapse for duplicated evidence, short-sentence bursts, paragraph-pattern reuse, expanded contrast/scaffold coverage, and stricter passive and phrase-repetition thresholds.
- Made conceptual coherence, sentence portability, discourse purpose, and voice/subtext mandatory human checks; the deterministic analyzer explicitly marks them unscored and still refuses authorship classification.
- Expanded the sentence regression corpus from six to eleven cases, including markup contamination, single-device false positives, paragraph choreography, punchline stacks, and semantic collisions.
- Reconciled the supplied languagejones transcript, Hank Green's primary public statement, current r/WritingWithAI discourse, and coherence/discourse research without promoting community folklore into automatic tells.
- Rewrote the README around the then-current plain-language categories and the exact evidence each category requires; 2.3.0 reconciles that prose into the canonical eight-category taxonomy.

## 2.1.1 — 2026-08-09

- Rewrote the README opening and tagline to say plainly that Scruffy finds, proves, and helps fix AI slop in web apps.
- Defined AI slop as observable product, interaction, copy, accessibility, performance, visual, and implementation failures while preserving the no-authorship boundary.
- Aligned the Claude marketplace, Claude plugin, Codex metadata, and shared skill entrypoint around the same simple product promise.

## 2.1.0 — 2026-08-09

- Added a Claude Code plugin manifest and one-plugin marketplace catalog while retaining the root Agent Skills entrypoint used by Codex and standalone Claude skills.
- Made Claude Code marketplace installation the primary quick start and documented the stable `/scruffy:scruffy`, bare `/scruffy`, and `$scruffy` invocation paths without duplicating runtime instructions.
- Extended package validation to enforce Claude and Codex metadata compatibility and the documented install commands.

## 2.0.0 — 2026-08-09

- Renamed the public skill, invocation, install directory, and repository from Anti-Slop to Scruffy.
- Replaced MOP-1 with an original deadpan interface-janitor mascot, a reusable transparent character model, and a flat transparent README hero showing Scruffy sweeping a field of loose nuts and bolts with a commercial push broom.
- Preserved the internal `anti-slop-*` durable-report and browser-storage namespace so existing audit registries, decisions, and dashboards remain compatible.

## 1.2.0 — 2026-08-09

- Added a research-grounded sentence-slop axis that measures copy-quality leads without classifying AI authorship.
- Added length thresholds, compound finding predicates, explicit non-native and genre false-positive guards, and deterministic standard-library analysis.
- Added six sentence-copy fixtures covering formulaic prose, UI filler, technical passive voice, supplied non-native context, concrete prose, and insufficient samples.
- Added a two-phase blind-audit protocol with allowed/forbidden-input manifests, skill and prompt hashes, frozen discovery digests, contamination rejection, and post-reveal reconciliation.
- Added blind-protocol and sentence-detector regression suites to package validation and CI.
- Documented shared-source installation and direct invocation for both Codex and Claude Code.

## 1.1.0 — 2026-08-08

- Added schema-v2 audit registries with immutable IDs, identity keys, revision lineage, and explicit carry/fix/clear/merge/supersede dispositions.
- Made shortlist limits presentation-only and required all active, resolved, merged, and cleared records in durable reports.
- Added decision migration with retained notes and history.
- Added a self-contained dashboard renderer and validators for registry continuity, decision coverage, required sections, and complete item rendering.
- Added positive and negative durability fixtures plus an executable regression suite.
- Added application-archetype probes for reference/course, SaaS, transactional, forms/settings, data-heavy, collaboration/realtime, media/editor, marketing/static, and hybrid interfaces.
- Reconciled an anonymized course audit as the golden cross-revision test case.

## 1.0.0 — 2026-08-08

- Converted the original Claude-oriented instruction set to the Agent Skills standard.
- Added Codex metadata and explicit/implicit `$anti-slop` invocation support.
- Replaced the monolithic runtime file with progressive-disclosure verification, scoring, and output references.
- Added capability preflight, privacy boundaries, falsification, calibrated severity/confidence, and checks-not-run behavior.
- Made interactive HTML optional with Markdown and JSON fallbacks.
- Added deterministic package and corpus validators plus trigger evaluation fixtures.
- Renamed `tools/` to the conventional `scripts/` directory.
- Added agent-agnostic installation guidance, contributing rules, and CI validation.
- Validated the method against an external public test bed.
