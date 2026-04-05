from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from core.config import resolve_main_and_full_paths
from core.manifests import collect_group_sources
from core.numbering import number_group

HEADER_RE = re.compile(r"<!-- MARKUP-HUB-FULL (?P<meta>\{.*?\}) -->")
BLOCK_RE = re.compile(
    r"<!-- MARKUP-HUB-FILE (?P<meta>\{.*?\}) -->\n?(?P<body>.*?)(?:\n)?<!-- /MARKUP-HUB-FILE -->",
    re.DOTALL,
)
LEVEL1_RE = re.compile(r"^(#)\s+\d+\.\s+(.*)$")
LEVEL23_RE = re.compile(r"^(##|###)\s+\d+(?:\.\d+)+\s+(.*)$")
CAPTION_PREFIX_RE = re.compile(r"^\*\*(Table|Figure) (?P<token>\{\{(?:tbl|fig):[^}]+\}\}|\d+)\.\*\*")
BUILD_DATE_TOKEN = "{{build_date}}"


def emit(text: str) -> None:
    stream = getattr(sys.stdout, "buffer", None)
    if stream is not None:
        stream.write((text + "\n").encode("utf-8", errors="replace"))
    else:
        print(text)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync edits from paper.full.md back into chapter files.")
    parser.add_argument("--full", help="Path to the generated full manuscript Markdown file")
    parser.add_argument("--config", default="collab_config.toml", help="Path to collab_config.toml")
    parser.add_argument("--group", help="Configured group name from collab_config.toml")
    parser.add_argument("--dry-run", action="store_true", help="Print what would change without writing files")
    parser.add_argument("--force", action="store_true", help="Allow sync even if source files changed after build")
    parser.add_argument("--no-backup", action="store_true", help="Do not write .bak backups before updating files")
    parser.add_argument(
        "--prompt-commit",
        action="store_true",
        help="Prompt to create a Git commit after a successful sync",
    )
    parser.add_argument(
        "--commit-message",
        help="Commit message to use with --prompt-commit. Defaults to 'sync full manuscript: <filename>'",
    )
    return parser.parse_args()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_header(document: str) -> dict[str, object]:
    match = HEADER_RE.search(document)
    if not match:
        raise ValueError("MARKUP-HUB-FULL header not found")
    return json.loads(match.group("meta"))


def parse_blocks(document: str) -> list[tuple[dict[str, object], str]]:
    blocks: list[tuple[dict[str, object], str]] = []
    for match in BLOCK_RE.finditer(document):
        blocks.append((json.loads(match.group("meta")), match.group("body")))
    if not blocks:
        raise ValueError("No MARKUP-HUB-FILE blocks found")
    return blocks


def strip_generated_heading_numbers(line: str) -> str:
    match = LEVEL1_RE.match(line)
    if match:
        return f"{match.group(1)} {match.group(2)}"
    match = LEVEL23_RE.match(line)
    if match:
        return f"{match.group(1)} {match.group(2)}"
    return line


def build_caption_prefix_map(raw_text: str, processed_text: str) -> list[tuple[str, str]]:
    mappings: list[tuple[str, str]] = []
    raw_lines = raw_text.splitlines()
    processed_lines = processed_text.splitlines()
    for raw_line, processed_line in zip(raw_lines, processed_lines):
        raw_match = CAPTION_PREFIX_RE.match(raw_line)
        processed_match = CAPTION_PREFIX_RE.match(processed_line)
        if not raw_match or not processed_match:
            continue
        raw_prefix = raw_match.group(0)
        processed_prefix = processed_match.group(0)
        if raw_prefix != processed_prefix:
            mappings.append((processed_prefix, raw_prefix))
    return mappings


def restore_source_text(
    edited_text: str,
    raw_text: str,
    processed_text: str,
    *,
    build_date: str | None,
) -> str:
    caption_prefix_map = build_caption_prefix_map(raw_text, processed_text)
    restored_lines: list[str] = []
    for line in edited_text.splitlines():
        updated = strip_generated_heading_numbers(line)
        for processed_prefix, raw_prefix in caption_prefix_map:
            if updated.startswith(processed_prefix):
                updated = raw_prefix + updated[len(processed_prefix) :]
                break
        restored_lines.append(updated)
    restored = "\n".join(restored_lines)
    if build_date and BUILD_DATE_TOKEN in raw_text:
        restored = restored.replace(build_date, BUILD_DATE_TOKEN)
    if edited_text.endswith("\n"):
        restored += "\n"
    return restored


