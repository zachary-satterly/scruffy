# Scruffy maintainer contract

This repository is the standalone source project for Scruffy. It publishes one
runtime method through a Claude Code plugin, a Codex Agent Skill, and other
Agent Skills-compatible runtimes. This file governs work **on Scruffy itself**;
it is not a second copy of the audit method. Claude Code imports this contract
through root `CLAUDE.md`.

Canonical public repository: `https://github.com/zachary-satterly/scruffy`.
`ur-passwd-hash` is the former GitHub username; do not use it for current routing.

## Start here

1. Classify the request as `USE`, `MAINTAIN`, or `BLIND FORWARD TEST`.
2. Read root `SKILL.md` completely before changing runtime behavior.
3. Load only the references that `SKILL.md` routes for the work in scope.
4. Inspect the canonical source before editing a generated projection.
5. State available capabilities and checks that cannot be run. Never invent
   browser, screenshot, source, test, or deployment proof.

`USE` means run the current skill against a target. Do not modify Scruffy or the
target unless the user explicitly authorizes those changes.

`MAINTAIN` means change this repository to improve Scruffy. Preserve the public
method, compatibility keys, evidence threshold, false-positive guards, and
cross-agent portability unless the user explicitly changes the product contract.

`BLIND FORWARD TEST` means evaluate the published skill in a fresh session with
only the target, skill, neutral request, and isolated output directory available.
A maintainer session that has seen prior findings, expected answers, target-specific
diagnoses, or proposed fixes is not blind.

## Source-of-truth map

| Concern | Canonical source | Generated or runtime projection |
|---|---|---|
| Audit workflow and trigger | `SKILL.md` | `skills/scruffy/SKILL.md` discovery adapter |
| Layers, categories, facets, labels, proof rules | `schema/taxonomy.json` | `references/taxonomy.md` and the README taxonomy block |
| Modes, authority, capabilities, evidence, editorial receipts | `schema/audit-contract.json` | `references/audit-contract.md` and the README modes block |
| Detailed audit protocols | `references/*.md` | Loaded progressively from `SKILL.md` |
| Research-backed principles and provenance | `principles/PRINCIPLES.md`, `principles/SOURCES.md`, `principles/INSPIRATIONS.md` | Operational rules only after reconciliation into the runtime contract |
| Lead rules and packs | `schema/rules/*.json` | Rule-engine lead output |
| Deterministic behavior | `scripts/*.py` | Reports, dashboards, validation output, and generated adapters |
| Regression evidence | `evals/` and `scripts/test_*.py` | Test results; never product claims by themselves |
| Claude distribution | `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | Claude plugin cache after installation |
| Codex metadata | `agents/openai.yaml` | Codex skill discovery UI |

Root `SKILL.md` is the sole runtime instruction source. Never add audit rules to
`skills/scruffy/SKILL.md`; regenerate that adapter instead.

## DRY edit routes

- Change taxonomy only in `schema/taxonomy.json`, then run
  `python3 scripts/taxonomy_contract.py --write`.
- Change modes, authority, capabilities, evidence kinds, or editorial receipts
  only in `schema/audit-contract.json`, then run
  `python3 scripts/audit_contract.py --write`.
- Change lead rules only in `schema/rules/*.json`; validate with
  `python3 scripts/rule_engine.py --check` and keep every rule cited and guarded.
- After changing root skill frontmatter, run
  `python3 scripts/claude_adapter.py --write`.
- Do not hand-edit `references/taxonomy.md`, `references/audit-contract.md`,
  `skills/scruffy/SKILL.md`, or generated README blocks.
- Keep **Editorial slop** as the public label and `copy` as its durable key.
- Keep existing `anti-slop-*` report markers and storage keys readable.
- Never convert sentence signals into an AI-authorship score or verdict.

## Improvement protocol

1. Reproduce the failure from raw target evidence. A prior audit may motivate a
   change, but it is not automatically ground truth.
2. Identify the narrowest owner: runtime instruction, canonical schema,
   reference, deterministic script, evaluation fixture, or public documentation.
3. For behavior changes, add or update a regression case and an adjacent
   false-positive guard before weakening a threshold or broadening a rule.
4. Make the smallest canonical edit. Regenerate projections; do not patch them.
5. Run focused tests, then the full validation suite below.
6. For a meaningful behavior change, forward-test from a fresh neutral session.
   Give it the target and task, not the suspected bug, intended fix, expected
   finding, prior report, stable finding IDs, or hidden evaluation key.
7. Freeze blind discovery before revealing any baseline. If contamination is
   encountered, record it and restart; never relabel the run as blind.
8. Reconcile any new principle across source, runtime, evaluation, and docs once.

## Validation

Run the complete dependency-free suite before committing:

```sh
python3 scripts/validate_skill.py
python3 scripts/claude_adapter.py --check
python3 scripts/validate_corpus.py
python3 scripts/test_durability.py
python3 scripts/test_audit_contract.py
python3 scripts/test_sentence_slop.py
python3 scripts/test_blind_protocol.py
python3 scripts/test_blind_evaluator.py
python3 scripts/test_sentence_blind_runner.py
python3 scripts/test_web_fixtures.py
python3 scripts/rule_engine.py --check
python3 scripts/test_rule_engine.py
python3 scripts/test_product_surfaces.py
```

When Claude Code is installed, also run `claude plugin validate .`. If behavior
changed, record the fresh forward-test prompt, capabilities, raw artifacts,
result, and contamination status without adding target-specific answers to this
file or the skill.

Before any commit or push, verify:

```sh
git status --short
git remote -v
git branch --show-current
git config user.email
```

Do not commit transcripts, frames, browser secrets, private application data,
generated audit outputs, or target-specific expected findings.

## Repair compatibility runtime

`mop/` holds Scruffy's approved-repair runtime. It is not a separate product; it
is a **read-only consumer** of this repository's audit contract. It reads the output
schema and implements approved findings, and it never edits, forks, or extends
Scruffy's schema. Its maintainer contract is `mop/AGENTS.md`, its runtime is
`mop/SKILL.md`, and the consumer compatibility key is `mop/schema/interop.json`.

- Change Scruffy's output contract only here (in `references/`, `schema/`); the
  repair runtime follows. A handoff-driven schema change is proposed here, never made
  from `mop/`.
- The repair runtime keeps its own dependency-free suite; run it alongside this one:
  `python3 mop/scripts/test_mop.py` and `python3 mop/scripts/validate_skill.py`.

## Definition of done

A maintenance change is done only when its canonical owner is clear, generated
projections are current, relevant regressions and false-positive guards pass,
the full suite passes, unsupported verification is disclosed, public version
metadata and `CHANGELOG.md` agree when releasing, and a behavior claim is not
called blind unless a fresh isolated run proves it.
