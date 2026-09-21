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
    content = content.lstrip("\ufeff")
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


def _load_skill_desc(skill_md: Path) -> str:
    """读取 SKILL.md 的 description (frontmatter → body 首行).

    **不做平台过滤**：这个函数只被 `scan_group_meta` 调用，而它的三个调用点全是
    nanoghost。NanoGhost 读 SKILL.md 时压根不看 `platforms:` —— 只把它存进
    `SkillDefinition.platforms` 供序列化，不参与任何判断。这边要是拿它把描述清空，
    面板的分组标题就会莫名少一行字，而 agent 那边一切正常。
    （Hermes 那条路有自己的平台语义 —— `platform_disabled`，但走的不是这个函数。）
    """
    try:
        content = skill_md.read_text(encoding="utf-8", errors="replace")[:4000]
    except OSError:
        return ""
    fm, body = _parse_frontmatter(content)
    desc = str(fm.get("description") or "").strip()
    if desc:
        return desc
    for line in body.strip().split("\n"):
        line = line.strip()
        if line and not line.startswith("#"):
            return line
    return ""


def scan_group_meta(skills_dir: Path) -> dict[str, str]:
    """提取每个深度=1 节点的 name → description, 用作 UI 组标题描述."""
    meta: dict[str, str] = {}
    if not skills_dir.is_dir():
        return meta
    for skill_md in skills_dir.rglob("SKILL.md"):
        try:
            rel = skill_md.relative_to(skills_dir)
        except ValueError:
            continue
        if len(rel.parts) != 2:
            continue
        gn = rel.parts[0]
        if gn in meta:
            continue
        desc = _load_skill_desc(skill_md)
        if desc:
            meta[gn] = desc
    return meta


def _category_from_skill_md_path(skill_md: Path, skills_dir: Path) -> str | None:
    """每个节点的 category = 最近一个也有 SKILL.md 的祖先目录名.
    深度=1 的节点 category = 自身目录名 (自己就是一个分组)."""
    try:
        rel = skill_md.relative_to(skills_dir)
    except ValueError:
        return None
    parts = rel.parts
    if len(parts) == 2:
        return parts[0]
    # 从祖父目录开始向上找有 SKILL.md 的祖先
    p = skill_md.parent.parent
    while p != skills_dir:
        if (p / "SKILL.md").is_file():
            return p.name
        p = p.parent
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


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent)
        return True
    except ValueError:
        return False


def _expand_skill_dir(raw: object, instance_dir: Path) -> Path | None:
    """展开一条 skills.dirs / extra_dirs 里的路径，指不到目录就返回 None。

    和 NanoGhost `resolve_instance_skill_dirs` 里的 `_expand` 同一套规则：
    `./x` 相对实例目录，`.` 就是实例目录本身，其余按 ~ 展开。
    """
    entry = str(raw).strip()
    if not entry:
        return None
    if entry.startswith("./") or entry.startswith(".\\"):
        p = instance_dir / entry[2:]
    elif entry == ".":
        p = instance_dir
    else:
        p = Path(os.path.expanduser(os.path.expandvars(entry)))
    return p if p.is_dir() else None


def _ordered_scan_dirs(*, instance_dir: Path, shared_dir: Path) -> list[Path]:
    """这次到底扫哪些目录 —— 逐条对齐 NanoGhost 的 `resolve_instance_skill_dirs`。

        配了 skills.dirs   → **只扫这些**，共享目录也丢掉
        配了 extra_dirs    → 那些 + 共享目录（**顶掉** <实例>/skills，不是并列）
        都没配             → 实例自己的 skills/ + 共享目录

    顺序 = 优先级，**实例目录排前面**：实例里放个同名技能就是为了覆盖全局那份。
    NanoGhost 的 `discover_skills` 按同一个顺序去重（先扫到的赢），面板列出的名字和
    来源必须跟 agent 实际拿到的那个是同一个。
    """
    cfg = _load_skills_config(instance_dir)

    def expand(key: str) -> list[Path]:
        raw = cfg.get(key)
        if not isinstance(raw, list):
            return []
        return [p for p in (_expand_skill_dir(x, instance_dir) for x in raw) if p]

    dirs = expand("dirs")
    if dirs:
        return dirs

    out = expand("extra_dirs")
    if not out:
        local = instance_dir / "skills"
        if local.is_dir():
            out = [local]

    if shared_dir.is_dir():
        out.append(shared_dir)
    return out


