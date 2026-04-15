from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from core.config import load_config
from core.manifests import collect_group_sources, read_text
from core.numbering import number_group

BUILD_DATE_TOKEN = "{{build_date}}"
IMAGE_LINK_RE = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')


def emit(text: str) -> None:
    stream = getattr(sys.stdout, 'buffer', None)
    if stream is not None:
        stream.write((text + '\n').encode('utf-8', errors='replace'))
    else:
        print(text)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Build the markup-hub HTML viewer.')
    parser.add_argument('--config', default='collab_config.toml', help='Path to collab_config.toml')
    parser.add_argument('--out', default='../collab_viewer.html', help='Output HTML path')
    return parser.parse_args()


def apply_dynamic_placeholders(text: str, build_date: str) -> str:
    return text.replace(BUILD_DATE_TOKEN, build_date)


def rewrite_image_links(text: str, rel_path: str, viewer_root: Path, hub_dir: Path) -> str:
    source_path = (hub_dir / rel_path).resolve()

    def replace(match: re.Match) -> str:
        alt_text = match.group(1)
        target = match.group(2).strip()
        if re.match(r'^([a-z][a-z0-9+.-]*:|/|#)', target, re.I):
            return match.group(0)
        asset_path = (source_path.parent / target).resolve()
        try:
            normalized = os.path.relpath(asset_path, viewer_root).replace('\\', '/')
        except ValueError:
            return match.group(0)
        return f'![{alt_text}]({normalized})'

    return IMAGE_LINK_RE.sub(replace, text)


def main() -> int:
    args = parse_args()
    hub_dir = Path(__file__).resolve().parent
    config_path = (hub_dir / args.config).resolve()
    out_path = (hub_dir / args.out).resolve()
    template_path = hub_dir / 'collab_viewer_template.html'

    config = load_config(config_path)

    labels_cfg = {str(key).replace('\\', '/'): value for key, value in config.get('labels', {}).items()}
    groups_cfg = config.get('groups', {})
    build_date = datetime.now().astimezone().date().isoformat()
    groups: dict[str, list[str]] = {}
    labels: dict[str, str] = {}
    files: dict[str, str] = {}
    total_chars = 0

    viewer_root = out_path.parent

    for group_name, group_data in groups_cfg.items():
        if not group_data.get('enabled', True):
            continue
        main_path = (hub_dir / group_data['main']).resolve()
        try:
            main_content = read_text(main_path)
        except FileNotFoundError:
            emit(f'Warning: main manifest missing for {group_name}: {main_path}')
            groups[group_name] = []
            continue
        except UnicodeDecodeError as exc:
            emit(f'Error: non-UTF-8 file in {group_name}: {main_path} ({exc})')
            return 1

        file_list, raw_group_files, group_labels = collect_group_sources(
            hub_dir,
            main_path,
            labels_cfg,
            skip_metadata=True,
            on_missing=lambda include_path: emit(f'Warning: included file missing: {include_path}'),
        )

        labels.update(group_labels)

        processed_group_files = number_group(file_list, raw_group_files)
        for rel_path in file_list:
            processed = apply_dynamic_placeholders(processed_group_files[rel_path], build_date)
            processed = rewrite_image_links(processed, rel_path, viewer_root, hub_dir)
            files[rel_path] = processed
            total_chars += len(processed)
        groups[group_name] = file_list

    docs_data = {
        'project': config['project'],
        'subtitle': config['subtitle'],
        'reviewers': config['reviewers'],
        'groups': groups,
        'labels': labels,
        'files': files,
    }

    try:
        template = read_text(template_path)
    except UnicodeDecodeError as exc:
        emit(f'Error: non-UTF-8 template file: {template_path} ({exc})')
        return 1
    html = template.replace('__DOCS_DATA__', json.dumps(docs_data, ensure_ascii=False, separators=(',', ':')), 1)
    out_path.write_text(html, encoding='utf-8')

    emit(f'✓ Built: {out_path}')
    emit(f'  {len(files)} files · {total_chars} chars · {out_path.stat().st_size / 1024:.1f} KB')
    emit('  Groups: ' + (', '.join(f'{name} ({len(paths)} files)' for name, paths in groups.items()) or 'None'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
