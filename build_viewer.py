from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from core.config import load_config
from core.manifests import collect_group_sources, read_text
from core.numbering import number_group

BUILD_DATE_TOKEN = "{{build_date}}"


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

    template = read_text(template_path)
    html = template.replace('__DOCS_DATA__', json.dumps(docs_data, ensure_ascii=False, separators=(',', ':')), 1)
    out_path.write_text(html, encoding='utf-8')

    emit(f'✓ Built: {out_path}')
    emit(f'  {len(files)} files · {total_chars} chars · {out_path.stat().st_size / 1024:.1f} KB')
    emit('  Groups: ' + (', '.join(f'{name} ({len(paths)} files)' for name, paths in groups.items()) or 'None'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