def _read_skill_md(md_path: Path) -> tuple[str, str]:
    """读 SKILL.md 的 (frontmatter name, description)。name 缺了就是空串。"""
    try:
        content = md_path.read_text(encoding="utf-8", errors="replace")[:4000]
    except OSError:
        return "", ""
    fm, body = _parse_frontmatter(content)
    name = str(fm.get("name") or "").strip()
    description = str(fm.get("description") or "").strip()
    if not description:
        for line in body.strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                description = line
                break
    return name, description


def _list_subdirs(basedir: Path) -> list[Path]:
    try:
        return sorted((d for d in basedir.iterdir() if d.is_dir()), key=lambda p: p.name)
    except (OSError, NotADirectoryError):
        return []


def _nanoghost_entries(
    skills_dir: Path, taken: set[str],
) -> list[tuple[str, Path, str | None, str]]:
    """照抄 NanoGhost 的遍历，返回 (名字, SKILL.md 路径, 分组, 描述)。

    逐条对齐 `discover_skills` + `_load_group_skills`，四个容易漏的点：

    · **只认两层**：扫描根 → 分组目录 → 子技能。第三层（分组/子/更深）NanoGhost
      的 `_list_subdirs` 只走一层，看不见，所以这里也不列。
    · **分组目录自己有 SKILL.md 时，会作为一个技能注册，名字取目录名**（不是
      frontmatter 里的 name）。`build_skill_context` 给出的展开提示正是
      `use_skill(name="分组名")` —— 名字对不上那个分组就展不开。
    · **缺 frontmatter name 的技能直接跳过**：`load_skill_from_dir` 是
      `if not name: return None`。回退成目录名会列出一个勾了也没用的假名字。
    · **去重按目录名**（NanoGhost 的 `loaded_names` 装的是目录名），`taken` 跨扫描根
      累计 —— 谁先扫到算谁的。
    """
    out: list[tuple[str, Path, str | None, str]] = []
    for entry in _list_subdirs(skills_dir):
        subs = [s for s in _list_subdirs(entry) if (s / "SKILL.md").is_file()]
        if subs:
            # 分组（显式：自己有 SKILL.md；隐式：没有但子目录有）
            if (entry / "SKILL.md").is_file() and entry.name not in taken:
                taken.add(entry.name)
                _, group_desc = _read_skill_md(entry / "SKILL.md")
                out.append((entry.name, entry / "SKILL.md", entry.name, group_desc))
            for sub in subs:
                if sub.name in taken:
                    continue
                taken.add(sub.name)
                name, desc = _read_skill_md(sub / "SKILL.md")
                if name:
                    out.append((name, sub / "SKILL.md", entry.name, desc))
            continue
        if not (entry / "SKILL.md").is_file() or entry.name in taken:
            continue
        taken.add(entry.name)
        name, desc = _read_skill_md(entry / "SKILL.md")
        if name:
            out.append((name, entry / "SKILL.md", None, desc))
    return out


def get_enabled_skill_names(*, instance_dir: Path) -> set[str]:
    """实例的技能白名单 —— NanoGhost 侧 `SkillRegistry._enabled_only()` 读的同一把钥匙。

    注意这跟 Hermes 那套（`disabled` 黑名单）**不是一回事**，别互相套用：
        Hermes     读 `skills.disabled`，默认只读不写、缺省=全开
        NanoGhost  读 `skills.enabled_only`，**缺省/空 = 全禁**（和 mcp.enabled_only 同语义）
    两边键名不同、极性相反。以前这里的 nanoghost 分支错用了 `disabled`，于是控制台
    面板里每个技能都显示勾选着，而 agent 实际一个都看不见 —— 写入的键根本没人读。
    """
    return _normalize_string_set(_load_skills_config(instance_dir).get("enabled_only"))


