from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class PortAlloc:
    gateway_start: int = 19000
    gateway_end: int = 19999


@dataclass(frozen=True)
class AppConfig:
    hermes_root: str | None
    nanoghost_root: str | None
    openclaw_root: str | None
    shared_skills_root: str | None
    port_alloc: PortAlloc
    bind_host: str = "127.0.0.1"
    bind_port: int = 8088
    # NanoGhost 可执行文件的显式覆盖。见 resolve_nanoghost_program()：
    # 它同时决定"控制台启动哪个程序"和"升级覆盖哪个程序"，两者必须是同一个答案。
    nanoghost_program: str | None = None


_SERVER_JSON_NAME = "openobstrator.server.json"


def _locate_server_json(config_path: Path) -> Path | None:
    exe_dir = Path(sys.executable).parent if getattr(sys, 'frozen', False) else None
    candidates = [
        exe_dir / _SERVER_JSON_NAME if exe_dir else None,
        config_path.parent.parent / _SERVER_JSON_NAME,
        config_path.parent / _SERVER_JSON_NAME,
    ]
    for p in candidates:
        if p and p.exists():
            return p
    return None


def _load_server_json(config_path: Path) -> dict:
    path = _locate_server_json(config_path)
    if path:
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def load_app_config(config_path: Path) -> AppConfig:
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    if not isinstance(raw, dict):
        raw = {}

    pa_raw = raw.get("port_alloc", {}) if isinstance(raw.get("port_alloc"), dict) else {}
    port_alloc = PortAlloc(
        gateway_start=int(pa_raw.get("gateway_start", 19000)),
        gateway_end=int(pa_raw.get("gateway_end", 19999)),
    )

    hermes_root = raw.get("hermes_root")
    hermes_root = str(hermes_root) if hermes_root not in (None, "", "null") else None
    nanoghost_root = raw.get("nanoghost_root")
    nanoghost_root = str(nanoghost_root) if nanoghost_root not in (None, "", "null") else None
    openclaw_root = raw.get("openclaw_root")
    openclaw_root = str(openclaw_root) if openclaw_root not in (None, "", "null") else None
    shared_skills_root = raw.get("shared_skills_root")
    shared_skills_root = str(shared_skills_root) if shared_skills_root not in (None, "", "null") else None

    nanoghost_program = raw.get("nanoghost_program")
    nanoghost_program = str(nanoghost_program) if nanoghost_program not in (None, "", "null") else None

    sj = _load_server_json(config_path)
    bind_host = str(sj.get("host") or raw.get("bind_host") or "127.0.0.1")
    bind_port = int(sj.get("port") or raw.get("bind_port") or 8088)

    return AppConfig(
        hermes_root=hermes_root,
        nanoghost_root=nanoghost_root,
        openclaw_root=openclaw_root,
        shared_skills_root=shared_skills_root,
        port_alloc=port_alloc,
        bind_host=bind_host,
        bind_port=bind_port,
        nanoghost_program=nanoghost_program,
    )


def resolve_hermes_root(*, config_path: Path) -> Path:
    cfg = load_app_config(config_path)
    if cfg.hermes_root:
        return Path(cfg.hermes_root)

    env_home = os.environ.get("HERMES_HOME", "").strip()
    if env_home:
        env_path = Path(env_home)
        if env_path.parent.name == "profiles":
            return env_path.parent.parent
        return env_path

    return Path.home() / ".hermes"


def resolve_nanoghost_root(*, config_path: Path) -> Path:
    cfg = load_app_config(config_path)
    if cfg.nanoghost_root:
        return Path(cfg.nanoghost_root)
    return config_path.parent / "nanoghost"


def resolve_openclaw_root(*, config_path: Path) -> Path:
    cfg = load_app_config(config_path)
    if cfg.openclaw_root:
        return Path(cfg.openclaw_root)
    return config_path.parent / "openclaw"


def resolve_shared_skills_root(*, config_path: Path) -> Path:
    cfg = load_app_config(config_path)
    if cfg.shared_skills_root:
        expanded = os.path.expanduser(os.path.expandvars(cfg.shared_skills_root))
        return Path(expanded)
    return Path(os.path.expanduser("~/.agents/skills"))


