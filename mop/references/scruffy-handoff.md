# Scruffy audit → repair handoff

Scruffy's repair stage is the consumer side of Scruffy's output contract. Scruffy owns every
schema named here; the canonical definitions live in
`../scruffy/references/output-schema.md` and
`../scruffy/schema/audit-contract.json`. The repair stage reads them and never redefines
them. The machine-readable compatibility key is [`../schema/interop.json`](../schema/interop.json).

## The loop

```
Scruffy AUDIT ─► findings.json + context.json + decisions.json (+ tokens.json)
                        │
                        ▼
        Scruffy implements approved work orders  ── (redesign/design authority, source_write)
                        │
                        ▼
Scruffy RE-AUDIT (new revision) ─► items move open → fixed / cleared on real evidence
```

The repair stage occupies the middle box only. It does not diagnose, decide, or clear.

## What Scruffy repair reads

| Artifact | Schema | Scruffy uses it for during repair |
|---|---|---|
| `findings.json` | registry 2.1 (2.0 read-only) | The immutable item registry: `recommendation`, `acceptance_checks`, `depends_on`, `category`, `severity`, `evidence_refs`. IDs and identity keys are never reassigned. |
| `context.json` | 1.2 (1.0 and 1.1 read-only) | `work_orders` (dependency order to implement in), `product_frame` (product truth to preserve), `tasks`, `scores`, `evidence_assets`, `checks_not_run`, plus routing, assumptions, and specialist referrals that constrain the repair boundary. |
| `decisions.json` | 2.1 | The approval gate. Scruffy implements **only** items whose `decision` is `approve`. |
| `tokens.json` | 1.0 (optional) | Observed-value token corrections to apply, mapped to `finding_ids`. |

For current context schema 1.2, version acceptance is not enough. Bundle loading invokes Scruffy's canonical `scripts/validate_audit.py` against the exact findings, context, and decisions artifacts before Mop plans work. When `baseline_revision_id` is non-null, the operator must also pass `--baseline-bundle <prior-bundle-dir>`; Mop forwards that bundle's exact `findings.json` and `context.json` as the canonical baseline pair. There is no implicit directory guess and no Mop-owned continuity schema. If the validator, baseline pair, or continuity check is unavailable or invalid, Mop stops. Legacy context schemas remain readable under the compatibility note and never acquire current-schema claims.

## Gates Scruffy repair must honor

1. **Mode + authority.** Write source only under Scruffy's `redesign` or `design`
   mode with `source_write` capability. Fail closed otherwise. An audit or a
   dashboard decision alone is not source-edit authorization.
2. **Approval.** Only `approve`d decisions are actioned. `pending`, `defer`, and
   `reject` are never implemented. A fixed, cleared, merged, or superseded item
   is terminal regardless of its preserved prior decision: show it as history,
   never as an approval or design-direction control.
3. **Dependency order.** Follow Scruffy's work-order order: structural blockers →
   routing/data/state → semantic and interaction primitives → visual tokens and
   responsive composition → page cleanup → verification.
4. **Preserve product truth.** Everything in `product_frame` and outside the
   approved scope survives unchanged.
5. **Don't self-certify.** Repair never sets `status: fixed`/`cleared`. It reports
   changed surfaces mapped to registry IDs; Scruffy's re-audit clears them.
6. **Don't action referrals.** Routing and specialist referrals are context, not
   approved work. Implement them only if a later Scruffy registry item and user
   decision independently authorize that repair.

## Version handling

`schema/interop.json` pins the versions the repair stage understands. Legacy schemas are
readable but read-only. An unrecognized major schema is a hard stop: disclose the
gap and refuse rather than coerce it.
