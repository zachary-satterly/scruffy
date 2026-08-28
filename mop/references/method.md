# Method

The operating loop for Scruffy repair. Load this first. It routes to
[`fix-protocols.md`](fix-protocols.md), [`craft-bar.md`](craft-bar.md), and
[`verification.md`](verification.md) as work reaches each stage. The interop
contract it enforces is [`../schema/interop.json`](../schema/interop.json);
[`scruffy-handoff.md`](scruffy-handoff.md) is the human-readable version.

The deterministic scripts do the mechanical, error-prone parts (version checks,
gate, ordering, handoff shape). Use them; do not re-derive their work by eye.

## 0. Locate the bundle

You need a directory holding a Scruffy audit's output: `findings.json`,
`context.json`, `decisions.json`, and optionally `tokens.json`. If the user gives
you a report but not these files, ask for the JSON artifacts — Scruffy repair
implements against the registry, not against prose.

For a repeat context-1.2 audit (its `baseline_revision_id` is non-null), also
locate the prior revision's bundle. Pass that directory explicitly with
`--baseline-bundle <prior-bundle-dir>`. The prior directory must contain its
canonical `findings.json` and `context.json`; Mop forwards those exact files to
Scruffy's validator and does not infer a baseline from filenames or copy the
schema. Missing or mismatched baseline artifacts are a hard stop.

## 1. Ingest and validate (fail closed)

```sh
python3 scripts/mop_bundle.py check <bundle-dir> [--baseline-bundle <prior-bundle-dir>]
```

This validates every artifact's `schema_version` against the versions Scruffy's
Mop understands and reports the gate. If it prints `REFUSED`, stop and disclose
the gap — never hand-edit the bundle to make it parse.

## 2. Confirm authority and approval

- **Authority.** Writes are allowed only under Scruffy's `redesign`/`design` mode
  with `source_write`, or an explicit user grant. `check` prints `authority:
  BLOCKED` with reasons when it is not satisfied. If the user is authorizing the
  work now, pass `--authorized` to represent that grant; otherwise you may only
  produce an advisory plan, not edits.
- **Approval.** Only items whose `decisions.json` value is `approve` are actioned.
  Deferred and rejected items are never implemented, even if they look easy.

When using `mop-dashboard.html`, set decisions and design directions. **Approve
all pending** is a safe bulk action: it leaves explicit defer and reject choices
unchanged and never includes a fixed, cleared, merged, or superseded item.
Terminal items and their prior decisions remain visible and exportable as
read-only history; completed direction groups are not offered again. Then use
**Copy AI handoff** in the sticky decision bar or after the final finding and
paste the generated message into the AI task. It contains exact fenced JSON for
`decisions.json` and, when active directions exist, `directions.json`.
Individual JSON downloads remain available as a fallback.

## 3. Build the plan

```sh
python3 scripts/mop_bundle.py plan <bundle-dir> [--baseline-bundle <prior-bundle-dir>] [--authorized] [--json]
```

The plan orders approved items by Scruffy's explicit `work_orders` when present,
otherwise synthesizes the order: dependencies first, then by lane
(structural → routing/data/state → semantics/interaction → visual/responsive →
page cleanup → verification), then by severity. Read the warnings — a warning
that an approved item depends on a non-approved one means you may be about to fix
a symptom whose cause is still deferred; raise it with the user before proceeding.

## 4. Implement, in order, to the craft bar

Work the steps top to bottom. For each item:

1. Read its registry entry in full: `observation`, `cause`, `user_impact`,
   `recommendation`, `acceptance_checks`, and any attached token change.
2. Open [`fix-protocols.md`](fix-protocols.md) at the item's `category` and follow
   that protocol.
3. Hold the change to [`craft-bar.md`](craft-bar.md). The bar is the difference
   between clearing a finding and camouflaging it.
4. Make the **smallest coherent** change that satisfies the acceptance checks and
   preserves everything in `product_frame` and outside the approved scope.

Never widen scope past the approved items. If implementing one correctly requires
a change Scruffy did not find, record it for a follow-up audit rather than
silently doing it.

## 5. Self-check and hand back

Before declaring anything done, run each acceptance check yourself
([`verification.md`](verification.md)). Then build the re-audit handoff:

```sh
python3 scripts/mop_handoff.py <bundle-dir> [--baseline-bundle <prior-bundle-dir>] --work work.json --authorized
```

The handoff maps each item to the surfaces you changed and your self-assessment.
It marks every item `implemented-pending-reaudit` — **never** `fixed` or
`cleared`. Only a Scruffy re-audit of a new revision clears a finding. Return the
handoff and the changed surfaces; recommend the re-audit.

## The one rule that governs all of this

Scruffy audits, decides, implements, and re-audits. If a repair step would
have you produce a finding, choose an approval, invent a severity, or mark your
own work cleared, you have crossed the line — stop and hand back instead.