def list_skills_nanoghost(
    instance_dir: Path,
    platform: str | None = None,
    shared_dir: Path | None = None,
) -> list[SkillItem]:
    """列出实例可扫到的技能，`enabled` 按 NanoGhost 的白名单口径算。

    白名单为空/缺失时全部为 False —— 这是如实反映，不是"坏了"：那个实例的 agent
    此刻确实一个技能都用不了。

    遍历用 `_nanoghost_entries`（照抄 NanoGhost），**不做平台过滤**（NanoGhost 不认
    `platforms:`）。`platform` 参数留着只是为了兼容调用方的签名，这里用不上。
    """
    shared_dir = shared_dir or Path(os.path.expanduser("~/.agents/skills"))
    enabled_only = get_enabled_skill_names(instance_dir=instance_dir)
    inst = instance_dir.resolve()
    items: list[SkillItem] = []
    seen_dirs: set[str] = set()   # NanoGhost 的 loaded_names：按目录名去重
    seen_names: set[str] = set()  # SkillRegistry 按 frontmatter name 去重，先到先得

    for skills_dir in _ordered_scan_dirs(instance_dir=instance_dir, shared_dir=shared_dir):
        source = "local" if _is_within(skills_dir, inst) else "external"
        for name, md_path, group, description in _nanoghost_entries(skills_dir, seen_dirs):
            if name in seen_names:
                continue
            seen_names.add(name)
            items.append(
                SkillItem(
                    name=name,
                    path=md_path,
                    enabled=name in enabled_only,
                    description=description,
                    category=group,
                    source=source,
                )
            )

    return items


def list_global_skills_runtime(
    shared_dir: Path,
    platform: str | None = None,
    *,
    apply_platform_filter: bool = True,
) -> list[dict]:
    """列出一个共享技能目录里的技能（全局注册表页的只读表格）。

    `apply_platform_filter` 由调用方按 runtime 传：

        hermes     True  —— 它真看 `platforms:`（`platform_disabled` 那套语义在这条路上）
        nanoghost  False —— NanoGhost 压根不拿 `platforms:` 做判断，只存进
                            `SkillDefinition.platforms` 供序列化

    不给这个开关的话，一个标了 `platforms:` 的技能会在面板里消失、agent 却照常加载 ——
    又一处"界面说没有、agent 说有"的静默分歧。顺带：这条分支走 `_nanoghost_entries`，
    所以连遍历深度和分组入口名也和 NanoGhost 一致，不另写一套。
    """
    if not apply_platform_filter:
        return [
            {"name": name, "path": str(md_path), "description": desc, "category": group}
            for name, md_path, group, desc in _nanoghost_entries(shared_dir, set())
        ]

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
    """把某个技能加进/移出实例白名单（`skills.enabled_only`）。

    只动这一个名字，白名单里其它名字原样保留 —— 面板里没显示出来的（比如按平台过滤
    掉的、放在 config.yaml 的 skills.dirs 里的）不能因为我们这一下被抹掉。

    写空列表等于"全禁"，和 MCP 的白名单一个语义。前端那套「勾选=启用」的复选框配
    这个键是对的：批量保存会把每个技能都发一遍，最后落盘的就是勾中的那些。
    """
    cfg_path = instance_dir / "config.yaml"
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
    if not isinstance(raw, dict):
        raw = {}

    skills_cfg = raw.get("skills", {}) if isinstance(raw.get("skills"), dict) else {}
    enabled_only = _normalize_string_set(skills_cfg.get("enabled_only"))

    skill_name = str(skill_name or "").strip()
    if not skill_name:
        raise ValueError("invalid skill name")

    if enabled:
        enabled_only.add(skill_name)
    else:
        enabled_only.discard(skill_name)

    skills_cfg["enabled_only"] = sorted(enabled_only)
    raw["skills"] = skills_cfg

    rendered = yaml.safe_dump(raw, sort_keys=False, allow_unicode=True)
    write_raw_yaml(cfg_path, rendered)
