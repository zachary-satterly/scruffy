# README editorial-slop dogfood — 2026-08-16

Target: `README.md`

Target SHA-256: `1752334d63fb24b8be0ea9103f3fa7c90f5e52b0cf4272312a921b467e62d31a`

Command:

```sh
python3 scripts/analyze_sentence_slop.py README.md --mode prose --language en
```

This is an editorial-quality review and makes no authorship assessment. Automated
surface measures are one evidence receipt; the disposition also requires manual
checks for coherence, specificity, information sequence, claims, recovery, and
voice.

## Automated receipt

- analyzer schema 1.3 with supported English scope
- 3,789 source words; 2,030 reader-facing words analyzed; 1,759 markup/code
  words excluded
- 184 sentences and 106 specificity markers
- zero abstract-filler matches and zero formulaic scaffolds
- one `quietly` match in the literal phrase “cannot quietly disappear,” not a
  commitment-free intensity claim
- four review lead families: repeated openings, repeated paragraph signatures,
  long enumerations, and comma-dense lists
- compound review required, but no automated finding eligibility; manual product
  consequence and counterexample tests remain mandatory

## Manual sentence checks

### Conceptual coherence — clear

The revised README uses one product name, **Scruffy**. Reference grounding,
principles, audit, repair, and verification are literal workflow stages rather
than mascot roles. The sweeping image and “AI slop” phrase stay within the
maintenance theme and do not carry technical claims.

### Sentence portability — clear

The promise names the target (web apps), inputs (URL, screenshot, prototype, or
repository), actors (Claude or Codex), method (operate and capture evidence), and
outputs (findings and repairs). Mode, authority, schema, installation, and
validation claims point to named artifacts or executable commands. The wording
would not describe an unrelated generic tool without material changes.

### Discourse purpose — clear

The repeated paragraph signatures occur in reference and procedural sections.
They help readers compare stages, categories, installation paths, and admission
steps. The repeated openings are separated boundary statements or two distinct
Mobbin instructions. Removing the parallel form would reduce scanning clarity
without changing any duplicated claim.

The two sentences over 35 words are bounded enumerations: validator rejection
conditions and source credits. The comma-dense leads are category inventories,
proof requirements, or immutable-status lists. Their objects share one governing
clause, so splitting them would make the contract harder to scan rather than
reduce cognitive load.

### Voice and subtext — clear

The voice is direct, workmanlike, and slightly irreverent. Product boundaries
stay literal. The copy no longer asks readers to remember DIRT, Keys, or Mop as
separate roles, and it does not overstate Mobbin, automation, authorship
detection, accessibility, performance, or verification.

## Broader editorial checks

### Terminology and information sequence — clear

The first screen explains the product before taxonomy or installation. One table
then maps the evidence loop. Reference grounding, modes, installation, repair,
validation, principle admission, boundaries, and credits follow in task order.
Historic `mop_*` and `scruffys-mop` identifiers are disclosed only as compatibility
interfaces, not as brand architecture.

### Claim support and provenance — clear

The validation badge links to executable repository checks. Principle and
reference claims point to the corpus, source registry, and grounding contract.
The README explicitly limits popular references to convention evidence and
preserves source attribution in the credits.

### Action and recovery clarity — clear

Claude, Codex, and generic Agent Skills paths provide install and invocation
steps. Audit scaffolding, repeat-audit migration, repair entry, validation, and
principle intake each name the next command or file. Missing capabilities are
recorded instead of being presented as successful checks.

### Voice and audience fit — clear

The document is for people evaluating, installing, operating, or maintaining a
developer tool. It keeps schema names and commands where those readers need
them, then translates durable keys and internal compatibility paths into plain
language.

## Final disposition

**Cleared:** no active editorial-slop finding in the README at the recorded
hash. The clearance combines normalized measurements, four manual sentence
checks, and four broader editorial checks. It is bounded to this file and hash
and makes no claim about AI authorship.

## Refresh — 2026-08-18 (data_fidelity facet added)

Prior target hash `8746c72bee6e6cee131a305f6db9a2783a41635c5a7f37972d4ac4452c271db2`; current `cf068872d989fa88c9a5b9673869e5dec8375e8b9bdf68f998fc7a0376e8bdb0`.

The only README change is one generated line inside the `scruffy-taxonomy` block:
the cross-cutting facet list gained **Input and reference-data fidelity**. It was
written by `scripts/taxonomy_contract.py --write` from `schema/taxonomy.json`, not
by hand.

