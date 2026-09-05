#!/usr/bin/env python3
"""Regression tests for the guards that keep untrusted audit data inert.

A skill runs on the operator's machine with the operator's file access, and the
JSON it reads — registries, assets manifests, decisions, directions — is written
by a model that has just finished reading a product nobody controls. A bundle can
also arrive from someone else entirely. So those artifacts are adversarial input,
not configuration.

Bounded command execution and confined raster evidence are covered by
`test_bounded_execution.py` and the `evidence_assets` guards. This file covers
what is left: the dashboard's own escaping, and locator probes during validation.
Each case is an attack that worked against 4.0.0.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "mop" / "scripts"))

import mop_dashboard as dash  # noqa: E402
from evidence_assets import confined_path  # noqa: E402

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ok  {name}")
    else:
        FAILURES.append(f"{name}: {detail}")
        print(f"  FAIL {name} — {detail}")


def main() -> int:
    print("dashboard links")
    check("javascript: href is dropped", dash._safe_href("javascript:alert(1)") is None, "href survived")
    check("data: href is dropped", dash._safe_href("data:text/html,<script>") is None, "href survived")
    check("protocol-relative href is dropped", dash._safe_href("//evil.example/x") is None, "href survived")
    check("leading whitespace does not smuggle a scheme",
          dash._safe_href("  javascript:alert(1)") is None, "href survived")
    check("https href survives",
          dash._safe_href("https://mobbin.com/screens/1") == "https://mobbin.com/screens/1",
          "a legitimate reference link was dropped")
    check("quotes in an http href are escaped",
          '"' not in (dash._safe_href('https://e.example/"onmouseover="alert(1)') or ""),
          "raw quote reached the attribute")

    print("script payloads")
    payload = dash._script_json({"note": "</script><script>alert(1)</script>"})
    check("script payload cannot close the tag", "</" not in payload, "raw </script> reached the payload")
    check("script payload stays valid JSON", payload.startswith("{") and payload.endswith("}"), "malformed")
    slots = {"__AUDIT__": '{"audit_id":"__DECISIONS__"}', "__DIRECTIONS__": "null", "__DECISIONS__": '{"real":1}'}
    filled = dash._SCRIPT_SLOT.sub(lambda m: slots[m.group(0)], "A=__AUDIT__;D=__DECISIONS__;")
    check("a placeholder inside data is not re-substituted",
          filled == 'A={"audit_id":"__DECISIONS__"};D={"real":1};', f"got {filled}")

    print("self-containment assertion")
    try:
        dash._assert_self_contained('<a href="javascript:alert(1)">x</a>')
        check("javascript: link fails the render", False, "render was certified self-contained")
    except dash.InteropError:
        check("javascript: link fails the render", True)
    try:
        dash._assert_self_contained('<a href="https://mobbin.com/x">x</a><a href="#top">y</a>')
        check("http and anchor links still pass", True)
    except dash.InteropError as error:
        check("http and anchor links still pass", False, str(error))

    print("evidence locators")
    with tempfile.TemporaryDirectory() as raw:
        bundle = Path(raw) / "bundle"
        bundle.mkdir()
        (Path(raw) / "outside.txt").write_text("private", encoding="utf-8")
        (bundle / "shot.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        for name, locator in (("relative escape", "../outside.txt"), ("absolute path", "/etc/hostname")):
            try:
                confined_path(locator, bundle)
                check(f"{name} is refused", False, "locator was accepted")
            except (OSError, ValueError):
                check(f"{name} is refused", True)
        check("in-bundle locator resolves",
              confined_path("shot.png", bundle) == (bundle / "shot.png").resolve(),
              "a legitimate locator was refused")

    if FAILURES:
        print(f"\nFAIL: {len(FAILURES)} security guard(s) regressed")
        for line in FAILURES:
            print(f"  - {line}")
        return 1
    print("\nPASS: security guards hold")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
