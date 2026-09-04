#!/usr/bin/env python3
"""Validate Scruffy corpus coverage with Python's standard library only."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"
PRINCIPLES = ROOT / "principles" / "PRINCIPLES.md"
SOURCES = ROOT / "principles" / "SOURCES.md"
TRANSCRIPTS = ROOT / "transcripts"

VIDEO_ID = re.compile(r"\[([A-Za-z0-9_-]{11})(?:\s|\])")
TIMED_CITATION = re.compile(
    r"\[([A-Za-z0-9_-]{11})\s+(\d+:\d{2})(?:[–-](\d+:\d{2}))?"
)


def die(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def seconds(stamp: str) -> int:
    minutes, secs = map(int, stamp.split(":"))
    return minutes * 60 + secs


def validate_frontmatter(skill: str) -> None:
    match = re.match(r"\A---\n(.*?)\n---\n", skill, re.S)
    if not match:
        die("SKILL.md frontmatter is missing")
    frontmatter = match.group(1)
    name = re.search(r"^name:\s*([^\n]+)$", frontmatter, re.M)
    if not name or not re.fullmatch(r"[a-z0-9-]{1,64}", name.group(1).strip()):
        die("SKILL.md name is missing or invalid")
    description = re.search(r"^description:\s*(.+)$", frontmatter, re.M)
    if not description:
        die("SKILL.md must have a non-empty description")
    value = description.group(1).strip()
    if len(value) > 1024:
        die(f"SKILL.md description is {len(value)} characters; maximum is 1024")


def transcript_index() -> dict[str, tuple[Path, str, int]]:
    index: dict[str, tuple[Path, str, int]] = {}
    if not TRANSCRIPTS.exists():
        return index
    for path in TRANSCRIPTS.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        video = re.search(r"^video_id:[ \t]*([^\n]+)$", text, re.M)
        identifier = video.group(1).strip() if video else ""
        if identifier.startswith('"'):
            try:
                identifier = json.loads(identifier)
            except (ValueError, TypeError):
                continue
        if not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9_-]{11}", identifier):
            continue
        duration = re.search(r'^duration:\s*"(\d+:\d{2})"$', text, re.M)
        if video and duration:
            index[identifier] = (path, text, seconds(duration.group(1)))
    return index


def main() -> int:
    skill = SKILL.read_text(encoding="utf-8")
    principles = PRINCIPLES.read_text(encoding="utf-8")
    sources = SOURCES.read_text(encoding="utf-8")

    validate_frontmatter(skill)

    section_numbers = [
        int(value) for value in re.findall(r"^## (\d+)\.", principles, re.M)
    ]
    expected_sections = list(range(1, max(section_numbers, default=0) + 1))
    if section_numbers != expected_sections:
        die(f"PRINCIPLES.md section sequence is {section_numbers}")

    required_aliases = {
        "WAI-APG",
        "WAI-TABS",
        "WAI-ALT",
        "WEBDEV-LCP",
        "WEBDEV-CLS",
        "WEBDEV-INP",
        "WEBDEV-RESPIMG",
        "WEBDEV-3P",
        "MDN-FONTDISPLAY",
        "W3C-READING",
        "GOVUK-CLEAR",
        "SADASIVAN23",
        "LIANG23",
        "MAGE24",
        "ZANOTTO25",
    }
    missing_aliases = sorted(alias for alias in required_aliases if f"[{alias}]" not in sources)
    if missing_aliases:
        die(f"SOURCES.md is missing aliases: {missing_aliases}")

    stale_markers = ("P2 queued", "Still queued", "not yet compiled")
    stale = [marker for marker in stale_markers if marker in sources or marker in principles]
    if stale:
        die(f"stale work-order markers remain: {stale}")

    transcripts = transcript_index()
    if not transcripts:
        print("WARN: no local transcripts; citation time and pilot coverage checks skipped")
    else:
        queue_start = sources.index("### Priority 1 - pilot results")
        queue_end = sources.index("### Hypothesis-only / corroboration required")
        distilled_queue = sources[queue_start:queue_end]
        distilled_ids = {
            video_id
            for line in distilled_queue.splitlines()
            if "distilled" in line.lower()
            for video_id in re.findall(r"`([A-Za-z0-9_-]{11})`", line)
        }
        pilot_ids = distilled_ids & set(transcripts)
        working_only = sorted(set(transcripts) - pilot_ids)
        if working_only:
            print(
                "WARN: local transcripts not in a distilled Priority 1/2 row were ignored: "
                + ", ".join(working_only)
            )
        principles_pilots = principles[principles.index("## 23.") :]
        principles_ids = set(VIDEO_ID.findall(principles_pilots))
        missing_principles = sorted(pilot_ids - principles_ids)
        if missing_principles:
            die(f"pilot transcripts not represented in PRINCIPLES.md: {missing_principles}")

        checked = 0
        overrun: list[tuple[str, str, int]] = []
        for video_id, start, end in TIMED_CITATION.findall(principles_pilots):
            if video_id not in transcripts:
                continue
            limit = transcripts[video_id][2]
            for stamp in (start, end):
                if stamp and seconds(stamp) > limit:
                    overrun.append((video_id, stamp, limit))
            checked += 1
        if overrun:
            die(f"citations exceed source duration: {overrun}")
        print(
            f"PASS: {len(pilot_ids)} pilot transcripts represented in principles; "
            f"{checked} timestamp citations within duration"
        )

    print(
        f"PASS: SKILL frontmatter, PRINCIPLES §§1-{len(section_numbers)}, "
        "source aliases, and work-order state"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
