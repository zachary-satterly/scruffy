# Evaluation smoke fixtures

Generic fixtures for the development smoke harness
(`scripts/run_evaluation_smoke.py`, asserted by `scripts/test_evaluation_smoke.py`
and discovered automatically by `scripts/check.py`). These check **harness
integrity** — that the existing evaluation and verification code paths still
discriminate a real defect from a lookalike and cannot falsely close a repair.
They are not a benchmark, not proof of audit accuracy, and never run blind.

## Detection fixtures (workflows 1 and 2)

Both pages are fed to the real deterministic engine `rule_engine.evaluate_page`
with the baseline rule packs.

| File | Role | Real behavior |
|---|---|---|
| `defect-page.html` | Clear defects with reproducible evidence | Raises leads including missing `alt`, empty control, missing `lang`, unlabeled input, and a multi-view group with no address |
| `clean-control.html` | Adjacent legitimate patterns | Raises **zero** leads: the same affordances with every false-positive guard satisfied (labeled input, named icon button, decorative `alt=""`, sized images, viewport meta, a view group whose script writes `location.hash`) |

Leads are suspicions, not findings. The workflow proves the engine tells a
planted defect from a lookalike control, not that the audit is complete.

## Repair fixtures (workflow 3)

The repair workflow reuses `evals/continuity/` (registry and decisions) and
`evals/durability/` (fixed-transition closure gate). It writes four in-memory
`router.py` variants of one finding — "lesson state is not addressable" — into a
temp directory and runs the real verifier `scripts/verify_fixes.py`:

- original broken behavior → `failed`
- authorized valid repair → `verified`
- plausible wrong repair (regresses the `home` default route) → `failed`, caught
  by the neighboring-invariant acceptance check
- alternative valid implementation → `verified`

Each verifier invocation runs in its own isolated temp directory with a bounded
timeout, and the harness cross-checks the process exit code against the receipt
result: a timeout, an out-of-contract exit, or a missing, malformed, or stale
receipt is surfaced as an infrastructure failure, never accepted as a pass.

The acceptance oracle checks the two declared inputs only — `lesson-3` gains a
shareable address and the `home` default is preserved. It makes no claim that
the valid and alternative implementations behave equivalently across all page
strings; they deliberately differ on other inputs.

It then confirms a skipped command check (no `--execute`) reports `not_run`, a
manual check reports `manual`, and `validate_audit.validate_fix_verification`
refuses to mark an item `fixed` when a promised check was skipped or failed.

## Limitations

Deterministic static leads and executable command checks only. No live browser,
screenshot, DOM, contrast, or performance runtime is exercised, no browser or
specialist receipt is authored, and the run is not blind. Editing a detection
fixture can change which leads fire; re-run `python3 scripts/run_evaluation_smoke.py`
and update `EXPECTED_DEFECT_LEADS` in the harness if the intended defects change.
