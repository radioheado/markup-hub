from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

PLACEHOLDER_RE = re.compile(r"\{\{(tbl|fig|sec):([A-Za-z0-9_\-]+)\}\}")
SPECIAL_CHAR_RE = re.compile(r"[^a-z0-9_\s]")


@dataclass
class LabelInfo:
    kind: str
    number: str
    line_number: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Number Markdown headings, tables, figures, and cross-references."
    )
    parser.add_argument(
        "--input",
        default="build/merged/paper.md",
        help="Path to the merged Markdown input file. Defaults to build/merged/paper.md.",
    )
    parser.add_argument(
        "--output",
        default="build/merged/paper_numbered.md",
        help="Path to the numbered Markdown output file. Defaults to build/merged/paper_numbered.md.",
    )
    return parser.parse_args()


def strip_metadata_comment(lines: list[str]) -> tuple[list[str], list[str]]:
    if not lines or lines[0].strip() != "<!--":
        return [], lines
    comment: list[str] = []
    remaining = lines[:]
    while remaining:
        line = remaining.pop(0)
        comment.append(line)
        if line.strip() == "-->":
            break
    return comment, remaining


def normalize_section_label(text: str) -> str:
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\$([^$]+)\$", r"\1", text)
    text = text.lower().replace("&", " and ")
    text = SPECIAL_CHAR_RE.sub("", text)
    text = re.sub(r"\s+", "_", text.strip())
    return text


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    lines = input_path.read_text(encoding="utf-8").splitlines()

    metadata_comment, body_lines = strip_metadata_comment(lines)
    label_registry: dict[tuple[str, str], LabelInfo] = {}
    warnings: list[str] = []
    numbered_lines: list[str] = []

    chapter = 0
    section = 0
    subsection = 0
    table_counter = 0
    figure_counter = 0

    for line_number, line in enumerate(body_lines, start=len(metadata_comment) + 1):
        heading_match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading_match:
            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()
            if level == 1:
                if title.lower() == "abstract":
                    numbered_lines.append(f"# {title}")
                else:
                    chapter += 1
                    section = 0
                    subsection = 0
                    number = str(chapter)
                    label_registry[("sec", normalize_section_label(title))] = LabelInfo(
                        "sec", number, line_number
                    )
                    numbered_lines.append(f"# {number}. {title}")
                continue
            if level == 2:
                section += 1
                subsection = 0
                number = f"{chapter}.{section}"
                label_registry[("sec", normalize_section_label(title))] = LabelInfo(
                    "sec", number, line_number
                )
                numbered_lines.append(f"## {number} {title}")
                continue
            # H3 — subsection X.Y.Z; resets on each new H2
            if level == 3:
                subsection += 1
                number = f"{chapter}.{section}.{subsection}"
                label_registry[("sec", normalize_section_label(title))] = LabelInfo(
                    "sec", number, line_number
                )
                numbered_lines.append(f"### {number} {title}")
                continue
            numbered_lines.append(line)
            continue

        def replace_caption(match: re.Match[str]) -> str:
            nonlocal table_counter, figure_counter
            kind, label = match.groups()
            key = (kind, label)
            if kind == "tbl":
                if key not in label_registry:
                    table_counter += 1
                    label_registry[key] = LabelInfo(kind, str(table_counter), line_number)
                return label_registry[key].number
            if key not in label_registry:
                figure_counter += 1
                label_registry[key] = LabelInfo(kind, str(figure_counter), line_number)
            return label_registry[key].number

        if re.search(r"\*\*Table\s+\{\{tbl:[^}]+\}\}\.\*\*", line) or re.search(
            r"\*\*Figure\s+\{\{fig:[^}]+\}\}\.\*\*", line
        ):
            numbered_lines.append(PLACEHOLDER_RE.sub(replace_caption, line))
            continue

        numbered_lines.append(line)

    resolved_lines: list[str] = []
    for line_number, line in enumerate(numbered_lines, start=len(metadata_comment) + 1):
        def replace_reference(match: re.Match[str]) -> str:
            kind, label = match.groups()
            info = label_registry.get((kind, label))
            if info is None:
                warnings.append(
                    f"Warning: unresolved placeholder {match.group(0)} at output line {line_number}"
                )
                return match.group(0)
            if kind == "tbl":
                return f"Table {info.number}"
            if kind == "fig":
                return f"Figure {info.number}"
            return f"Section {info.number}"

        resolved_lines.append(PLACEHOLDER_RE.sub(replace_reference, line))

    output_parts: list[str] = []
    if metadata_comment:
        output_parts.extend(metadata_comment)
        output_parts.append("")
    output_parts.extend(resolved_lines)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(output_parts).rstrip() + "\n", encoding="utf-8")

    print(f"Wrote numbered Markdown to {output_path}")
    print("Label registry:")
    for (kind, label), info in sorted(
        label_registry.items(),
        key=lambda item: (item[1].line_number, item[0][0], item[0][1]),
    ):
        print(f"- {kind}:{label} -> {info.number} (line {info.line_number})")
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"- {warning}")
    else:
        print("Warnings: none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
