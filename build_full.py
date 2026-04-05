from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from core.config import resolve_main_and_full_paths
from core.manifests import collect_group_sources
from core.numbering import number_group

HEADER_PREFIX = "<!-- MARKUP-HUB-FULL "
FILE_PREFIX = "<!-- MARKUP-HUB-FILE "
FILE_END = "<!-- /MARKUP-HUB-FILE -->"
BUILD_DATE_TOKEN = "{{build_date}}"


def emit(text: str) -> None:
    stream = getattr(sys.stdout, "buffer", None)
    if stream is not None:
        stream.write((text + "\n").encode("utf-8", errors="replace"))
    else:
        print(text)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a reversible full-manuscript Markdown file.")
    parser.add_argument("--main", help="Path to the main.md manifest")
    parser.add_argument("--config", default="collab_config.toml", help="Path to collab_config.toml")
    parser.add_argument("--group", help="Configured group name from collab_config.toml")
    parser.add_argument(
        "--out",
        help="Output path for the full manuscript Markdown file. Defaults to <main dir>/paper.full.md",
    )
    parser.add_argument(
        "--include-metadata",
        action="store_true",
        help="Include metadata.md if it appears in the manifest",
    )
    parser.add_argument(
        "--resolve-references",
        action="store_true",
        help="Replace {{sec:*}}, {{tbl:*}}, and {{fig:*}} references in the generated file",
    )
    return parser.parse_args()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def json_comment(prefix: str, payload: dict[str, object]) -> str:
    return f"{prefix}{json.dumps(payload, ensure_ascii=False, separators=(',', ':'))} -->"


def apply_dynamic_placeholders(text: str, build_date: str) -> str:
    return text.replace(BUILD_DATE_TOKEN, build_date)


def build_full_document(
    hub_dir: Path,
    main_path: Path,
    out_path: Path,
    *,
    include_metadata: bool,
    resolve_references: bool,
) -> tuple[str, list[str]]:
    file_list, raw_group_files, labels = collect_group_sources(
        hub_dir,
        main_path,
        {},
        skip_metadata=not include_metadata,
        on_missing=lambda include_path: emit(f"Warning: included file missing: {include_path}"),
    )
    processed_group_files = number_group(file_list, raw_group_files, resolve_references=resolve_references)
    main_dir = main_path.parent.resolve()
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    build_date = datetime.now().astimezone().date().isoformat()

    header_payload = {
        "version": 1,
        "main": os.path.relpath(main_path, out_path.parent).replace("\\", "/"),
        "generated": generated_at,
        "includeMetadata": include_metadata,
        "numbering": {
            "headings": True,
            "captions": True,
            "references": resolve_references,
        },
        "note": "Edit content inside file blocks only. Do not modify marker comments.",
    }

    parts = [json_comment(HEADER_PREFIX, header_payload), ""]
    for rel_path in file_list:
        abs_path = (hub_dir / rel_path).resolve()
        raw = raw_group_files[rel_path]
        processed = apply_dynamic_placeholders(processed_group_files[rel_path], build_date)
        block_payload = {
            "path": os.path.relpath(abs_path, main_dir).replace("\\", "/"),
            "label": labels.get(rel_path, Path(rel_path).stem),
            "sourceDigest": sha256_text(raw),
        }
        parts.append(json_comment(FILE_PREFIX, block_payload))
        parts.append(processed.rstrip("\n"))
        parts.append(FILE_END)
        parts.append("")

    document = "\n".join(parts).rstrip() + "\n"
    return document, file_list


def report_success(
    out_path: Path,
    main_path: Path,
    file_count: int,
    resolve_references: bool,
    group_name: str | None,
) -> int:
    emit(f"Built full manuscript: {out_path}")
    emit(f"  Source manifest: {main_path}")
    emit(f"  Included files: {file_count}")
    emit("  Numbering: headings=yes, captions=yes, references=" + ("yes" if resolve_references else "no"))
    if group_name:
        emit(f"  Group: {group_name}")
    return 0


def main() -> int:
    args = parse_args()
    hub_dir = Path(__file__).resolve().parent
    try:
        main_path, out_path, group_name = resolve_main_and_full_paths(
            hub_dir,
            main_arg=args.main,
            full_arg=args.out,
            config_arg=args.config,
            group_arg=args.group,
        )
    except ValueError as exc:
        emit(f"Error: {exc}")
        return 1
    if not main_path.exists():
        emit(f"Error: main manifest not found: {main_path}")
        return 1

    document, file_list = build_full_document(
        hub_dir,
        main_path,
        out_path,
        include_metadata=args.include_metadata,
        resolve_references=args.resolve_references,
    )
    out_path.write_text(document, encoding="utf-8")
    return report_success(out_path, main_path, len(file_list), args.resolve_references, group_name)

    emit(f"✓ Built full manuscript: {out_path}")
    emit(f"Built full manuscript: {out_path}")
    emit(f"  Source manifest: {main_path}")
    emit(f"  Included files: {len(file_list)}")
    emit("  Numbering: headings=yes, captions=yes, references=" + ("yes" if args.resolve_references else "no"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
