from __future__ import annotations

import re
from pathlib import Path

from server.template_copy import clone_template_dir


_PROFILE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_RESERVED_NAMES = frozenset({"hermes", "default", "test", "tmp", "root", "sudo"})


def validate_profile_name(name: str) -> None:
    if not isinstance(name, str):
        raise ValueError("invalid profile name")
    n = name.strip()
    if not n:
        raise ValueError("profile name cannot be empty")
    if n != n.lower():
        raise ValueError("profile name must be lowercase")
    if not _PROFILE_ID_RE.match(n):
        raise ValueError("invalid profile name")
    if n in _RESERVED_NAMES:
        raise ValueError("profile name is reserved")


def create_profile_clone_default(*, hermes_root: Path, name: str) -> Path:
    validate_profile_name(name)
    profiles_root = hermes_root / "profiles"
    profile_dir = profiles_root / name
    if profile_dir.exists():
        raise FileExistsError("profile already exists")
    profiles_root.mkdir(parents=True, exist_ok=True)

    clone_template_dir(
        template_dir=hermes_root,
        dest_dir=profile_dir,
        exclude_names={"profiles"},
    )

    for sub in ["memories", "sessions", "skills", "skins", "logs", "plans", "workspace", "cron", "home"]:
        (profile_dir / sub).mkdir(parents=True, exist_ok=True)
    return profile_dir
