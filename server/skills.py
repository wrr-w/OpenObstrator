from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re

import yaml

from server.configfile import write_raw_yaml


@dataclass(frozen=True)
class SkillItem:
    name: str
    path: Path
    enabled: bool
    description: str = ""
    category: str | None = None
    source: str = "local"


_EXCLUDED_SKILL_DIRS = frozenset((".git", ".github", ".hub", ".archive"))
_FRONTMATTER_END_RE = re.compile(r"\n---\s*\n")
_PLATFORM_MAP = {
    "macos": "darwin",
    "linux": "linux",
    "windows": "win32",
}


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    if not content.startswith("---"):
        return {}, content
    m = _FRONTMATTER_END_RE.search(content[3:])
    if not m:
        return {}, content
    yaml_content = content[3 : m.start() + 3]
    body = content[m.end() + 3 :]
    try:
        parsed = yaml.safe_load(yaml_content)
    except Exception:
        parsed = {}
    return (parsed if isinstance(parsed, dict) else {}), body


def _skill_matches_platform(frontmatter: dict) -> bool:
    platforms = frontmatter.get("platforms")
    if not platforms:
        return True
    if not isinstance(platforms, list):
        platforms = [platforms]
    current = os.sys.platform
    for p in platforms:
        normalized = str(p).lower().strip()
        mapped = _PLATFORM_MAP.get(normalized, normalized)
        if current.startswith(mapped):
            return True
    return False


def _iter_skill_index_files(skills_dir: Path) -> list[Path]:
    if not skills_dir.is_dir():
        return []
    out: list[Path] = []
    for p in skills_dir.rglob("SKILL.md"):
        if any(part in _EXCLUDED_SKILL_DIRS for part in p.parts):
            continue
        out.append(p)
    return sorted(out)


def skill_name_from_md_path(*, profile_dir: Path, md_path: Path) -> str:
    skills_dir = profile_dir / "skills"
    rel = md_path.parent.relative_to(skills_dir)
    return rel.as_posix()


def _load_skills_config(profile_dir: Path) -> dict:
    cfg_path = profile_dir / "config.yaml"
    if not cfg_path.exists():
        return {}

    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return {}

    skills_cfg = raw.get("skills", {}) if isinstance(raw.get("skills"), dict) else {}
    return skills_cfg if isinstance(skills_cfg, dict) else {}


def _normalize_string_set(values) -> set[str]:
    if values is None:
        return set()
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list):
        return set()
    return {str(v).strip() for v in values if str(v).strip()}


def get_disabled_skill_names(*, profile_dir: Path, platform: str | None = None) -> set[str]:
    skills_cfg = _load_skills_config(profile_dir)
    resolved_platform = platform or os.environ.get("HERMES_PLATFORM", "").strip() or None
    if resolved_platform:
        pd = skills_cfg.get("platform_disabled", {})
        if isinstance(pd, dict):
            platform_disabled = pd.get(resolved_platform)
            if platform_disabled is not None:
                return _normalize_string_set(platform_disabled)
    return _normalize_string_set(skills_cfg.get("disabled"))


def get_external_skills_dirs(profile_dir: Path) -> list[Path]:
    skills_cfg = _load_skills_config(profile_dir)
    raw_dirs = skills_cfg.get("external_dirs")
    if not raw_dirs:
        return []
    if isinstance(raw_dirs, str):
        raw_dirs = [raw_dirs]
    if not isinstance(raw_dirs, list):
        return []

    local_skills = (profile_dir / "skills").resolve()
    seen: set[Path] = set()
    out: list[Path] = []
    for entry in raw_dirs:
        entry = str(entry).strip()
        if not entry:
            continue
        expanded = os.path.expanduser(os.path.expandvars(entry))
        p = Path(expanded)
        p = (profile_dir / p).resolve() if not p.is_absolute() else p.resolve()
        if p == local_skills:
            continue
        if p in seen:
            continue
        seen.add(p)
        if p.is_dir():
            out.append(p)
    return out


def set_skill_enabled(profile_dir: Path, skill_name: str, enabled: bool) -> None:
    cfg_path = profile_dir / "config.yaml"
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
    if not isinstance(raw, dict):
        raw = {}

    skills_cfg = raw.get("skills", {}) if isinstance(raw.get("skills"), dict) else {}
    disabled = skills_cfg.get("disabled", []) if isinstance(skills_cfg.get("disabled"), list) else []
    disabled_set = {str(x) for x in disabled}

    if enabled:
        disabled_set.discard(skill_name)
    else:
        disabled_set.add(skill_name)

    skills_cfg["disabled"] = sorted(disabled_set)
    raw["skills"] = skills_cfg

    rendered = yaml.safe_dump(raw, sort_keys=False, allow_unicode=True)
    write_raw_yaml(cfg_path, rendered)


