# Durable audit revisions

Use this protocol for every substantial audit that creates files and every run with a prior report, registry, or decision export.

## Invariants

1. `audit_id` identifies the product/target and never changes across revisions.
2. `revision_id` identifies one run and is unique within the audit.
3. Each item has an immutable `id` and `identity_key`. Titles and wording may become more precise; identity may not move to another problem.
4. Every item from the baseline registry appears in the new registry.
5. Every baseline item receives exactly one revision disposition: `carried`, `reopened`, `fixed`, `cleared`, `merged`, or `superseded`.
6. `merged` and `superseded` require a valid `destination_id`. `fixed` and `cleared` require new evidence and a reason.
7. New items use disposition `new` and a previously unused ID and identity key.
8. The registry is complete. Presentation limits affect only shortlist arrays.
9. Decisions remain attached to the original item. A destination item never inherits approval automatically.
10. If a baseline cannot be read, stop revision reconciliation, label the run a provisional independent audit, and do not claim continuity.
11. Context 1.2 routing, assumption, and referral IDs remain attached to the same lane, proposition, or specialist question across revisions; never reuse them for a different concern.
12. Every canonical routing lane remains visible across revisions. Every ledger row records first-seen and last-observed revisions plus an explicit `new`, `carried`, or `updated` disposition and reason.
13. A context-1.2 revision names `baseline_revision_id` and supplies the prior `context.json` to validation. Missing baseline context blocks a continuity claim.
14. A completed specialist referral survives later revisions with its verified typed specialist-review receipt and claim boundary; a later run may update it, never erase it.
15. A non-interface stop-and-refer preserves the ledger without fabricating interface coverage: Scruffy is marked not applicable, no Scruffy-owned lane is selected, and no interface finding, work order, or score is emitted.

Do not renumber a legacy ID merely to normalize padding or prefixes. Preserve `ENH-1` if that is the published identity; use any preferred convention only for genuinely new IDs.

## Revision procedure

1. Discover prior artifacts by explicit path, matching `audit_id`, canonical target, and adjacent output directories.
2. Validate the baseline before relying on it.
3. Copy all baseline items into a draft revision before adding new observations.
4. Operate and measure the current interface without treating old findings as truth.
5. Reconcile each prior item:
   - `carried`: reproduced or still supported.
   - `reopened`: previously resolved, now reproduced again.
   - `fixed`: the defect no longer reproduces because the product changed.
   - `cleared`: the earlier interpretation was wrong or insufficiently supported.
   - `merged`: the item remains true but is represented by a broader surviving item.
   - `superseded`: a better formulation replaces the old item without claiming it was fixed.
6. Add genuinely new items with new IDs.
7. Reconcile decisions by ID. Preserve each prior decision and history entry. New and destination items start `pending` unless the user explicitly decides otherwise.
8. Validate registry continuity, decision coverage, presentation lists, and dashboard completeness.
9. Publish a reconciliation table showing every prior ID, new status, disposition reason, and destination when applicable.
10. Reconcile the context 1.2 routing, assumption, and referral ledgers against the baseline context. Preserve open, supported, and refuted assumptions; preserve completed referrals and their verified specialist-review receipts even when no new specialist work ran.
11. Run `validate_audit.py` with both `--baseline` and `--baseline-context`. Treat a missing baseline context, dropped ledger ID, reused identity, or inaccurate carried/updated disposition as a hard continuity failure.

## Registry contract

New audits use the current registry schema from [audit-contract.md](audit-contract.md) and the exact artifact shape in [output-schema.md](output-schema.md). This file owns revision invariants only; it does not duplicate category, evidence, mode, authority, or editorial-review definitions. Schema 2.0 registries remain readable as baselines, while new and revised output is emitted in schema 2.1.

Strengths use severity `none`, status `open`, and recommendations describing what to preserve. Enhancements use severity as priority (`low`, `medium`, or `high`) rather than defect impact.

## Decisions

Use the registry's schema version, the same `audit_id` and `revision_id`, and one record for every finding or enhancement. The current decision shape comes from [output-schema.md](output-schema.md); history remains append-only.

When migrating:

- Same ID: carry the decision and history.
- New ID: start `pending`.
- Merged/superseded source: preserve its decision on the source record; add `destination_id` for context.
- Destination: remain `pending` unless separately decided.
- Missing prior decision data: record `decision_source: "unavailable"`; do not invent a choice.
- Legacy decision exports without identity keys require the trusted prior registry. Never migrate them by ID alone; an intervening report may have reused an ID for another problem.

## Presentation and archive

Show at most eight prioritized findings and five prioritized enhancements in the executive section. Also render:

- Additional open and needs-verification items
- Fixed and cleared items with evidence
- Merged and superseded items with destinations
- All strengths
- A revision reconciliation table

Collapsed presentation is allowed; absent registry items are not.

## Validation

Run:

```text
python3 scripts/validate_audit.py findings.json --context context.json --baseline previous-findings.json --decisions decisions.json --dashboard audit-report.html --markdown audit-report.md
```

Treat any missing baseline ID, reused identity, invalid destination, orphan decision, absent dashboard item, or missing dashboard section as a hard failure.
