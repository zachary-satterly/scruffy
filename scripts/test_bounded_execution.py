#!/usr/bin/env python3
"""Real-subprocess guards for bounded command execution and run provenance.

Every case here launches actual processes. A check that runs commands cannot be
proven by mocking the thing that runs commands: the questions are whether a
metacharacter reaches a shell, whether a runaway child is actually killed,
whether a flood is bounded while it is being read, and whether the receipt can
still be trusted after someone edits the bundle underneath it.
"""

from __future__ import annotations

import copy
import json
import os
import signal
import subprocess
import sys
import threading
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import observation_manifest as om  # noqa: E402
from report_contract import check_summary  # noqa: E402
from render_dashboard import check_summary as dashboard_summary, fix_packet_html  # noqa: E402
from render_markdown import check_summary as markdown_summary, fix_packet_block  # noqa: E402
from validate_audit import validate_verification_receipt  # noqa: E402

VERIFY = ROOT / "scripts" / "verify_fixes.py"
CONTINUITY = ROOT / "evals" / "continuity"
ITEM = "AS-02"
POSIX = os.name == "posix"


def git_repo(directory: Path) -> bool:
    """Make a real one-commit repository. False when git is unavailable."""
    commands = [
        ["git", "init", "-q"],
        ["git", "config", "user.email", "verify@example.invalid"],
        ["git", "config", "user.name", "Verify"],
        ["git", "add", "-A"],
        ["git", "-c", "commit.gpgsign=false", "commit", "-qm", "baseline"],
    ]
    (directory / "tracked.txt").write_text("original\n", encoding="utf-8")
    for command in commands:
        try:
            result = subprocess.run(command, cwd=directory, capture_output=True, text=True, timeout=60)
        except OSError:
            return False
        if result.returncode:
            return False
    return True


def packet(acceptance: list[dict]) -> dict:
    return {
        "target": [{"kind": "file", "value": "router.py"}],
        "change": "Give each lesson a stable address.",
        "effort": "S",
        "rollback": "Revert router.py.",
        "acceptance": acceptance,
    }


