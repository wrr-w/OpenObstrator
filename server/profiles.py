from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProfileInfo:
    name: str
    path: Path
    is_default: bool


def list_profiles(hermes_root: Path) -> list[ProfileInfo]:
    result: list[ProfileInfo] = []
    profiles_root = hermes_root / "profiles"
    if profiles_root.is_dir():
        for entry in sorted(profiles_root.iterdir()):
            if entry.is_dir() and not entry.name.startswith("."):
                result.append(ProfileInfo(name=entry.name, path=entry, is_default=False))

    return result
