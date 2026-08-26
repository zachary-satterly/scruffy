# Scruffy — repair workflow

![Scruffy sweeping a field of cartoon nuts and bolts](../assets/scruffy-hero.png)

This directory contains Scruffy’s approved-repair stage. The `mop/` path and
`mop_*` filenames remain for automation compatibility; **Mop is not a separate
product or human-facing role**.

## The loop

```text
Scruffy audits → findings + context + decisions (+ tokens)
                         │ approved items only
                         ▼
Scruffy proposes three visual directions per design work group
                         │ one is recommended; a human selects
                         ▼
Scruffy implements under explicit source-write authority
                         ▼
Scruffy re-audits → items move open → fixed or cleared on evidence
```

Non-design findings such as copy, backend shape, and performance skip the
direction picker and follow the approved recommendation. A recommendation is
advice; nothing is implemented without approval and write authority.

## Visual contract

Every visual direction cites the principle that motivated the finding and must
have an image anchor: an annotated target screenshot, declared taste-library
entry, or named design reference. Text-only visual advice fails closed. Each
image declares its origin, and evidence from one product cannot silently ground
another product’s direction.

Mobbin or an equivalent design-reference search is optional. A built-in craft
floor still applies when no external connector is available, and the capability
gap is disclosed rather than treated as a defect.

## Authority and interoperability

Scruffy owns the audit contract and consumes these artifacts read-only during
repair:

| Artifact | Schema | Used for |
|---|---|---|
| `findings.json` | registry 2.1 | what to repair and how success is checked |
| `context.json` | 1.2 | dependency-ordered work orders, product truth, routing, assumptions, and referrals |
| `decisions.json` | 2.1 | the human approval gate |
| `tokens.json` | 1.0, optional | observed-value token corrections |

An approved decision is not repository authority. Source changes require an
explicit design/redesign request with source-write permission. Scruffy never
produces a finding during repair and never marks its own change fixed; that
status belongs to the subsequent re-audit.

Routing and referral records do not authorize repair work. They preserve the
audit boundary; only approved `findings.json` items enter the implementation plan.

The compatibility contract is in [`schema/interop.json`](schema/interop.json),
and the complete artifact handoff is in
[`references/scruffy-handoff.md`](references/scruffy-handoff.md).

## Usage

Every repair session starts with the orchestrator:

```sh
python3 scripts/mop_run.py <bundle-dir> [--templates <taste-library-dir>] [--assets assets.json] [--authorized]
```

It produces `mop-preflight.json`, a validated or scaffolded `directions.json`,
and one self-contained `mop-dashboard.html`. The filenames are stable machine
interfaces, not product names.

The underlying tools remain available individually through `mop_bundle.py`,
`mop_preflight.py`, `mop_directions.py`, `mop_dashboard.py`, and
`mop_handoff.py`. A worked fixture is available in
[`fixtures/sample-audit/`](fixtures/sample-audit/).

## Verification

```sh
python3 scripts/test_mop.py
python3 scripts/validate_skill.py
```

The runtime method, compatibility contract, deterministic scripts, fixture
bundle, and regression suite are field-run. Fixture findings are marked
`[FIXTURE]` so demo data cannot read as a real product claim.

## License

MIT © 2026 Zach Satterly
