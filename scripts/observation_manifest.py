#!/usr/bin/env python3
"""Bind a collected-evidence receipt to the run that produced it.

A verification receipt used to assert results with nothing tying them to an
invocation: which inputs were read, where the commands ran, which promised
checks were answered, and whether a result was collected here or imported from
somewhere else. Two receipts for two different targets were textually
interchangeable.

This module owns the optional `observation_manifest` block defined in
`schema/audit-contract.json`. It is deliberately small:

- digests, never paths, output, or command text — a manifest is safe to publish
  next to a report;
- additive — a receipt without a manifest is still a valid schema-1.0 receipt,
  and historical receipts are never rewritten;
- fail-closed — an unknown version, a malformed field, a target mismatch, or a
  checks digest that no longer matches the registry refuses validation instead
  of being read as a weaker claim.

What a manifest does **not** do: it does not raise the authority of a result. An
imported result stays imported, and a manifest on a failed check does not make
it a pass.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import uuid
from fnmatch import fnmatch
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

CONTRACT_PATH = Path(__file__).resolve().parents[1] / "schema" / "audit-contract.json"

# Reading git identity is a local, read-only call, time-bounded so a hung or
# wedged git cannot stall a verification run.
#
# Precisely: the metadata call is bounded in *time*, not in output size. `git
# status` output is buffered whole, so a worktree with a pathological number of
# changed or untracked entries produces a correspondingly large buffer. File
# *content* reads below are byte-bounded. "Bounded scan" in this module means
# bounded content reads plus a time-bounded metadata call — not a memory bound
# on git's own output.
GIT_TIMEOUT_SECONDS = 15
# Fingerprint reads are bounded so a large artifact in the worktree cannot turn
# identity capture into an unbounded scan. Exceeding either bound is recorded as
# an incomplete scan, never as a content claim.
MAX_FINGERPRINT_FILE_BYTES = 8 * 1024 * 1024
MAX_FINGERPRINT_TOTAL_BYTES = 128 * 1024 * 1024
DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


class ManifestError(ValueError):
    """A manifest that cannot be trusted. Callers treat this as a refusal."""


@lru_cache(maxsize=1)
def contract(path: str | None = None) -> dict[str, Any]:
    document = json.loads(Path(path or CONTRACT_PATH).read_text(encoding="utf-8"))
    block = document.get("observation_manifest")
    if not isinstance(block, dict):
        raise ManifestError("audit contract defines no observation_manifest block")
    return block


def current_version() -> str:
    return str(contract()["schema_version"])


def supported_versions() -> set[str]:
    return {str(value) for value in contract()["supported_versions"]}


def canonical_digest(document: Any) -> str:
    """Digest a JSON document by value, so key order cannot hide a swap."""
    payload = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def text_digest(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _git(cwd: Path, *arguments: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(cwd), *arguments],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return completed.stdout if completed.returncode == 0 else None


def _porcelain_entries(status: str) -> list[tuple[str, str]]:
    """Parse `git status --porcelain -z` into (status code, path) pairs.

    NUL-delimited because a path may contain a newline. Rename and copy records
    carry a second NUL-terminated path (the origin); it is consumed and the
    destination is what gets hashed.
    """
    fields = [field for field in status.split("\0") if field != ""]
    entries: list[tuple[str, str]] = []
    index = 0
    while index < len(fields):
        record = fields[index]
        index += 1
        if len(record) < 4:
            continue
        code, path = record[:2], record[3:]
        if code[0] in {"R", "C"} and index < len(fields):
            index += 1  # the origin path of a rename or copy
        entries.append((code, path))
    return entries


def _file_digest(path: Path, max_file_bytes: int) -> str | None:
    """Hash one worktree file, bounded. `None` means the scan is incomplete.

    The size check before opening is a cheap filter, not the bound: a file can
    grow between `stat` and the last read. The read loop counts what it actually
    consumes and gives up at the same limit.

    Only regular files are opened. A FIFO, socket, or device would block a read
    forever, so a non-regular path ends the content claim instead of being read.
    """
    try:
        status = os.lstat(path)
        if stat.S_ISLNK(status.st_mode):
            return "symlink:" + text_digest(os.readlink(path))
        if not stat.S_ISREG(status.st_mode):
            # A directory is a submodule or nested repository; anything else is
            # a special file. Neither has in-scope content this can hash.
            return None
        if status.st_size > max_file_bytes:
            return None
        digest = hashlib.sha256()
        read = 0
        with path.open("rb") as handle:
            while chunk := handle.read(65536):
                read += len(chunk)
                if read > max_file_bytes:
                    return None
                digest.update(chunk)
        return "sha256:" + digest.hexdigest()
    except FileNotFoundError:
        return "absent"
    except OSError:
        return None


def target_identity(
    cwd: Path,
    *,
    ignore: Callable[[str], bool] | None = None,
    max_file_bytes: int = MAX_FINGERPRINT_FILE_BYTES,
    max_total_bytes: int = MAX_FINGERPRINT_TOTAL_BYTES,
) -> dict[str, Any]:
    """Identify the directory an observation ran against, by bytes where possible.

    A commit plus `git status` output is **not** a content fingerprint: editing
    an already-modified file leaves the status letters identical, so two
    different worktrees produce the same digest. This hashes the actual bytes of
    every in-scope tracked modification and untracked file, on top of the commit.

    Bounded and fail-closed for file contents; see `GIT_TIMEOUT_SECONDS` for
    the one remaining unbounded buffer (git's own status output).
    A file over `max_file_bytes`, a scan over
    `max_total_bytes`, an unreadable path, or a nested repository ends the
    content claim: `content_fingerprint` becomes `None` and
    `fingerprint_scope` says why. A `None` fingerprint never validates as
    content binding — it is the absence of a claim, not a weak one.

    Excluded by construction: files the repository ignores, file modes and
    timestamps, submodule contents, anything outside `cwd`, and any path the
    caller's `ignore` predicate names (its own output artifacts).
    """
    resolved = cwd.resolve()
    identity: dict[str, Any] = {
        "identity_kind": "directory",
        "path_digest": text_digest(str(resolved)),
        "content_fingerprint": None,
        "fingerprint_scope": "path_only",
    }
    head = _git(resolved, "rev-parse", "HEAD")
    if head is None:
        return identity
    identity["identity_kind"] = "git_commit"
    identity["commit"] = head.strip()
    status = _git(resolved, "status", "--porcelain", "-z", "--untracked-files=all", "--", ".")
    root = _git(resolved, "rev-parse", "--show-toplevel")
    if status is None or root is None:
        # HEAD resolved but the worktree read did not. Do not guess clean.
        identity["dirty"] = None
        identity["fingerprint_scope"] = "unavailable"
        return identity
    base = Path(root.strip())
    # The ignore predicate is asked about absolute paths: the caller knows where
    # its own receipt lives, not where the repository root happens to be.
    entries = [
        (code, path)
        for code, path in _porcelain_entries(status)
        if not (ignore and ignore(str(base / path)))
    ]
    identity["dirty"] = bool(entries)
    parts = [identity["commit"]]
    budget = max_total_bytes
    for code, path in sorted(entries, key=lambda row: row[1]):
        target = base / path
        try:
            size = target.stat().st_size if target.is_file() and not target.is_symlink() else 0
        except OSError:
            size = 0
        budget -= size
        digest = _file_digest(target, max_file_bytes) if budget >= 0 else None
        if digest is None:
            identity["fingerprint_scope"] = "incomplete"
            return identity
        parts.append(f"{code}\0{path}\0{digest}")
    identity["content_fingerprint"] = text_digest("\n".join(parts))
    identity["fingerprint_scope"] = "commit_and_worktree_bytes"
    return identity


IDENTITY_FIELDS = ("identity_kind", "path_digest", "commit", "content_fingerprint", "fingerprint_scope")


def _identity(record: Any) -> tuple:
    return tuple(record.get(field) for field in IDENTITY_FIELDS)


def same_target(before: Any, after: Any) -> bool:
    """Is this provably the same target, by bytes?

    Used where a positive identity claim is needed — proving a receipt still
    describes the tree in front of you. Fail-closed: without a byte-level
    fingerprint there is nothing to compare, so it answers no. "I could not
    tell" and "yes" must not be the same answer here.
    """
    if not isinstance(before, dict) or not isinstance(after, dict):
        return False
    if before.get("fingerprint_scope") != "commit_and_worktree_bytes":
        return False
    return _identity(before) == _identity(after)


def observed_change(before: Any, after: Any) -> bool:
    """Did the target visibly change between two captures?

    The mirror question, and deliberately not the negation of `same_target`. A
    target with no byte fingerprint was not observed to change; calling that
    "changed" would withdraw results on every non-git target and turn a missing
    measurement into a finding. Strength of the binding is carried separately by
    `fingerprint_scope`, which a reader can see.
    """
    if not isinstance(before, dict) or not isinstance(after, dict):
        return True
    return _identity(before) != _identity(after)


def ignore_predicate(cwd: Path, excluded_path_digests: list[str], globs: list[str], extra_prefixes: list[Path] | None = None):
    """The exclusion rule a run used, rebuildable by anyone validating it later.

    The run's own receipt usually lands inside the target it describes, so a
    naive fingerprint invalidates every run that writes into its own repository.
    Excluding it is correct, but the exclusion has to be *reproducible*: a
    validator that cannot rebuild the same rule sees drift that never happened.
    Exclusions travel as path digests, so the rule survives without publishing
    anyone's directory layout.
    """
    resolved = Path(cwd).resolve()
    digests = set(excluded_path_digests)
    prefixes = [str(Path(path).resolve()) for path in (extra_prefixes or [])]

    def ignored(absolute: str) -> bool:
        if text_digest(absolute) in digests:
            return True
        if any(absolute == prefix or absolute.startswith(prefix + os.sep) for prefix in prefixes):
            return True
        try:
            relative = str(Path(absolute).relative_to(resolved))
        except ValueError:
            relative = absolute
        return any(fnmatch(relative, pattern) or fnmatch(absolute, pattern) for pattern in globs)

    return ignored


def build(
    *,
    tool: str,
    inputs: dict[str, Any],
    target: dict[str, Any],
    target_after: dict[str, Any],
    execution: dict[str, Any],
    checks_digest: str,
    result_counts: dict[str, int],
    started_at: str,
    completed_at: str,
) -> dict[str, Any]:
    """Assemble a manifest. `inputs` maps a contract input role to a document."""
    roles = list(contract()["input_roles"])
    unknown = sorted(set(inputs) - set(roles))
    if unknown:
        raise ManifestError(f"unknown observation input roles: {', '.join(unknown)}")
    return {
        "manifest_version": current_version(),
        "run_id": str(uuid.uuid4()),
        "tool": tool,
        "started_at": started_at,
        "completed_at": completed_at,
        "inputs": [
            {"role": role, "digest_form": "canonical_json", "digest": canonical_digest(inputs[role])}
            for role in roles
            if role in inputs
        ],
        # Identity is captured on both sides of execution. A check that edits the
        # target would otherwise get its earlier results attributed to a tree
        # that no longer exists.
        "target": target,
        "target_after": target_after,
        "target_stable": not observed_change(target, target_after),
        "target_binding": target.get("fingerprint_scope"),
        "execution": execution,
        "checks_digest": checks_digest,
        "result_counts": result_counts,
    }


def promised_checks_digest(registry: dict[str, Any], item_ids: list[str]) -> str:
    """Digest the acceptance checks the receipt claims to answer, in row order.

    This is what makes replaced content refusable: if the registry's promised
    checks change, or the receipt is moved onto a different registry, the digest
    no longer reproduces.
    """
    items = {item.get("id"): item for item in registry.get("items", []) if isinstance(item, dict)}
    payload = []
    for item_id in item_ids:
        item = items.get(item_id)
        packet = item.get("fix_packet") if isinstance(item, dict) else None
        acceptance = packet.get("acceptance") if isinstance(packet, dict) else None
        payload.append({"id": item_id, "acceptance": acceptance})
    return canonical_digest(payload)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ManifestError(message)


def _require_text(value: Any, label: str) -> str:
    _require(isinstance(value, str) and value.strip() != "", f"observation manifest {label} must be a non-empty string")
    return str(value)


def _require_digest(value: Any, label: str) -> str:
    digest = _require_text(value, label)
    _require(bool(DIGEST_PATTERN.match(digest)), f"observation manifest {label} must be a sha256:<64 hex> digest")
    return digest


def _require_timestamp(value: Any, label: str) -> dt.datetime:
    text = _require_text(value, label)
    try:
        return dt.datetime.fromisoformat(text)
    except ValueError:
        raise ManifestError(f"observation manifest {label} must be an ISO-8601 timestamp") from None


def _validate_target(target: Any, label: str) -> dict[str, Any]:
    """Strict shape for one identity record. Hostile JSON refuses, never raises."""
    _require(isinstance(target, dict), f"observation manifest {label} must be an object")
    kind = target.get("identity_kind")
    # `in` against an unhashable value (a parsed [] or {}) raises TypeError, so
    # the type is checked before membership.
    _require(
        isinstance(kind, str) and kind in set(contract()["target_identity_kinds"]),
        f"observation manifest {label} identity_kind {kind!r} is not in the contract",
    )
    _require_digest(target.get("path_digest"), f"{label} path_digest")
    scope = target.get("fingerprint_scope")
    allowed_scopes = {"commit_and_worktree_bytes", "incomplete", "unavailable", "path_only"}
    _require(
        isinstance(scope, str) and scope in allowed_scopes,
        f"observation manifest {label} fingerprint_scope must be one of {sorted(allowed_scopes)}",
    )
    fingerprint = target.get("content_fingerprint")
    _require(
        fingerprint is None or isinstance(fingerprint, str),
        f"observation manifest {label} content_fingerprint must be a digest or null",
    )
    if scope == "commit_and_worktree_bytes":
        _require_digest(fingerprint, f"{label} content_fingerprint")
    else:
        _require(fingerprint is None, f"observation manifest {label} claims a fingerprint it did not compute")
    if kind == "git_commit":
        commit = _require_text(target.get("commit"), f"{label} commit")
        _require(bool(re.fullmatch(r"[0-9a-f]{7,64}", commit)), f"observation manifest {label} commit must be a hex object name")
        _require(
            target.get("dirty") is None or isinstance(target["dirty"], bool),
            f"observation manifest {label} dirty must be a boolean or null",
        )
    else:
        _require(scope != "commit_and_worktree_bytes", f"observation manifest {label} cannot claim git byte scope without a commit")
    return target


def validate(
    manifest: Any,
    *,
    registry: dict[str, Any] | None = None,
    item_ids: list[str] | None = None,
    decisions: dict[str, Any] | None = None,
    expected_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Refuse a manifest that cannot support the receipt carrying it.

    `registry` and `decisions` are compared against the digests the manifest
    stored, so a receipt cannot be moved onto a different bundle. `item_ids`
    additionally reproduces the promised-checks digest. `expected_target` is the
    freshness check: supply a freshly captured identity to prove the receipt
    still describes the tree in front of you.
    """
    _require(isinstance(manifest, dict), "observation manifest must be an object")
    version = manifest.get("manifest_version")
    _require(
        isinstance(version, str) and version in supported_versions(),
        f"observation manifest version {version!r} is not readable by this contract",
    )
    for field in contract()["required_fields"]:
        _require(field in manifest, f"observation manifest is missing {field}")
    run_id = _require_text(manifest.get("run_id"), "run_id")
    try:
        uuid.UUID(run_id)
    except ValueError:
        raise ManifestError("observation manifest run_id must be a UUID") from None
    _require_text(manifest.get("tool"), "tool")
    started = _require_timestamp(manifest.get("started_at"), "started_at")
    completed = _require_timestamp(manifest.get("completed_at"), "completed_at")
    _require(completed >= started, "observation manifest completed_at precedes started_at")

    roles = set(contract()["input_roles"])
    entries = manifest.get("inputs")
    _require(isinstance(entries, list) and entries, "observation manifest inputs must be a non-empty array")
    stored: dict[str, str] = {}
    for entry in entries:
        _require(isinstance(entry, dict), "observation manifest input entries must be objects")
        role = _require_text(entry.get("role"), "input role")
        _require(role in roles, f"observation manifest input role {role!r} is not in the contract")
        _require(role not in stored, f"observation manifest repeats the {role} input")
        _require(entry.get("digest_form") == "canonical_json", f"{role} input digest_form must be canonical_json")
        stored[role] = _require_digest(entry.get("digest"), f"{role} input digest")
    _require("registry" in stored, "observation manifest must record its registry input")
    for role, document in (("registry", registry), ("decisions", decisions)):
        if document is not None and role in stored:
            _require(
                stored[role] == canonical_digest(document),
                f"observation manifest {role} digest does not match the supplied {role}",
            )

    target = _validate_target(manifest.get("target"), "target")
    after = _validate_target(manifest.get("target_after"), "target_after")
    stable = manifest.get("target_stable")
    _require(isinstance(stable, bool), "observation manifest target_stable must be a boolean")
    _require(
        stable == (not observed_change(target, after)),
        "observation manifest target_stable disagrees with its own before/after identities",
    )
    _require(
        manifest.get("target_binding") == target.get("fingerprint_scope"),
        "observation manifest target_binding must report the scope it actually captured",
    )

    execution = manifest.get("execution")
    _require(isinstance(execution, dict), "observation manifest execution must be an object")
    for field in ("executed", "shell_allowed"):
        _require(isinstance(execution.get(field), bool), f"observation manifest execution.{field} must be a boolean")
    _require(
        not execution["shell_allowed"] or execution["executed"],
        "observation manifest cannot allow shell execution in a run that executed nothing",
    )

    counts = manifest.get("result_counts")
    _require(isinstance(counts, dict), "observation manifest result_counts must be an object")
    provenance = list(contract()["result_provenance"])
    _require(set(counts) == set(provenance), f"observation manifest result_counts must cover {', '.join(provenance)}")
    for key, value in counts.items():
        _require(type(value) is int and value >= 0, f"observation manifest result_counts.{key} must be a non-negative integer")
    if not execution["executed"]:
        _require(counts["collected"] == 0, "a run that executed nothing cannot report collected results")

    digest = _require_digest(manifest.get("checks_digest"), "checks_digest")
    if registry is not None and item_ids is not None:
        _require(
            digest == promised_checks_digest(registry, item_ids),
            "observation manifest checks_digest does not match the registry's promised checks",
        )
    if expected_target is not None:
        _require(
            same_target(target, expected_target),
            "observation manifest target does not match the environment being validated",
        )
    return manifest


def confine(root: Path, paths: dict[str, Path]) -> Path:
    """Require every named artifact to resolve inside a caller-named root.

    Containment is checked on the **resolved** path of both sides, so a symlink
    anywhere in the chain cannot point out of the root, and a canonicalized root
    (macOS `/tmp` is a symlink to `/private/tmp`) still matches its own children.

    Scope, stated honestly: this confines the artifacts this tool reads and
    writes. It is not a sandbox for the checks themselves, and it says nothing
    about `--cwd`, which is the target the caller deliberately points at.
    """
    resolved_root = Path(root).resolve()
    if not resolved_root.is_dir():
        raise ManifestError(f"artifact root {root} is not an existing directory")
    for label, path in paths.items():
        if path is None:
            continue
        resolved = Path(path).resolve()
        if resolved != resolved_root and resolved_root not in resolved.parents:
            raise ManifestError(f"{label} resolves outside the artifact root; refusing to read or write outside the bundle")
    return resolved_root


def environment(allowlist: list[str] | None = None) -> tuple[dict[str, str], list[str]]:
    """Build the small documented environment a check runs with.

    Default: no ambient secrets. Only the variables a process needs to start and
    resolve a program are inherited, plus whatever the *caller* names on the
    command line. An artifact cannot add to this list; the packet is untrusted
    input, and a check that needs a credential must have it passed deliberately.
    """
    base_keys = ("PATH", "HOME", "LANG", "LC_ALL", "TZ", "TMPDIR", "SYSTEMROOT", "COMSPEC", "PATHEXT", "USERPROFILE")
    env = {key: os.environ[key] for key in base_keys if key in os.environ}
    env.setdefault("PATH", os.defpath)
    env["SCRUFFY_VERIFICATION"] = "1"
    passed = []
    for name in allowlist or []:
        if name in os.environ:
            env[name] = os.environ[name]
            passed.append(name)
    return env, sorted(set(passed))


def _load(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ManifestError(f"{path.name} must contain a JSON object")
    return document


def main(argv: list[str] | None = None) -> int:
    """Check a receipt's manifest, optionally against the target in front of you.

    Ordinary registry validation can only prove a receipt is internally coherent
    and answers a given bundle. It cannot know whether the target still looks
    like the one that was observed — nobody re-reads the working tree during a
    document check. That is what `--cwd` is for here, and it is why freshness is
    an explicit, opt-in question rather than an implied property of any receipt.
    """
    parser = argparse.ArgumentParser(description="Validate an observation manifest on a verification receipt.")
    parser.add_argument("receipt", type=Path, help="verification.json carrying an observation_manifest")
    parser.add_argument("--registry", type=Path, help="findings.json the receipt claims to answer")
    parser.add_argument("--decisions", type=Path, help="decisions.json read by that run")
    parser.add_argument("--cwd", type=Path, help="target directory to re-read: refuses a stale or moved target")
    args = parser.parse_args(argv)
    try:
        receipt = _load(args.receipt)
        manifest = receipt.get("observation_manifest")
        if manifest is not None and not isinstance(manifest, dict):
            raise ManifestError("observation_manifest must be an object")
        if manifest is None:
            print(
                "FAIL: this receipt carries no observation manifest. Receipts written before this "
                "contract are readable but cannot prove run, input, or target binding.",
                file=sys.stderr,
            )
            return 1
        registry = _load(args.registry) if args.registry else None
        decisions = _load(args.decisions) if args.decisions else None
        rows = receipt.get("items")
        if not isinstance(rows, list):
            raise ManifestError("receipt items must be an array; this file is not a verification receipt")
        item_ids = [row["id"] for row in rows if isinstance(row, dict) and isinstance(row.get("id"), str)]
        expected = None
        if args.cwd:
            execution = manifest.get("execution") if isinstance(manifest, dict) else None
            execution = execution if isinstance(execution, dict) else {}
            expected = target_identity(
                args.cwd,
                ignore=ignore_predicate(
                    args.cwd,
                    [d for d in execution.get("excluded_path_digests", []) or [] if isinstance(d, str)],
                    [g for g in execution.get("target_ignore_globs", []) or [] if isinstance(g, str)],
                ),
            )
        if expected is not None and expected.get("fingerprint_scope") != "commit_and_worktree_bytes":
            raise ManifestError(
                f"cannot prove freshness against this target: byte fingerprint is {expected.get('fingerprint_scope')}"
            )
        validate(
            manifest,
            registry=registry,
            item_ids=item_ids if registry is not None else None,
            decisions=decisions,
            expected_target=expected,
        )
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    checked = ["run and input shape"]
    if args.registry:
        checked.append("registry digest and promised checks")
    if args.decisions:
        checked.append("decisions digest")
    checked.append("target freshness" if args.cwd else "target freshness NOT checked (no --cwd)")
    if not manifest.get("target_stable"):
        print("WARN: the target changed while that run executed; its results are not target-bound", file=sys.stderr)
    print(f"PASS: observation manifest {manifest['run_id']} — " + "; ".join(checked))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
