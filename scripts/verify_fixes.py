#!/usr/bin/env python3
"""Run the executable acceptance checks for approved registry items.

This is the half of the loop an audit alone never closes: an approved item is
not value until its fix is applied and its acceptance checks pass. The script
reads the registry and decisions, selects approved open or needs-verification
items that carry a `fix_packet`, executes every check it can, and writes
`verification.json`. It never edits the registry: a status only changes in the
next revision, where `verification.json` is the evidence for a `fixed`
disposition.

Check kinds:
  command      run a program from --cwd; pass when the exit code is 0 (or
               `expect.exit_code`) and, when given, stdout contains
               `expect.stdout_contains`. Runs only with --execute.
  dom_state    a selector plus expected state. Needs a browser; supply results
               through --results, otherwise recorded as not_run.
  measurement  a metric name plus threshold. Same rule as dom_state.
  manual       a human must confirm. Recorded as manual, never pass.

A `command` check names its program one of two ways:

  argv  ["pytest", "-q", "tests/test_router.py"]   preferred; executed directly
        with no shell, so quoting, globs, pipes, and `$(...)` are literal text.
  run   "pytest -q tests/test_router.py"           legacy readable form; needs
        a shell, so it executes only with --execute *and* --allow-shell.

An artifact cannot grant itself shell access: `--allow-shell` is a decision the
person running the verifier makes about a bundle they have read. Without it a
legacy check is recorded `not_run`, never passed.

**This is not a sandbox and not a network boundary.** Both forms run trusted
local code with the invoking user's privileges and filesystem access. What is
bounded here is time, captured output, and inherited environment — not what a
check is allowed to do. Read the commands and the target directory first.

Receipts are written to be safe to publish: raw stdout, stderr, and command
text never enter them. Author-written `summary` prose is copied through as-is
and is not scrubbed — it is your text, not process output, so do not put a
secret in a summary.

`--results` is a JSON object keyed "ITEM-ID:index" -> {"result": "pass"|"fail",
"detail": "..."} for checks an agent or browser session ran out of band. Those
results are recorded with `provenance: imported`; this run did not observe them.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import signal
import subprocess
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import observation_manifest as om
from validate_audit import ACTIVE_STATUSES as ACTIVE, load_json, validate_decisions

TOOL = "scruffy/verify_fixes"
DEFAULT_CHECK_TIMEOUT = 120
DEFAULT_MAX_SECONDS = 120
DEFAULT_MAX_OUTPUT_BYTES = 256 * 1024
# Grace between asking a timed-out process group to stop and killing it.
TERMINATE_GRACE_SECONDS = 5
# How long a finished command's pipes may still be held by descendants before
# the observation is called unaccountable. Deliberately short: this window is
# time the caller did not ask for.
PIPE_DRAIN_SECONDS = 2
POSIX = os.name == "posix"


def load(path: Path | None) -> dict[str, Any]:
    return {} if path is None else load_json(path)


def decision_map(decisions: dict[str, Any]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for row in decisions.get("decisions", []) or []:
        item_id = row.get("item_id") or row.get("finding_id")
        if item_id:
            mapping[str(item_id)] = str(row.get("decision") or "pending")
    return mapping


class _CappedReader(threading.Thread):
    """Drain a pipe, keeping at most `cap` bytes.

    The cap is applied while reading, not after: a check that floods stdout is
    bounded in this process's memory, and the child still gets its pipe drained
    so it fails on its own terms instead of blocking forever on a full buffer.
    """

    def __init__(self, stream: Any, cap: int) -> None:
        super().__init__(daemon=True)
        self._stream = stream
        self._cap = cap
        self.data = bytearray()
        self.total = 0

    def run(self) -> None:
        try:
            while True:
                chunk = self._stream.read(65536)
                if not chunk:
                    break
                self.total += len(chunk)
                if len(self.data) < self._cap:
                    self.data.extend(chunk[: self._cap - len(self.data)])
        except (OSError, ValueError):  # pipe torn down by a kill; nothing to keep
            pass
        finally:
            try:
                self._stream.close()
            except OSError:
                pass

    @property
    def truncated(self) -> bool:
        return self.total > len(self.data)


def publish(document: dict[str, Any], staging: Path, destination: Path) -> None:
    """Write a receipt into place atomically."""
    receipt = staging / "verification.json"
    receipt.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    receipt.replace(destination)


def _drain(readers: tuple[_CappedReader, ...], seconds: float) -> bool:
    """Wait out the reader threads against one shared deadline."""
    deadline = time.monotonic() + seconds
    for reader in readers:
        reader.join(timeout=max(0.0, deadline - time.monotonic()))
    return all(not reader.is_alive() for reader in readers)


def _signal_group(pgid: int, sig: int) -> bool:
    """Signal a process group. False means nothing was left to signal."""
    try:
        os.killpg(pgid, sig)
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False


def _group_alive(pgid: int | None) -> bool:
    return bool(pgid) and POSIX and _signal_group(pgid, 0)


def _stop(process: subprocess.Popen[bytes], pgid: int | None) -> bool:
    """Stop a process and everything left in its group, then reap it.

    The earlier version of this returned as soon as the group leader died, so a
    child that ignored SIGTERM was never sent SIGKILL and outlived the run.
    Reaping the leader is not the end of the job: the group is signalled again
    after the leader exits, because that is exactly when survivors are left
    holding the pipes.

    Returns whether anything had to be killed after the leader was gone.

    Scope: POSIX only, and only for processes that stay in the session created
    for the check. A process that deliberately calls `setsid` leaves the group
    and is outside this guarantee. On non-POSIX platforms only the direct child
    is stopped; descendants can survive, and the receipt records that.
    """
    if not POSIX or pgid is None:
        for stopper in (process.terminate, process.kill):
            try:
                stopper()
            except OSError:
                pass
            try:
                process.wait(timeout=TERMINATE_GRACE_SECONDS)
                break
            except subprocess.TimeoutExpired:
                continue
        return False
    _signal_group(pgid, signal.SIGTERM)
    try:
        process.wait(timeout=TERMINATE_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        _signal_group(pgid, signal.SIGKILL)
        try:
            process.wait(timeout=TERMINATE_GRACE_SECONDS)
        except subprocess.TimeoutExpired:  # pragma: no cover - unkillable process
            pass
    # The leader is reaped; the group may still hold survivors. Always finish.
    survivors = _signal_group(pgid, 0)
    if survivors:
        _signal_group(pgid, signal.SIGKILL)
    return survivors


class Runner:
    """Execute command checks under caller-owned bounds."""

    def __init__(self, *, cwd: Path, execute: bool, allow_shell: bool, max_seconds: int, max_output_bytes: int, env: dict[str, str]) -> None:
        self.cwd = cwd
        self.execute = execute
        self.allow_shell = allow_shell
        self.max_seconds = max_seconds
        self.max_output_bytes = max_output_bytes
        self.env = env
        self.refused_legacy = 0

    def _launch(self, check: dict[str, Any]) -> subprocess.Popen[bytes]:
        argv = check.get("argv")
        kwargs: dict[str, Any] = {
            "cwd": str(self.cwd),
            "env": self.env,
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
        }
        if POSIX:
            kwargs["start_new_session"] = True
        if isinstance(argv, list):
            return subprocess.Popen([str(part) for part in argv], shell=False, **kwargs)
        return subprocess.Popen(str(check.get("run") or ""), shell=True, **kwargs)

    def run(self, check: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
        """Return (result, human detail, observation record).

        The observation record holds generic status only. Captured stdout and
        stderr and the command text are deliberately not persisted: acceptance
        checks routinely print tokens, connection strings, and paths, and a
        receipt is an artifact people paste into reports and tickets.
        """
        form = "argv" if isinstance(check.get("argv"), list) else "run"
        base = {"form": form, "status": "not_run"}
        if not self.execute:
            return "not_run", "command checks run only with --execute", base
        if form == "run" and not self.allow_shell:
            self.refused_legacy += 1
            return (
                "not_run",
                "legacy shell command refused: rerun with --allow-shell after reading it, or move the check to argv",
                {**base, "status": "refused_no_shell_opt_in"},
            )
        timeout = min(int(check.get("timeout", DEFAULT_CHECK_TIMEOUT)), self.max_seconds)
        started = time.monotonic()
        try:
            process = self._launch(check)
        except (OSError, ValueError) as error:
            # Do not echo the command; the error class is the useful part.
            return "fail", f"could not start command: {type(error).__name__}", {**base, "status": "launch_failed"}
        # start_new_session makes the child its own group leader, so the group
        # id is the child pid and stays usable after the leader is reaped.
        pgid = process.pid if POSIX else None
        out = _CappedReader(process.stdout, self.max_output_bytes)
        err = _CappedReader(process.stderr, self.max_output_bytes)
        out.start()
        err.start()
        timed_out = False
        survivors = False
        try:
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                survivors = _stop(process, pgid)
        except BaseException:
            # Ctrl-C or any other unwind must not leave the child running, and
            # must not let this check be reported as anything at all.
            _stop(process, pgid)
            raise
        # A leader can exit cleanly and leave descendants holding its pipes. That
        # is not a completed observation: output is still being produced by
        # something this run cannot account for. The drain window is short and
        # shared between both pipes — waiting on each in turn would quietly
        # extend the caller's time bound by however long the descendants live.
        drained = _drain((out, err), PIPE_DRAIN_SECONDS)
        if not drained or _group_alive(pgid):
            survivors = True
            _stop(process, pgid)
            _drain((out, err), TERMINATE_GRACE_SECONDS)
        duration_ms = int((time.monotonic() - started) * 1000)
        status = "timed_out" if timed_out else ("completed_with_survivors" if survivors else "completed")
        observation = {
            **base,
            "status": status,
            "exit_code": None if timed_out else process.returncode,
            "duration_ms": duration_ms,
            "timeout_seconds": timeout,
            "stdout_bytes": out.total,
            "stderr_bytes": err.total,
            "output_truncated": out.truncated or err.truncated,
            "child_cleanup": "process_group" if POSIX else "direct_child_only",
            "descendants_terminated": survivors,
        }
        if timed_out:
            return "fail", f"timed out after {timeout}s", observation
        if survivors:
            return (
                "fail",
                "the command exited but left running descendants; the observation is not accountable",
                observation,
            )
        expect = check.get("expect") or {}
        expect = expect if isinstance(expect, dict) else {}
        wanted_code = int(expect.get("exit_code", 0))
        expectations: dict[str, str] = {}
        expectations["exit_code"] = "met" if process.returncode == wanted_code else "unmet"
        needle = expect.get("stdout_contains")
        if isinstance(needle, str) and needle:
            found = needle in out.data.decode("utf-8", "replace")
            expectations["stdout_contains"] = "met" if found else "unmet"
        else:
            expectations["stdout_contains"] = "not_specified"
        observation["expectations"] = expectations
        if expectations["exit_code"] == "unmet":
            return "fail", f"exited {process.returncode}, expected {wanted_code}", observation
        if expectations["stdout_contains"] == "unmet":
            truncated = " (captured output was truncated at the byte cap)" if out.truncated else ""
            return "fail", f"stdout did not contain the expected text{truncated}", observation
        return "pass", f"exited {process.returncode} as expected", observation


def evaluate(item: dict[str, Any], packet: dict[str, Any], results: dict[str, Any], runner: Runner) -> dict[str, Any]:
    checks_out: list[dict[str, Any]] = []
    for index, check in enumerate(packet.get("acceptance") or []):
        kind = str(check.get("kind") or "manual")
        key = f"{item['id']}:{index}"
        supplied = results.get(key)
        observation: dict[str, Any] | None = None
        if kind == "command":
            result, detail, observation = runner.run(check)
            provenance = "collected" if observation.get("status") in {"completed", "timed_out"} else "not_collected"
        elif kind == "manual":
            result, detail, provenance = "manual", "needs a human confirmation", "not_collected"
        else:
            if isinstance(supplied, dict) and supplied.get("result") in {"pass", "fail"}:
                result = str(supplied["result"])
                detail = str(supplied.get("detail") or "supplied result")
                provenance = "imported"
            else:
                result = "not_run"
                detail = f"{kind} check needs a runtime result supplied with --results"
                provenance = "not_collected"
        row = {
            "index": index,
            "kind": kind,
            # Author-written prose only. A command string can carry a secret and
            # is never copied into the receipt.
            "summary": str(check.get("summary") or "") or f"{kind} check {index}",
            "result": result,
            "detail": detail,
            "provenance": provenance,
        }
        if observation is not None:
            row["observation"] = observation
        checks_out.append(row)
    outcomes = {c["result"] for c in checks_out}
    if not checks_out:
        overall = "not_run"
    elif "fail" in outcomes:
        overall = "failed"
    elif outcomes <= {"pass"}:
        overall = "verified"
    elif "not_run" in outcomes:
        overall = "not_run"
    else:
        overall = "manual"
    return {"id": item["id"], "title": item.get("title"), "result": overall, "checks": checks_out}


def positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("registry", type=Path)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--results", type=Path, help="out-of-band check results JSON; recorded as imported, not collected")
    parser.add_argument("--cwd", type=Path, default=Path.cwd(), help="working directory for command checks")
    parser.add_argument("--execute", action="store_true", help="actually run command checks")
    parser.add_argument(
        "--allow-shell",
        action="store_true",
        help="additionally execute legacy `run` string checks through a shell; requires --execute",
    )
    parser.add_argument("--max-seconds", type=positive_int, default=DEFAULT_MAX_SECONDS, help="per-check ceiling; caps any packet timeout")
    parser.add_argument("--max-output-bytes", type=positive_int, default=DEFAULT_MAX_OUTPUT_BYTES, help="bytes of stdout/stderr kept per check while reading")
    parser.add_argument("--env-allow", action="append", default=[], metavar="NAME", help="pass one named environment variable through to checks; repeatable")
    parser.add_argument(
        "--artifact-root",
        type=Path,
        help="directory every input and the receipt must resolve inside; defaults to the registry's directory",
    )
    parser.add_argument(
        "--target-ignore",
        action="append",
        default=[],
        metavar="GLOB",
        help="target paths that may change without invalidating the run (build output, generated state); repeatable",
    )
    parser.add_argument("--output", type=Path, default=Path("verification.json"))
    parser.add_argument("--include-pending", action="store_true", help="preview undecided items; incompatible with --execute")
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    if args.execute and args.include_pending:
        raise SystemExit("FAIL: --include-pending is preview-only and cannot be combined with --execute")
    if args.allow_shell and not args.execute:
        raise SystemExit("FAIL: --allow-shell only means something beside --execute")
    # Containment is decided before anything is opened. A policy that reads a
    # file and then asks whether it was allowed has already followed the path it
    # was supposed to refuse. `--cwd` is deliberately outside this rule: it is
    # the target, not a bundle artifact, and confining it would forbid the
    # ordinary case of a bundle that lives beside the repository it describes.
    try:
        om.confine(
            args.artifact_root or args.registry.resolve().parent,
            {
                "registry": args.registry,
                "--decisions": args.decisions,
                "--output": args.output,
                **({"--results": args.results} if args.results is not None else {}),
            },
        )
    except om.ManifestError as error:
        raise SystemExit(f"FAIL: {error}")
    registry = load(args.registry)
    decision_document = load(args.decisions)
    # Validate the entire bundle before the first command or receipt write.
    validate_decisions(decision_document, registry)
    decisions = decision_map(decision_document)
    results = load(args.results)
    if not args.cwd.is_dir():
        raise SystemExit("FAIL: --cwd must be an existing directory")
    inputs = [path.resolve() for path in (args.registry, args.decisions, args.results) if path is not None]
    if args.output.resolve() in inputs:
        raise SystemExit("FAIL: --output must not overwrite an input artifact")
    if args.output.exists() and not args.output.is_file():
        raise SystemExit("FAIL: --output must name a file")
    env, allowlisted = om.environment(args.env_allow)
    runner = Runner(
        cwd=args.cwd,
        execute=args.execute,
        allow_shell=args.allow_shell,
        max_seconds=args.max_seconds,
        max_output_bytes=args.max_output_bytes,
        env=env,
    )
    # Reserve a writable sibling before execution, then atomically publish the
    # receipt. A misspelled/unwritable parent must fail before side effects.
    with tempfile.TemporaryDirectory(prefix=".scruffy-verification-", dir=args.output.parent) as staging:
        started_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
        run_id = str(uuid.uuid4())
        # This run's own receipt is excluded by digest so a later validator can
        # rebuild the same rule; the staging directory is ephemeral and only
        # needs excluding while the run is in flight.
        own_receipt_digest = om.text_digest(str(args.output.resolve()))
        # Preflight has passed, so the destination is ours to take. Retire any
        # prior receipt *before* the first check runs: an interrupted run that
        # left the previous `verified` bytes in place reads, to anyone holding
        # only the output file, as a success that this invocation never
        # produced. A started receipt is durable and self-describing, so an
        # interruption leaves evidence of an incomplete run rather than stale
        # evidence of a complete one.
        publish(
            {
                "schema_version": "1.0",
                "audit_id": registry.get("audit_id"),
                "revision_id": registry.get("revision_id"),
                "verified_at": started_at,
                "executed_commands": False,
                "run_state": "started",
                "run_id": run_id,
                "items": [],
                "skipped": [],
                "note": (
                    "A verification run started and has not reported. Results from any earlier run "
                    "were retired when this one began; do not read this as a result."
                ),
            },
            Path(staging),
            args.output,
        )
        ignore = om.ignore_predicate(
            args.cwd, [own_receipt_digest], args.target_ignore, extra_prefixes=[Path(staging)]
        )
        target_before = om.target_identity(args.cwd, ignore=ignore)
        items_out: list[dict[str, Any]] = []
        skipped: list[dict[str, str]] = []
        for item in registry.get("items", []):
            if item.get("kind") not in {"finding", "enhancement"} or item.get("status") not in ACTIVE:
                continue
            decision = decisions.get(str(item["id"]), "pending")
            if decision != "approve" and not (args.include_pending and decision == "pending"):
                continue
            packet = item.get("fix_packet")
            if not isinstance(packet, dict):
                skipped.append({"id": item["id"], "reason": "no fix_packet; acceptance is prose only"})
                continue
            row = evaluate(item, packet, results, runner)
            row["decision"] = decision
            items_out.append(row)

        target_after = om.target_identity(args.cwd, ignore=ignore)
        if om.observed_change(target_before, target_after):
            # A check changed the target while the run was in progress, so an
            # earlier pass describes a tree that is no longer there. Keep the
            # check-level facts and withdraw the item-level claim. Targets with no
            # byte fingerprint are not treated as changed; the manifest's
            # target_binding records how strong the binding actually is.
            for row in items_out:
                if row["result"] == "verified":
                    row["result"] = "not_run"
                    row["target_changed"] = True
        completed_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
        provenance_counts = {"collected": 0, "imported": 0, "not_collected": 0}
        for row in items_out:
            for check in row["checks"]:
                provenance_counts[check["provenance"]] += 1
        manifest_inputs: dict[str, Any] = {"registry": registry, "decisions": decision_document}
        if args.results is not None:
            manifest_inputs["results"] = results
        manifest = om.build(
            tool=TOOL,
            inputs=manifest_inputs,
            target=target_before,
            target_after=target_after,
            execution={
                "executed": bool(args.execute),
                "shell_allowed": bool(args.allow_shell),
                "legacy_shell_checks_refused": runner.refused_legacy,
                "max_seconds": args.max_seconds,
                "output_cap_bytes": args.max_output_bytes,
                "platform": os.name,
                "child_cleanup": "process_group" if POSIX else "direct_child_only",
                "environment_policy": "minimal_documented",
                "environment_allowlist": allowlisted,
                "target_ignore_globs": list(args.target_ignore),
                "excluded_path_digests": [own_receipt_digest],
            },
            checks_digest=om.promised_checks_digest(registry, [row["id"] for row in items_out]),
            result_counts=provenance_counts,
            started_at=started_at,
            completed_at=completed_at,
        )
        # Self-check before publishing: an unvalidatable manifest is a defect
        # here, not something for a downstream reader to discover.
        manifest["run_id"] = run_id
        om.validate(manifest, registry=registry, item_ids=[row["id"] for row in items_out])
        report = {
            "schema_version": "1.0",
            "audit_id": registry.get("audit_id"),
            "revision_id": registry.get("revision_id"),
            "verified_at": completed_at,
            "executed_commands": bool(args.execute),
            "run_state": "complete",
            "run_id": run_id,
            "items": items_out,
            "skipped": skipped,
            "observation_manifest": manifest,
        }
        publish(report, Path(staging), args.output)
        counts = {k: sum(1 for r in items_out if r["result"] == k) for k in ("verified", "failed", "manual", "not_run")}
        status = "FAIL" if counts["failed"] else ("PASS" if items_out and counts["verified"] == len(items_out) and not skipped else "INCOMPLETE")
        refused = f"; {runner.refused_legacy} legacy shell checks refused without --allow-shell" if runner.refused_legacy else ""
        if not manifest["target_stable"]:
            refused += "; target changed during the run, so no item is target-bound"
        print(
            f"{status}: {len(items_out)} selected items evaluated — "
            f"{counts['verified']} verified, {counts['failed']} failed, {counts['manual']} manual, "
            f"{counts['not_run']} not run; {len(skipped)} skipped without a fix packet{refused} -> {args.output}"
        )
        return 1 if counts["failed"] else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        raise SystemExit(f"FAIL: {error}")
    except KeyboardInterrupt:
        # The started receipt stays in place. A reader sees an incomplete run,
        # never the previous run's success.
        raise SystemExit("FAIL: interrupted before this run reported; the receipt records a started, incomplete run")
