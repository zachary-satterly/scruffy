#!/usr/bin/env python3
"""Render and validate Scruffy's canonical taxonomy projections."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "schema" / "taxonomy.json"
README = ROOT / "README.md"
REFERENCE = ROOT / "references" / "taxonomy.md"
README_START = "<!-- scruffy-taxonomy:start -->"
README_END = "<!-- scruffy-taxonomy:end -->"


def load_taxonomy(path: Path = MANIFEST) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != "1.0":
        raise ValueError("taxonomy schema_version must be 1.0")
    categories = data.get("categories")
    layers = data.get("inspection_layers")
    facets = data.get("facets")
    if not isinstance(categories, list) or len(categories) != 8:
        raise ValueError("taxonomy must define exactly eight categories")
    if not isinstance(layers, list) or len(layers) != 4:
        raise ValueError("taxonomy must define exactly four inspection layers")
    if not isinstance(facets, list) or not facets:
        raise ValueError("taxonomy facets must be a non-empty array")

    category_keys = [row.get("key") for row in categories]
    layer_keys = [row.get("key") for row in layers]
    facet_keys = [row.get("key") for row in facets]
    for label, values in (("category", category_keys), ("layer", layer_keys), ("facet", facet_keys)):
        if any(not isinstance(value, str) or not value for value in values):
            raise ValueError(f"taxonomy has an invalid {label} key")
        if len(values) != len(set(values)):
            raise ValueError(f"taxonomy repeats a {label} key")

    required_category_fields = {
        "key", "public_label", "score_label", "inspection_layer", "plain_meaning",
        "required_proof", "readme_detail", "applicable_facets", "principle_sections",
    }
    required_layer_fields = {"key", "label", "purpose", "category_keys"}
    required_facet_fields = {"key", "label", "description"}
    for row in layers:
        missing = sorted(required_layer_fields - set(row))
        if missing:
            raise ValueError(f"inspection layer {row.get('key')} is missing {missing}")
    for row in facets:
        missing = sorted(required_facet_fields - set(row))
        if missing:
            raise ValueError(f"facet {row.get('key')} is missing {missing}")
    for row in categories:
        missing = sorted(required_category_fields - set(row))
        if missing:
            raise ValueError(f"category {row.get('key')} is missing {missing}")
        if row["inspection_layer"] not in layer_keys:
            raise ValueError(f"category {row['key']} references an unknown inspection layer")
        unknown_facets = sorted(set(row["applicable_facets"]) - set(facet_keys))
        if unknown_facets:
            raise ValueError(f"category {row['key']} references unknown facets {unknown_facets}")
        if not isinstance(row["principle_sections"], list) or not row["principle_sections"]:
            raise ValueError(f"category {row['key']} must name its principle basis")

    projected = [key for layer in layers for key in layer.get("category_keys", [])]
    if len(projected) != len(set(projected)) or set(projected) != set(category_keys):
        raise ValueError("inspection layers must project every category exactly once")

    projected_layers = {key: layer["key"] for layer in layers for key in layer["category_keys"]}
    for row in categories:
        if projected_layers[row["key"]] != row["inspection_layer"]:
            raise ValueError(f"category {row['key']} inspection_layer contradicts its layer membership")

    aliases = data.get("legacy_category_aliases")
    if not isinstance(aliases, dict) or any(value not in category_keys for value in aliases.values()):
        raise ValueError("legacy category aliases must target canonical keys")
    if data.get("registry_schema", {}).get("current") != "2.1":
        raise ValueError("taxonomy current registry schema must be 2.1")
    for label, rows in (("category", categories), ("layer", layers), ("facet", facets)):
        public_labels = [row.get("public_label", row.get("label")) for row in rows]
        if any(not isinstance(value, str) or not value.strip() for value in public_labels):
            raise ValueError(f"taxonomy has an invalid {label} label")
        if len(public_labels) != len(set(public_labels)):
            raise ValueError(f"taxonomy repeats a {label} label")
    return data


def canonical_category_keys(data: dict[str, Any]) -> tuple[str, ...]:
    return tuple(row["key"] for row in data["categories"])


def canonical_facet_keys(data: dict[str, Any]) -> tuple[str, ...]:
    return tuple(row["key"] for row in data["facets"])


def markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def render_readme(data: dict[str, Any]) -> str:
    lines = [
        README_START,
        "## The eight slop categories",
        "",
        "Scruffy uses four inspection layers to produce findings in eight canonical categories. The layers control review order; the categories classify evidence. Cross-cutting facets prevent category sprawl.",
        "",
        "| Category | Durable key | Plain meaning | What turns a suspicion into a finding |",
        "|---|---|---|---|",
    ]
    for row in data["categories"]:
        lines.append(
            f"| **{markdown_cell(row['public_label'])}** | `{row['key']}` | "
            f"{markdown_cell(row['plain_meaning'])} | {markdown_cell(row['required_proof'])} |"
        )
    lines.extend([""])
    for row in data["categories"]:
        lines.extend(
            [
                f"### {row['public_label']}",
                "",
                row["readme_detail"],
                "",
            ]
        )
    lines.extend(
        [
            "### Cross-cutting facets",
            "",
            "Apply these only where the product exposes the concern: "
            + ", ".join(f"**{row['label']}**" for row in data["facets"])
            + ". They refine a category; they do not replace it.",
            README_END,
        ]
    )
    return "\n".join(lines)


def render_reference(data: dict[str, Any]) -> str:
    lines = [
        "# Canonical taxonomy",
        "",
        "> Generated from `schema/taxonomy.json` by `scripts/taxonomy_contract.py`. Do not edit this file directly.",
        "",
        "The inspection layer controls order. The category classifies each registry item. A facet records a cross-cutting concern without creating another competing category.",
        "",
        "## Inspection layers",
        "",
        "| Order | Layer | Purpose | Categories |",
        "|---:|---|---|---|",
    ]
    for index, row in enumerate(data["inspection_layers"], 1):
        categories = ", ".join(f"`{value}`" for value in row["category_keys"])
        lines.append(f"| {index} | **{row['label']}** | {markdown_cell(row['purpose'])} | {categories} |")
    lines.extend(
        [
            "",
            "## Canonical categories",
            "",
        ]
    )
    for row in data["categories"]:
        lines.extend(
            [
                f"### {row['public_label']} (`{row['key']}`)",
                "",
                f"- **Score label:** {row['score_label']}",
                f"- **Inspection layer:** `{row['inspection_layer']}`",
                f"- **Meaning:** {row['plain_meaning']}",
                f"- **Required proof:** {row['required_proof']}",
                f"- **Applicable facets:** {', '.join(f'`{value}`' for value in row['applicable_facets'])}",
                f"- **Principle basis:** {', '.join(row['principle_sections'])}",
                "",
                row["readme_detail"],
                "",
            ]
        )
    lines.extend(["## Cross-cutting facets", "", "| Facet | Meaning |", "|---|---|"])
    for row in data["facets"]:
        lines.append(f"| `{row['key']}` — **{row['label']}** | {markdown_cell(row['description'])} |")
    lines.extend(
        [
            "",
            "## Legacy category aliases",
            "",
            "Schema 2.0 reports remain readable for durability. Schema 2.1 reports must emit canonical keys.",
            "",
            "| Legacy key | Canonical key |",
            "|---|---|",
        ]
    )
    for legacy, canonical in sorted(data["legacy_category_aliases"].items()):
        lines.append(f"| `{legacy}` | `{canonical}` |")
    return "\n".join(lines) + "\n"


def replace_readme_block(text: str, rendered: str) -> str:
    pattern = re.compile(
        rf"{re.escape(README_START)}.*?{re.escape(README_END)}",
        re.S,
    )
    if pattern.search(text):
        return pattern.sub(lambda match: rendered, text)
    heading = re.search(r"(?ms)^## The seven slop categories\n.*?(?=^## Why the method is harder to fool\n)", text)
    if not heading:
        raise ValueError("README taxonomy section or generated markers were not found")
    return text[: heading.start()] + rendered + "\n\n" + text[heading.end() :]


def expected_files(data: dict[str, Any]) -> tuple[str, str]:
    readme = replace_readme_block(README.read_text(encoding="utf-8"), render_readme(data))
    reference = render_reference(data)
    return readme, reference


def check(data: dict[str, Any]) -> list[str]:
    expected_readme, expected_reference = expected_files(data)
    failures: list[str] = []
    if README.read_text(encoding="utf-8") != expected_readme:
        failures.append("README taxonomy projection is stale")
    if not REFERENCE.is_file() or REFERENCE.read_text(encoding="utf-8") != expected_reference:
        failures.append("references/taxonomy.md is stale or missing")
    return failures


def write(data: dict[str, Any]) -> None:
    expected_readme, expected_reference = expected_files(data)
    README.write_text(expected_readme, encoding="utf-8")
    REFERENCE.write_text(expected_reference, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true")
    action.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        data = load_taxonomy()
        if args.write:
            write(data)
            print("PASS: taxonomy projections updated")
            return 0
        failures = check(data)
        if failures:
            for failure in failures:
                print(f"FAIL: {failure}", file=sys.stderr)
            return 1
        print("PASS: canonical taxonomy and projections are synchronized")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