def _category_from_skill_md_path(skill_md: Path, skills_dir: Path) -> str | None:
    try:
        rel = skill_md.relative_to(skills_dir)
    except ValueError:
        return None
    parts = rel.parts
    if len(parts) >= 3:
        return parts[0]
    return None


def list_skills(profile_dir: Path, platform: str | None = None) -> list[SkillItem]:
    disabled = get_disabled_skill_names(profile_dir=profile_dir, platform=platform)
    items: list[SkillItem] = []
    seen: set[str] = set()

    local_dir = profile_dir / "skills"
    scan_dirs: list[tuple[str, Path]] = []
    if local_dir.exists():
        scan_dirs.append(("local", local_dir))
    for d in get_external_skills_dirs(profile_dir):
        scan_dirs.append(("external", d))

    for source, skills_dir in scan_dirs:
        for skill_md in _iter_skill_index_files(skills_dir):
            skill_dir = skill_md.parent
            try:
                content = skill_md.read_text(encoding="utf-8", errors="replace")[:4000]
            except OSError:
                continue
            fm, body = _parse_frontmatter(content)
            if not _skill_matches_platform(fm):
                continue

            name = str(fm.get("name") or skill_dir.name).strip()
            if not name or name in seen:
                continue

            description = str(fm.get("description") or "").strip()
            if not description:
                for line in body.strip().split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        description = line
                        break

            category = _category_from_skill_md_path(skill_md, skills_dir)
            seen.add(name)
            items.append(
                SkillItem(
                    name=name,
                    path=skill_md,
                    enabled=name not in disabled,
                    description=description,
                    category=category,
                    source=source,
                )
            )

    return items


def list_skills_nanoghost(
    instance_dir: Path,
    platform: str | None = None,
    shared_dir: Path | None = None,
) -> list[SkillItem]:
    shared_dir = shared_dir or Path(os.path.expanduser("~/.agents/skills"))
    disabled = _normalize_string_set(_load_skills_config(instance_dir).get("disabled"))
    items: list[SkillItem] = []
    seen: set[str] = set()

    for skill_md in _iter_skill_index_files(shared_dir):
        skill_dir = skill_md.parent
        try:
            content = skill_md.read_text(encoding="utf-8", errors="replace")[:4000]
        except OSError:
            continue
        fm, body = _parse_frontmatter(content)
        if not _skill_matches_platform(fm):
            continue

        name = str(fm.get("name") or skill_dir.name).strip()
        if not name or name in seen:
            continue

        description = str(fm.get("description") or "").strip()
        if not description:
            for line in body.strip().split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    description = line
                    break

        category = _category_from_skill_md_path(skill_md, shared_dir)
        seen.add(name)
        items.append(
            SkillItem(
                name=name,
                path=skill_md,
                enabled=name not in disabled,
                description=description,
                category=category,
                source="external",
            )
        )

    return items


def list_global_skills_runtime(
    shared_dir: Path,
    platform: str | None = None,
) -> list[dict]:
    items: list[dict] = []
    seen: set[str] = set()

    for skill_md in _iter_skill_index_files(shared_dir):
        skill_dir = skill_md.parent
        try:
            content = skill_md.read_text(encoding="utf-8", errors="replace")[:4000]
        except OSError:
            continue
        fm, body = _parse_frontmatter(content)
        if not _skill_matches_platform(fm):
            continue

        name = str(fm.get("name") or skill_dir.name).strip()
        if not name or name in seen:
            continue

        description = str(fm.get("description") or "").strip()
        if not description:
            for line in body.strip().split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    description = line
                    break

        category = _category_from_skill_md_path(skill_md, shared_dir)
        seen.add(name)
        items.append({
            "name": name,
            "path": str(skill_md),
            "description": description,
            "category": category,
        })

    return items


def set_skill_enabled_nanoghost(instance_dir: Path, skill_name: str, enabled: bool) -> None:
    cfg_path = instance_dir / "config.yaml"
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
    if not isinstance(raw, dict):
        raw = {}

    skills_cfg = raw.get("skills", {}) if isinstance(raw.get("skills"), dict) else {}
    disabled = skills_cfg.get("disabled", []) if isinstance(skills_cfg.get("disabled"), list) else []
    disabled_set = {str(x).strip() for x in disabled if str(x).strip()}

    skill_name = str(skill_name or "").strip()
    if not skill_name:
        raise ValueError("invalid skill name")

    if enabled:
        disabled_set.discard(skill_name)
    else:
        disabled_set.add(skill_name)

    skills_cfg["disabled"] = sorted(disabled_set)
    raw["skills"] = skills_cfg

    rendered = yaml.safe_dump(raw, sort_keys=False, allow_unicode=True)
    write_raw_yaml(cfg_path, rendered)