def maybe_commit(repo_dir: Path, paths: list[Path], message: str) -> None:
    response = input("Create a Git snapshot commit for these synced edits? [y/N]: ").strip().lower()
    if response not in {"y", "yes"}:
        emit("Skipped Git commit.")
        return

    rel_paths = [os.path.relpath(path, repo_dir) for path in paths]
    add_cmd = ["git", "add", "--"] + rel_paths
    commit_cmd = ["git", "commit", "-m", message]

    add_result = subprocess.run(add_cmd, cwd=repo_dir, capture_output=True, text=True)
    if add_result.returncode != 0:
        emit("Git add failed:")
        emit(add_result.stderr.strip() or add_result.stdout.strip())
        return

    commit_result = subprocess.run(commit_cmd, cwd=repo_dir, capture_output=True, text=True)
    if commit_result.returncode != 0:
        emit("Git commit failed:")
        emit(commit_result.stderr.strip() or commit_result.stdout.strip())
        return

    emit(commit_result.stdout.strip() or "Created Git commit.")


def main() -> int:
    args = parse_args()
    hub_dir = Path(__file__).resolve().parent
    try:
        _main_path, full_path, group_name = resolve_main_and_full_paths(
            hub_dir,
            full_arg=args.full,
            config_arg=args.config,
            group_arg=args.group,
        )
    except ValueError as exc:
        emit(f"Error: {exc}")
        return 1

    if not full_path.exists():
        emit(f"Error: full manuscript not found: {full_path}")
        return 1

    document = full_path.read_text(encoding="utf-8", errors="replace")
    try:
        header = parse_header(document)
        blocks = parse_blocks(document)
    except ValueError as exc:
        emit(f"Error: {exc}")
        return 1

    main_path = (full_path.parent / str(header["main"])).resolve()
    if not main_path.exists():
        emit(f"Error: manifest referenced by full file not found: {main_path}")
        return 1

    include_metadata = bool(header.get("includeMetadata", False))
    numbering_cfg = header.get("numbering", {})
    resolve_references = bool(numbering_cfg.get("references", False)) if isinstance(numbering_cfg, dict) else False
    generated_at = str(header.get("generated", ""))
    build_date = generated_at[:10] if len(generated_at) >= 10 else None
    main_dir = main_path.parent.resolve()

    file_list, raw_group_files, _labels = collect_group_sources(
        hub_dir,
        main_path,
        {},
        skip_metadata=not include_metadata,
        on_missing=lambda include_path: emit(f"Warning: included file missing: {include_path}"),
    )
    processed_group_files = number_group(file_list, raw_group_files, resolve_references=resolve_references)
    source_index = {(hub_dir / rel_path).resolve(): rel_path for rel_path in file_list}

    written_paths: list[Path] = []
    skipped_paths: list[str] = []
    unchanged = 0

    for meta, body in blocks:
        rel_path = str(meta["path"])
        source_path = (main_dir / rel_path).resolve()
        hub_rel = source_index.get(source_path)
        if hub_rel is None:
            skipped_paths.append(rel_path)
            emit(f"Warning: block path not found in current manifest: {source_path}")
            continue

        current_raw = raw_group_files[hub_rel]
        current_digest = sha256_text(current_raw)
        expected_digest = str(meta.get("sourceDigest", ""))
        if expected_digest and current_digest != expected_digest and not args.force:
            emit(f"Error: source changed since build, refusing to overwrite: {source_path}")
            emit("  Rebuild paper.full.md or rerun with --force if you intend to overwrite.")
            return 1

        original_processed = processed_group_files[hub_rel]
        restored = restore_source_text(
            body,
            current_raw,
            original_processed,
            build_date=build_date,
        )
        normalized_restored = restored.rstrip("\n") + "\n"
        normalized_current = current_raw.rstrip("\n") + "\n"
        if normalized_restored == normalized_current:
            unchanged += 1
            continue

        if args.dry_run:
            emit(f"Would update: {source_path}")
            written_paths.append(source_path)
            continue

        if not args.no_backup:
            backup_path = source_path.with_suffix(source_path.suffix + ".bak")
            backup_path.write_text(current_raw, encoding="utf-8")
        source_path.write_text(normalized_restored, encoding="utf-8")
        written_paths.append(source_path)
        emit(f"Updated: {source_path}")

    emit("")
    emit(f"Changed files: {len(written_paths)}")
    emit(f"Unchanged files: {unchanged}")
    if group_name:
        emit(f"Group: {group_name}")
    if skipped_paths:
        emit("Skipped blocks: " + ", ".join(skipped_paths))

    if args.prompt_commit and written_paths and not args.dry_run:
        git_probe = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=main_dir,
            capture_output=True,
            text=True,
        )
        if git_probe.returncode != 0:
            emit("Git repository not detected for the manuscript folder. Skipping commit prompt.")
            return 0

        repo_dir = Path(git_probe.stdout.strip()).resolve()
        commit_paths = written_paths + [full_path]
        commit_message = args.commit_message or f"sync full manuscript: {full_path.name}"
        maybe_commit(repo_dir, commit_paths, commit_message)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
