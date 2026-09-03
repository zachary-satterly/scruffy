<p align="center">
  <img src="assets/scruffy-hero.png" alt="Scruffy sweeping a field of cartoon nuts and bolts with a janitorial push broom" width="100%">
</p>

<h1 align="center">Scruffy</h1>

<p align="center"><strong>Find the AI slop. Prove it. Fix it.</strong></p>

<p align="center">
  <a href="https://github.com/zachary-satterly/scruffy/actions/workflows/validate.yml"><img src="https://github.com/zachary-satterly/scruffy/actions/workflows/validate.yml/badge.svg" alt="Validation"></a>
  <a href="evals/sentence-slop/readme-dogfood-2026-08-16.md"><img src="https://img.shields.io/badge/README-AI--slop%20reviewed-13543e" alt="README AI-slop reviewed"></a>
  <img src="https://img.shields.io/badge/Agent%20Skills-compatible-13543e" alt="Agent Skills compatible">
  <img src="https://img.shields.io/badge/Codex%20%2B%20Claude-compatible-c69b3f" alt="Codex and Claude compatible">
  <img src="https://img.shields.io/badge/license-MIT-7a4f8f" alt="MIT license">
</p>

<p align="center"><sub>One tool from evidence through verified repair.</sub></p>

**Scruffy finds AI slop in web apps—and shows its work.** Give Claude or Codex a URL, screenshot, prototype, or source repository. Scruffy operates the real interface, inspects the available code and copy, captures evidence, and returns a prioritized report with practical fixes.

**What “AI slop” means here:** low-quality app output that looks finished because the generator, template, or builder supplied a plausible surface while important product decisions were skipped. Scruffy checks eight evidence categories, including first-class Editorial slop across content strategy, microcopy, claims, provenance, voice, and sentence construction.

**What it does not mean:** Scruffy does not guess whether AI wrote the app. It judges the result, not the author. The same failures can appear in hand-written, template-derived, outsourced, and AI-generated work.

## One Scruffy, one evidence loop

Scruffy has one name and one job: inspect a real product, explain what is wrong,
repair only approved work, and verify the result. References, principles,
detectors, audit reports, direction choices, implementation, and re-audit are
stages of that workflow—not separately branded tools.

| Stage | What Scruffy does | Boundary |
|---|---|---|
| **Frame** | Records the product, audience, task, constraints, and evidence capability. | Missing evidence is disclosed, never invented. |
| **Ground** | Uses the governed [principle corpus](principles/PRINCIPLES.md), user taste evidence, and optional references such as Mobbin. | A popular pattern or creator opinion is evidence to test, not an automatic rule. |
| **Audit** | Operates representative tasks, challenges suspicions, and publishes findings, cleared suspicions, and optional enhancements. | Leads do not become findings without evidence and a demonstrated consequence. |
| **Repair** | Implements only human-approved work under explicit write authority, with visual direction choices when needed. | An audit decision alone does not grant repository write authority. |
| **Verify** | Re-runs acceptance checks and reconciles every stable finding ID. | Scruffy never marks a repair fixed merely because code changed. |

The product theme and naming boundary are defined in [`assets/BRAND.md`](assets/BRAND.md).

### This README is part of the product

The README is written for people evaluating, installing, or maintaining Scruffy. Its **AI-slop reviewed** badge links to a hash-bound dogfood receipt. The review combines normalized sentence measurements with manual checks for coherence, specificity, information sequence, claims, recovery, and voice. It evaluates the writing and makes no claim about who or what authored it.

## What you get

- A product frame before anyone starts arguing about border radii
- Live task walkthroughs instead of screenshot astrology
- Findings with evidence, user impact, confidence, falsification attempts, and acceptance checks
- Cleared suspicions published beside confirmed defects
- Editorial review that covers content strategy, claims, provenance, voice, microcopy, and sentence construction while returning **no authorship score**
- Stable finding IDs that cannot quietly disappear in a repeat audit
- Complete JSON, Markdown, and self-contained decision-dashboard outputs
- Dependency-ordered work orders when implementation is authorized

