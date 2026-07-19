from __future__ import annotations

import os
import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
import yaml

from server.envfile import parse_env_keys

_ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def hermes_config_path(*, hermes_root: Path) -> Path:
    return hermes_root / "config.yaml"


def read_hermes_config_raw(*, hermes_root: Path) -> str:
    p = hermes_config_path(hermes_root=hermes_root)
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8")


def _validate_yaml_mapping(raw: str) -> dict:
    data = yaml.safe_load(raw) if (raw or "").strip() else {}
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError("config must be a YAML mapping")
    return data


def write_hermes_config_raw(*, hermes_root: Path, raw: str) -> None:
    _validate_yaml_mapping(raw)
    p = hermes_config_path(hermes_root=hermes_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(raw.rstrip() + "\n", encoding="utf-8")
    tmp.replace(p)


def _load_env_map(*, hermes_root: Path) -> dict[str, str]:
    m: dict[str, str] = {k: str(v) for k, v in os.environ.items()}
    env_path = hermes_root / ".env"
    if env_path.exists():
        keys = parse_env_keys(env_path)
        for k, v in keys.items():
            vv = (v or "").strip()
            if not vv:
                continue
            if len(vv) >= 2 and vv[0] == vv[-1] and vv[0] in ('"', "'", "`"):
                vv = vv[1:-1].strip()
            m[k] = vv
    return m


def _interpolate_env_vars(s: str, env: dict[str, str]) -> str:
    def repl(match: re.Match) -> str:
        key = match.group(1)
        return env.get(key, "")

    return _ENV_VAR_PATTERN.sub(repl, s)


def _interpolate_obj(obj, env: dict[str, str]):
    if isinstance(obj, str):
        return _interpolate_env_vars(obj, env)
    if isinstance(obj, list):
        return [_interpolate_obj(x, env) for x in obj]
    if isinstance(obj, dict):
        return {k: _interpolate_obj(v, env) for k, v in obj.items()}
    return obj


def _mask_headers(headers: dict) -> dict:
    out: dict[str, str] = {}
    for k, v in headers.items():
        ks = str(k)
        vs = str(v)
        if ks.lower() in ("authorization", "x-api-key", "api-key", "token"):
            out[ks] = "***"
        else:
            out[ks] = vs if len(vs) <= 16 else (vs[:8] + "…" + vs[-4:])
    return out


@dataclass(frozen=True)
class HermesMcpProbeItem:
    server_id: str
    enabled: bool
    transport: str
    url: str | None
    ok: bool
    status_code: int | None
    error: str | None


def parse_mcp_servers(*, hermes_root: Path, raw: str) -> dict[str, dict]:
    cfg = _validate_yaml_mapping(raw)
    raw_servers = cfg.get("mcp_servers", {})
    if not isinstance(raw_servers, dict):
        raw_servers = {}

    env = _load_env_map(hermes_root=hermes_root)
    servers = {}
    for sid, scfg in raw_servers.items():
        if not isinstance(sid, str):
            continue
        if not isinstance(scfg, dict):
            continue
        servers[sid] = _interpolate_obj(scfg, env)
    return servers


def hermes_mcp_config_get(*, hermes_root: Path) -> dict:
    raw = read_hermes_config_raw(hermes_root=hermes_root)
    servers: list[dict] = []
    try:
        parsed = parse_mcp_servers(hermes_root=hermes_root, raw=raw)
        for sid, scfg in parsed.items():
            enabled = bool(scfg.get("enabled", True))
            url = scfg.get("url")
            transport = "http" if isinstance(url, str) and url.strip() else "stdio"
            item = {"id": sid, "enabled": enabled, "transport": transport}
            if isinstance(url, str) and url.strip():
                item["url"] = url
            if isinstance(scfg.get("headers"), dict):
                item["headers"] = _mask_headers(scfg["headers"])
            servers.append(item)
    except ValueError:
        servers = []

    return {"raw": raw, "servers": servers}


def _probe_http_url(*, url: str, headers: dict[str, str], timeout_seconds: float) -> tuple[bool, int | None, str | None]:
    t = max(0.2, float(timeout_seconds))
    timeout = httpx.Timeout(connect=t, read=t, write=t, pool=t)
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, trust_env=False) as client:
            with client.stream("GET", url, headers=headers) as r:
                code = int(r.status_code)
                return True, code, None
    except Exception as e:
        return False, None, str(e)


def probe_mcp_servers(*, hermes_root: Path, raw: str) -> list[HermesMcpProbeItem]:
    servers = parse_mcp_servers(hermes_root=hermes_root, raw=raw)
    out: list[HermesMcpProbeItem] = []
    for sid, scfg in servers.items():
        enabled = bool(scfg.get("enabled", True))
        url = scfg.get("url") if isinstance(scfg.get("url"), str) else None
        if url and url.strip():
            transport = "http"
            if not enabled:
                out.append(HermesMcpProbeItem(sid, enabled, transport, url, False, None, "disabled"))
                continue
            headers = scfg.get("headers") if isinstance(scfg.get("headers"), dict) else {}
            headers2 = {str(k): str(v) for k, v in headers.items()}
            connect_timeout = scfg.get("connect_timeout", scfg.get("timeout_seconds", 2))
            ok, code, err = _probe_http_url(url=url, headers=headers2, timeout_seconds=float(connect_timeout))
            out.append(HermesMcpProbeItem(sid, enabled, transport, url, ok, code, err))
            continue

        transport = "stdio"
        if not enabled:
            out.append(HermesMcpProbeItem(sid, enabled, transport, None, False, None, "disabled"))
            continue
        cmd = scfg.get("command")
        if isinstance(cmd, str) and cmd.strip():
            if Path(cmd).is_file() or shutil.which(cmd):
                out.append(HermesMcpProbeItem(sid, enabled, transport, None, True, None, None))
            else:
                out.append(HermesMcpProbeItem(sid, enabled, transport, None, False, None, "command not found"))
            continue

        out.append(HermesMcpProbeItem(sid, enabled, transport, None, False, None, "unknown transport"))

    return out


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")

