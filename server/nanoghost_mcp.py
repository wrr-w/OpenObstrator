from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

import httpx
import yaml

_ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def nanoghost_global_config_path() -> Path:
    p = (os.getenv("NANOGHOST_GLOBAL_CONFIG") or "").strip()
    if p:
        return Path(p).expanduser().resolve()
    return Path.home() / ".nanoghost" / "config.yaml"


def read_nanoghost_global_config_raw() -> str:
    p = nanoghost_global_config_path()
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


def _is_jsonish(obj) -> bool:
    if obj is None:
        return True
    if isinstance(obj, (str, int, float, bool)):
        return True
    if isinstance(obj, list):
        return all(_is_jsonish(x) for x in obj)
    if isinstance(obj, dict):
        return all(isinstance(k, (str, int, float, bool)) and _is_jsonish(v) for k, v in obj.items())
    return False


def write_nanoghost_global_config_raw(raw: str) -> None:
    data = _validate_yaml_mapping(raw)
    if not _is_jsonish(data):
        raise ValueError("config contains unsupported YAML types")
    p = nanoghost_global_config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(raw.rstrip() + "\n", encoding="utf-8")
    tmp.replace(p)


def _load_env_map() -> dict[str, str]:
    return {k: str(v) for k, v in os.environ.items()}


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
            vv = vs.strip()
            if vv.lower().startswith("bearer "):
                out[ks] = "Bearer ***"
            else:
                out[ks] = "***"
        else:
            out[ks] = vs if len(vs) <= 16 else (vs[:8] + "…" + vs[-4:])
    return out


def parse_global_mcp_servers(raw: str) -> dict[str, dict]:
    cfg = _validate_yaml_mapping(raw)
    raw_servers = cfg.get("mcp_servers", {})
    if not isinstance(raw_servers, dict):
        raw_servers = {}
    env = _load_env_map()
    servers: dict[str, dict] = {}
    for sid, scfg in raw_servers.items():
        if not isinstance(sid, str):
            continue
        if not isinstance(scfg, dict):
            continue
        servers[sid] = _interpolate_obj(scfg, env)
    return servers


def nanoghost_mcp_config_get() -> dict:
    raw = read_nanoghost_global_config_raw()
    servers: list[dict] = []
    try:
        parsed = parse_global_mcp_servers(raw)
        for sid, scfg in parsed.items():
            enabled = bool(scfg.get("enabled", True))
            transport = str(scfg.get("transport") or "http_sse").strip() or "http_sse"
            url = scfg.get("url")
            item: dict = {
                "id": sid,
                "enabled": enabled,
                "transport": transport,
            }
            if isinstance(url, str) and url.strip():
                item["url"] = url.strip()
            if isinstance(scfg.get("headers"), dict):
                item["headers"] = _mask_headers(scfg["headers"])
            item["timeout_seconds"] = int(scfg.get("timeout_seconds") or 30)
            servers.append(item)
    except ValueError:
        servers = []

    return {"raw": raw, "servers": servers}


def _ensure_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return ""
    if not u.endswith("/"):
        u += "/"
    return u


def _sse_url(base_url: str) -> str:
    return urljoin(_ensure_url(base_url), "sse")


def _messages_url(base_url: str) -> str:
    return urljoin(_ensure_url(base_url), "messages")


def _probe_http_sse(*, url: str, headers: dict[str, str], timeout_seconds: float) -> tuple[bool, str, str | None, int]:
    t0 = time.time()
    t = max(0.2, float(timeout_seconds))
    timeout = httpx.Timeout(connect=min(5.0, t), read=t, write=t, pool=min(5.0, t))
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            with client.stream("GET", _sse_url(url), headers={**headers, "Accept": "text/event-stream"}) as r:
                if int(r.status_code) < 200 or int(r.status_code) >= 400:
                    dur = int((time.time() - t0) * 1000)
                    return False, "bad_status", f"status {int(r.status_code)}", dur
                dur = int((time.time() - t0) * 1000)
                return True, "connected", None, dur
    except Exception as e:
        dur = int((time.time() - t0) * 1000)
        return False, "unreachable", str(e), dur


def probe_http_sse(*, url: str, headers: dict[str, str], timeout_seconds: float) -> tuple[bool, str, str | None, int]:
    return _probe_http_sse(url=url, headers=headers, timeout_seconds=timeout_seconds)


def _discover_message_url(*, base_url: str, headers: dict[str, str], timeout_seconds: float) -> tuple[bool, str | None, str | None]:
    t = max(0.2, float(timeout_seconds))
    timeout = httpx.Timeout(connect=min(5.0, t), read=t, write=t, pool=min(5.0, t))
    data_lines: list[str] = []
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            with client.stream("GET", _sse_url(base_url), headers={**headers, "Accept": "text/event-stream"}) as r:
                if int(r.status_code) < 200 or int(r.status_code) >= 400:
                    return False, None, f"status {int(r.status_code)}"
                start = time.time()
                for raw in r.iter_lines():
                    if raw is None:
                        continue
                    line = raw.strip()
                    if line.startswith("data:"):
                        data_lines.append(line[5:].strip())
                        continue
                    if line == "":
                        if not data_lines:
                            continue
                        data_str = "\n".join(data_lines).strip()
                        data_lines.clear()
                        try:
                            payload = json_loads_safe(data_str)
                        except Exception:
                            payload = None
                        if isinstance(payload, dict) and isinstance(payload.get("endpoint"), str):
                            endpoint = payload["endpoint"].strip()
                            if endpoint:
                                return True, urljoin(_ensure_url(base_url), endpoint.lstrip("/")), None
                    if time.time() - start > max(1.0, t):
                        break
    except Exception as e:
        return False, None, str(e)
    return True, _messages_url(base_url), None


