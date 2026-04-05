from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


IGNORED_PATH_PARTS = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        ".yarn",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        "build",
        "coverage",
        "dist",
        "node_modules",
        "target",
        "vendor",
        "venv",
    }
)
IGNORED_FILE_NAMES = frozenset({".DS_Store"})


@dataclass(frozen=True)
class WorkspaceTree:
    files: tuple[Path, ...]
    top_level_directories: tuple[str, ...]
    top_level_files: tuple[str, ...]
    skipped_paths: tuple[str, ...]


def should_ignore_repository_path(relative_path: Path) -> bool:
    if relative_path.name in IGNORED_FILE_NAMES:
        return True

    return any(part in IGNORED_PATH_PARTS for part in relative_path.parts)


def scan_workspace_tree(workspace_path: Path, *, skipped_limit: int = 200) -> WorkspaceTree:
    files: list[Path] = []
    top_level_directories: list[str] = []
    top_level_files: list[str] = []
    skipped_paths: list[str] = []

    for current_root, dirnames, filenames in os.walk(workspace_path, topdown=True):
        root_path = Path(current_root)
        relative_root = root_path.relative_to(workspace_path)

        kept_dirnames: list[str] = []
        for dirname in sorted(dirnames):
            relative_dir = relative_root / dirname
            if should_ignore_repository_path(relative_dir):
                _record_skipped_path(skipped_paths, f"{relative_dir.as_posix()}/", limit=skipped_limit)
            else:
                kept_dirnames.append(dirname)
                if relative_root == Path("."):
                    top_level_directories.append(dirname)
        dirnames[:] = kept_dirnames

        for filename in sorted(filenames):
            relative_file = relative_root / filename
            if should_ignore_repository_path(relative_file):
                _record_skipped_path(skipped_paths, relative_file.as_posix(), limit=skipped_limit)
            else:
                files.append(relative_file)
                if relative_root == Path("."):
                    top_level_files.append(filename)

    return WorkspaceTree(
        files=tuple(files),
        top_level_directories=tuple(top_level_directories),
        top_level_files=tuple(top_level_files),
        skipped_paths=tuple(skipped_paths),
    )


def _record_skipped_path(skipped_paths: list[str], value: str, *, limit: int) -> None:
    if len(skipped_paths) >= limit:
        return
    skipped_paths.append(value)
