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
  --cwd . \
  --output verification.json
```

Before any command or receipt write, the verifier validates the registry and
its decisions together. Audit and revision identifiers must match; duplicate or
orphan approvals and malformed packets are refused. `--include-pending` is a
preview option and cannot be combined with `--execute`.

`command` checks run only with `--execute`. Write them as `argv` arrays:

```json
{"kind": "command", "argv": ["pytest", "-q", "tests/test_router.py"],
 "summary": "routing tests pass"}
```

An `argv` check runs with no shell, so quoting, globs, pipes, and `$(...)` are
literal arguments. Only the program name must be non-empty; empty string
arguments after it are passed through. The legacy readable form —
`"run": "pytest -q tests/test_router.py"` — still validates and still renders,
but it needs a shell, so it executes only with `--execute` **and**
`--allow-shell`. Without that opt-in it is recorded `not_run`, never passed. No
field inside a packet can grant shell access; the person running the verifier
grants it, having read the bundle.

**This is not a sandbox and not a network boundary.** Both forms run trusted
local code with your privileges. Read the commands and the target directory
first. What the runner does bound is:

- **Time.** `--max-seconds` is a caller ceiling that caps any packet timeout. A
  timed-out check fails; on POSIX its whole process group is terminated and
  then killed, including children.
- **Output.** `--max-output-bytes` is applied while reading, so a check that
  floods stdout cannot exhaust memory. Truncation is recorded, and an expected
  substring that falls past the cap fails rather than passing unread.
- **Environment.** Checks get a small documented environment, not your ambient
  one. Use `--env-allow NAME` to pass a specific variable through.
- **Artifacts.** Inputs and the receipt must resolve inside `--artifact-root`
  (default: the registry's directory), so no symlink writes the receipt
  somewhere nobody is looking. `--cwd` is the target and is deliberately not
  confined.

A command timeout must be a positive integer in seconds, an expected exit code
must be an integer, and an expected output substring must be a string. For
`dom_state` and `measurement` checks the agent can run in a browser, supply the
outcomes with `--results` (a JSON object keyed `"ITEM-ID:index"`); they are
recorded `provenance: imported`, because this run did not observe them.
`manual` checks never pass automatically and stay visibly second-class.

## What the receipt proves

New receipts carry an `observation_manifest` (see
[audit-contract.md](audit-contract.md)) binding results to one run: a unique
`run_id`, digests of every input document, the target's identity before and
after execution, a digest of the promised checks, and counts of collected
versus imported results. Validation refuses an unknown manifest version, a
malformed field, an input digest that no longer reproduces, or replaced
promised checks.

Content reads have a per-file size bound. Git metadata collection currently has
a timeout but no output-size cap; a repository with an unusually large number
of changed paths can still use substantial memory during fingerprinting.

Two consequences worth knowing:

- If a check changes the target while the run executes, no item in that run can
  be `verified`. Check-level results are kept; the item-level claim is
  withdrawn. Name generated state with `--target-ignore GLOB` when a change is
  expected.
- Freshness is a separate, explicit question. Document validation cannot know
  whether the target still matches. Ask it directly:

  ```sh
  python3 scripts/observation_manifest.py verification.json \
    --registry findings.json --cwd .
  ```

Use the actual target directory for `--cwd`; `.` means the current directory.
The default child environment carries `PATH`, `HOME`, `LANG`, `LC_ALL`, `TZ`,
`TMPDIR`, `SYSTEMROOT`, `COMSPEC`, `PATHEXT`, and `USERPROFILE` when present,
plus the runner's `SCRUFFY_VERIFICATION` marker. Other variables require
`--env-allow NAME`.

Raw stdout, stderr, and command text never enter new receipts. Author-written
summaries, titles, and imported details are copied through without secret
redaction, so review them before sharing a report.

Once preflight passes, the run takes the output path immediately: it writes a
`run_state: started` receipt before the first check. If the run is interrupted,
that started receipt is what remains — an incomplete run with its own `run_id`
and no results — rather than the previous run's `verified` bytes. A completed
run replaces it with `run_state: complete`. A run refused during preflight
writes nothing and leaves the historical receipt untouched.

Receipts written before this contract have no manifest. They remain valid and
are not rewritten, but their provenance is weaker by construction: they cannot
prove which run, inputs, or target produced them. Treat an unmanifested receipt
as a claim about a run you cannot reconstruct.

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