def json_loads_safe(s: str):
    import json

    return json.loads(s)


def _post_jsonrpc(
    *,
    message_url: str,
    headers: dict[str, str],
    method: str,
    params: dict,
    timeout_seconds: float,
) -> tuple[bool, object, str | None, int]:
    import uuid

    t0 = time.time()
    t = max(0.2, float(timeout_seconds))
    timeout = httpx.Timeout(connect=min(5.0, t), read=t, write=t, pool=min(5.0, t))
    payload = {"jsonrpc": "2.0", "id": uuid.uuid4().hex, "method": method, "params": params or {}}
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            r = client.post(message_url, headers={**headers, "Content-Type": "application/json"}, json=payload)
            data = r.json() if (r.text or "").strip() else {}
    except Exception as e:
        return False, None, str(e), int((time.time() - t0) * 1000)
    if isinstance(data, dict) and data.get("error"):
        err_obj = data.get("error")
        if isinstance(err_obj, dict):
            msg = err_obj.get("message") or str(err_obj)
        else:
            msg = str(err_obj)
        return False, data, msg, int((time.time() - t0) * 1000)
    if not isinstance(data, dict):
        return False, data, "invalid response", int((time.time() - t0) * 1000)
    return True, data.get("result"), None, int((time.time() - t0) * 1000)


def list_tools_http_sse(*, url: str, headers: dict[str, str], timeout_seconds: float) -> tuple[bool, object, str | None, int]:
    ok, msg_url, err = _discover_message_url(base_url=url, headers=headers, timeout_seconds=timeout_seconds)
    if not ok or not msg_url:
        return False, None, err or "discover failed", 0
    return _post_jsonrpc(
        message_url=msg_url,
        headers=headers,
        method="tools/list",
        params={},
        timeout_seconds=timeout_seconds,
    )


@dataclass(frozen=True)
class NanoGhostMcpProbeItem:
    server_id: str
    enabled: bool
    transport: str
    url: str | None
    ok: bool
    status: str
    error: str | None
    duration_ms: int


def probe_global_mcp_servers(raw: str) -> list[NanoGhostMcpProbeItem]:
    servers = parse_global_mcp_servers(raw)
    out: list[NanoGhostMcpProbeItem] = []
    for sid, scfg in servers.items():
        enabled = bool(scfg.get("enabled", True))
        transport = str(scfg.get("transport") or "http_sse").strip() or "http_sse"
        url = scfg.get("url") if isinstance(scfg.get("url"), str) else None
        if not enabled:
            out.append(NanoGhostMcpProbeItem(sid, enabled, transport, url, False, "disabled", "disabled", 0))
            continue
        if transport != "http_sse":
            out.append(NanoGhostMcpProbeItem(sid, enabled, transport, url, False, "unsupported", "unsupported transport", 0))
            continue
        if not url or not url.strip():
            out.append(NanoGhostMcpProbeItem(sid, enabled, transport, None, False, "invalid", "missing url", 0))
            continue
        headers = scfg.get("headers") if isinstance(scfg.get("headers"), dict) else {}
        headers2 = {str(k): str(v) for k, v in headers.items()}
        t = float(scfg.get("timeout_seconds") or 30)
        ok, status, err, dur = _probe_http_sse(url=url, headers=headers2, timeout_seconds=t)
        out.append(NanoGhostMcpProbeItem(sid, enabled, transport, url, ok, status, err, int(dur or 0)))
    return out


def read_instance_enabled_only(*, instance_dir: Path) -> list[str]:
    cfg_path = instance_dir / "config.yaml"
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
    if not isinstance(raw, dict):
        raw = {}
    mcp = raw.get("mcp") if isinstance(raw.get("mcp"), dict) else {}
    enabled_only = mcp.get("enabled_only") if isinstance(mcp.get("enabled_only"), list) else []
    out = [str(x).strip() for x in enabled_only if str(x).strip()]
    return out


def write_instance_enabled_only(*, instance_dir: Path, enabled_only: list[str]) -> None:
    cfg_path = instance_dir / "config.yaml"
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
    if not isinstance(raw, dict):
        raw = {}
    mcp = raw.get("mcp") if isinstance(raw.get("mcp"), dict) else {}
    mcp["enabled_only"] = sorted({str(x).strip() for x in enabled_only if str(x).strip()})
    raw["mcp"] = mcp
    rendered = yaml.safe_dump(raw, sort_keys=False, allow_unicode=True)
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = cfg_path.with_suffix(cfg_path.suffix + ".tmp")
    tmp.write_text(rendered, encoding="utf-8")
    tmp.replace(cfg_path)