## Sixty-second start — Claude Code

Inside Claude Code, add this repository as a marketplace and install Scruffy:

```text
/plugin marketplace add zachary-satterly/scruffy
```

```text
/plugin install scruffy@scruffy-marketplace
```

Then run the stable, namespaced plugin command:

```text
/scruffy:scruffy audit https://example.com end to end. Operate the real tasks, capture desktop and mobile evidence, challenge every suspicion, and show me the cleared ones too.
```

### Codex quick start

```sh
git clone https://github.com/zachary-satterly/scruffy.git
mkdir -p ~/.agents/skills
ln -s "$(pwd)/scruffy" ~/.agents/skills/scruffy
```

```text
$scruffy audit https://example.com end to end. Operate the real tasks, capture desktop and mobile evidence, test editorial quality without guessing authorship, publish the full findings registry, and generate the decision dashboard.
```

The method is deliberately evidence-first. It operates representative tasks, challenges its own suspicions, distinguishes defects from enhancements, and publishes cleared suspicions alongside findings. Repeated audits use an immutable registry: every earlier item must be carried, reopened, fixed, cleared, merged, or superseded. A shortlist may change; the historical record cannot silently shrink.

Most users can stop after the quick start. The rest of this README explains the method, installation variants, evidence contracts, and maintainer workflow.

<!-- scruffy-taxonomy:start -->
## The eight slop categories

Scruffy uses four inspection layers to produce findings in eight canonical categories. The layers control review order; the categories classify evidence. Cross-cutting facets prevent category sprawl.

| Category | Durable key | Plain meaning | What turns a suspicion into a finding |
|---|---|---|---|
| **Product slop** | `product` | The app has no clear user, job, outcome, differentiator, or reason to return. | A missing or contradictory product decision blocks understanding, trust, or task success. |
| **Information-architecture slop** | `information_architecture` | People cannot find, understand, address, retrieve, or share the information or state they need. | Navigation, labeling, hierarchy, retrieval, URL, or state evidence shows a realistic task becoming materially harder. |
| **Interaction slop** | `interaction` | Controls, state, feedback, and recovery do not behave as promised. | Operating the real task exposes a wrong action, dead end, lost state, unusable path, or misleading transition. |
| **Accessibility slop** | `accessibility` | Semantics, focus, state, contrast, alternatives, or reflow excludes people from the task. | A named accessibility requirement or functional interaction contract fails with reproducible evidence. |
| **Visual slop** | `visual` | Plausible decoration and interchangeable composition replace hierarchy, information, and product identity. | Rendered evidence shows scanning friction, weakened task priority, lost product character, or misleading visual state. |
| **Editorial slop** | `copy` | Words, claims, labels, information sequence, voice, or provenance are vague, repetitive, incoherent, unsupported, or useless at the moment of action. | Quoted reader-facing material plus surface or task context demonstrates a comprehension, choice, trust, recovery, differentiation, provenance, or voice consequence; sentence-pattern findings also require the sentence-review contract. |
| **Structure slop** | `backend_shape` | Routes, data, state, content, or components are shaped so badly that several features fail together. | Source and runtime evidence connect multiple symptoms or unsafe change cost to one shared implementation cause. |
| **Performance slop** | `performance` | Loading and interaction are slow, unstable, wasteful, or dishonest about waiting. | A runtime trace or repeatable measurement connects delay, instability, or waste to user-visible harm. |

### Product slop

The surface never establishes who it serves, what job it performs, or what success looks like. Common signals include features copied from adjacent products, unshareable multi-state experiences, absent return value, and dead-end terminal states.

### Information-architecture slop

Navigation may expose the wrong structure, labels may conceal the reader's vocabulary, or meaningful application states may have no stable address. Information architecture is separate from backend shape: a poor route or content model can create both, but the user-facing retrieval failure remains independently visible.

