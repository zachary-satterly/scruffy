# Changelog

All notable changes to Scruffy's compatibility repair workflow are recorded here.

## [0.1.0] — unreleased

First functional release: implements approved Scruffy findings and hands them back
for re-audit. Not yet exercised against a real-world audit outside the fixture.

### Added
- Simplified the decision handoff with **Approve all pending** (without
  overwriting defers or rejects), an end-of-review **Copy AI handoff** action,
  shorter instructions, and removal of stale process and theme-toggle chrome.
- Made the dashboard's primary handoff a paste-ready **Copy AI handoff**
  action containing exact `decisions.json` and `directions.json` blocks, while
  retaining separate downloads as fallback. Direction controls no longer leak
  orphan rows into `decisions.json`.
- Product record (`PRODUCT.md`) via Impeccable init.
- Consumer interop contract against Scruffy's output schema
  (`schema/interop.json`): registry 2.1, context 1.2 (1.0 and 1.1 read-only),
  decisions 2.1, tokens 1.0, plus the work-order lane / ordering model.
- Canonical context-1.2 validation through Scruffy's parent validator, including
  explicit `--baseline-bundle <prior-bundle-dir>` support for repeat revisions.
  Mop forwards the prior `findings.json` and `context.json` for registry and
  routing/assumption/referral continuity; a missing or malformed baseline fails
  closed. The r2/r1 fixture regression covers library load, CLI check, and CLI
  plan while retaining malformed-repeat rejection.
- Runtime method: `SKILL.md` routing into `references/method.md`,
  `fix-protocols.md` (per-category protocols for all eight Scruffy categories),
  `craft-bar.md`, `verification.md`, and `scruffy-handoff.md`.
- Deterministic scripts: `scripts/mop_bundle.py` (ingest, fail-closed version
  validation, authority + approval gates, dependency-ordered planning),
  `scripts/mop_handoff.py` (re-audit handoff that never self-certifies), and
  `scripts/validate_skill.py` (repo self-consistency).
- Test suite `scripts/test_mop.py` (17 cases) and worked fixture bundle
  `fixtures/sample-audit/`.
- Planner guard: an approved item already in a terminal status
  (`fixed`/`cleared`/`merged`/`superseded`) is skipped with a warning rather
  than re-implemented — surfaced by the first real-target dry run.
- Claude plugin and Codex skill distribution metadata; maintainer contract
  (`AGENTS.md`).

- Visual redesign is the headline job: `references/visual-redesign.md` adds the
  first-class path for `visual`/`product` findings (capability preflight, optional
  design-reference grounding, impeccable-or-floor implementation).
- Augmentation model in `schema/interop.json`: **impeccable** (free, first-class
  when present), **design-reference search** (Mobbin or equivalent; paid, optional),
  and **browser** (free renderer, mechanically probed), with a built-in free floor.
- **`scripts/mop_preflight.py`** — probes capabilities so a capability is `absent`
  only after a probe fails; omission is `not_run`, never `absent`. The browser is
  probed mechanically; runtime/MCP capabilities require an attested result and
  refuse `absent` without a reason.
- **`scripts/mop_dashboard.py`** — generates the Mop's standard deliverable: a
  single self-contained HTML dashboard from a Scruffy bundle + assets manifest,
  every image embedded as a `data:` URI, failing closed on any external loader.
- `interop.json` `probe_rule` and `output_rule`; `references/visual-redesign.md`
  gains the probe-don't-assume preflight and the self-contained-output steps. The
  handoff now discloses `browser` alongside impeccable and the reference search.
  Tests now 25 cases.

### Decided
- Named the project **Scruffy's Mop** (machine name `scruffys-mop`).
- Product is a **visual-redesign-forward** fix executor (option 3).
- Craft engine is a **free floor plus optional augmentations**: impeccable is free
  and first-class when present; the design-reference search is paid and optional.
  Neither is ever a hard dependency; absences are disclosed, not defects. This is
  the free-tier behavior required for open-sourcing.

### Not yet built
- Real-world audit runs beyond the fixture; a broader regression corpus.
- Optional deterministic helpers for applying token changes.
