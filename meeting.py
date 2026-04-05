from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from lib.config import load_config, resolve_groups


def run_step(script: str, args: list[str], hub_dir: Path) -> int:
    command = [sys.executable, str(hub_dir / script)] + args
    result = subprocess.run(command, cwd=hub_dir)
    return result.returncode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Config-driven meeting workflow for full-manuscript review.")
    parser.add_argument("action", choices=["build", "build-all", "sync"], help="Workflow step to run")
    parser.add_argument("--config", default="collab_config.toml", help="Path to collab_config.toml")
    parser.add_argument("--group", help="Configured group name from collab_config.toml")
    parser.add_argument("--full", help="Override the full manuscript path")
    parser.add_argument("--resolve-references", action="store_true", help="Resolve refs during build")
    parser.add_argument("--include-metadata", action="store_true", help="Include metadata.md during build")
    parser.add_argument("--dry-run", action="store_true", help="Dry-run sync without writing files")
    parser.add_argument("--force", action="store_true", help="Force sync even if sources changed since build")
    parser.add_argument("--no-backup", action="store_true", help="Skip .bak backups during sync")
    parser.add_argument("--prompt-commit", action="store_true", help="Prompt for a Git commit after sync")
    parser.add_argument("--commit-message", help="Commit message to use when creating a sync commit")
    return parser.parse_args()


def build_all(args: argparse.Namespace, hub_dir: Path) -> int:
    config_path = (hub_dir / args.config).resolve()
    config = load_config(config_path)
    groups = resolve_groups(hub_dir, config)
    if not groups:
        print("No enabled groups found in collab_config.toml.")
        return 1

    exit_code = 0
    for group_name in groups:
        print(f"==> Building: {group_name}")
        build_args = ["--config", args.config, "--group", group_name]
        if args.include_metadata:
            build_args.append("--include-metadata")
        if args.resolve_references:
            build_args.append("--resolve-references")
        if run_step("build_full.py", build_args, hub_dir) != 0:
            exit_code = 1
    return exit_code


def main() -> int:
    args = parse_args()
    hub_dir = Path(__file__).resolve().parent

    if args.action == "build-all":
        return build_all(args, hub_dir)

    common_args = ["--config", args.config]
    if args.group:
        common_args += ["--group", args.group]
    if args.full:
        common_args += ["--full" if args.action == "sync" else "--out", args.full]

    if args.action == "build":
        build_args = list(common_args)
        if args.include_metadata:
            build_args.append("--include-metadata")
        if args.resolve_references:
            build_args.append("--resolve-references")
        return run_step("build_full.py", build_args, hub_dir)

    sync_args = list(common_args)
    if args.dry_run:
        sync_args.append("--dry-run")
    if args.force:
        sync_args.append("--force")
    if args.no_backup:
        sync_args.append("--no-backup")
    if args.prompt_commit:
        sync_args.append("--prompt-commit")
    if args.commit_message:
        sync_args += ["--commit-message", args.commit_message]
    return run_step("sync_full.py", sync_args, hub_dir)


if __name__ == "__main__":
    raise SystemExit(main())
