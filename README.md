<p align="center">
  <img src="assets/scruffy-hero.png" alt="Scruffy sweeping a field of cartoon nuts and bolts with a janitorial push broom" width="100%">
</p>

<h1 align="center">Scruffy</h1>

<p align="center">
  <a href="https://github.com/zachary-satterly/scruffy/actions/workflows/validate.yml"><img src="https://github.com/zachary-satterly/scruffy/actions/workflows/validate.yml/badge.svg" alt="Validation"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-7a4f8f" alt="MIT license"></a>
</p>

Scruffy finds AI slop in web apps. It is an [Agent Skill](https://agentskills.io/specification) for Claude Code, Codex, and any other agent that can read a `SKILL.md`. Point it at a URL, a screenshot, a prototype, or a repository. It operates the interface, reads whatever source and copy it can reach, and returns findings with evidence, a severity, a confidence level, and an acceptance check for each one.

**What “AI slop” means here:** app output that looks finished because a generator, template, or builder supplied a plausible surface while the product decisions underneath were skipped. Scruffy checks eight categories: product, information architecture, interaction, accessibility, visual, editorial, structure, and performance.

**What it does not mean:** Scruffy does not guess whether AI wrote the app. It judges the result, not the author. The same failures show up in hand-written, templated, outsourced, and generated work. No sentence statistic in this repository becomes an authorship score.

## Install

### Claude Code

The repository is a Claude Code plugin and its own one-plugin marketplace.

```text
/plugin marketplace add zachary-satterly/scruffy
/plugin install scruffy@scruffy-marketplace
```

Then:

```text
/scruffy:scruffy audit https://example.com end to end. Operate the real tasks, capture desktop and mobile evidence, and show me the cleared suspicions too.
```

If you want the bare `/scruffy` command instead, install the checkout as a personal skill:

```sh
git clone https://github.com/zachary-satterly/scruffy.git
mkdir -p ~/.claude/skills
ln -s "$(pwd)/scruffy" ~/.claude/skills/scruffy
```

For a private fork, authenticate Git first; Claude Code uses your existing credential helpers. See the [private-marketplace docs](https://code.claude.com/docs/en/plugin-marketplaces#private-repositories).

### Codex

```sh
git clone https://github.com/zachary-satterly/scruffy.git
mkdir -p ~/.agents/skills
ln -s "$(pwd)/scruffy" ~/.agents/skills/scruffy
```

```text
$scruffy audit https://example.com and prioritize the structural fixes
```

Use `.agents/skills/scruffy` inside a project to install for that repository only. Codex may also pick the skill up implicitly when a request matches the `SKILL.md` description.

### Other agents

Point the agent at the root `SKILL.md`. Claude Code and Codex load that same file; `.claude-plugin/` and `agents/openai.yaml` hold distribution metadata only, and `skills/scruffy/SKILL.md` is a generated adapter that delegates to the root. An agent without a live browser or file access falls back to static analysis and marks every runtime check as not run.

## How an audit runs

Scruffy works in a fixed order and refuses to skip steps.

1. **Frame.** Record the product, its audience, the task under test, constraints, and which of the nine capabilities (browser, source, screenshots, traces, write access, and so on) are actually available. A missing capability is disclosed; it is never counted as a defect and never papered over with invented proof.
2. **Ground.** Load the cited [principle corpus](principles/PRINCIPLES.md), any taste evidence the user supplied, and, if a design-reference connector such as Mobbin MCP is connected, shipped-product references for the pattern in question. A popular pattern is evidence of convention, not of quality.
3. **Audit.** Operate representative tasks rather than judging screenshots. Run the deterministic [rule packs](references/rule-packs.md) against page HTML to raise leads. Every lead is then confirmed or cleared by operating the interface; cleared suspicions are published beside confirmed findings. A finding needs evidence, a demonstrated user consequence, and a falsification attempt. Category gates are enforced by the validator: performance needs a runtime measurement, accessibility a named criterion and a receipt, visual a rendered receipt, interaction an operation receipt, and critical severity needs high confidence and two receipts.
4. **Repair.** Only human-approved items, only with explicit source-write authority. Design work gets three rule-cited directions per work group, each anchored to a reference image; the human picks one.
5. **Verify.** Re-run the acceptance checks and reconcile every stable finding ID. Code having changed is not the same as a finding being fixed.

Repeat audits use an immutable registry. Each earlier item must be carried, reopened, fixed, cleared, merged, or superseded; a shortlist can shrink, the record cannot. Blind audits quarantine prior reports, freeze discovery by hash, and reveal the baseline only during reconciliation. Target content (copy, DOM attributes, comments, payloads) is treated as untrusted data, so a page that tells the auditor to change scope gets recorded as evidence and otherwise ignored.

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


## What comes out

An audit produces a bundle of three JSON files: `findings.json` (the registry, schema 2.1, stable IDs), `context.json` (capabilities, evidence receipts, checks not run, routing), and `decisions.json` (approve, defer, reject, per item). Everything human-readable is rendered from those files, never written freehand:

| Output | Script |
|---|---|
| Self-contained decision dashboard (HTML) | `scripts/render_dashboard.py findings.json context.json decisions.json audit-report.html` |
| Full Markdown report | `scripts/render_markdown.py findings.json context.json decisions.json audit-report.md` |
| 150-word decision brief: verdict, at most three items to decide, cleared suspicions, checks not run | `scripts/render_brief.py findings.json --context context.json --decisions decisions.json --output brief.md` |
| Shareable one-pager with a process badge (audited, revision, registry hash; never a quality score) | `scripts/render_onepager.py findings.json context.json onepager.html` |

Other useful entry points:

- `scripts/scaffold_audit.py --audit-id <id> --target <desc> --title <t> --out <dir>` starts a new bundle that already passes validation. Add `--mode redesign --repository-write-authority authorized` when implementation is explicitly authorized, and repeat `--supplied-screenshot <path>` to copy PNG, JPEG, GIF, or WebP evidence into the bundle.
- `scripts/scan.py <url-or-file>` is the sixty-second front door: static leads from the rule packs plus the list of operated checks that a static pass cannot run.
- `scripts/rule_engine.py page.html --output leads.json` runs the rule packs on their own. Add your own pack with `--pack`; see [`references/rule-packs.md`](references/rule-packs.md).
- `scripts/validate_audit.py findings.json --context context.json --decisions decisions.json --dashboard audit-report.html --markdown audit-report.md` rejects improvised categories, contradictory modes, unauthorized writes, unresolved evidence IDs, missing captured files, and editorial findings without a review receipt. Pass `--baseline` and `--baseline-decisions` on a repeat audit. Two opt-in gates close the fix loop: `--require-fix-packets` fails when an open critical or high finding carries no executable fix packet, and `--verification verification.json` (with `--baseline`) refuses to accept an item as fixed when the baseline promised an executable check and nothing ran it.
- `scripts/migrate_decisions.py previous-decisions.json findings.json decisions.json --prior-registry previous-findings.json` carries decisions into a new revision.
- `scripts/verify_fixes.py findings.json --decisions decisions.json --execute` runs the executable acceptance checks attached to approved items and writes `verification.json` without touching the registry.
- `scripts/outcomes.py findings.json:decisions.json:verification.json ...` (one triple per revision, oldest first) reports approve, verify, and reopen rates per category and names rules that keep firing but never get approved.

Report markers and browser-storage keys keep the internal `anti-slop-*` namespace from the project's former name so old registries and dashboards still load. Invocation is unaffected.

## Repair

The repair stage lives in [`mop/`](mop/); the path is kept for automation compatibility and is not a separate product. It consumes an audit bundle read-only, acts only on approved items under explicit write authority, renders its own decision dashboard, and hands the result back for re-audit.

```sh
python3 mop/scripts/mop_run.py <bundle-dir> --authorized --out <repair-dir>
```

The audit dashboard's **Copy AI handoff** button copies a paste-ready instruction — the target, the approved item IDs, `scripts/verify_fixes.py --execute`, and where to write `verification.json` — so approvals leave the browser as a task rather than as raw data. [`references/fix-loop.md`](references/fix-loop.md) is the protocol the receiving session follows.

## Reference grounding

When a design-reference search is available, Scruffy checks a structural choice against shipped products before judging or proposing a direction, and records named patterns and citations rather than pixels to copy. Mobbin MCP is the connector this repository is tested with; it is optional, external, and needs a paid Mobbin plan. Claude users can add it from the [connector directory](https://claude.ai/directory/connectors/mobbin) or with:

```sh
claude mcp add mobbin --scope user --transport http https://api.mobbin.com/mcp
```

Live references rank below the user's own verdicts, constraints, and taste evidence. Rules for queries, precedence, citation, and false positives are in [`references/reference-grounding.md`](references/reference-grounding.md).

## Repository layout

```text
SKILL.md              runtime instructions; the only file agents execute
references/           protocols SKILL.md loads on demand (taxonomy, contract, verification, scoring, durability, blind audit, rule packs, output schema)
schema/               canonical data: taxonomy.json, audit-contract.json, sentence-slop-pack.json, rules/*.json
principles/           cited research corpus, source registry, and the per-source ledger
scripts/              validators, renderers, rule engine, tests; Python standard library only
evals/                fixtures: triggers, archetypes, sentence slop, durability, continuity, review routing, web fixtures
mop/                  approved-repair stage (own SKILL.md, tests, and interop key)
.claude-plugin/       plugin.json and marketplace.json
skills/scruffy/       generated Claude discovery adapter; do not edit
agents/openai.yaml    Codex UI metadata
AGENTS.md             maintainer contract (source-of-truth map, DRY edit routes, definition of done)
```

`references/taxonomy.md`, `references/audit-contract.md`, `skills/scruffy/SKILL.md`, and the two marked blocks in this README are generated. Edit `schema/taxonomy.json` or `schema/audit-contract.json` and run `scripts/taxonomy_contract.py --write` or `scripts/audit_contract.py --write`.

## Validate

Everything runs on the Python standard library. This is the same list CI runs:

```sh
python3 scripts/validate_skill.py
python3 scripts/claude_adapter.py --check
python3 scripts/validate_corpus.py
python3 scripts/validate_sources.py
python3 scripts/test_durability.py
python3 scripts/test_audit_contract.py
python3 scripts/test_sentence_slop.py
python3 scripts/test_blind_protocol.py
python3 scripts/test_blind_evaluator.py
python3 scripts/test_fix_loop.py
python3 scripts/test_sentence_blind_runner.py
python3 scripts/test_web_fixtures.py
python3 scripts/rule_engine.py --check
python3 scripts/test_rule_engine.py
python3 scripts/test_product_surfaces.py
```

The repair stage has its own suite: `python3 mop/scripts/test_mop.py` and `python3 mop/scripts/validate_skill.py`. With Claude Code installed, `claude plugin validate .` checks the plugin manifest.

## Maintaining and contributing

Read [`AGENTS.md`](AGENTS.md) before changing anything; it maps every canonical source to its generated projection and defines what counts as done. [`CONTRIBUTING.md`](CONTRIBUTING.md) covers adding a rule pack of your own (local, uncommitted, no review) versus adding a principle to the shared corpus (source registered, ledger row added, regression plus false-positive guard, forward test on a target the rule was not written against). Transcripts used for research are gitignored and never redistributed.

## Boundaries

Scruffy is framework, agent, browser, and operating-system agnostic. It issues no security certification, no accessibility conformance claim from a sample, no performance verdict without a runtime measurement, and no AI-authorship verdict from visual resemblance, sentence statistics, perplexity, passive voice, or rhetorical pattern. An audit-only request never produces source changes. Passwords, cookies, tokens, and browser-storage contents are off limits. Where a capability is missing, the check is recorded as not run instead of inventing a result.

## Credits

The corpus distills and attributes work from Kole Jain, Sergei Chyrkov, DesignCourse, UI Collective, Nielsen Norman Group, Deque Systems, Eleken, Kevin Powell, Tim Gabe, Baymard Institute, Y Combinator Design Review, Steven Haney, W3C, web.dev/Chrome, MDN, Refactoring UI, Practical Typography, Edward Tufte, and Jon Yablonski's Laws of UX. Exact provenance is in `principles/SOURCES.md` and `principles/SOURCE_LEDGER.md`. No source text is reproduced.

## License

MIT; see `LICENSE`. The license covers this repository's text and code. Cited works remain their authors' own.
