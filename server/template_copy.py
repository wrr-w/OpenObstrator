from __future__ import annotations

import os
import shutil
from pathlib import Path

_DEFAULT_EXCLUDES = frozenset(
    {
        ".git",
        ".venv",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
    }
)

_ALLOW_DOT_NAMES = frozenset({".env"})


def _assert_no_symlinks(root: Path) -> None:
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dp = Path(dirpath)
        for name in dirnames:
            if (dp / name).is_symlink():
                raise ValueError("template_dir contains symlink")
        for name in filenames:
            if (dp / name).is_symlink():
                raise ValueError("template_dir contains symlink")


def clone_template_dir(*, template_dir: Path, dest_dir: Path, exclude_names: set[str]) -> None:
    if not template_dir.is_dir():
        raise ValueError("template_dir is not a directory")
    if dest_dir.exists():
        raise FileExistsError("dest_dir already exists")

    excludes = set(exclude_names) | set(_DEFAULT_EXCLUDES)

    tpl_res = template_dir.resolve()
    dest_res = dest_dir.resolve()
    try:
        rel = dest_res.relative_to(tpl_res)
    except ValueError:
        rel = None
    if rel and rel.parts and rel.parts[0] not in excludes:
        raise ValueError("dest_dir cannot be inside template_dir unless excluded")

    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    dest_dir.mkdir(parents=True, exist_ok=False)

    for entry in template_dir.iterdir():
        name = entry.name
        if name in excludes:
            continue
        if name.startswith(".") and name not in _ALLOW_DOT_NAMES:
            continue
        if entry.is_symlink():
            raise ValueError("template_dir contains symlink")

        target = dest_dir / name
        if entry.is_dir():
            _assert_no_symlinks(entry)
            shutil.copytree(entry, target, dirs_exist_ok=False)
        elif entry.is_file():
            shutil.copy2(entry, target)
