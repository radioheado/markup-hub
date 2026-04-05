from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

INCLUDE_RE = re.compile(r"<!--\s*INCLUDE\s+(.+?)\s*-->")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge Markdown files referenced by INCLUDE directives into a single paper.md file."
    )
    parser.add_argument(
        "--main",
        default="main.md",
        help="Path to the manifest file relative to the current working directory. Defaults to main.md.",
    )
    return parser.parse_args()


def split_metadata_block(text: str) -> tuple[str | None, str]:
    if not text.startswith("---"):
        return None, text
    lines = text.splitlines()
    if len(lines) < 2 or lines[0].strip() != "---":
        return None, text
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            metadata = "\n".join(lines[: idx + 1])
            remainder = "\n".join(lines[idx + 1 :]).lstrip("\n")
            return metadata, remainder
    return None, text


def merge_file(
    path: Path,
    project_root: Path,
    included_order: list[Path],
    stack: list[Path],
    metadata_holder: dict[str, str],
) -> str:
    resolved = path.resolve()
    if resolved in stack:
        chain = " -> ".join(str(item.relative_to(project_root)) for item in stack + [resolved])
        raise ValueError(f"Circular include detected: {chain}")
    if not resolved.exists():
        raise FileNotFoundError(f"Included file not found: {resolved}")

    stack.append(resolved)
    included_order.append(resolved)
    content = resolved.read_text(encoding="utf-8")

    if resolved.name == "metadata.md":
        metadata, content = split_metadata_block(content)
        if metadata:
            metadata_holder["text"] = metadata

    merged_parts: list[str] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        match = INCLUDE_RE.fullmatch(line.strip())
        if not match:
            merged_parts.append(line)
            continue
        include_target = (project_root / match.group(1).strip()).resolve()
        if not include_target.exists():
            rel_parent = resolved.relative_to(project_root)
            raise FileNotFoundError(
                f"Included file not found: {include_target} (referenced from {rel_parent}:{line_number})"
            )
        merged_parts.append(
            merge_file(include_target, project_root, included_order, stack, metadata_holder)
        )

    stack.pop()
    return "\n".join(merged_parts).strip("\n")


def format_metadata_comment(metadata: str) -> str:
    lines = ["<!--", "Metadata from src/metadata.md"]
    lines.extend(metadata.splitlines())
    lines.append("-->")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.main).resolve()
    if not manifest_path.exists():
        print(f"Error: manifest file not found: {manifest_path}", file=sys.stderr)
        return 1

    project_root = manifest_path.parent
    included_order: list[Path] = []
    metadata_holder: dict[str, str] = {}

    try:
        merged_body = merge_file(
            manifest_path,
            project_root,
            included_order,
            stack=[],
            metadata_holder=metadata_holder,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    output_parts: list[str] = []
    metadata = metadata_holder.get("text")
    if metadata:
        output_parts.append(format_metadata_comment(metadata))
    if merged_body.strip():
        output_parts.append(merged_body.strip())
    merged_output = "\n\n".join(output_parts).rstrip() + "\n"

    output_path = project_root / "build" / "merged" / "paper.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(merged_output, encoding="utf-8")

    total_lines = len(merged_output.splitlines())
    print(f"Wrote merged Markdown to {output_path}")
    print("Included files in order:")
    for item in included_order:
        print(f"- {item.relative_to(project_root)}")
    print(f"Total line count: {total_lines}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