class Bundle:
    """A minimal approved bundle on disk, plus a verifier invocation."""

    def __init__(self, directory: Path, acceptance: list[dict]) -> None:
        self.directory = directory
        self.registry = json.loads((CONTINUITY / "revision.json").read_text(encoding="utf-8"))
        decisions = json.loads((CONTINUITY / "decisions.json").read_text(encoding="utf-8"))
        next(i for i in self.registry["items"] if i["id"] == ITEM)["fix_packet"] = packet(acceptance)
        next(r for r in decisions["decisions"] if r["item_id"] == ITEM)["decision"] = "approve"
        self.decisions = decisions
        self.registry_path = directory / "findings.json"
        self.decisions_path = directory / "decisions.json"
        self.output = directory / "verification.json"
        self.registry_path.write_text(json.dumps(self.registry), encoding="utf-8")
        self.decisions_path.write_text(json.dumps(decisions), encoding="utf-8")

    def verify(self, *extra: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
        command = [
            sys.executable, str(VERIFY), str(self.registry_path),
            "--decisions", str(self.decisions_path),
            "--cwd", str(self.directory),
            "--output", str(self.output),
            *extra,
        ]
        return subprocess.run(command, capture_output=True, text=True, timeout=180, env=env)

    def receipt(self) -> dict:
        return json.loads(self.output.read_text(encoding="utf-8"))

    def checks(self) -> list[dict]:
        return self.receipt()["items"][0]["checks"]


class BoundedExecution(unittest.TestCase):
    def test_argv_metacharacters_stay_literal(self):
        """No shell runs an argv check, so `;` and `$(...)` are just text."""
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            payload = "lesson; touch pwned.txt; $(touch also-pwned.txt)"
            bundle = Bundle(directory, [{
                "kind": "command",
                "argv": [sys.executable, "-c", "import sys; print(sys.argv[1])", payload],
                "expect": {"stdout_contains": payload},
                "summary": "argument reaches the program unmodified",
            }])
            result = bundle.verify("--execute")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(bundle.checks()[0]["result"], "pass")
            self.assertFalse((directory / "pwned.txt").exists())
            self.assertFalse((directory / "also-pwned.txt").exists())

    def test_legacy_shell_needs_an_explicit_opt_in(self):
        """A legacy `run` string stays readable, refuses by default, and an
        artifact field cannot turn the shell on for itself."""
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            marker = directory / "shell-ran.txt"
            bundle = Bundle(directory, [{
                "kind": "command",
                "run": f"{sys.executable} -c \"open(r'{marker}','w').write('x')\"",
                "summary": "legacy readable command",
                # Artifact-supplied fields that look like permission grants.
                "allow_shell": True,
                "shell": True,
            }])
            refused = bundle.verify("--execute")
            self.assertEqual(refused.returncode, 0, refused.stderr)
            row = bundle.checks()[0]
            self.assertEqual(row["result"], "not_run")
            self.assertEqual(row["observation"]["status"], "refused_no_shell_opt_in")
            self.assertEqual(bundle.receipt()["items"][0]["result"], "not_run")
            self.assertFalse(marker.exists(), "artifact fields must not grant shell permission")
            self.assertIn("legacy shell checks refused", refused.stdout)

            allowed = bundle.verify("--execute", "--allow-shell")
            self.assertEqual(allowed.returncode, 0, allowed.stderr)
            self.assertEqual(bundle.checks()[0]["result"], "pass")
            self.assertTrue(marker.exists())
            self.assertTrue(bundle.receipt()["observation_manifest"]["execution"]["shell_allowed"])

    def test_allow_shell_requires_execute(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            bundle = Bundle(directory, [{"kind": "command", "argv": [sys.executable, "-c", "pass"]}])
            result = bundle.verify("--allow-shell")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--allow-shell only means something beside --execute", result.stderr)
            self.assertFalse(bundle.output.exists())

    def test_timeout_bounds_the_caller_not_the_artifact(self):
        """The packet asks for 600s; the caller's ceiling wins and the process dies."""
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            bundle = Bundle(directory, [{
                "kind": "command",
                "argv": [sys.executable, "-c", "import time; time.sleep(600)"],
                "timeout": 600,
                "summary": "a check that never returns",
            }])
            started = time.monotonic()
            result = bundle.verify("--execute", "--max-seconds", "1")
            elapsed = time.monotonic() - started
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertLess(elapsed, 60, "a timed-out check must not run to the packet's timeout")
            row = bundle.checks()[0]
            self.assertEqual(row["result"], "fail")
            self.assertEqual(row["observation"]["status"], "timed_out")
            self.assertEqual(row["observation"]["timeout_seconds"], 1)
            self.assertIsNone(row["observation"]["exit_code"])

    @unittest.skipUnless(POSIX, "process-group cleanup is POSIX-only; elsewhere only the direct child is stopped")
    def test_timeout_reaps_grandchildren(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            marker = directory / "grandchild.txt"
            child = f"import time; from pathlib import Path; time.sleep(4); Path(r'{marker}').write_text('x')"
            parent = f"import subprocess, sys, time; subprocess.Popen([sys.executable, '-c', {child!r}]); time.sleep(600)"
            bundle = Bundle(directory, [{
                "kind": "command",
                "argv": [sys.executable, "-c", parent],
                "summary": "a check that spawns a background process",
            }])
            result = bundle.verify("--execute", "--max-seconds", "1")
            self.assertEqual(result.returncode, 1, result.stdout)
            time.sleep(6)
            self.assertFalse(marker.exists(), "the grandchild outlived its process group")
            self.assertEqual(bundle.checks()[0]["observation"]["child_cleanup"], "process_group")

    def test_output_flood_is_bounded_while_reading(self):
        """A check that prints megabytes is capped, and the cap is honest.

        The expectation is unmet because the needle is past the cap, so the
        check fails rather than passing on evidence that was never read.
        """
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            flood = "import sys\nsys.stdout.write('x' * 2_000_000)\nsys.stdout.write('NEEDLE')\n"
            bundle = Bundle(directory, [{
                "kind": "command",
                "argv": [sys.executable, "-c", flood],
                "expect": {"stdout_contains": "NEEDLE"},
                "summary": "a check that floods stdout",
            }])
            result = bundle.verify("--execute", "--max-output-bytes", "4096")
            self.assertEqual(result.returncode, 1, result.stdout)
            row = bundle.checks()[0]
            self.assertEqual(row["result"], "fail")
            self.assertTrue(row["observation"]["output_truncated"])
            self.assertGreater(row["observation"]["stdout_bytes"], 4096)
            self.assertEqual(row["observation"]["expectations"]["stdout_contains"], "unmet")
            self.assertLess(bundle.output.stat().st_size, 64 * 1024, "the receipt grew with the flood")
            self.assertNotIn("xxxxxxxxxx", bundle.output.read_text(encoding="utf-8"))

    def test_failure_detail_keeps_status_and_drops_output(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            secret = "hunter2-token-value"
            bundle = Bundle(directory, [{
                "kind": "command",
                "argv": [sys.executable, "-c", f"import sys; sys.stderr.write('{secret}'); raise SystemExit(3)"],
                "summary": "a failing check that prints a credential",
            }])
            result = bundle.verify("--execute")
            self.assertEqual(result.returncode, 1)
            text = bundle.output.read_text(encoding="utf-8")
            self.assertNotIn(secret, text)
            self.assertNotIn("SystemExit", text)
            row = bundle.checks()[0]
            self.assertEqual(row["result"], "fail")
            self.assertIn("exited 3, expected 0", row["detail"])
            self.assertEqual(row["observation"]["exit_code"], 3)
            self.assertEqual(row["observation"]["expectations"]["exit_code"], "unmet")

    def test_ambient_environment_is_not_inherited_without_an_allowlist(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            probe = "import os, sys; sys.exit(0 if os.environ.get('SCRUFFY_AMBIENT_SECRET') is None else 9)"
            bundle = Bundle(directory, [{
                "kind": "command",
                "argv": [sys.executable, "-c", probe],
                "summary": "the ambient secret is absent",
            }])
            environment = {**os.environ, "SCRUFFY_AMBIENT_SECRET": "leaked"}
            self.assertEqual(bundle.verify("--execute", env=environment).returncode, 0)
            self.assertEqual(bundle.checks()[0]["result"], "pass")
            passed = bundle.verify("--execute", "--env-allow", "SCRUFFY_AMBIENT_SECRET", env=environment)
            self.assertEqual(passed.returncode, 1, "the allowlisted variable never reached the check")
            self.assertEqual(
                bundle.receipt()["observation_manifest"]["execution"]["environment_allowlist"],
                ["SCRUFFY_AMBIENT_SECRET"],
            )

    def test_neighbouring_checks_are_evaluated_independently(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            bundle = Bundle(directory, [
                {"kind": "command", "argv": [sys.executable, "-c", "print('ok')"],
                 "expect": {"stdout_contains": "ok"}, "summary": "the repair holds"},
                {"kind": "command", "argv": [sys.executable, "-c", "raise SystemExit(1)"],
                 "summary": "the neighbouring invariant"},
                {"kind": "dom_state", "selector": "main h1", "expect": {"text_contains": "Lesson 3"},
                 "summary": "browser evidence"},
            ])
            results = directory / "results.json"
            results.write_text(json.dumps({f"{ITEM}:2": {"result": "pass", "detail": "observed in a browser"}}), encoding="utf-8")
            result = bundle.verify("--execute", "--results", str(results))
            self.assertEqual(result.returncode, 1, result.stdout)
            rows = bundle.checks()
            self.assertEqual([row["result"] for row in rows], ["pass", "fail", "pass"])
            self.assertEqual([row["provenance"] for row in rows], ["collected", "collected", "imported"])
            self.assertEqual(bundle.receipt()["items"][0]["result"], "failed")
            counts = bundle.receipt()["observation_manifest"]["result_counts"]
            self.assertEqual(counts, {"collected": 2, "imported": 1, "not_collected": 0})

    def test_artifact_escaping_the_root_is_refused_before_execution(self):
        """Confinement is about resolved containment, not symlinks as such.

        A link that stays inside the root is fine; one that resolves out of it is
        how a receipt gets written somewhere nobody is looking.
        """
        with tempfile.TemporaryDirectory() as raw, tempfile.TemporaryDirectory() as outside_raw:
            directory, outside = Path(raw), Path(outside_raw)
            marker = directory / "executed.txt"
            bundle = Bundle(directory, [{
                "kind": "command",
                "argv": [sys.executable, "-c", f"open(r'{marker}','w').write('x')"],
            }])
            escape = outside / "elsewhere.json"
            escape.write_text("previous receipt", encoding="utf-8")
            link = directory / "linked-verification.json"
            try:
                link.symlink_to(escape)
            except (OSError, NotImplementedError):  # pragma: no cover - platform without symlinks
                self.skipTest("this platform cannot create symlinks")
            escaping = subprocess.run(
                [sys.executable, str(VERIFY), str(bundle.registry_path), "--decisions", str(bundle.decisions_path),
                 "--cwd", str(directory), "--execute", "--output", str(link)],
                capture_output=True, text=True, timeout=60,
            )
            self.assertNotEqual(escaping.returncode, 0)
            self.assertIn("outside the artifact root", escaping.stderr)
            self.assertFalse(marker.exists(), "a refused preflight must run nothing")
            self.assertEqual(escape.read_text(encoding="utf-8"), "previous receipt")

            # A plain path inside the same root still works, and an explicit
            # --artifact-root that does not contain the bundle is refused too.
            self.assertEqual(bundle.verify("--execute").returncode, 0)
            wrong_root = subprocess.run(
                [sys.executable, str(VERIFY), str(bundle.registry_path), "--decisions", str(bundle.decisions_path),
                 "--cwd", str(directory), "--output", str(bundle.output), "--artifact-root", str(outside)],
                capture_output=True, text=True, timeout=60,
            )
            self.assertNotEqual(wrong_root.returncode, 0)
            self.assertIn("outside the artifact root", wrong_root.stderr)

    @unittest.skipUnless(POSIX, "process-group cleanup is POSIX-only")
    def test_exiting_leader_does_not_hide_surviving_descendants(self):
        """The counterexample Codex reproduced: a SIGTERM-ignoring child.

        The leader used to be reaped and the group left alone, so a child that
        ignored SIGTERM outlived the run and the check still read as completed.
        """
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            marker = directory / "survivor.txt"
            stubborn = (
                "import signal, time; from pathlib import Path; "
                "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
                f"time.sleep(8); Path(r'{marker}').write_text('x')"
            )
            parent = f"import subprocess, sys; subprocess.Popen([sys.executable, '-c', {stubborn!r}])"
            bundle = Bundle(directory, [{
                "kind": "command",
                "argv": [sys.executable, "-c", parent],
                "summary": "a check whose child ignores SIGTERM and outlives it",
            }])
            result = bundle.verify("--execute", "--max-seconds", "5")
            self.assertEqual(result.returncode, 1, result.stdout)
            row = bundle.checks()[0]
            self.assertEqual(row["result"], "fail", "a run with survivors must not read as a pass")
            self.assertEqual(row["observation"]["status"], "completed_with_survivors")
            self.assertTrue(row["observation"]["descendants_terminated"])
            time.sleep(9)
            self.assertFalse(marker.exists(), "the SIGTERM-ignoring child survived the run")


class CheckRendering(unittest.TestCase):
    """Both review surfaces must say something useful about an argv check.

    A reviewer approves what the surfaces show them. An argv check with no
    author summary rendered as "no detail recorded" on both, which is a decision
    made blind.
    """

    def test_argv_without_a_summary_is_shown_on_both_surfaces(self):
        check = {"kind": "command", "argv": ["python3", "-m", "unittest"]}
        rendered = check_summary(check)
        self.assertEqual(rendered, 'argv: ["python3", "-m", "unittest"]')
        self.assertNotIn("no detail recorded", rendered)
        # The same helper backs both renderers, so neither can drift.
        self.assertIs(markdown_summary, check_summary)
        self.assertIs(dashboard_summary, check_summary)

    def test_argument_boundaries_and_empty_arguments_survive(self):
        self.assertEqual(
            check_summary({"kind": "command", "argv": ["grep", "", "a file.txt"]}),
            'argv: ["grep", "", "a file.txt"]',
        )
        # Not a pasteable shell line: the quoting is JSON, and it stays data.
        joined = check_summary({"kind": "command", "argv": ["rm", "-rf", "/tmp/x y"]})
        self.assertNotEqual(joined, "rm -rf /tmp/x y")
        self.assertTrue(joined.startswith("argv: ["))

    def test_hostile_argv_text_is_escaped_by_the_dashboard(self):
        hostile = '<script>alert("x")</script>'
        item = {
            "id": "AS-02", "kind": "finding", "title": "t", "status": "open",
            "fix_packet": {
                "target": [{"kind": "file", "value": "app.py"}],
                "change": "c", "effort": "S", "rollback": "r",
                "acceptance": [{"kind": "command", "argv": ["echo", hostile, ""]}],
            },
        }
        html = fix_packet_html(item)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html)
        self.assertIn("argv:", html)
        markdown = fix_packet_block(item)
        # Markdown is not HTML: the text stays literal, quoted as JSON data, and
        # the empty trailing argument is still visible.
        self.assertIn(r'argv: ["echo", "<script>alert(\"x\")</script>", ""]', markdown)

    def test_adjacent_check_shapes_are_unchanged(self):
        for check, expected in (
            ({"kind": "command", "argv": ["true"], "summary": "the author's words"}, "the author's words"),
            ({"kind": "command", "run": "pytest -q tests/"}, "pytest -q tests/"),
            ({"kind": "manual", "summary": "a colleague opens the link"}, "a colleague opens the link"),
            ({"kind": "dom_state", "selector": "main h1"}, "main h1"),
            ({"kind": "measurement", "metric": "lcp_ms"}, "lcp_ms"),
            ({"kind": "command", "expect": {"exit_code": 3}}, '{"exit_code": 3}'),
            ({"kind": "command"}, "no detail recorded"),
            ({"kind": "command", "argv": []}, "no detail recorded"),
            ({"kind": "command", "argv": "not a list"}, "no detail recorded"),
        ):
            with self.subTest(check=check):
                self.assertEqual(check_summary(check), expected)


class RunLifecycle(unittest.TestCase):
    """A run in progress must never be readable as the previous run's success."""

    @unittest.skipUnless(POSIX, "SIGINT delivery to a process group is POSIX-only")
    def test_interruption_cannot_leave_the_previous_success_readable(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            wait = "import os, time; time.sleep(int(os.environ.get('QA_WAIT', '0')))"
            bundle = Bundle(directory, [{
                "kind": "command",
                "argv": [sys.executable, "-c", wait],
                "summary": "a check whose duration the environment controls",
            }])
            environment = {**os.environ, "QA_WAIT": "0"}
            first = bundle.verify("--execute", "--env-allow", "QA_WAIT", env=environment)
            self.assertEqual(first.returncode, 0, first.stderr)
            success = bundle.receipt()
            self.assertEqual(success["items"][0]["result"], "verified")
            self.assertEqual(success["run_state"], "complete")
            previous_bytes = bundle.output.read_bytes()

            # Same registry, same command, same output path: only the wait changes.
            environment["QA_WAIT"] = "20"
            process = subprocess.Popen(
                [sys.executable, str(VERIFY), str(bundle.registry_path), "--decisions", str(bundle.decisions_path),
                 "--cwd", str(directory), "--execute", "--env-allow", "QA_WAIT", "--output", str(bundle.output)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=environment, start_new_session=True,
            )
            time.sleep(1)
            os.killpg(os.getpgid(process.pid), signal.SIGINT)
            try:
                _, errors = process.communicate(timeout=60)
            except subprocess.TimeoutExpired:  # pragma: no cover - runner did not stop
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                raise
            self.assertNotEqual(process.returncode, 0)
            self.assertNotEqual(bundle.output.read_bytes(), previous_bytes, "the stale success survived the interruption")
            interrupted = bundle.receipt()
            self.assertEqual(interrupted["run_state"], "started")
            self.assertEqual(interrupted["items"], [])
            self.assertNotEqual(interrupted["run_id"], success["run_id"])
            self.assertFalse(interrupted["executed_commands"])
            self.assertIn("do not read this as a result", interrupted["note"])
            self.assertIn("interrupted", errors)

    def test_preflight_refusal_preserves_the_historical_receipt(self):
        """The other half of the rule: a run that never started takes nothing."""
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            bundle = Bundle(directory, [{"kind": "command", "argv": [sys.executable, "-c", "pass"]}])
            self.assertEqual(bundle.verify("--execute").returncode, 0)
            historical = bundle.output.read_bytes()
            bundle.decisions_path.write_text(json.dumps({"schema_version": "2.1"}), encoding="utf-8")
            refused = bundle.verify("--execute")
            self.assertNotEqual(refused.returncode, 0)
            self.assertEqual(bundle.output.read_bytes(), historical, "a refused preflight must not touch the receipt")

    def test_inputs_outside_the_root_are_never_opened(self):
        with tempfile.TemporaryDirectory() as raw, tempfile.TemporaryDirectory() as outside_raw:
            directory, outside = Path(raw), Path(outside_raw)
            bundle = Bundle(directory, [{"kind": "command", "argv": [sys.executable, "-c", "pass"]}])
            # Unparseable on purpose: if containment ran after the read, the
            # error would be about JSON rather than about the boundary.
            escaped = outside / "decisions.json"
            escaped.write_text("{ this is not json", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(VERIFY), str(bundle.registry_path), "--decisions", str(escaped),
                 "--cwd", str(directory), "--output", str(bundle.output)],
                capture_output=True, text=True, timeout=60,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("outside the artifact root", result.stderr)
            for leak in ("Expecting", "JSONDecodeError", "Traceback"):
                self.assertNotIn(leak, result.stderr)

    def test_a_target_outside_the_artifact_root_is_still_allowed(self):
        """Confinement covers bundle artifacts, not the target being verified."""
        with tempfile.TemporaryDirectory() as raw, tempfile.TemporaryDirectory() as target_raw:
            directory, target = Path(raw), Path(target_raw)
            bundle = Bundle(directory, [{
                "kind": "command",
                "argv": [sys.executable, "-c", "from pathlib import Path; assert Path('marker.txt').exists()"],
                "summary": "the check reads the separate target directory",
            }])
            (target / "marker.txt").write_text("present", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(VERIFY), str(bundle.registry_path), "--decisions", str(bundle.decisions_path),
                 "--cwd", str(target), "--execute", "--output", str(bundle.output)],
                capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(bundle.receipt()["items"][0]["result"], "verified")


class FingerprintBounds(unittest.TestCase):
    def test_oversized_and_special_files_end_the_content_claim(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            big = directory / "big.bin"
            big.write_bytes(b"x" * 4096)
            self.assertIsNone(om._file_digest(big, 1024), "a file over the cap must not be hashed")
            self.assertTrue(om._file_digest(big, 8192).startswith("sha256:"))
            self.assertEqual(om._file_digest(directory / "missing.txt", 1024), "absent")
            self.assertIsNone(om._file_digest(directory, 1024), "a directory has no in-scope content")

    def test_a_file_that_grows_past_the_cap_while_read_is_refused(self):
        """stat is a filter, not the bound; the read loop counts what it takes."""
        with tempfile.TemporaryDirectory() as raw:
            grower = Path(raw) / "grows.bin"
            grower.write_bytes(b"y" * 512)
            original_open = Path.open

            def growing_open(self, *args, **kwargs):
                handle = original_open(self, *args, **kwargs)
                if self == grower:
                    # Built-in open, not Path.open: this hook is the patch.
                    with open(str(grower), "wb") as growth:
                        growth.write(b"y" * (1024 * 1024))
                return handle

            Path.open = growing_open
            try:
                self.assertIsNone(om._file_digest(grower, 4096))
            finally:
                Path.open = original_open

    @unittest.skipUnless(POSIX, "named pipes are POSIX-only")
    def test_a_fifo_is_refused_rather_than_read(self):
        """Opening a FIFO for reading blocks until a writer appears."""
        with tempfile.TemporaryDirectory() as raw:
            fifo = Path(raw) / "pipe"
            os.mkfifo(fifo)
            finished = []

            def probe():
                finished.append(om._file_digest(fifo, 1024))

            worker = threading.Thread(target=probe, daemon=True)
            worker.start()
            worker.join(timeout=10)
            self.assertFalse(worker.is_alive(), "reading a FIFO blocked the fingerprint scan")
            self.assertEqual(finished, [None])


class RunProvenance(unittest.TestCase):
    """The manifest must bind a receipt to one run, one bundle, one target."""

    def setUp(self):
        self.raw = tempfile.TemporaryDirectory()
        directory = Path(self.raw.name)
        self.git = git_repo(directory)
        self.bundle = Bundle(directory, [{
            "kind": "command",
            "argv": [sys.executable, "-c", "print('ok')"],
            "summary": "the repair holds",
        }])
        self.assertEqual(self.bundle.verify("--execute").returncode, 0)
        self.receipt = self.bundle.receipt()
        self.manifest = self.receipt["observation_manifest"]

    def tearDown(self):
        self.raw.cleanup()

    def test_receipt_validates_and_records_its_run(self):
        validate_verification_receipt(self.receipt, self.bundle.registry, self.bundle.decisions)
        self.assertEqual(self.manifest["manifest_version"], om.current_version())
        self.assertEqual(self.manifest["tool"], "scruffy/verify_fixes")
        self.assertEqual({entry["role"] for entry in self.manifest["inputs"]}, {"registry", "decisions"})
        self.assertTrue(self.manifest["execution"]["executed"])
        self.assertFalse(self.manifest["execution"]["shell_allowed"])

    def test_each_run_gets_a_distinct_run_id(self):
        first = self.manifest["run_id"]
        self.assertEqual(self.bundle.verify("--execute").returncode, 0)
        self.assertNotEqual(self.bundle.receipt()["observation_manifest"]["run_id"], first)

    def test_manifest_records_no_paths_or_command_text(self):
        text = json.dumps(self.manifest)
        self.assertNotIn(str(self.bundle.directory), text)
        self.assertNotIn(sys.executable, text)
        self.assertNotIn("print('ok')", text)

    def test_replaced_promised_checks_refuse_validation(self):
        tampered = copy.deepcopy(self.bundle.registry)
        item = next(i for i in tampered["items"] if i["id"] == ITEM)
        item["fix_packet"]["acceptance"][0]["argv"] = [sys.executable, "-c", "pass"]
        with self.assertRaises(ValueError):
            validate_verification_receipt(self.receipt, tampered, self.bundle.decisions)

    def test_unknown_version_and_malformed_fields_refuse(self):
        mutations = [("manifest_version", "9.9"), ("run_id", ""), ("checks_digest", "sha256:00"),
                     ("result_counts", {"collected": 1}), ("target", "somewhere"), ("inputs", [])]
        for field, value in mutations:
            with self.subTest(field=field):
                bad = copy.deepcopy(self.receipt)
                bad["observation_manifest"][field] = value
                with self.assertRaises(ValueError):
                    validate_verification_receipt(bad, self.bundle.registry, self.bundle.decisions)
        for field in ("run_id", "target", "execution", "checks_digest", "result_counts"):
            with self.subTest(missing=field):
                bad = copy.deepcopy(self.receipt)
                del bad["observation_manifest"][field]
                with self.assertRaises(ValueError):
                    validate_verification_receipt(bad, self.bundle.registry, self.bundle.decisions)

    def reread_target(self, directory: Path | None = None) -> dict:
        """Re-read a target the way a consumer does: with the run's own rule."""
        execution = self.manifest["execution"]
        return om.target_identity(
            directory or self.bundle.directory,
            ignore=om.ignore_predicate(
                directory or self.bundle.directory,
                execution["excluded_path_digests"],
                execution["target_ignore_globs"],
            ),
        )

    def test_target_mismatch_refuses(self):
        if not self.git:
            self.skipTest("git is unavailable; byte fingerprints cannot be captured")
        self.assertEqual(self.manifest["target_binding"], "commit_and_worktree_bytes")
        om.validate(self.manifest, expected_target=self.reread_target())
        with tempfile.TemporaryDirectory() as other:
            with self.assertRaises(om.ManifestError):
                om.validate(self.manifest, expected_target=self.reread_target(Path(other)))

    def test_editing_an_already_modified_file_changes_the_fingerprint(self):
        """The counterexample Codex reproduced.

        Commit plus `git status` output is stable across content edits: the file
        was already modified, so the status letters do not move. Only hashing the
        bytes tells the two worktrees apart.
        """
        if not self.git:
            self.skipTest("git is unavailable; byte fingerprints cannot be captured")
        directory = self.bundle.directory
        tracked = directory / "tracked.txt"
        tracked.write_text("candidate one\n", encoding="utf-8")
        first = om.target_identity(directory)
        tracked.write_text("candidate two\n", encoding="utf-8")
        second = om.target_identity(directory)
        self.assertEqual(first["commit"], second["commit"])
        self.assertTrue(first["dirty"] and second["dirty"])
        self.assertEqual(first["fingerprint_scope"], "commit_and_worktree_bytes")
        self.assertNotEqual(first["content_fingerprint"], second["content_fingerprint"])
        self.assertTrue(om.observed_change(first, second))
        self.assertFalse(om.same_target(first, second))
        # A receipt collected against the earlier bytes is refused as stale.
        with self.assertRaises(om.ManifestError):
            om.validate(self.manifest, expected_target=second)

    def test_a_check_that_edits_the_target_cannot_verify(self):
        if not self.git:
            self.skipTest("git is unavailable; byte fingerprints cannot be captured")
        directory = self.bundle.directory
        target = directory / "tracked.txt"
        bundle = Bundle(directory, [{
            "kind": "command",
            "argv": [sys.executable, "-c", f"open(r'{target}','a').write('edited by the check')"],
            "summary": "a check that edits its own target",
        }])
        outcome = bundle.verify("--execute")
        self.assertEqual(outcome.returncode, 0, outcome.stdout + outcome.stderr)
        receipt = bundle.receipt()
        self.assertFalse(receipt["observation_manifest"]["target_stable"])
        row = receipt["items"][0]
        self.assertEqual(row["checks"][0]["result"], "pass", "the check-level fact is kept")
        self.assertEqual(row["result"], "not_run", "the item-level claim is withdrawn")
        self.assertTrue(row["target_changed"])
        validate_verification_receipt(receipt, bundle.registry, bundle.decisions)
        forged = copy.deepcopy(receipt)
        forged["items"][0]["result"] = "verified"
        with self.assertRaises(ValueError):
            validate_verification_receipt(forged, bundle.registry, bundle.decisions)

    def test_own_receipt_does_not_invalidate_its_own_run(self):
        """The receipt lands inside the target here; that must not count as drift."""
        if not self.git:
            self.skipTest("git is unavailable; byte fingerprints cannot be captured")
        self.assertTrue(self.bundle.output.exists())
        self.assertTrue(self.manifest["target_stable"])
        self.assertEqual(self.receipt["items"][0]["result"], "verified")

    def test_stored_input_digests_are_compared(self):
        moved = copy.deepcopy(self.bundle.registry)
        moved["items"].append({"id": "AS-99"})
        with self.assertRaises(ValueError):
            om.validate(self.manifest, registry=moved)
        altered = copy.deepcopy(self.bundle.decisions)
        altered["decisions"][0]["notes"] = "edited after the run"
        with self.assertRaises(om.ManifestError):
            om.validate(self.manifest, registry=self.bundle.registry, decisions=altered)

    def test_freshness_cli_reports_what_it_checked(self):
        if not self.git:
            self.skipTest("git is unavailable; byte fingerprints cannot be captured")
        command = [sys.executable, str(ROOT / "scripts/observation_manifest.py"), str(self.bundle.output),
                   "--registry", str(self.bundle.registry_path), "--decisions", str(self.bundle.decisions_path)]
        fresh = subprocess.run([*command, "--cwd", str(self.bundle.directory)], capture_output=True, text=True, timeout=60)
        self.assertEqual(fresh.returncode, 0, fresh.stderr)
        self.assertIn("target freshness", fresh.stdout)
        (self.bundle.directory / "tracked.txt").write_text("moved on\n", encoding="utf-8")
        stale = subprocess.run([*command, "--cwd", str(self.bundle.directory)], capture_output=True, text=True, timeout=60)
        self.assertNotEqual(stale.returncode, 0)
        self.assertIn("does not match the environment", stale.stderr)
        # Without --cwd the document still validates, and says freshness was not checked.
        document_only = subprocess.run(command, capture_output=True, text=True, timeout=60)
        self.assertEqual(document_only.returncode, 0, document_only.stderr)
        self.assertIn("target freshness NOT checked", document_only.stdout)

    def test_dry_run_cannot_claim_collected_results(self):
        self.assertEqual(self.bundle.verify().returncode, 0)
        manifest = self.bundle.receipt()["observation_manifest"]
        self.assertFalse(manifest["execution"]["executed"])
        self.assertEqual(manifest["result_counts"]["collected"], 0)
        bad = copy.deepcopy(self.bundle.receipt())
        bad["observation_manifest"]["result_counts"]["collected"] = 1
        with self.assertRaises(ValueError):
            validate_verification_receipt(bad, self.bundle.registry, self.bundle.decisions)

    def test_malformed_receipt_containers_refuse_without_a_traceback(self):
        broken = self.bundle.directory / "broken.json"
        for label, document in (
            ("items null", {"observation_manifest": self.manifest, "items": None}),
            ("manifest not an object", {"observation_manifest": "trust me", "items": []}),
            ("not an object", ["a receipt is not a list"]),
        ):
            with self.subTest(label=label):
                broken.write_text(json.dumps(document), encoding="utf-8")
                result = subprocess.run(
                    [sys.executable, str(ROOT / "scripts/observation_manifest.py"), str(broken)],
                    capture_output=True, text=True, timeout=60,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("FAIL:", result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_receipts_without_a_manifest_still_validate(self):
        """Schema-1.0 receipts written before this contract are not rewritten."""
        legacy = copy.deepcopy(self.receipt)
        del legacy["observation_manifest"]
        validate_verification_receipt(legacy, self.bundle.registry, self.bundle.decisions)
        cli = subprocess.run(
            [sys.executable, str(ROOT / "scripts/observation_manifest.py"), str(self.bundle.output)],
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(cli.returncode, 0)
        stripped = self.bundle.directory / "legacy-verification.json"
        stripped.write_text(json.dumps(legacy), encoding="utf-8")
        weaker = subprocess.run(
            [sys.executable, str(ROOT / "scripts/observation_manifest.py"), str(stripped)],
            capture_output=True, text=True, timeout=60,
        )
        self.assertNotEqual(weaker.returncode, 0)
        self.assertIn("cannot prove run, input, or target binding", weaker.stderr)
        historical = json.loads((ROOT / "evals/durability/verification-fixed.json").read_text(encoding="utf-8"))
        self.assertNotIn("observation_manifest", historical)
        baseline = json.loads((ROOT / "evals/durability/baseline.json").read_text(encoding="utf-8"))
        validate_verification_receipt(historical, baseline)


if __name__ == "__main__":
    unittest.main()
