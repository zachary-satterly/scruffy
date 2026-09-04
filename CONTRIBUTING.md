# Contributing

Scruffy is evidence-first. Contributions should make the method more accurate, portable, or falsifiable—not merely add more disliked styles to a blacklist.

## Before opening a change

Read `AGENTS.md` for the canonical project map, generated-file routes, and the
boundary between maintainer sessions and clean-room blind tests. Claude imports
the same contract through `CLAUDE.md`; there is no second maintenance method.

1. Decide whether the change belongs in runtime instructions, a progressive-disclosure reference, the research corpus, a script, or an evaluation fixture.
2. Preserve agent, vendor, framework, browser, and operating-system neutrality in `SKILL.md` and `references/`.
3. Separate an observable predicate from personal taste. A new negative rule needs user/task impact, a way to verify it, and a false-positive guard.
4. Keep research provenance intact. Distill and attribute sources; do not reproduce transcripts or copyrighted source text.

## Research contributions

**Using scruffy does not require the corpus.** Transcripts are build-time input,
not a runtime dependency: the plugin ships the distilled, cited principles and
the baseline rule packs. Nobody needs to fetch ~50 videos to run an audit.

Pick the right lane before opening anything:

| Lane | Use when | Transcripts | Review |
|---|---|---|---|
| **User rule pack** | You want your own rules, house style, or a principle from a source you found | Yours, local, never committed | none — see `references/rule-packs.md` |
| **Corpus principle** | The rule should hold for every scruffy user | Required, gated | PR + admission gates |

Most contributions belong in the first lane. Set `origin: "user"`, fill
`source_attribution`, and run `python3 scripts/rule_engine.py --check`.

### Corpus contributions

Use `scripts/intake.py --no-frames <video-url>` to collect caption working material. Full-channel ingestion requires an explicit `--channel <channel-url>`; help or missing inputs never start downloads. `transcripts/` and `frames/` are intentionally ignored and must not be committed.

For a durable principle:

1. Register the source in `principles/SOURCES.md` **and add a row to `principles/SOURCE_LEDGER.md`.** The ledger is the committed record that survives the ignored transcript folder; `scripts/validate_sources.py` fails the build when a row is `ingested` but produced no cited rule.
2. Add the distilled rule to a numbered section in `principles/PRINCIPLES.md` with the repository’s citation format.
3. Include what would disprove or limit the rule.
4. Reconcile `SKILL.md` or `references/` only when the operational method must change.
5. Run both validators.

Promotional tool demonstrations, trend galleries, and uncited aesthetic claims may inform a hypothesis but are not sufficient foundations for a general rule.

## Runtime changes

- Keep `SKILL.md` below 500 lines and the repository’s conservative 4,000-word proxy.
- Put detailed protocols in one-level `references/` files and link them directly from `SKILL.md`.
- Do not require a named agent, browser driver, framework, package manager, OS path, or proprietary service.
- Capability-dependent steps need an explicit fallback and a **not run** state.
- Never make HTML output, screenshots, source access, or implementation access prerequisites for a valid static audit.
- Do not weaken the privacy boundary around passwords, cookies, tokens, or browser-storage contents.
- Keep the taxonomy DRY. Edit category/layer/facet definitions only in `schema/taxonomy.json`, then run `python3 scripts/taxonomy_contract.py --write`; do not hand-edit the generated README block or `references/taxonomy.md`.
- Keep execution rules DRY. Edit modes, authority, capabilities, evidence kinds, and editorial receipt requirements only in `schema/audit-contract.json`, then run `python3 scripts/audit_contract.py --write`; do not hand-edit the generated modes block or `references/audit-contract.md`.
- Treat **Editorial slop** as the public category and `copy` as its compatibility key. Content strategy, claims/provenance, microcopy, voice, and sentence construction are review types, not new top-level categories.
- Keep Claude distribution DRY. Root `SKILL.md` is canonical; regenerate `skills/scruffy/SKILL.md` with `python3 scripts/claude_adapter.py --write` after changing frontmatter. Never add runtime rules to the adapter.

## Evaluation fixtures

Update `evals/triggers.json` when the skill description changes. Positive cases should cover natural-language requests and explicit invocation. Negative cases should protect against security-only, backend-only, image-generation, and unrelated research tasks.

Changes to application coverage must update `references/archetypes.md` and `evals/archetypes.json`. Every archetype needs concrete task probes; a named category without observable probes is not coverage.

Changes to sentence-copy detection must update `references/sentence-slop.md`, `evals/sentence-slop/cases.json`, and the sentence regression suite. No fixture may use or expect an authorship label. Add a false-positive case for every new signal or threshold. English analysis must declare `en`; non-English and unknown-language input must exercise the abstention path unless a language-competent human review is recorded.

Changes to any editorial review path must also update the canonical audit contract and `scripts/test_audit_contract.py`. An active editorial finding needs typed evidence, a demonstrated consequence, a tested counterexample, and the applicable manual-review receipt; sentence patterns additionally require an adequate or limited sample and two independent signal families.

Changes to blind-audit behavior must preserve quarantine before discovery, temporary candidate IDs, digest freeze before reveal, and contamination rejection. Never place a live blind test's evaluation key in an agent-readable packet.

Changes to findings, decisions, reporting, or repeat-audit behavior must preserve these invariants:

- An existing ID keeps the same `identity_key` and `first_seen_revision`.
- Every baseline item receives an explicit revision disposition.
- A resolved item can become active only as `reopened`.
- Merged and superseded items retain their original records and point to a destination.
- Non-pending decisions and their history survive migration unless a user explicitly changes them.
- Presentation limits never remove entries from the registry, HTML, or Markdown report.

## Validation

```sh
python3 scripts/check.py
```

This runs the package validators and every `test_*.py` script in `scripts/`
and `mop/scripts/`, including newly added regression suites. Use
`python3 scripts/check.py --list` to inspect the exact checks.

When editing registry tooling, also prove the expected failure. The durability suite includes invalid fixtures for silent omission and ID reuse; add another invalid fixture when introducing a new invariant.

For a behavioral change, also run the skill against a real or reproducible interface and record:

- Capabilities available and checks not run
- Representative tasks
- Verified findings and cleared suspicions
- Severity and confidence
- Regressions after any implementation

## Pull requests

Describe the failure class, evidence, false-positive guard, files changed, and validation performed. Do not include generated transcripts, browser secrets, private application data, or claims that were not reproduced.