### Interaction slop

A contents button opens an unwieldy chip strip, a filter sorts instead of filtering, a media action gives no state feedback, or a visual application has no workable keyboard path. These defects require operation of the interface, not inference from appearance.

### Accessibility slop

Missing landmarks, unnamed controls, invisible focus, low contrast, unannounced state changes, absent alternatives, and layouts that fail under zoom are functional defects. Scruffy identifies specific barriers; it does not claim full conformance from a sample.

### Visual slop

Card soup, excessive type roles, decorative badges, arbitrary gradients, identical radii everywhere, synthetic proof, and interchangeable hero composition are candidate signals. They become findings only when rendered evidence shows weak hierarchy, task friction, misinformation, or lost identity.

### Editorial slop

Editorial review covers content strategy, terminology, microcopy, sentence and passage construction, conceptual coherence, claim support, provenance, information sequence, recovery language, and voice. Scruffy first verifies what readers actually see. Automated sentence signals remain leads; a human must test meaning, purpose, portability, voice, and consequences. Scruffy never classifies authorship.

### Structure slop

Content may be fused to rendering, navigation state may have no address, styles may be copied instead of tokenized, or failures may disappear into empty exception handlers. When several visible problems share one verified structural cause, record that cause once and link its dependent symptoms.

### Performance slop

Slow interaction, unstable layout, delayed primary content, blocking third parties, or dishonest wait states count only when measured at runtime. Source size alone can justify an investigation, not a performance finding.

### Cross-cutting facets

Apply these only where the product exposes the concern: **Trust and content integrity**, **Resilience and recovery**, **Localization and adaptability**, **Agent and AI behavior**, **Privacy and safety UX**, **Input and reference-data fidelity**. They refine a category; they do not replace it.
<!-- scruffy-taxonomy:end -->

## Why the method is harder to fool

- Product framing precedes visual critique.
- A capability preflight prevents unsupported claims when source, browser, screenshots, traces, or write access are absent.
- Representative task walkthroughs replace screenshot-only judgment.
- Findings require evidence and a falsification attempt.
- Blind audits quarantine prior reports and expected answers, freeze discovery by hash, and reveal the baseline only during reconciliation.
- Editorial findings require typed evidence and a demonstrated consequence; sentence-pattern findings additionally require adequate samples, multiple independent signals, and manual semantic review.
- Category evidence gates are machine-enforced. An active performance finding needs runtime evidence, accessibility a receipt plus a named criterion, visual a rendered receipt, and interaction an operation receipt. Critical severity demands high confidence and two receipts. `user_impact` has a concrete-consequence floor.
- Sentence lexicons live in a data-driven pack registry (`--list-packs` / `--disable-pack`), parity-checked against a cited signal manifest. Disabling a pack is disclosed in every result.
- Findings can carry `principle_refs`, which identify the sourced rule that fired. `detector_refs` identify the pack or target gate that raised the lead. A judgement traces Source → Rule → Detector pack → Signal → Finding.
- Stable IDs and identity keys prevent a later report from reusing or dropping earlier findings.
- Application-archetype probes adapt the task walkthrough to courses, SaaS tools, transactions, forms, analytics, collaboration, editors, marketing sites, and hybrids.
- Structural blockers are fixed before cosmetic symptoms.
- Severity, confidence, and category scores use a calibrated rubric.
- Retractions receive the same prominence as findings.
- An interactive decision report is supported, but Markdown and JSON fallbacks keep the skill portable.

## Reference grounding

When live search is available, Scruffy grounds structural choices in relevant
shipped-product references before exploring or judging a direction. It extracts
named patterns and citations, not pixels to copy, and applies only principles
that survive the corpus admission and false-positive checks.

