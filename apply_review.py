from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import re
import sys

BLOCK_SPLIT_RE = re.compile(r'\n\n+')


def emit(text: str) -> None:
    stream = getattr(sys.stdout, 'buffer', None)
    if stream is not None:
        stream.write((text + '\n').encode('utf-8', errors='replace'))
    else:
        print(text)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Apply markup-hub reviews into markdown files.')
    parser.add_argument('--hub', default='.', help='Path to the markup-hub directory')
    parser.add_argument('--dry-run', action='store_true', help='Print changes without writing files')
    parser.add_argument('--no-backup', action='store_true', help='Do not write .bak backups')
    return parser.parse_args()


def truncate_quote(text: str, limit: int = 200) -> str:
    compact = ' '.join(text.split())
    return compact[:limit]


def format_stamp(value: str) -> str:
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        dt = datetime.now()
    return dt.strftime('%Y-%m-%d %H:%M')


def format_comment(annotation: dict) -> str:
    reviewer = annotation.get('reviewer', 'Unknown')
    stamp = format_stamp(annotation.get('timestamp', ''))
    quote = truncate_quote(annotation.get('quote', ''))
    text = annotation.get('text', '').strip()
    if annotation.get('type') == 'edit':
        suggested = '\n'.join('       ' + line for line in (text.splitlines() or ['']))
        return (
            f'<!-- EDIT-SUGGESTION {reviewer} | {stamp}\n'
            f'     original:  "{quote}"\n'
            f'     suggested:\n'
            f'{suggested}\n'
            f'-->'
        )
    return (
        f'<!-- REVIEW {reviewer} | {stamp}\n'
        f'     quote:   "{quote}"\n'
        f'     comment: {text}\n'
        f'-->'
    )


def main() -> int:
    args = parse_args()
    hub_dir = Path(args.hub).resolve()
    reviews_path = hub_dir / 'reviews.json'
    if not reviews_path.exists():
        emit(f'reviews.json not found in {hub_dir}')
        return 1

    data = json.loads(reviews_path.read_text(encoding='utf-8'))
    annotations = data.get('annotations', [])
    grouped: dict[str, list[dict]] = defaultdict(list)
    for annotation in annotations:
        filename = annotation.get('filename')
        if filename:
            grouped[filename].append(annotation)

    applied = 0
    skipped = 0
    missing_files: list[str] = []

    for filename, file_annotations in grouped.items():
        resolved = (hub_dir / filename).resolve()
        if not resolved.exists():
            missing_files.append(filename)
            skipped += len(file_annotations)
            emit(f'Warning: target file missing: {resolved}')
            continue

        original = resolved.read_text(encoding='utf-8', errors='replace')
        blocks = BLOCK_SPLIT_RE.split(original) if original else ['']
        if not blocks:
            blocks = ['']

        for annotation in sorted(file_annotations, key=lambda item: int(item.get('paragraphIndex', 0)), reverse=True):
            idx = min(max(int(annotation.get('paragraphIndex', 0)), 0), len(blocks) - 1)
            blocks.insert(idx + 1, format_comment(annotation))
            applied += 1

        updated = '\n\n'.join(blocks)
        if args.dry_run:
            emit(f'--- {resolved} ---')
            emit(updated)
            continue

        if not args.no_backup:
            backup_path = resolved.with_suffix(resolved.suffix + '.bak')
            backup_path.write_text(original, encoding='utf-8')
        resolved.write_text(updated, encoding='utf-8')

    emit(f'Applied: {applied} annotations across {len(grouped) - len(missing_files)} files')
    emit(f'Skipped: {skipped} annotations (files not found: {missing_files})')
    emit('')
    emit('Next steps:')
    emit('  1. Open modified .md files in VSCode')
    emit('  2. Search for <!-- REVIEW or <!-- EDIT-SUGGESTION')
    emit('  3. Review each annotation, apply edits manually if accepted')
    emit('  4. Delete the comment blocks when done')
    emit('  5. Run build_viewer.py to refresh the viewer')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
