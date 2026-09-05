# Security

Scruffy is an Agent Skill. It ships instructions and Python scripts that an AI
agent runs on your machine, with your file access, against products you point it
at. That makes its threat model different from a library's: the dangerous input
is not a network request, it is the audited product and the JSON an agent writes
while reading that product.

## Reporting a vulnerability

Report privately through GitHub's [Report a vulnerability][advisory] form on this
repository. If that is unavailable, email zachary.satterly@gmail.com with
`scruffy security` in the subject.

[advisory]: https://github.com/zachary-satterly/scruffy/security/advisories/new

Include the version or commit, the file and line, what an attacker controls, and
the smallest reproduction you have — ideally a bundle or manifest that triggers
it. You will get an acknowledgement within seven days and an assessment within
fourteen. Please give a fix thirty days before public disclosure. There is no
bounty; credit in the advisory and the changelog is offered unless you decline.

This is a single-maintainer project with no release train. Only the latest commit
on `main` and the latest tagged release receive fixes.

## What is in scope

- Any path where audit data — `findings.json`, `context.json`, `decisions.json`,
  `directions.json`, an assets manifest, a fix packet — causes a script to read a
  file outside the bundle, write outside its output directory, execute a command,
  or emit active content into a rendered dashboard.
- Prompt injection that survives the guard in `SKILL.md` and changes the auditor's
  behaviour rather than being recorded as evidence.
- Anything shipped in the repository that leaks the operator's local data into an
  artifact meant to be shared.

## What is out of scope

- Findings the skill produces about *your* product's security. Scruffy audits
  interfaces; it refers exploitability to a specialist review and does not claim
  to be one.
- Vulnerabilities in a product you audit.
- Model output quality, false positives, or a missed finding.
- Anything requiring the operator to already have write access to the repository.

## Threat model

**Untrusted by default.** Everything the audited target controls — rendered copy,
DOM attributes, source comments, metadata, alt text, filenames, API payloads,
logs, uploaded documents — is evidence, never instruction. `SKILL.md` states this
as a run rule and the run-completion checks verify it.

**The artifacts are untrusted too.** This is the subtler half, and the one that
produced every fix listed below. A findings registry or an assets manifest is
written by a model that has just finished reading a hostile page, and a bundle can
arrive from someone else. The scripts therefore assume those files are hostile:

- **Commands are bounded.** `verify_fixes.py` prefers an `argv` list and executes
  it with no shell, so quoting, globs, pipes, and `$(…)` are literal text. A
  legacy `run` string reaches a shell only under `--execute` *and* `--allow-shell`
  — an artifact cannot grant itself shell access. Runs are additionally bounded by
  a timeout, an output cap, and an environment allowlist.
- **Evidence is confined and sniffed.** `evidence_assets.confined_path` refuses
  absolute paths and `../` walks, so a manifest cannot pull `~/.ssh/id_rsa` into a
  dashboard built to be shared. Raster evidence is size-capped and identified by
  magic bytes, so a manifest's declared MIME can never reach an attribute.
- **Validation does not probe.** Evidence locators are confined before any
  `.exists()` check, so a crafted bundle cannot use pass/fail as a file-existence
  oracle for the auditor's machine.
- **Dashboards escape everything.** Registry item ids and reference URLs are
  escaped into attributes; links are `http(s)`-only, so a `javascript:` href fails
  the render rather than executing in a reader's browser; JSON embedded in a
  `<script>` block has `</` escaped and fills its template in a single pass, so
  neither a `</script>` in registry text nor an `audit_id` containing a template
  placeholder can break out.

**Where the operator still carries the risk.** `--execute` runs commands a model
wrote. Read them first. `--allow-shell` hands a legacy string to a shell; treat it
as running a script a stranger sent you. Nothing here should be pointed at a
product you are not authorised to audit.

**What this repository does not do.** No network calls at import or validation
time, no archive extraction, no `pickle`, `eval`, `exec`, or `yaml.load`, and no
credentials of any kind. Transcripts, frames, private holdouts, and local run
evidence are gitignored and must never be committed.

## Regression coverage

`scripts/test_security_guards.py` and `scripts/test_bounded_execution.py` encode
these attacks as tests. `scripts/check.py` discovers every `test_*.py` under
`scripts/` and `mop/scripts/`, so CI runs them on each push and pull request. A
fix without a test there is not finished.
