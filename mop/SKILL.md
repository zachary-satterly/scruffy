---
name: scruffys-mop
description: Implement and verify fixes for AI slop that Scruffy has already audited. Use when a Scruffy audit exists (findings.json, context.json, decisions.json, optional tokens.json) and approved findings must be turned into real, high-craft source changes under repository-write authority, then handed back for re-audit. Consumes Scruffy's output contract read-only; implements only approved work orders in dependency order; never diagnoses, scores authorship, or marks its own work fixed. Do not use to produce a fresh audit or findings (that is Scruffy), or for non-interface code work.
---

# Scruffy — repair workflow

This compatibility entrypoint runs Scruffy’s approved-repair stage. Scruffy
implements the smallest coherent, genuinely well-crafted change for each
**approved** finding, then re-audits the result. The `scruffys-mop` machine name
and `mop_*` filenames remain stable for existing installations; they are not a
separate human-facing product.

This skill is agent-, vendor-, framework-, browser-, and operating-system-
agnostic, and stays inside Scruffy's evidence-bound loop.

## Required run order

Every repair session starts with the orchestrator and renders the decision surface
before any implementation:

```
python3 scripts/mop_run.py <bundle> [--baseline-bundle <prior-bundle>] [--templates <reference-image-dir>] [--authorized]
```

This always produces, in order: `mop-preflight.json` (capabilities probed and
disclosed, never assumed), a validated or freshly scaffolded `directions.json`
(three structurally distinct, principle-cited directions per design group, with
template/screenshot imagery attached when the runtime has it), and
`mop-dashboard.html` — the self-contained picker the human uses to select
directions and approve items. **Approve all pending** changes only untouched
pending items and preserves every explicit defer or reject. **Copy AI handoff**
is available both in the sticky decision bar and after the final finding; it
copies a paste-ready message containing both `decisions.json` and
`directions.json`. Separate JSON downloads remain available as fallback.
Implementation begins only after the human's
exported selections pass `mop_directions.py check`; a visual direction without
an image anchor cannot be selected, and text-only design advice fails closed.

## Non-negotiable boundary

- **Consume, don't re-diagnose.** Scruffy owns the audit schema. Read it
  read-only; never redefine, extend, or fork it.
- **Only approved items.** Implement only registry items whose `decisions.json`
  value is `approve`. Never action `pending`, `defer`, or `reject`.
- **Authority is inherited.** Write source only under Scruffy's `redesign`/
  `design` mode with `source_write`, or an explicit user grant. Fail closed
  otherwise; an audit or a dashboard decision alone is not source-edit authority.
- **Don't self-certify.** Never set `status: fixed`/`cleared`. Only a Scruffy
  re-audit clears a finding.
- **Preserve product truth.** Everything in Scruffy's `product_frame` and outside
  the approved scope survives unchanged.
- **Preserve audit boundaries.** Read context routing, assumptions, and referrals,
  but never implement a referral as though it were an approved Scruffy finding.
  Only an approved registry item enters the repair plan.
- **Validate current context canonically.** A context-1.2 bundle is usable only
  after Scruffy's parent `validate_audit.py` accepts its exact findings, context,
  and decisions artifacts. A repeat revision must also pass the prior bundle's
  `findings.json` and `context.json` through `--baseline-bundle`; Mop forwards
  them to that same validator for registry and ledger continuity. If the
  canonical validator or required baseline is absent, or validation rejects the
  bundle, stop; never substitute a Mop-owned interpretation of the schema.

## Load order

1. [`references/method.md`](references/method.md) — the end-to-end operating loop.
   Start here every time.
2. [`schema/interop.json`](schema/interop.json) +
   [`references/scruffy-handoff.md`](references/scruffy-handoff.md) — exactly which
   Scruffy artifacts and schema versions are consumed, and the gates.
3. [`references/fix-protocols.md`](references/fix-protocols.md) — the per-category
   fix protocol, opened at the item's `category` as you implement it.
4. [`references/visual-redesign.md`](references/visual-redesign.md) — the
   first-class path for `visual`/`product` findings: capability preflight, optional
   design-reference grounding, and impeccable-or-floor implementation.
5. [`references/craft-bar.md`](references/craft-bar.md) — the quality floor that
   separates clearing a finding from camouflaging it.
6. [`references/verification.md`](references/verification.md) — self-check and the
   re-audit handoff.

Visual redesign is the headline job. Optional craft augmentations — **impeccable**
(free, first-class when the runtime has it) and a **design-reference search**
(Mobbin or equivalent; paid, optional) — are detected at runtime, used if present,
and disclosed if absent via `mop_handoff.py --augmentations`. The built-in craft
floor always applies; no augmentation is ever a hard dependency, and an absence is
never a defect.

## The loop, in one screen

```sh
python3 scripts/mop_bundle.py check <bundle-dir> [--baseline-bundle <prior-bundle>]              # ingest, validate, gate
python3 scripts/mop_bundle.py plan  <bundle-dir> [--baseline-bundle <prior-bundle>] --authorized # approved-item plan
python3 scripts/mop_preflight.py --design-reference-search available  # probe capabilities (never assume)
# implement each step to the craft bar, in order, per fix-protocols.md
python3 scripts/mop_dashboard.py <bundle-dir> --assets assets.json --out dashboard.html --authorized  # self-contained deliverable
python3 scripts/mop_handoff.py <bundle-dir> --work work.json --authorized  # re-audit handoff (never marks fixed)
```

For visual/product work, the deliverable is a **single self-contained HTML
dashboard** (`mop_dashboard.py`) with all evidence embedded as `data:` URIs, and
capabilities come from a real **probe** (`mop_preflight.py`), never an assumption:
a capability is `absent` only after a probe fails. See
[`references/visual-redesign.md`](references/visual-redesign.md).

The scripts do the mechanical, error-prone parts — schema-version validation, the
authority and approval gates, dependency ordering, and the handoff shape. Use
them; do not re-derive their work by eye. If a script prints `REFUSED`, stop and
disclose the gap rather than editing the bundle to make it pass.

## When to refuse

If a step would have you produce a finding, choose an approval, invent a severity
or evidence, mark your own work cleared, or widen scope past the approved items —
stop and return to Scruffy’s audit stage.
