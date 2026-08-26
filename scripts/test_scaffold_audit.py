#!/usr/bin/env python3
"""The scaffolder must emit a bundle that validates without edits."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAFFOLD = ROOT / "scripts" / "scaffold_audit.py"


def run_scaffold(out: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCAFFOLD),
         "--audit-id", "scaffold-check", "--target", "Scaffold fixture",
         "--title", "Scaffold self-check", "--out", str(out), *extra],
        capture_output=True, text=True,
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    try:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)

            default_out = base / "default"
            proc = run_scaffold(default_out)
            require(proc.returncode == 0, f"default scaffold failed: {proc.stdout}{proc.stderr}")
            default_context = json.loads((default_out / "context.json").read_text(encoding="utf-8"))
            require(default_context["schema_version"] == "1.2", "scaffold did not emit current context schema 1.2")
            require(default_context["baseline_revision_id"] is None, "baseline scaffold invented a context baseline")
            require(default_context["scruffy_applicability"] == "applicable", "scaffold did not default to an applicable interface audit")
            require(len(default_context["routing"]) == 10, "scaffold did not account for every canonical review lane")
            core_route = next(row for row in default_context["routing"] if row["lane"] == "core_interface")
            require(core_route["disposition"] == "selected", "scaffold did not select the required core interface lane")
            require(core_route["id"] == "ROUTE-CORE-INTERFACE", "scaffold did not emit the stable core routing ID")
            require(core_route["revision_disposition"] == "new", "baseline route was not marked new")
            require(default_context["assumptions"] == [], "scaffold invented assumptions")
            require(default_context["referrals"] == [], "scaffold invented specialist referrals")

            invalid_prefix_out = base / "invalid-prefix"
            proc = run_scaffold(invalid_prefix_out, "--item-prefix", "OMP-MOB")
            require(proc.returncode != 0, "long/hyphenated item prefix unexpectedly passed")
            require(not invalid_prefix_out.exists(), "invalid item prefix wrote output before failing")
            require("2-6 uppercase" in proc.stderr, "invalid item prefix did not explain the contract")

            redesign_out = base / "redesign"
            proc = run_scaffold(
                redesign_out,
                "--item-prefix", "OMPMOB",
                "--mode", "redesign",
                "--repository-write-authority", "authorized",
            )
            require(proc.returncode == 0, f"authorized redesign scaffold failed: {proc.stdout}{proc.stderr}")
            registry = json.loads((redesign_out / "findings.json").read_text(encoding="utf-8"))
            context = json.loads((redesign_out / "context.json").read_text(encoding="utf-8"))
            require(registry["items"][0]["id"] == "OMPMOB-1", "valid six-character prefix changed")
            require(registry["run"]["effective_mode"] == "redesign", "redesign mode was not preserved")
            require(registry["run"]["repository_write_authority"] == "authorized", "authority was lost")
            source_write = next(row for row in context["capabilities"] if row["key"] == "source_write")
            require(source_write["status"] == "available", "authorized source_write did not start available")

            contradictory_out = base / "contradictory"
            proc = run_scaffold(
                contradictory_out,
                "--mode", "audit",
                "--repository-write-authority", "authorized",
            )
            require(proc.returncode != 0, "audit mode accepted contradictory write authority")
            require(not contradictory_out.exists(), "contradictory mode/authority wrote output before failing")

            png = base / "phone.png"
            png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"fixture-png")
            jpeg = base / "desktop.jpeg"
            jpeg.write_bytes(b"\xff\xd8\xff\xe0" + b"fixture-jpeg")
            screenshot_out = base / "screenshots"
            proc = run_scaffold(
                screenshot_out,
                "--supplied-screenshot", str(png),
                "--supplied-screenshot", str(jpeg),
            )
            require(proc.returncode == 0, f"screenshot scaffold failed: {proc.stdout}{proc.stderr}")
            context = json.loads((screenshot_out / "context.json").read_text(encoding="utf-8"))
            assets = context["evidence_assets"]
            require([row["kind"] for row in assets] == ["screenshot", "screenshot"], "screenshots were not typed")
            require(all(row["verification"] == "supplied" for row in assets), "supplied evidence was misclassified")
            require("example.invalid" not in json.dumps(context), "fake evidence survived supplied screenshots")
            require(all((screenshot_out / row["locator"]).is_file() for row in assets), "prepared screenshots are missing")
            screenshot_capability = next(row for row in context["capabilities"] if row["key"] == "screenshots")
            require(screenshot_capability["status"] == "partial", "supplied screenshots did not seed capability coverage")

            dashboard = screenshot_out / "dashboard.html"
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "render_dashboard.py"),
                 str(screenshot_out / "findings.json"), str(screenshot_out / "context.json"),
                 str(screenshot_out / "decisions.json"), str(dashboard)],
                capture_output=True, text=True,
            )
            require(proc.returncode == 0, f"dashboard render failed: {proc.stdout}{proc.stderr}")
            html = dashboard.read_text(encoding="utf-8")
            require("data:image/png;base64," in html, "PNG was not embedded in the dashboard")
            require("data:image/jpeg;base64," in html, "JPEG was not embedded in the dashboard")
    except AssertionError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: scaffold defaults, authority, prefix preflight, and supplied screenshots validate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