Mobbin MCP is the current reference connector, but any equivalent design-reference search satisfies the capability. The connector is optional and external to the Scruffy package. Its absence is disclosed and never treated as a defect. Live references sit below the user's verdicts, supplied constraints, and taste evidence. Popularity establishes convention, not quality. The complete query, precedence, citation, and false-positive rules live in [`references/reference-grounding.md`](references/reference-grounding.md).

Mobbin MCP requires a paid Mobbin plan, enforced during OAuth. Claude users can
connect it through the [Mobbin directory connector](https://claude.ai/directory/connectors/mobbin),
or register the HTTP endpoint for a user-scoped CLI session:

```sh
claude mcp add mobbin --scope user --transport http https://api.mobbin.com/mcp
```

<!-- scruffy-modes:start -->
## Modes

| Mode | Use it for | Repository authority |
|---|---|---|
| **AUDIT** | Inspect and report on an existing target without changing its source. | Repository writes forbidden |
| **REDESIGN** | Audit, establish a coherent direction, implement authorized source changes, and verify them. | Explicit source-write authority required |
| **DESIGN** | Create an authorized new interface after establishing the product frame and exploring structural directions. | Explicit source-write authority required |
| **DEMONSTRATE-FIX** | Demonstrate reversible live-page changes without representing them as repository changes. | Repository writes forbidden |

New schema-2.1 reports record requested mode, effective mode, selection basis, explicit-request write authority, performed mutations, live demonstrations, and blind status. Validation fails closed when those facts conflict.
<!-- scruffy-modes:end -->

## Install

This repository follows the [Agent Skills specification](https://agentskills.io/specification). Clone or copy it so the installed skill directory is named `scruffy`.

### Claude Code — priority path

The repository is both a Claude Code plugin and a one-plugin marketplace. Install it from inside Claude Code:

```text
/plugin marketplace add zachary-satterly/scruffy
```

```text
/plugin install scruffy@scruffy-marketplace
```

Invoke the installed plugin explicitly:

```text
/scruffy:scruffy audit https://example.com and prioritize the structural fixes
```

The equivalent shell commands are:

```sh
claude plugin marketplace add zachary-satterly/scruffy
claude plugin install scruffy@scruffy-marketplace
```

For local plugin development, clone the repository and load it directly:

```sh
git clone https://github.com/zachary-satterly/scruffy.git
cd scruffy
claude --plugin-dir .
```

Root `CLAUDE.md` makes the checkout a Claude maintainer project by importing the
agent-neutral contract in `AGENTS.md`. That contract maps canonical files,
generated projections, validation, and clean-room test boundaries. Start Claude
in the repository and paste this prompt:

```text
Work in Scruffy MAINTAIN mode. Read CLAUDE.md and its imported AGENTS.md first,
then map the canonical source, generated projections, tests, and distribution entrypoints before
editing. Use the current skill on the evidence I provide, but do not treat a
prior audit or my suspected fix as ground truth. Reproduce the gap, identify
the narrowest canonical owner, add a regression and a false-positive guard for
behavior changes, regenerate projections, and run the full validation suite.
If the runtime behavior changes, give me a separate neutral prompt for a fresh
blind forward test; do not call this maintainer session blind. Explain what
changed, what remains unverified, and whether a release version should change.
```

Use `CLAUDE.local.md` for machine-specific notes and keep it uncommitted. Do not
put target findings or expected blind-test answers in either project file.

If you prefer the bare `/scruffy` command, install the same checkout as a personal skill instead of a plugin:

```sh
mkdir -p ~/.claude/skills
ln -s /absolute/path/to/scruffy ~/.claude/skills/scruffy
```

```text
/scruffy audit https://example.com and prioritize the structural fixes
```

For a private GitHub repository, authenticate Git first. Claude Code uses existing credential helpers for manual installs and updates; GitHub shorthand uses SSH by default. See the [official private-marketplace guidance](https://code.claude.com/docs/en/plugin-marketplaces#private-repositories).

### Codex

Install for all projects:

```sh
mkdir -p ~/.agents/skills
ln -s /absolute/path/to/scruffy ~/.agents/skills/scruffy
```

Or install only for one repository:

```sh
mkdir -p .agents/skills
ln -s /absolute/path/to/scruffy .agents/skills/scruffy
```

Invoke explicitly:

```text
$scruffy audit https://example.com and prioritize the structural fixes
```

Codex may also invoke the skill implicitly when a request matches the `SKILL.md` description.

Codex and Claude load the same root `SKILL.md`; there is no duplicated runtime copy to drift. `agents/openai.yaml` provides Codex UI metadata, while `.claude-plugin/` provides Claude Code distribution metadata. Claude's generated `skills/scruffy/SKILL.md` exists only for plugin discovery and immediately delegates to the canonical root file. This proves source compatibility, not identical agent behavior.

| Runtime | Native entrypoint | Explicit invocation |
|---|---|---|
| Claude Code plugin | `.claude-plugin/plugin.json` + root `SKILL.md` | `/scruffy:scruffy` |
| Claude Code personal skill | `~/.claude/skills/scruffy/SKILL.md` | `/scruffy` |
| Codex | root `SKILL.md` + `agents/openai.yaml` | `$scruffy` |

### Other agents

Point any Agent Skills-compatible agent at `SKILL.md`. For agents without live-browser or file capabilities, the skill degrades to static analysis and clearly marks runtime checks not run.

## Repair approved findings

Scruffy’s repair workflow lives in [`mop/`](mop/) for compatibility with existing
automation; it is not a separate product. It consumes an audit bundle read-only
and acts only on human-approved items under explicit source-write authority. For
design work it proposes three rule-cited directions per work group, each grounded
in reference imagery—text-only visual advice fails closed. It renders a
self-contained decision dashboard and hands the result back to Scruffy for
re-audit. Start the repair stage with
`python3 mop/scripts/mop_run.py <bundle-dir>`.

## Repository layout

```text
scruffy/
├── .claude-plugin/
│   ├── plugin.json               # Claude Code plugin manifest
│   └── marketplace.json          # installable one-plugin marketplace
├── AGENTS.md                      # canonical agent-neutral maintainer contract
├── CLAUDE.md                      # Claude import and local plugin invocation
├── skills/scruffy/
│   └── SKILL.md                   # generated Claude discovery adapter; points to canonical root skill
├── assets/
│   ├── BRAND.md                   # product theme, naming, voice, and visual boundaries
│   ├── scruffy-hero.png          # Transparent README action banner
│   └── scruffy-character.png     # Transparent reusable character model
├── SKILL.md                      # shared Agent Skills runtime instructions
├── agents/
│   └── openai.yaml               # Codex UI metadata
├── schema/
│   ├── taxonomy.json             # canonical layers, categories, facets, labels, and proof rules
│   ├── rules/                    # deterministic lead packs: cited, guarded, leads never findings
│   └── audit-contract.json       # canonical modes, authority, capabilities, evidence, and editorial receipts
├── references/
│   ├── taxonomy.md              # generated human projection of the category contract
│   ├── audit-contract.md        # generated human projection of execution contracts
│   ├── verification.md          # live-operation and falsification protocol
│   ├── scoring.md               # calibrated severity, confidence, and scores
│   ├── durability.md            # immutable identity and revision reconciliation
│   ├── archetypes.md            # task probes by application class
│   ├── sentence-slop.md         # copy-quality signals, thresholds, and false-positive guards
│   ├── blind-audit.md            # quarantine, digest freeze, reveal, and reconciliation
│   └── output-schema.md         # registries, decisions, reports, work orders
├── evals/
│   ├── triggers.json            # positive and negative invocation fixtures
│   ├── archetypes.json          # application-class coverage fixtures
│   ├── sentence-slop/           # quality-signal and false-positive fixtures
│   ├── durability/              # valid and intentionally invalid synthetic revisions
│   └── continuity/                 # real seventeen-record reconciliation golden case
│   └── web-fixtures/            # known-answer pages with a hidden discrimination key
├── principles/
│   ├── PRINCIPLES.md            # source-of-truth research corpus
│   ├── SOURCES.md               # source registry and intake provenance
│   └── INSPIRATIONS.md          # reference-source tiers
├── scripts/
│   ├── intake.py                # caption intake for corpus research
│   ├── validate_corpus.py        # citation and corpus validation
│   ├── validate_skill.py         # package, reference, and portability validation
│   ├── claude_adapter.py         # generate/check the DRY Claude plugin adapter
│   ├── taxonomy_contract.py      # synchronize and validate category projections
│   ├── audit_contract.py         # synchronize and validate execution-contract projections
│   ├── report_contract.py        # shared renderer labels and evidence projections
│   ├── analyze_sentence_slop.py  # deterministic measurements; never an authorship score
│   ├── blind_protocol.py         # blind manifest, freeze, and integrity verification
│   ├── evaluate_blind_outputs.py # hidden-key scoring with no authorship labels
│   ├── run_sentence_blind.py     # unlabeled surface leads; defers semantic checks
│   ├── validate_audit.py         # registry, decisions, and report validation
│   ├── migrate_decisions.py      # carry decisions into a new revision
│   ├── render_dashboard.py       # complete self-contained decision dashboard
│   ├── render_brief.py           # 150-word decision brief, rendered never authored
│   ├── render_markdown.py        # complete human-readable report
│   ├── verify_fixes.py           # runs approved items' executable acceptance checks
│   ├── outcomes.py               # approve / verify / reopen rates: the value ledger
│   ├── test_durability.py        # continuity and rendering regression tests
│   ├── test_audit_contract.py    # category, authority, evidence, and editorial-contract tests
│   ├── test_sentence_slop.py     # sentence-signal and guard regression tests
│   ├── test_blind_protocol.py    # contamination and post-freeze mutation tests
│   ├── test_blind_evaluator.py   # coverage, temporary-ID, and no-authorship tests
│   ├── test_sentence_blind_runner.py # compound-signal vs guarded-copy regression
│   └── annotate.html             # local screenshot annotation utility
├── .github/workflows/validate.yml # dependency-free CI checks
├── CONTRIBUTING.md
├── CHANGELOG.md
├── README.md
└── LICENSE
```

## Validate

The validators use only the Python standard library:

```sh
python3 scripts/validate_skill.py
python3 scripts/claude_adapter.py --check
python3 scripts/validate_corpus.py
python3 scripts/test_durability.py
python3 scripts/test_audit_contract.py
python3 scripts/test_sentence_slop.py
python3 scripts/test_category_gates.py
python3 scripts/test_scaffold_audit.py
python3 scripts/test_blind_protocol.py
python3 scripts/test_blind_evaluator.py
python3 scripts/test_sentence_blind_runner.py
python3 scripts/test_web_fixtures.py
python3 scripts/rule_engine.py --check
python3 scripts/test_rule_engine.py
python3 scripts/test_product_surfaces.py
```

The first checks metadata, the Claude maintainer contract, generated DRY contracts, progressive-disclosure budgets, referenced files, durability and blind-audit terms, editorial and archetype fixtures, Codex metadata, portability traps, and trigger coverage. The second checks corpus coverage, citations, timestamps, aliases, and source-state consistency. The remaining suites prove registry durability, canonical categories, write authority, typed evidence, editorial receipts, sentence false-positive guards, blind-output immutability, and contamination rejection.

Compatibility note: durable report markers and browser-storage keys retain the internal `anti-slop-*` namespace so existing registries, dashboards, and decisions remain readable after the rename. This does not affect `$scruffy` or `/scruffy` invocation.

## Start a new report bundle from green

`python3 scripts/scaffold_audit.py --audit-id <id> --target <desc> --title <t> --out <dir>` emits a pre-valid findings/context/decisions trio, TODO-seeded and self-validating. Add `--mode redesign --repository-write-authority authorized` when the request explicitly authorizes implementation. Repeat `--supplied-screenshot <path>` to copy recognized PNG, JPEG, GIF, or WebP evidence into the bundle for self-contained dashboard embedding. Explicit item prefixes must be two to six uppercase alphanumeric characters, beginning with a letter. Authoring an audit becomes editing a passing document instead of negotiating with the validator.

## Repeat an audit without losing history

Treat `findings.json` as the canonical record and the dashboard as a view of that record:

```sh
python3 scripts/migrate_decisions.py previous-decisions.json findings.json decisions.json \
  --prior-registry previous-findings.json
python3 scripts/render_dashboard.py findings.json context.json decisions.json audit-report.html
python3 scripts/render_brief.py findings.json --context context.json --decisions decisions.json --output brief.md
python3 scripts/render_markdown.py findings.json context.json decisions.json audit-report.md
python3 scripts/validate_audit.py findings.json \
  --context context.json \
  --baseline previous-findings.json \
  --decisions decisions.json \
  --baseline-decisions previous-decisions.json \
  --dashboard audit-report.html \
  --markdown audit-report.md
```

For schema 2.1, the validator also rejects improvised category names, inapplicable facets, contradictory run modes, unauthorized writes, incomplete capability or score ledgers, unresolved evidence IDs, missing captured files, and Editorial slop findings without the required review receipt. The “top eight findings” and “top five enhancements” remain presentation limits only; additional and resolved items are still rendered.

## Add a principle

```sh
python3 scripts/intake.py --channel <youtube-channel-videos-url>
```

Transcripts and frames remain local working material and are ignored by Git. A
creator, book, heuristic, or attractive reference contributes no principle until
the material has been reviewed, traced, corroborated, tested against a
counterexample, and translated into an operational check.

For every addition:

1. Register the source and its review status in `principles/SOURCES.md`.
2. Add the narrow, attributed rule to `principles/PRINCIPLES.md`, including its
   exceptions and the consequence it is meant to prevent.
3. Add or update an operated/static check only when the signal can be reproduced;
   the check must raise a lead, never manufacture a finding.
4. Add a positive regression and a plausible false-positive counterexample.
5. Regenerate derived contracts and run the complete validation suite.
6. Forward-test the behavior against a target that was not used to write the rule.

This keeps the trace legible: **source → principle → operated check → signal →
finding → approved repair → re-audit evidence**.

Do not sweep fashionable gallery or redesign channels indiscriminately. Separate research-backed rules, implementation evidence, explicit AI-default critiques, visual hypotheses, and promotional material.

## Boundaries

- Framework, agent, browser, and operating system agnostic
- No security certification or vulnerability scan
- No accessibility conformance claim from partial coverage
- No performance verdict without runtime measurement
- No claim of AI authorship from visual resemblance
- No claim of AI authorship from sentence statistics, perplexity, “burstiness,” passive voice, or rhetorical patterns
- No implementation changes from an audit-only request
- No inspection of passwords, cookies, tokens, or browser-storage contents
- Broad web-application coverage is capability-dependent; the skill records checks not run instead of inventing proof

## Credits

The corpus distills and attributes work from Kole Jain; Sergei Chyrkov; DesignCourse; UI Collective; Nielsen Norman Group; Deque Systems; Eleken; Kevin Powell; Tim Gabe; Baymard Institute; Y Combinator Design Review; Steven Haney; W3C; web.dev/Chrome; MDN; Refactoring UI; Practical Typography; Edward Tufte; and Laws of UX. See `principles/SOURCES.md` for exact provenance. No source text is reproduced.

## License

MIT — see `LICENSE`. The license covers this repository’s text and code; cited works remain their authors’ own.
