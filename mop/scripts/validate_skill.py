#!/usr/bin/env python3
"""Validate Scruffy's compatibility repair runtime.

Dependency-free. Checks that the interop contract is well formed, distribution
metadata agrees, the skill frontmatter and routed references exist, and the
shipped fixture bundle still loads, validates, and plans. Exits non-zero on the
first failure so it can gate a commit.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from mop_bundle import build_plan, load_bundle, load_interop

REPO = Path(__file__).resolve().parent.parent
FAILURES: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        FAILURES.append(msg)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _frontmatter_name(md_path: Path) -> str | None:
    text = _read(md_path)
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return None
    for line in m.group(1).splitlines():
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip()
    return None


def main() -> int:
    # 1. Interop contract shape.
    try:
        interop = load_interop()
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: interop.json unreadable: {exc}")
        return 1
    for key in ("consumes", "authority_gate", "ordering", "compatibility_policy"):
        check(key in interop, f"interop.json missing key: {key}")
    for name in ("findings.json", "context.json", "decisions.json", "tokens.json"):
        check(name in interop["consumes"], f"interop consumes missing {name}")

    # 2. Distribution metadata agrees.
    plugin = json.loads(_read(REPO / ".claude-plugin" / "plugin.json"))
    market = json.loads(_read(REPO / ".claude-plugin" / "marketplace.json"))
    check(plugin["name"] == "scruffys-mop", "plugin name is not scruffys-mop")
    market_plugin = market["plugins"][0]
    check(market_plugin["name"] == plugin["name"], "marketplace/plugin name mismatch")
    check(market_plugin["version"] == plugin["version"],
          "marketplace/plugin version mismatch")

    # 3. Skill frontmatter + routed references exist.
    root_name = _frontmatter_name(REPO / "SKILL.md")
    check(root_name == plugin["name"], f"SKILL.md name {root_name!r} != plugin name")
    adapter = REPO / "skills" / "scruffys-mop" / "SKILL.md"
    check(adapter.exists(), "skills/scruffys-mop/SKILL.md is missing")
    for ref in ("method.md", "fix-protocols.md", "craft-bar.md", "verification.md",
                "visual-redesign.md", "scruffy-handoff.md"):
        check((REPO / "references" / ref).exists(),
              f"routed reference missing: references/{ref}")

    # 4. The shipped fixture still loads, validates, and plans.
    try:
        bundle = load_bundle(REPO / "fixtures" / "sample-audit", interop)
        plan = build_plan(bundle, interop)
        order = [s["item_id"] for s in plan["steps"]]
        check(order == ["AS-04", "AS-02", "AS-05", "AS-01"],
              f"fixture plan order changed: {order}")
        check(plan["gate"]["permissible"], "fixture gate should be permissible")
    except Exception as exc:  # noqa: BLE001
        FAILURES.append(f"fixture bundle failed: {exc}")

    # 5. The dashboard generator produces a self-contained file from the fixture.
    try:
        import tempfile
        from mop_dashboard import render
        with tempfile.TemporaryDirectory() as d:
            out = render(REPO / "fixtures" / "sample-audit", None,
                         str(Path(d) / "dash.html"), authorized=True)
            doc = out.read_text()
        import re as _re
        ext = [u for u in _re.findall(r'src="([^"]+)"', doc) if not u.startswith("data:")]
        check(not ext, f"dashboard has external image loaders: {ext}")
        check("Billing state is computed" in doc, "dashboard missing an item title")
    except Exception as exc:  # noqa: BLE001
        FAILURES.append(f"dashboard generator failed: {exc}")

    # 6. The preflight enforces the never-assume rule.
    try:
        from mop_preflight import build_preflight, PreflightError
        try:
            build_preflight({"impeccable": {"status": "absent"}},
                            browser={"status": "absent", "reason": "t"})
            FAILURES.append("preflight accepted 'absent' without a reason")
        except PreflightError:
            pass
    except Exception as exc:  # noqa: BLE001
        FAILURES.append(f"preflight check failed: {exc}")

    if FAILURES:
        print("validate_skill: FAIL")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("validate_skill: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