# ---------------------------------------------------------------------------
# NanoGhost 可执行文件
# ---------------------------------------------------------------------------
#
# 这个解析器存在的唯一理由是**防止版本错位**：
#   "控制台启动哪个程序" 和 "升级覆盖哪个程序" 必须是同一个答案。
#
# 改造前这两件事是分开的 —— 启动路径硬编码猜 dist/NanoGhost/NanoGhost.exe，
# 而升级会打在安装目录。结果是"点完更新、重启后还是旧版本"且没有任何报错，
# 因为控制台压根没启动被更新的那个程序。这是最难查的一类故障。
#
# 来源标记（PROGRAM_SOURCE_*）会显示在界面上。"从哪找到的"是排查这类问题的
# 第一线索，所以它不是一个内部实现细节。

PROGRAM_SOURCE_CONFIG = "config"
PROGRAM_SOURCE_INSTALLED = "installed"
PROGRAM_SOURCE_SOURCE_DIST = "source-dist"
PROGRAM_SOURCE_NONE = ""


def _installed_nanoghost_program() -> Path | None:
    """安装版的默认落点。

    Inno Setup 在 PrivilegesRequired=lowest 下把 {autopf} 解析成
    %LOCALAPPDATA%\\Programs（scripts/installer.iss:21/25），所以 per-user
    安装落在这里。用户在全机器模式下装到 {commonpf} 的话这里找不到 ——
    那种情况靠 nanoghost_program 显式配置覆盖。
    """
    local = (os.environ.get("LOCALAPPDATA") or "").strip()
    if not local:
        return None
    p = Path(local) / "Programs" / "NanoGhost" / "NanoGhost.exe"
    return p if p.is_file() else None


def locate_nanoghost_program(*, config_path: Path, repo_dir: Path | None = None) -> tuple[Path | None, str]:
    """定位 NanoGhost 程序，返回 (路径, 来源)。

    优先级：
      1. 配置 nanoghost_program（显式覆盖，可含 %VAR% / ~）
      2. %LOCALAPPDATA%\\Programs\\NanoGhost\\NanoGhost.exe（安装版）
      3. <repo_dir>/dist/NanoGhost/NanoGhost.exe（源码态；repo_dir 由调用方传入，
         因为"源码仓库在哪"的逻辑在 app.py 的 _nanoghost_repo_dir() 里）

    (None, PROGRAM_SOURCE_NONE) 表示**本机没有找到 NanoGhost**。这是一个合法
    状态而非错误 —— 上层据此把"升级"降级成"安装"。返回 None 而不是抛异常，
    是为了让这条分支能被直接单测覆盖。

    例外：显式配置了 nanoghost_program 却指不到文件时抛 FileNotFoundError。
    这时**不能**静默退回下一级 —— 用户改了配置却看到行为没变，会以为配置生效了，
    比直接报错难查得多。
    """
    cfg = load_app_config(config_path)
    if cfg.nanoghost_program:
        expanded = os.path.expanduser(os.path.expandvars(cfg.nanoghost_program))
        p = Path(expanded)
        if p.is_file():
            return p, PROGRAM_SOURCE_CONFIG
        raise FileNotFoundError(f"nanoghost_program 指向的文件不存在: {p}")

    installed = _installed_nanoghost_program()
    if installed is not None:
        return installed, PROGRAM_SOURCE_INSTALLED

    if repo_dir is not None:
        p = Path(repo_dir) / "dist" / "NanoGhost" / "NanoGhost.exe"
        if p.is_file():
            return p, PROGRAM_SOURCE_SOURCE_DIST

    return None, PROGRAM_SOURCE_NONE


def resolve_nanoghost_program(*, config_path: Path, repo_dir: Path | None = None) -> Path | None:
    """只取路径的简写形式。需要给界面显示来源时用 locate_nanoghost_program()。"""
    return locate_nanoghost_program(config_path=config_path, repo_dir=repo_dir)[0]
