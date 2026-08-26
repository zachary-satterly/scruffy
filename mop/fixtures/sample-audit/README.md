# Sample Scruffy audit bundle

A small, schema-faithful Scruffy audit output used to test and demonstrate
Scruffy's repair workflow. It is **input**, not a Scruffy product claim.

- `findings.json` — registry 2.1, six items across `backend_shape`,
  `accessibility`, `interaction`, `copy`, and `visual`, with `depends_on` edges
  (`AS-02` and `AS-05` depend on the structural blocker `AS-04`).
- `context.json` — schema 1.2 baseline (`revision_id: r1`), product frame, one
  failed task, applicability and durable routing ledgers, capability ledger
  (`source_write: available`, mode `redesign`), scores, and empty `work_orders`
  so the ordering is synthesized. The repeat-audit regression derives a valid
  r2 current bundle from this fixture and supplies this directory through
  `--baseline-bundle`, proving canonical r2/r1 continuity without a second
  hand-maintained schema copy.
- `decisions.json` — schema 2.1. Approved: `AS-04`, `AS-02`, `AS-05`, `AS-01`.
  Deferred: `AS-03`. Rejected: `AS-06`.
- `tokens.json` — schema 1.0, one contrast correction tied to `AS-02`.

Expected synthesized order of approved items: **AS-04 → AS-02 → AS-05 → AS-01**
(structural blocker first; then lane-3 items by severity; then the copy cleanup).
