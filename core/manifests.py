from __future__ import annotations

import os
import re
from pathlib import Path

INCLUDE_RE = re.compile(r"<!-- INCLUDE (.+?) -->")
HEADING_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
BOM = "\ufeff"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def to_hub_relative(path: Path, hub_dir: Path) -> str:
    return os.path.relpath(path.resolve(), hub_dir.resolve()).replace("\\", "/")


def extract_label(file_path: Path, content: str, labels: dict[str, str], hub_dir: Path) -> str:
    rel_path = to_hub_relative(file_path, hub_dir)
    if rel_path in labels:
        return labels[rel_path]
    match = HEADING_RE.search(content.lstrip(BOM))
    if match:
        return match.group(1).strip()
    return file_path.stem.replace("_", " ")


def collect_group_sources(
    hub_dir: Path,
    main_path: Path,
    labels_cfg: dict[str, str],
    *,
    skip_metadata: bool = True,
    on_missing: callable | None = None,
) -> tuple[list[str], dict[str, str], dict[str, str]]:
    main_content = read_text(main_path)
    file_list: list[str] = []
    raw_group_files: dict[str, str] = {}
    labels: dict[str, str] = {}

    for include in INCLUDE_RE.findall(main_content):
        include_path = (main_path.parent / include).resolve()
        try:
            content = read_text(include_path)
        except FileNotFoundError:
            if on_missing is not None:
                on_missing(include_path)
            continue
        if skip_metadata and include_path.name == "metadata.md":
            continue
        rel_path = to_hub_relative(include_path, hub_dir)
        file_list.append(rel_path)
        raw_group_files[rel_path] = content
        labels[rel_path] = extract_label(include_path, content, labels_cfg, hub_dir)

    return file_list, raw_group_files, labels