Analyzer rerun on the new target returns `finding_eligible: false`, unchanged. The
lead codes (`clause_pileup`, `overlong_sentence`, `paragraph_pattern_reuse`,
`repeated_openings`) are the pre-existing set carried by earlier refreshes; the
added clause introduces none of them and lengthens no sentence past the gate.

Manual passes rechecked against the changed line only, since nothing else moved:

- **Conceptual coherence** — the facet name states its concern without needing its
  description, and sits among peers at the same level of abstraction.
- **Terminology and information sequence** — it reuses the noun-phrase shape of the
  five existing facets and introduces no README vocabulary the taxonomy does not
  already define.
- **Claim support and provenance** — the line asserts only that the facet exists,
  which `schema/taxonomy.json` now carries.

**Cleared:** no active editorial-slop finding in the current README. This refresh
reconciles the hash only; it does not reopen or supersede any prior disposition.

## Refresh — 2026-08-25 (audit scaffold options documented)

Prior target hash `cf068872d989fa88c9a5b9673869e5dec8375e8b9bdf68f998fc7a0376e8bdb0`; current `7bf91f6f18e86055564fed5fe096f1592b89add8a324b817e9cd4050748ca949`.

The README change is one paragraph in **Start a new report bundle from green**.
It names the new mode, authority, supplied-screenshot, image-format, and item-ID
prefix inputs beside the scaffold command they modify.

The English prose analyzer was rerun on the complete README. It reports 3,838
source words, 2,073 reader-facing words, 187 sentences, 111 specificity markers,
zero formulaic scaffolds, and `finding_eligible: false`. The pre-existing lead
codes remain `clause_pileup`, `overlong_sentence`, `paragraph_pattern_reuse`, and
`repeated_openings`; the changed paragraph is not an analyzer example for any
lead.

Manual passes rechecked the new paragraph and its surrounding task section:

- **Conceptual coherence** — mode, authority, screenshot, renderer, and prefix
  terms each name a literal scaffold input or output behavior.
- **Sentence portability** — the paragraph names `scaffold_audit.py`, exact CLI
  flags, supported formats, the self-contained dashboard, and the prefix shape;
  it cannot describe an unrelated generic tool without material changes.
- **Discourse purpose** — every sentence answers a distinct operator question:
  how to start, how to record implementation authority, how to seed screenshots,
  and which IDs are accepted.
- **Voice and subtext** — the wording remains direct and workmanlike, without
  promotional claims or invented assurances.
- **Terminology and information sequence** — options sit immediately after the
  base scaffold command and use the exact public CLI spellings.
- **Claim support and provenance** — the claims are exercised by
  `scripts/test_scaffold_audit.py`, including the renderer embedding path and the
  fail-before-write prefix case.
- **Action and recovery clarity** — the paragraph gives the exact authorized
  redesign flags, the repeatable screenshot input, accepted image formats, and
  the valid prefix boundary.
- **Voice and audience fit** — the detail is appropriate for operators starting
  a durable audit bundle and does not burden the earlier product overview.

**Cleared:** no active editorial-slop finding in the current README. This refresh
binds the badge to the changed file and makes no authorship assessment.

## Refresh — 2026-08-25 (GitHub owner renamed)

Prior target hash `7bf91f6f18e86055564fed5fe096f1592b89add8a324b817e9cd4050748ca949`;
current `1752334d63fb24b8be0ea9103f3fa7c90f5e52b0cf4272312a921b467e62d31a`.

The README changes only replace the former GitHub owner `ur-passwd-hash` with
the authenticated current owner `zachary-satterly` in the workflow badge and
public Claude/Codex install commands. No product claim, workflow, taxonomy,
authority, or invocation contract changed.

The English prose analyzer was rerun on the complete README. It remains at
3,838 source words, 2,073 reader-facing words, 187 sentences, 111 specificity
markers, zero formulaic scaffolds, and `finding_eligible: false`. The unchanged
lead set remains `clause_pileup`, `overlong_sentence`,
`paragraph_pattern_reuse`, and `repeated_openings`; URL destinations and code
commands are excluded from prose statistics.

Manual review of the changed lines found no coherence, portability, discourse,
voice, terminology, provenance, action, recovery, or audience-fit change beyond
making the public repository destinations accurate and directly usable.

**Cleared:** no active editorial-slop finding in the current README. This
refresh reconciles the hash after the verified GitHub rename and makes no
authorship assessment.
