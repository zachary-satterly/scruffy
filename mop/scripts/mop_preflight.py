#!/usr/bin/env python3
"""Probe runtime capabilities for the visual-redesign path — never assume.

The rule this enforces: a capability is marked ``absent`` only after a probe
fails. Omission is ``not_run``, never ``absent``. This exists because assuming a
capability was missing (a browser, the Mobbin connector) once produced confident,
false disclosures — the exact failure the method forbids.

- The **browser** is a local binary, so this script probes it mechanically.
- **impeccable** and the **design-reference search** (Mobbin/equivalent) are
  runtime/MCP capabilities a subprocess cannot reach; only the agent can test
  them by actually invoking them. This script therefore *records the agent's
  attested probe result* and refuses to accept ``absent`` without a failure
  reason — so an unattested run can never silently become ``absent``.

Dependency-free (stdlib only).
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys

# Runtime/MCP capabilities the agent must attest (this process cannot call them).
RUNTIME_CAPS = ("impeccable", "design_reference_search")
ATTESTED_STATES = ("available", "absent", "not_run")

# Absolute browser locations (macOS app bundles) and PATH names to try.
_BROWSER_APPS = [
    ("Google Chrome", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    ("Chromium", "/Applications/Chromium.app/Contents/MacOS/Chromium"),
    ("Microsoft Edge", "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
    ("Brave", "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"),
]
_BROWSER_PATH_NAMES = [
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
    "microsoft-edge", "brave-browser", "chrome",
]


class PreflightError(Exception):
    """A probe result violates the never-assume rule."""


def _version(path: str) -> str | None:
    try:
        out = subprocess.run([path, "--version"], capture_output=True, text=True,
                             timeout=8)
        return (out.stdout or out.stderr).strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def probe_browser() -> dict:
    """Mechanically locate a headless-capable browser. Absent only if none found."""
    checked: list[str] = []
    for name, path in _BROWSER_APPS:
        checked.append(path)
        import os
        if os.access(path, os.X_OK):
            return {"status": "available", "tool": name, "path": path,
                    "version": _version(path), "checked": checked}
    for cmd in _BROWSER_PATH_NAMES:
        found = shutil.which(cmd)
        checked.append(cmd)
        if found:
            return {"status": "available", "tool": cmd, "path": found,
                    "version": _version(found), "checked": checked}
    import glob
    from pathlib import Path
    playwright_globs = (
        str(Path.home() / ".cache/ms-playwright/chromium*/chrome-linux*/chrome"),
        str(Path.home() / ".cache/ms-playwright/chromium*/chrome-linux*/headless_shell"),
        str(Path.home() / ".cache/ms-playwright/chromium_headless_shell*/chrome-linux*/headless_shell"),
        str(Path.home() / "Library/Caches/ms-playwright/chromium*/chrome-mac*/Chromium.app/Contents/MacOS/Chromium"),
    )
    for pattern in playwright_globs:
        checked.append(pattern)
        matches = sorted(glob.glob(pattern))
        if matches:
            return {"status": "available", "tool": "playwright-chromium", "path": matches[-1],
                    "version": _version(matches[-1]), "checked": checked}
    return {"status": "absent", "reason": "no Chrome/Chromium/Edge/Brave binary found",
            "checked": checked}


def _attest(name: str, status, reason) -> dict:
    if status is None:
        return {"status": "not_run"}
    status = str(status)
    if status not in ATTESTED_STATES:
        raise PreflightError(f"{name}: status {status!r} not in {ATTESTED_STATES}")
    if status == "absent" and not (reason and str(reason).strip()):
        raise PreflightError(
            f"{name}: 'absent' requires a failed-probe reason — omission is "
            f"'not_run', never 'absent'"
        )
    out = {"status": status}
    if reason and str(reason).strip():
        out["reason" if status == "absent" else "detail"] = str(reason).strip()
    return out


def build_preflight(attestations: dict | None = None, browser: dict | None = None) -> dict:
    """Combine the mechanical browser probe with attested runtime results."""
    attestations = attestations or {}
    for key in attestations:
        if key not in RUNTIME_CAPS:
            raise PreflightError(f"unknown attested capability: {key}")
    browser = browser if browser is not None else probe_browser()
    augmentations = {"browser": browser}
    for cap in RUNTIME_CAPS:
        a = attestations.get(cap, {})
        augmentations[cap] = _attest(cap, a.get("status"), a.get("reason"))
    return {
        "schema_version": "1.0",
        "producer": "scruffys-mop",
        "augmentations": augmentations,
        "rule": ("A capability is 'absent' only after a probe fails; omission is "
                 "'not_run', never 'absent'."),
    }


def to_handoff_augmentations(preflight: dict) -> dict:
    """Disclose probes without inferring use from capability availability."""
    mapping = {"available": "not_reported", "absent": "absent", "not_run": "not_reported"}
    out = {}
    for cap, rec in preflight["augmentations"].items():
        out[cap] = mapping.get(rec.get("status"), "not_reported")
    return out


def _human(report: dict) -> str:
    lines = ["Scruffy repair preflight", f"  rule: {report['rule']}"]
    for cap, rec in report["augmentations"].items():
        extra = rec.get("version") or rec.get("reason") or rec.get("detail") or ""
        tool = f" ({rec['tool']})" if rec.get("tool") else ""
        lines.append(f"  {cap}: {rec['status']}{tool}{'  — ' + extra if extra else ''}")
    return "\n".join(lines)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Scruffy repair capability preflight")
    for cap in RUNTIME_CAPS:
        p.add_argument(f"--{cap.replace('_', '-')}", choices=ATTESTED_STATES,
                       help=f"attested probe result for {cap}")
        p.add_argument(f"--{cap.replace('_', '-')}-reason",
                       help=f"failure reason (required if {cap} is 'absent')")
    p.add_argument("--json", action="store_true")
    p.add_argument(
        "--handoff-augmentations",
        action="store_true",
        help="Print only the handoff augmentations JSON (save to a file, pass to mop_handoff --augmentations @file)",
    )
    args = p.parse_args(argv)

    attest = {}
    for cap in RUNTIME_CAPS:
        status = getattr(args, cap)
        reason = getattr(args, f"{cap}_reason")
        if status is not None or reason is not None:
            attest[cap] = {"status": status, "reason": reason}
    try:
        report = build_preflight(attest)
    except PreflightError as exc:
        print(f"REFUSED (never-assume rule): {exc}", file=sys.stderr)
        return 2
    if args.handoff_augmentations:
        print(json.dumps(to_handoff_augmentations(report), indent=2))
        return 0
    print(json.dumps(report, indent=2) if args.json else _human(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
