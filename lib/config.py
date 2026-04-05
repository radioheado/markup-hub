from __future__ import annotations

import os
from pathlib import Path

try:
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib


def load_config(config_path: Path) -> dict:
    text = config_path.read_text(encoding="utf-8-sig")
    return tomllib.loads(text)


def is_group_enabled(group_data: dict) -> bool:
    return bool(group_data.get("enabled", True))


def resolve_groups(hub_dir: Path, config: dict) -> dict[str, Path]:
    groups_cfg = config.get("groups", {})
    return {
        group_name: (hub_dir / group_data["main"]).resolve()
        for group_name, group_data in groups_cfg.items()
        if is_group_enabled(group_data)
    }


def default_full_path(main_path: Path) -> Path:
    return main_path.parent / "paper.full.md"


def select_group(
    group_paths: dict[str, Path],
    requested_group: str | None,
    default_group: str | None = None,
) -> tuple[str, Path]:
    if requested_group:
        try:
            return requested_group, group_paths[requested_group]
        except KeyError as exc:
            available = ", ".join(group_paths) or "none"
            raise ValueError(f'Group "{requested_group}" not found. Available groups: {available}') from exc

    if default_group:
        try:
            return default_group, group_paths[default_group]
        except KeyError as exc:
            available = ", ".join(group_paths) or "none"
            raise ValueError(f'Default group "{default_group}" not found. Available groups: {available}') from exc

    if len(group_paths) == 1:
        group_name, main_path = next(iter(group_paths.items()))
        return group_name, main_path

    available = ", ".join(group_paths) or "none"
    raise ValueError(f"Multiple groups configured. Please specify --group. Available groups: {available}")


def resolve_main_and_full_paths(
    hub_dir: Path,
    *,
    main_arg: str | None = None,
    full_arg: str | None = None,
    config_arg: str = "collab_config.toml",
    group_arg: str | None = None,
) -> tuple[Path, Path, str | None]:
    if main_arg:
        main_path = (hub_dir / main_arg).resolve()
        full_path = (hub_dir / full_arg).resolve() if full_arg else default_full_path(main_path)
        return main_path, full_path, None

    config_path = (hub_dir / config_arg).resolve()
    if not config_path.exists():
        raise ValueError(f"Config not found: {config_path}")

    config = load_config(config_path)
    group_paths = resolve_groups(hub_dir, config)
    group_name, main_path = select_group(group_paths, group_arg, config.get("default_group"))

    if full_arg:
        full_path = (hub_dir / full_arg).resolve()
    else:
        full_path = default_full_path(main_path)
    return main_path, full_path, group_name


def repo_relative(path: Path, root: Path) -> str:
    return os.path.relpath(path, root).replace("\\", "/")
