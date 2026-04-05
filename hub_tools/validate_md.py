from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

INCLUDE_RE = re.compile(r"<!--\s*INCLUDE\s+(.+?)\s*-->")
PLACEHOLDER_RE = re.compile(r"\{\{(tbl|fig|sec):([A-Za-z0-9_\-]+)\}\}")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
HARDCODED_REF_RE = re.compile(r"\b(Table|Figure)\s+\d+\b")
SPECIAL_CHAR_RE = re.compile(r"[^a-z0-9_\s]")


@dataclass
class Issue:
    severity: str
    path: Path
    line_number: int
    message: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Markdown sources, INCLUDE directives, labels, and numbering conventions."
    )
    parser.add_argument(
        "--main",
        default="main.md",
        help="Path to the manifest file relative to the current working directory. Defaults to main.md.",
    )
    return parser.parse_args()


def normalize_section_label(text: str) -> str:
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\$([^$]+)\$", r"\1", text)
    text = text.lower().replace("&", " and ")
    text = SPECIAL_CHAR_RE.sub("", text)
    text = re.sub(r"\s+", "_", text.strip())
    return text


def collect_includes(
    path: Path, project_root: Path, visited: set[Path], ordered: list[Path], issues: list[Issue]
) -> None:
    resolved = path.resolve()
    if resolved in visited:
        return
    visited.add(resolved)
    ordered.append(resolved)

    if not resolved.exists():
        issues.append(Issue("ERROR", path, 0, "File does not exist"))
        return

    for line_number, line in enumerate(resolved.read_text(encoding="utf-8").splitlines(), start=1):
        match = INCLUDE_RE.fullmatch(line.strip())
        if not match:
            continue
        include_path = (project_root / match.group(1).strip()).resolve()
        if not include_path.exists():
            issues.append(
                Issue(
                    "ERROR",
                    resolved,
                    line_number,
                    f"Included file not found: {match.group(1).strip()}",
                )
            )
            continue
        collect_includes(include_path, project_root, visited, ordered, issues)


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.main).resolve()
    if not manifest_path.exists():
        print(f"ERROR: manifest file not found: {manifest_path}", file=sys.stderr)
        return 1

    project_root = manifest_path.parent
    issues: list[Issue] = []
    ordered_files: list[Path] = []
    collect_includes(manifest_path, project_root, set(), ordered_files, issues)

    src_dir = project_root / "src"
    candidate_files = sorted(src_dir.glob("*.md"))

    section_defs: dict[str, tuple[Path, int]] = {}
    table_defs: dict[str, tuple[Path, int]] = {}
    figure_defs: dict[str, tuple[Path, int]] = {}
    placeholder_uses: list[tuple[str, str, Path, int]] = []

    for path in candidate_files:
        lines = path.read_text(encoding="utf-8").splitlines()
        for line_number, line in enumerate(lines, start=1):
            heading_match = HEADING_RE.match(line)
            if heading_match:
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                if level > 3:
                    issues.append(Issue("ERROR", path, line_number, "Heading depth exceeds ### maximum"))
                if re.match(r"^\d", title):
                    issues.append(Issue("WARN", path, line_number, "Heading appears to be pre-numbered"))
                section_defs.setdefault(normalize_section_label(title), (path, line_number))

            for match in PLACEHOLDER_RE.finditer(line):
                kind, label = match.groups()
                if kind == "sec":
                    placeholder_uses.append((kind, label, path, line_number))
                elif re.search(rf"\*\*(Table|Figure)\s+\{{\{{{kind}:{re.escape(label)}\}}\}}\.\*\*", line):
                    if kind == "tbl":
                        table_defs.setdefault(label, (path, line_number))
                    else:
                        figure_defs.setdefault(label, (path, line_number))
                else:
                    placeholder_uses.append((kind, label, path, line_number))

            if HARDCODED_REF_RE.search(line) and "{{tbl:" not in line and "{{fig:" not in line:
                issues.append(
                    Issue(
                        "WARN",
                        path,
                        line_number,
                        "Hard-coded table/figure number found; prefer placeholder syntax",
                    )
                )

    for kind, label, path, line_number in placeholder_uses:
        if kind == "tbl" and label not in table_defs:
            issues.append(Issue("ERROR", path, line_number, f"Undefined table label: {label}"))
        elif kind == "fig" and label not in figure_defs:
            issues.append(Issue("ERROR", path, line_number, f"Undefined figure label: {label}"))
        elif kind == "sec" and label not in section_defs:
            issues.append(Issue("ERROR", path, line_number, f"Undefined section label: {label}"))

    error_count = sum(1 for issue in issues if issue.severity == "ERROR")
    warn_count = sum(1 for issue in issues if issue.severity == "WARN")

    print(f"Validated manifest: {manifest_path}")
    print("Files checked:")
    for path in ordered_files:
        print(f"- {path.relative_to(project_root)}")

    if issues:
        print("Issues:")
        for issue in issues:
            rel_path = issue.path.relative_to(project_root) if issue.path.is_absolute() else issue.path
            print(f"- {issue.severity} {rel_path}:{issue.line_number} {issue.message}")
    else:
        print("Issues: none")

    if error_count:
        print(f"Validation FAILED with {error_count} error(s) and {warn_count} warning(s).")
        return 1

    print(f"Validation PASSED with {warn_count} warning(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
