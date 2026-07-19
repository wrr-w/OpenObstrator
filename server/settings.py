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
