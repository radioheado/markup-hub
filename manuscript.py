from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from lib.config import load_config, resolve_group_settings, select_group


def run_python(script: Path, args: list[str], cwd: Path) -> int:
    result = subprocess.run([sys.executable, str(script)] + args, cwd=cwd)
    return result.returncode


def run_powershell(script: Path, cwd: Path) -> int:
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)],
        cwd=cwd,
    )
    return result.returncode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hub-owned manuscript pipeline for configured paper groups.")
    parser.add_argument(
        "action",
        choices=["merge", "number", "validate", "html", "docx", "pdf", "word", "all"],
        help="Pipeline step to run",
    )
    parser.add_argument("--config", default="collab_config.toml", help="Path to collab_config.toml")
    parser.add_argument("--group", help="Configured group name from collab_config.toml")
    return parser.parse_args()


def resolve_target(hub_dir: Path, config_path: Path, requested_group: str | None) -> tuple[str, Path, dict]:
    config = load_config(config_path)
    group_settings = resolve_group_settings(config)
    group_paths = {
        group_name: (hub_dir / group_data["main"]).resolve()
        for group_name, group_data in group_settings.items()
    }
    group_name, main_path = select_group(group_paths, requested_group, config.get("default_group"))
    return group_name, main_path.parent.resolve(), group_settings[group_name]


def main() -> int:
    args = parse_args()
    hub_dir = Path(__file__).resolve().parent
    config_path = (hub_dir / args.config).resolve()
    if not config_path.exists():
        print(f"Error: config not found: {config_path}", file=sys.stderr)
        return 1

    try:
        group_name, project_root, group_data = resolve_target(hub_dir, config_path, args.group)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    tools_dir = hub_dir / "hub_tools"
    docx_template = group_data.get("docx_template")
    template_args: list[str] = []
    if isinstance(docx_template, str) and docx_template.strip():
        template_path = (hub_dir / docx_template).resolve()
        template_args = ["--template", str(template_path)]

    steps: dict[str, tuple[str, list[str]] | tuple[str, None]] = {
        "merge": ("merge_md.py", []),
        "number": ("number_md.py", []),
        "validate": ("validate_md.py", ["--main", "main.md"]),
        "html": ("build_html.py", []),
        "docx": ("export_docx.py", template_args),
        "pdf": ("export_pdf.py", []),
        "word": ("build_word.ps1", None),
    }

    if args.action == "all":
        order = ["merge", "number", "validate", "html", "docx", "pdf"]
    else:
        order = [args.action]

    print(f"Group: {group_name}")
    print(f"Project root: {project_root}")
    for action in order:
        script_name, script_args = steps[action]
        print(f"==> {action}")
        script_path = tools_dir / script_name
        exit_code = (
            run_powershell(script_path, project_root)
            if script_args is None
            else run_python(script_path, script_args, project_root)
        )
        if exit_code != 0:
            return exit_code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
