from __future__ import annotations

import re

PLACEHOLDER_RE = re.compile(r"\{\{(tbl|fig|sec):([A-Za-z0-9_\-]+)\}\}")
SPECIAL_CHAR_RE = re.compile(r"[^a-z0-9_\s]")


def normalize_section_label(text: str) -> str:
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\$([^$]+)\$", r"\1", text)
    text = text.lower().replace("&", " and ")
    text = SPECIAL_CHAR_RE.sub("", text)
    text = re.sub(r"\s+", "_", text.strip())
    return text


def number_group(
    file_order: list[str],
    file_contents: dict[str, str],
    *,
    resolve_references: bool = True,
) -> dict[str, str]:
    chapter = 0
    section = 0
    subsection = 0
    table_counter = 0
    figure_counter = 0
    label_registry: dict[tuple[str, str], str] = {}
    numbered: dict[str, str] = {}

    for rel_path in file_order:
        original = file_contents[rel_path]
        lines = original.splitlines()
        out_lines: list[str] = []
        for line in lines:
            heading_match = re.match(r"^(#{1,6})\s+(.*)$", line)
            if heading_match:
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                if level == 1:
                    if title.lower() == "abstract":
                        out_lines.append(f"# {title}")
                    else:
                        chapter += 1
                        section = 0
                        subsection = 0
                        number = str(chapter)
                        label_registry[("sec", normalize_section_label(title))] = number
                        out_lines.append(f"# {number}. {title}")
                    continue
                if level == 2:
                    section += 1
                    subsection = 0
                    number = f"{chapter}.{section}"
                    label_registry[("sec", normalize_section_label(title))] = number
                    out_lines.append(f"## {number} {title}")
                    continue
                if level == 3:
                    subsection += 1
                    number = f"{chapter}.{section}.{subsection}"
                    label_registry[("sec", normalize_section_label(title))] = number
                    out_lines.append(f"### {number} {title}")
                    continue

            def replace_caption(match: re.Match[str]) -> str:
                nonlocal table_counter, figure_counter
                kind, label = match.groups()
                key = (kind, label)
                if kind == "tbl":
                    if key not in label_registry:
                        table_counter += 1
                        label_registry[key] = str(table_counter)
                    return label_registry[key]
                if key not in label_registry:
                    figure_counter += 1
                    label_registry[key] = str(figure_counter)
                return label_registry[key]

            if re.search(r"\*\*Table\s+\{\{tbl:[^}]+\}\}\.\*\*", line) or re.search(
                r"\*\*Figure\s+\{\{fig:[^}]+\}\}\.\*\*", line
            ):
                out_lines.append(PLACEHOLDER_RE.sub(replace_caption, line))
            else:
                out_lines.append(line)

        numbered[rel_path] = "\n".join(out_lines)

    if not resolve_references:
        return numbered

    resolved: dict[str, str] = {}
    for rel_path in file_order:

        def replace_reference(match: re.Match[str]) -> str:
            kind, label = match.groups()
            number = label_registry.get((kind, label))
            if number is None:
                return match.group(0)
            if kind == "tbl":
                return f"Table {number}"
            if kind == "fig":
                return f"Figure {number}"
            return f"Section {number}"

        resolved[rel_path] = PLACEHOLDER_RE.sub(replace_reference, numbered[rel_path])

    return resolved
