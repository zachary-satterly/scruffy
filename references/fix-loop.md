# Act on decisions

An audit that ends at an approval is half a loop. This file owns the other
half: what an agent does when a human has already approved items, and what
counts as proof that the approved change worked. Read it whenever a
`decisions.json` is in scope.

## Trigger

Act on decisions only when both of these hold:

1. A `decisions.json` is present for the current bundle, or the user pasted a
   handoff block that contains one.
2. The run mode is `redesign` or `design` with source-write authority recorded
   in the run receipt, **or** the user explicitly says to implement the approved
   items.

Otherwise report the approve count and stop. An approval is a product decision,
not write authority; the fail-closed rule in
[audit-contract.md](audit-contract.md) still governs. Never infer authority from
the existence of approvals.

## Scope

- Implement only items whose `decision` is `approve` **and** whose `status` is
  `open` or `needs-verification`.
- `defer`, `reject`, and `pending` items are untouchable. Do not implement them,
  and do not re-decide them on the user's behalf.
- Do not modify any item's `status` in the current revision. Status is a
  reconciliation judgment made at the next revision (see
  [durability.md](durability.md)).
- Preserve the product's real identity and content. An approval to fix a
  specific finding is not licence to restyle the surrounding interface.

## Per item

For each approved item:

1. Apply `fix_packet.change` to `fix_packet.target`.
2. If the item has no `fix_packet`, author one first — `target`, `change`,
   `effort`, `rollback`, and executable `acceptance` checks — and record in the
   run notes that it was authored after approval rather than at audit time. A
   packet written after the fact is weaker evidence of intent than one the
   auditor wrote; say so rather than hiding it.
3. Keep the change reversible in the way `rollback` describes.

## Verify

After implementation, run:

```sh
python3 scripts/verify_fixes.py findings.json \
  --decisions decisions.json \
  --execute \
  --cwd <target repo root> \
  --output verification.json
```

Before any command or receipt write, the verifier validates the registry and
its decisions together. Audit and revision identifiers must match; duplicate or
orphan approvals and malformed packets are refused. `--include-pending` is a
preview option and cannot be combined with `--execute`.

`command` checks execute through the local shell only with `--execute`. Review
the command text and target working directory before execution; this runner is
not a sandbox. A command timeout must be a positive integer in seconds, an
expected exit code must be an integer, and an expected output substring must
be a string. For `dom_state` and `measurement` checks the
agent can run in a browser, supply the outcomes with `--results` (a JSON object
keyed `"ITEM-ID:index"`). `manual` checks never pass automatically and stay
visibly second-class.

Write `verification.json` into the bundle directory, next to `findings.json`.
It is the required artifact of an implementation run: an implementation with no
`verification.json` is an unproven claim, not a fix.

## Hand-off to re-audit

`verify_fixes.py` never edits the registry, by design. The next revision is
where status changes: it loads this revision as its baseline, re-operates the
interface, and only then may mark an item `fixed`. When the prior item carried a
`fix_packet`, that `fixed` disposition needs `verification.json` evidence —
`validate_audit.py --baseline <prior> --verification verification.json`
enforces it. The receipt's audit and revision identifiers must match the
baseline that promised the checks. Each fixed item needs one approved result
with every promised check, in order and with its original kind. Executable
checks must pass; manual checks remain manual and require re-audit judgment.
Free-text overrides and evidence-ID prefixes cannot bypass this check.

## Repair stage

When the bundle contains design work groups, the repair stage in `mop/`
(`python3 mop/scripts/mop_run.py <bundle> --authorized --out <dir>`) produces
directions and a handoff; this protocol applies after a direction is chosen.
