from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from server.configfile import read_raw_yaml, write_raw_yaml
from server.envfile import delete_env_key, parse_env_keys, set_env_kv
from server.hermes_mcp import hermes_config_path
from server.hermes_mcp import hermes_mcp_config_get as hermes_mcp_config_summary
from server.hermes_mcp import probe_mcp_servers
from server.hermes_mcp import read_hermes_config_raw
from server.hermes_mcp import write_hermes_config_raw
from server.nanoghost_mcp import list_tools_http_sse
from server.nanoghost_mcp import nanoghost_mcp_config_get as nanoghost_mcp_config_summary
from server.nanoghost_mcp import nanoghost_global_config_path
from server.nanoghost_mcp import parse_global_mcp_servers
from server.nanoghost_mcp import probe_http_sse
from server.nanoghost_mcp import read_instance_enabled_only
from server.nanoghost_mcp import read_nanoghost_global_config_raw
from server.nanoghost_mcp import write_instance_enabled_only
from server.nanoghost_mcp import write_nanoghost_global_config_raw
from server.logbuffer import get_log_lines, install_log_buffer
from server.ports import allocate_port, is_port_open
from server.profiles import list_profiles
from server.profile_create import create_profile_clone_default
from server.processes import is_pid_running, kill_pid_tree, spawn, spawn_logged, spawn_with
from server.registry import load_registry, save_registry
from server.soulfile import read_raw_text, write_raw_text
from server.skills import list_global_skills_runtime
from server.skills import list_skills, list_skills_nanoghost, set_skill_enabled, set_skill_enabled_nanoghost
from server.settings import load_app_config
from server.settings import resolve_hermes_root
from server.settings import resolve_nanoghost_root
from server.settings import resolve_openclaw_root
from server.settings import resolve_shared_skills_root
from server.template_copy import clone_template_dir

APP_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = APP_ROOT / "data"
CONFIG_PATH = DATA_DIR / "config.yaml"
REGISTRY_PATH = DATA_DIR / "registry.json"

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"

SERVICE_HOST = "127.0.0.1"

app = FastAPI()
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
install_log_buffer()

logger = logging.getLogger(__name__)

class EnvPutBody(BaseModel):
    key: str
    value: str


class EnvBatchPutBody(BaseModel):
    items: dict[str, str]


class EnvDeleteBody(BaseModel):
    key: str


class ConfigRawPutBody(BaseModel):
    raw: str


class NanoGhostMcpAllowlistPutBody(BaseModel):
    enabled_only: list[str]


class ChannelConfigPutBody(BaseModel):
    config: dict


class SkillTogglePutBody(BaseModel):
    name: str
    enabled: bool


class SkillBatchPutBody(BaseModel):
    items: dict[str, bool]


class SoulRawPutBody(BaseModel):
    raw: str


class MemoryRawPutBody(BaseModel):
    raw: str


class ProfileCreateBody(BaseModel):
    name: str


class RuntimeInstanceCreateBody(BaseModel):
    name: str
    template_id: str | None = None


class InstanceCreateBody(BaseModel):
    runtime: str
    name: str
    template_id: str | None = None


class ExportTemplateBody(BaseModel):
    template_name: str
    overwrite: bool = False


class InstanceRenameBody(BaseModel):
    new_name: str


_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/manager/logs")
def manager_logs_get(limit: int = 500):
    lines = get_log_lines(limit=limit)
    return {"ok": True, "items": lines}


@app.get("/", response_class=HTMLResponse)
def page_index(request: Request, profile: str = "default", runtime: str = "hermes"):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "initial_profile": profile, "initial_runtime": runtime},
    )


@app.get("/profiles/{name}", response_class=HTMLResponse)
def page_profile(request: Request, name: str):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "initial_profile": name, "initial_runtime": "hermes"},
    )


@app.get("/pages/templates", response_class=HTMLResponse)
def page_templates(request: Request):
    return templates.TemplateResponse("pages/templates.html", {"request": request})


@app.get("/pages/logs", response_class=HTMLResponse)
def page_logs(request: Request):
    return templates.TemplateResponse("pages/logs.html", {"request": request})


@app.get("/pages/global-registry", response_class=HTMLResponse)
def page_global_registry(request: Request):
    return templates.TemplateResponse("pages/global_registry.html", {"request": request})


@app.get("/api/profiles")
def api_profiles():
    hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
    profiles = list_profiles(hermes_root)
    return {
        "hermes_root": str(hermes_root),
        "profiles": [{"name": p.name, "path": str(p.path), "is_default": p.is_default} for p in profiles],
    }


@app.post("/api/profiles")
def api_profile_create(body: ProfileCreateBody):
    hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
    if not hermes_root.exists():
        raise HTTPException(status_code=400, detail="hermes_root does not exist")
    try:
        path = create_profile_clone_default(hermes_root=hermes_root, name=body.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except OSError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return {"ok": True, "name": body.name, "path": str(path)}


@app.delete("/api/profiles/{name}")
def api_profile_delete(name: str):
    hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
    profile_dir = hermes_root / "profiles" / name
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail="profile not found")
    import shutil
    shutil.rmtree(profile_dir)
    reg = load_registry(REGISTRY_PATH)
    reg.get("profiles", {}).pop(name, None)
    save_registry(REGISTRY_PATH, reg)
    return {"ok": True}


@app.get("/api/profiles/{name}/env")
def env_get(name: str):
    hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
    profile_dir = hermes_root / "profiles" / name
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail="profile not found")

    env_path = profile_dir / ".env"
    keys = parse_env_keys(env_path)
    return {
        "ok": True,
        "path": str(env_path),
        "items": [
            {"key": k, "is_set": v != "", "value": v} for k, v in keys.items()
        ],
    }


@app.put("/api/profiles/{name}/env")
def env_put(name: str, body: EnvPutBody):
    hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
    profile_dir = hermes_root / "profiles" / name
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail="profile not found")

    env_path = profile_dir / ".env"
    set_env_kv(env_path, body.key, body.value)
    return {"ok": True}


@app.put("/api/profiles/{name}/env/batch")
def env_batch_put(name: str, body: EnvBatchPutBody):
    hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
    profile_dir = hermes_root / "profiles" / name
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail="profile not found")

    env_path = profile_dir / ".env"
    for k, v in body.items.items():
        set_env_kv(env_path, k, v)
    return {"ok": True}


@app.delete("/api/profiles/{name}/env")
def env_delete(name: str, body: EnvDeleteBody):
    hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
    profile_dir = hermes_root / "profiles" / name
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail="profile not found")

    env_path = profile_dir / ".env"
    delete_env_key(env_path, body.key)
    return {"ok": True}


@app.get("/api/profiles/{name}/config/raw")
def config_raw_get(name: str):
    hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
    profile_dir = hermes_root / "profiles" / name
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail="profile not found")

    cfg_path = profile_dir / "config.yaml"
    return {"ok": True, "path": str(cfg_path), "raw": read_raw_yaml(cfg_path)}


@app.put("/api/profiles/{name}/config/raw")
def config_raw_put(name: str, body: ConfigRawPutBody):
    hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
    profile_dir = hermes_root / "profiles" / name
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail="profile not found")

    cfg_path = profile_dir / "config.yaml"
    try:
        write_raw_yaml(cfg_path, body.raw)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return {"ok": True}


@app.get("/api/profiles/{name}/soul/raw")
def soul_raw_get(name: str):
    hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
    profile_dir = hermes_root / "profiles" / name
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail="profile not found")

    soul_path = profile_dir / "SOUL.md"
    return {
        "ok": True,
        "path": str(soul_path),
        "exists": soul_path.exists(),
        "raw": read_raw_text(soul_path),
    }


@app.put("/api/profiles/{name}/soul/raw")
def soul_raw_put(name: str, body: SoulRawPutBody):
    hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
    profile_dir = hermes_root / "profiles" / name
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail="profile not found")

    soul_path = profile_dir / "SOUL.md"
    write_raw_text(soul_path, body.raw)
    return {"ok": True}


@app.get("/api/profiles/{name}/memories/user/raw")
def memories_user_raw_get(name: str):
    hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
    profile_dir = hermes_root / "profiles" / name
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail="profile not found")

    mem_path = profile_dir / "memories" / "USER.md"
    return {
        "ok": True,
        "path": str(mem_path),
        "exists": mem_path.exists(),
        "raw": read_raw_text(mem_path),
    }


@app.put("/api/profiles/{name}/memories/user/raw")
def memories_user_raw_put(name: str, body: MemoryRawPutBody):
    hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
    profile_dir = hermes_root / "profiles" / name
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail="profile not found")

    mem_path = profile_dir / "memories" / "USER.md"
    write_raw_text(mem_path, body.raw)
    return {"ok": True}


@app.get("/api/profiles/{name}/memories/memory/raw")
def memories_memory_raw_get(name: str):
    hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
    profile_dir = hermes_root / "profiles" / name
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail="profile not found")

    mem_path = profile_dir / "memories" / "MEMORY.md"
    return {
        "ok": True,
        "path": str(mem_path),
        "exists": mem_path.exists(),
        "raw": read_raw_text(mem_path),
    }


@app.put("/api/profiles/{name}/memories/memory/raw")
def memories_memory_raw_put(name: str, body: MemoryRawPutBody):
    hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
    profile_dir = hermes_root / "profiles" / name
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail="profile not found")

    mem_path = profile_dir / "memories" / "MEMORY.md"
    write_raw_text(mem_path, body.raw)
    return {"ok": True}


@app.get("/api/profiles/{name}/skills")
def skills_get(name: str, platform: str | None = None):
    hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
    profile_dir = hermes_root / "profiles" / name
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail="profile not found")

    items = list_skills(profile_dir, platform=platform)
    return {
        "ok": True,
        "toggle_rewrites_config_yaml": True,
        "items": [
            {
                "name": i.name,
                "path": str(i.path),
                "enabled": i.enabled,
                "description": i.description,
                "category": i.category,
                "source": i.source,
            }
            for i in items
        ],
    }


@app.put("/api/profiles/{name}/skills/toggle")
def skills_toggle(name: str, body: SkillTogglePutBody):
    hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
    profile_dir = hermes_root / "profiles" / name
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail="profile not found")

    set_skill_enabled(profile_dir, body.name, body.enabled)
    return {"ok": True, "name": body.name, "enabled": body.enabled}


@app.put("/api/profiles/{name}/skills/batch")
def skills_batch_put(name: str, body: SkillBatchPutBody):
    hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
    profile_dir = hermes_root / "profiles" / name
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail="profile not found")

    for skill_name, enabled in body.items.items():
        set_skill_enabled(profile_dir, skill_name, enabled)
    return {"ok": True}


def _proc_record(reg: dict, runtime: str, instance_name: str, proc_name: str) -> dict:
    rts = reg.setdefault("runtimes", {})
    rt = rts.setdefault(runtime, {})
    inst = rt.setdefault("instances", {})
    imap = inst.setdefault(instance_name, {})
    rec = imap.setdefault(proc_name, {"port": None, "pid": None, "started_at": None})
    if not isinstance(rec, dict):
        rec = {"port": None, "pid": None, "started_at": None}
        imap[proc_name] = rec
    return rec


def _collect_used_ports(reg: dict) -> set[int]:
    used: set[int] = set()
    runtimes = reg.get("runtimes") if isinstance(reg.get("runtimes"), dict) else {}
    if not isinstance(runtimes, dict):
        runtimes = {}
    for rt in runtimes.values():
        if not isinstance(rt, dict):
            continue
        instances = rt.get("instances")
        if not isinstance(instances, dict):
            continue
        for p in instances.values():
            if not isinstance(p, dict):
                continue
            for v in p.values():
                if not isinstance(v, dict):
                    continue
                port = v.get("port")
                if port not in (None, "", 0):
                    used.add(int(port))
    return used


def _status_for_record(rec: dict) -> dict:
    port = rec.get("port")
    pid = rec.get("pid")
    pid_running = bool(pid) and is_pid_running(int(pid))
    port_open = bool(port) and is_port_open(SERVICE_HOST, int(port))
    return {
        "port": int(port) if port not in (None, "", 0) else None,
        "pid": int(pid) if pid not in (None, "", 0) else None,
        "started_at": rec.get("started_at"),
        "pid_running": pid_running,
        "port_open": port_open,
        "running": pid_running or port_open,
    }


def _hermes_bin_dir() -> str | None:
    """Locate the directory containing ``hermes.exe`` / ``hermes``."""
    from shutil import which
    exe = which("hermes")
    if exe:
        return str(Path(exe).resolve().parent)
    return None


@app.post("/api/profiles/{name}/gateway/start")
def gateway_start(name: str):
    cfg = load_app_config(CONFIG_PATH)
    reg = load_registry(REGISTRY_PATH)
    gw = _proc_record(reg, "hermes", name, "gateway")

    if gw.get("pid") and is_pid_running(int(gw["pid"])):
        logger.info("hermes gateway %s already running (pid %s)", name, gw["pid"])
        return {"ok": True, **_status_for_record(gw)}

    used = _collect_used_ports(reg)
    if not gw.get("port"):
        gw["port"] = allocate_port(
            SERVICE_HOST,
            cfg.port_alloc.gateway_start,
            cfg.port_alloc.gateway_end,
            used=used,
        )

    hermes_bin = _hermes_bin_dir()
    if hermes_bin:
        os.environ["PATH"] = hermes_bin + os.pathsep + os.environ.get("PATH", "")

    # Check if already running via hermes CLI
    r = subprocess.run(["hermes", "-p", name, "gateway", "status"], capture_output=True, text=True, errors="replace")
    if "Gateway is running" in (r.stdout or ""):
        logger.info("hermes gateway %s already running (cli status)", name)
        for token in (r.stdout or "").split():
            m = re.search(r"(\d+)", token)
            if m:
                gw["pid"] = int(m.group(1))
                gw["started_at"] = gw.get("started_at") or int(time.time())
                save_registry(REGISTRY_PATH, reg)
                return {"ok": True, "running": True, "pid": gw["pid"]}
        return {"ok": True, "running": True}

    argv = [
        "hermes",
        "-p",
        name,
        "gateway",
        "run",
    ]
    logger.info("starting hermes gateway %s port=%s argv=%s", name, gw["port"], " ".join(argv))
    sr = spawn_logged(argv, tag=f"hermes-gateway-{name}")
    logger.info("hermes gateway %s pid=%s", name, sr.pid)
    gw["pid"] = sr.pid
    gw["started_at"] = int(time.time())
    save_registry(REGISTRY_PATH, reg)
    return {"ok": True, **_status_for_record(gw), "argv": argv}


@app.post("/api/profiles/{name}/gateway/stop")
def gateway_stop(name: str):
    argv = ["hermes", "-p", name, "gateway", "stop"]
    logger.info("stopping hermes gateway %s argv=%s", name, " ".join(argv))
    r = subprocess.run(argv, capture_output=True, text=True, errors="replace")
    out = (r.stdout or "").strip() + (r.stderr or "").strip()
    logger.info("hermes gateway %s stop result: %s", name, out or "ok")
    reg = load_registry(REGISTRY_PATH)
    gw = _proc_record(reg, "hermes", name, "gateway")
    gw["pid"] = None
    gw["started_at"] = None
    save_registry(REGISTRY_PATH, reg)
    return {"ok": True}


@app.get("/api/profiles/{name}/gateway/status")
def gateway_status(name: str):
    r = subprocess.run(
        ["hermes", "-p", name, "gateway", "status"],
        capture_output=True, text=True, errors="replace",
    )
    cli_out = (r.stdout or "").strip() + (r.stderr or "").strip()
    reg = load_registry(REGISTRY_PATH)
    gw = _proc_record(reg, "hermes", name, "gateway")

    if "Gateway is running" in cli_out:
        for token in cli_out.split():
            m = re.search(r"(\d+)", token)
            if m:
                gw["pid"] = int(m.group(1))
                gw["started_at"] = gw.get("started_at") or int(time.time())
                save_registry(REGISTRY_PATH, reg)
                return {"ok": True, "running": True, "pid": gw["pid"]}
        save_registry(REGISTRY_PATH, reg)
        return {"ok": True, "running": True, "pid": gw.get("pid")}
    else:
        # CLI 未检测到运行中（可能因为前台 run 模式），回退到 PID/端口检测
        pid_running = bool(gw.get("pid")) and is_pid_running(int(gw["pid"]))
        port_open = bool(gw.get("port")) and is_port_open(SERVICE_HOST, int(gw["port"]))
        if pid_running or port_open:
            save_registry(REGISTRY_PATH, reg)
            return {"ok": True, "running": True, "pid": gw["pid"]}
        gw["pid"] = None
        gw["started_at"] = None

    save_registry(REGISTRY_PATH, reg)
    return {"ok": True, "running": False, "pid": None}


@app.get("/api/profiles/{name}/channels")
def channels_get(name: str):
    hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
    profile_dir = hermes_root / "profiles" / name
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail="profile not found")

    ch_path = profile_dir / "channel_directory.json"
    if not ch_path.exists():
        return {"ok": True, "path": str(ch_path), "updated_at": None, "platforms": {}}

    raw = ch_path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"invalid channel_directory.json: {e}")

    return {
        "ok": True,
        "path": str(ch_path),
        "updated_at": data.get("updated_at"),
        "platforms": data.get("platforms", {}),
    }


@app.get("/api/profiles/{name}/cron")
def cron_get(name: str):
    hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
    profile_dir = hermes_root / "profiles" / name
    cron_dir = profile_dir / "cron"
    items = []
    if cron_dir.exists():
        for f in sorted(cron_dir.iterdir()):
            if f.suffix == ".yaml" or f.suffix == ".yml":
                try:
                    raw = f.read_text(encoding="utf-8")
                    import yaml
                    data = yaml.safe_load(raw)
                except Exception:
                    data = None
                items.append({
                    "name": f.stem,
                    "path": str(f),
                    "raw": raw,
                    "parsed": data,
                })
    return {"ok": True, "items": items, "dir": str(cron_dir)}


@app.get("/api/profiles/{name}/logs")
def logs_get(name: str):
    hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
    profile_dir = hermes_root / "profiles" / name
    log_dir = profile_dir / "logs"
    files = []
    if log_dir.exists():
        for f in sorted(log_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)[:20]:
            if f.is_file() and f.suffix == ".log":
                try:
                    tail = f.read_text(encoding="utf-8", errors="replace").splitlines()[-100:]
                except Exception:
                    tail = ["(error reading file)"]
                files.append({
                    "name": f.name,
                    "path": str(f),
                    "size": f.stat().st_size,
                    "mtime": f.stat().st_mtime,
                    "tail": "\n".join(tail[-50:]),
                })
    return {"ok": True, "files": files, "dir": str(log_dir)}


@app.get("/api/profiles/{name}/sessions")
def sessions_get(name: str):
    hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
    profile_dir = hermes_root / "profiles" / name
    sessions_dir = profile_dir / "sessions"
    items = []
    if sessions_dir.exists():
        for f in sorted(sessions_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)[:50]:
            if f.suffix == ".json":
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                except Exception:
                    data = None
                items.append({
                    "name": f.stem,
                    "path": str(f),
                    "size": f.stat().st_size,
                    "mtime": f.stat().st_mtime,
                    "preview": data.get("title") or data.get("name") or f.stem if isinstance(data, dict) else f.stem,
                })
    return {"ok": True, "items": items, "dir": str(sessions_dir)}


def _nanoghost_repo_dir() -> Path:
    cand = APP_ROOT.parent / "NanoGhost"
    if cand.is_dir() and cand.joinpath("run.py").is_file():
        return cand
    raise HTTPException(status_code=500, detail="NanoGhost repo not found (expected sibling folder NanoGhost)")


def _nanoghost_run_py() -> Path:
    return _nanoghost_repo_dir() / "run.py"


def _nanoghost_python() -> str:
    """Resolve NanoGhost's own venv Python instead of sys.executable."""
    repo = _nanoghost_repo_dir()
    for venv_dir in ("venv", ".venv"):
        cand = repo / venv_dir / "Scripts" / "python.exe"
        if cand.is_file():
            return str(cand)
    import sys
    return sys.executable


def _nanoghost_instance_dir(name: str) -> Path:
    root = resolve_nanoghost_root(config_path=CONFIG_PATH)
    return root / "instances" / name


def _nanoghost_memory_md_path(name: str) -> Path:
    return _nanoghost_instance_dir(name) / "memory.md"


def _nanoghost_agent_db_path(name: str):
    inst = _nanoghost_instance_dir(name)
    for cand in (inst / "data" / "agent_data.db", inst / "data" / "agent.db"):
        if cand.exists():
            return cand
    return inst / "data" / "agent.db"


def _list_nanoghost_instances(root: Path) -> list[dict]:
    root = root / "instances"
    if not root.is_dir():
        return []
    out: list[dict] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith("."):
            continue
        out.append({"name": entry.name, "path": str(entry), "is_default": False})
    return out


def _require_valid_instance_name(name: str) -> None:
    if not _NAME_RE.match(name or ""):
        raise HTTPException(status_code=400, detail="invalid instance name")


def _normalize_runtime(runtime: str) -> str:
    rt = (runtime or "").strip().lower()
    if rt in ("hermes", "nanoghost", "openclaw"):
        return rt
    raise HTTPException(status_code=404, detail="runtime not found")


def _runtime_badge(runtime: str) -> dict:
    runtime = _normalize_runtime(runtime)
    if runtime == "hermes":
        return {"text": "HERMES", "color": "#38bdf8"}
    if runtime == "nanoghost":
        return {"text": "NANOGHOST", "color": "#a78bfa"}
    return {"text": "OPENCLAW", "color": "#fb923c"}


def _instance_path(runtime: str, name: str) -> Path:
    runtime = _normalize_runtime(runtime)
    if runtime == "hermes":
        hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
        return hermes_root / "profiles" / name
    if runtime == "nanoghost":
        return _nanoghost_instance_dir(name)
    raise HTTPException(status_code=400, detail="openclaw not implemented")


def _template_root(runtime: str) -> Path:
    runtime = _normalize_runtime(runtime)
    if runtime == "hermes":
        return resolve_hermes_root(config_path=CONFIG_PATH)
    if runtime == "nanoghost":
        return resolve_nanoghost_root(config_path=CONFIG_PATH)
    raise HTTPException(status_code=400, detail="openclaw not implemented")


def _require_template_root(runtime: str) -> Path:
    runtime = _normalize_runtime(runtime)
    if runtime == "openclaw":
        raise HTTPException(status_code=400, detail="openclaw not implemented")
    root = _template_root(runtime)
    if not root.exists():
        raise HTTPException(status_code=400, detail=f"{runtime}_root does not exist")
    if not root.is_dir():
        raise HTTPException(status_code=400, detail=f"{runtime}_root is not a directory")
    return root


def _template_dir(runtime: str, template_id: str | None) -> Path:
    runtime = _normalize_runtime(runtime)
    root = _require_template_root(runtime)
    tid = (template_id or "root").strip()
    if tid == "root":
        return root
    if tid.startswith("tpl:"):
        name = tid[4:]
        _require_valid_instance_name(name)
        path = root / "templates" / name
        if not path.exists():
            raise HTTPException(status_code=404, detail="template not found")
        if not path.is_dir():
            raise HTTPException(status_code=400, detail="template is not a directory")
        return path
    raise HTTPException(status_code=400, detail="invalid template_id")


@app.get("/api/templates/{runtime}/list")
def templates_list(runtime: str):
    runtime = _normalize_runtime(runtime)
    root = _require_template_root(runtime)
    items: list[dict] = [{"id": "root", "name": "root", "path": str(root)}]

    tpl_root = root / "templates"
    if tpl_root.is_dir():
        for entry in sorted(tpl_root.iterdir()):
            if not entry.is_dir():
                continue
            if entry.name.startswith("."):
                continue
            if not _NAME_RE.match(entry.name):
                continue
            items.append({"id": f"tpl:{entry.name}", "name": entry.name, "path": str(entry)})

    return {"ok": True, "runtime": runtime, "items": items}


@app.get("/api/templates/{runtime}/manifest")
def template_manifest(runtime: str, template_id: str | None = None):
    runtime = _normalize_runtime(runtime)
    root = _template_dir(runtime, template_id)

    tabs: list[str] = ["env", "skills"]
    if runtime == "hermes":
        tabs = ["env", "config", "skills", "channels"]
    elif runtime == "nanoghost":
        tabs = ["env", "memories", "skills", "channels", "config", "mcp"]

    return {
        "ok": True,
        "instance": {
            "runtime": runtime,
            "name": "__template__",
            "path": str(root),
            "badge": _runtime_badge(runtime),
        },
        "services": [],
        "tabs": tabs,
    }


@app.get("/api/templates/{runtime}/env")
def template_env_get(runtime: str, template_id: str | None = None):
    runtime = _normalize_runtime(runtime)
    root = _template_dir(runtime, template_id)
    env_path = root / ".env"
    keys = parse_env_keys(env_path)
    return {
        "ok": True,
        "path": str(env_path),
        "items": [{"key": k, "is_set": v != "", "value": v} for k, v in keys.items()],
    }


@app.put("/api/templates/{runtime}/env")
def template_env_put(runtime: str, body: EnvPutBody, template_id: str | None = None):
    runtime = _normalize_runtime(runtime)
    root = _template_dir(runtime, template_id)
    env_path = root / ".env"
    set_env_kv(env_path, body.key, body.value)
    return {"ok": True}


@app.put("/api/templates/{runtime}/env/batch")
def template_env_batch_put(runtime: str, body: EnvBatchPutBody, template_id: str | None = None):
    runtime = _normalize_runtime(runtime)
    root = _template_dir(runtime, template_id)
    env_path = root / ".env"
    for k, v in body.items.items():
        set_env_kv(env_path, k, v)
    return {"ok": True}


@app.delete("/api/templates/{runtime}/env")
def template_env_delete(runtime: str, body: EnvDeleteBody, template_id: str | None = None):
    runtime = _normalize_runtime(runtime)
    root = _template_dir(runtime, template_id)
    env_path = root / ".env"
    delete_env_key(env_path, body.key)
    return {"ok": True}


@app.get("/api/templates/{runtime}/skills")
def template_skills_get(runtime: str, platform: str | None = None, template_id: str | None = None):
    runtime = _normalize_runtime(runtime)
    root = _template_dir(runtime, template_id)
    if runtime == "hermes":
        items = list_skills(root, platform=platform)
    elif runtime == "nanoghost":
        shared_dir = resolve_shared_skills_root(config_path=CONFIG_PATH)
        items = list_skills_nanoghost(root, platform=platform, shared_dir=shared_dir)
    else:
        raise HTTPException(status_code=400, detail="openclaw not implemented")
    return {
        "ok": True,
        "items": [
            {
                "name": i.name,
                "path": str(i.path),
                "enabled": i.enabled,
                "description": i.description,
                "category": i.category,
                "source": i.source,
            }
            for i in items
        ],
    }


@app.put("/api/templates/{runtime}/skills/batch")
def template_skills_batch_put(runtime: str, body: SkillBatchPutBody, template_id: str | None = None):
    runtime = _normalize_runtime(runtime)
    root = _template_dir(runtime, template_id)
    if runtime == "hermes":
        for skill_name, enabled in body.items.items():
            set_skill_enabled(root, skill_name, enabled)
        return {"ok": True}
    if runtime == "nanoghost":
        for skill_name, enabled in body.items.items():
            try:
                set_skill_enabled_nanoghost(root, skill_name, enabled)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e)) from e
        return {"ok": True}
    raise HTTPException(status_code=400, detail="openclaw not implemented")


@app.get("/api/templates/{runtime}/channels")
def template_channels_get(runtime: str, template_id: str | None = None):
    runtime = _normalize_runtime(runtime)
    root = _template_dir(runtime, template_id)
    ch_path = root / "channel_directory.json"
    if runtime == "hermes":
        if not ch_path.exists():
            return {"ok": True, "path": str(ch_path), "updated_at": None, "platforms": {}}
        raw = ch_path.read_text(encoding="utf-8")
        try:
            data = json.loads(raw)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"invalid channel_directory.json: {e}")
        return {
            "ok": True,
            "path": str(ch_path),
            "updated_at": data.get("updated_at"),
            "platforms": data.get("platforms", {}),
        }
    if runtime == "nanoghost":
        if ch_path.exists():
            try:
                raw = json.loads(ch_path.read_text(encoding="utf-8"))
            except Exception:
                raw = {}
        else:
            raw = {}
        if not isinstance(raw, dict):
            raw = {}
        raw.setdefault("updated_at", None)
        channels = raw.get("channels")
        if not isinstance(channels, dict):
            channels = {}
            raw["channels"] = channels
        channels.setdefault("feishu", {"enabled": False})
        channels.setdefault("cli", {"enabled": True})
        return {"ok": True, "path": str(ch_path), "config": raw}
    raise HTTPException(status_code=400, detail="openclaw not implemented")


@app.put("/api/templates/{runtime}/channels")
def template_channels_put(runtime: str, body: ChannelConfigPutBody, template_id: str | None = None):
    runtime = _normalize_runtime(runtime)
    root = _template_dir(runtime, template_id)
    ch_path = root / "channel_directory.json"
    cfg = body.config if isinstance(body.config, dict) else {}
    if runtime == "hermes":
        cfg.setdefault("platforms", {})
        if not isinstance(cfg.get("platforms"), dict):
            cfg["platforms"] = {}
        cfg["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    elif runtime == "nanoghost":
        cfg.setdefault("channels", {})
        if not isinstance(cfg.get("channels"), dict):
            cfg["channels"] = {}
        cfg["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    else:
        raise HTTPException(status_code=400, detail="openclaw not implemented")
    ch_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = ch_path.with_suffix(ch_path.suffix + ".tmp")
    tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(ch_path)
    return {"ok": True}


@app.get("/api/templates/{runtime}/config/raw")
def template_config_raw_get(runtime: str, template_id: str | None = None):
    runtime = _normalize_runtime(runtime)
    root = _template_dir(runtime, template_id)
    cfg_path = root / "config.yaml"
    return {"ok": True, "path": str(cfg_path), "raw": read_raw_yaml(cfg_path)}


@app.put("/api/templates/{runtime}/config/raw")
def template_config_raw_put(runtime: str, body: ConfigRawPutBody, template_id: str | None = None):
    runtime = _normalize_runtime(runtime)
    root = _template_dir(runtime, template_id)
    cfg_path = root / "config.yaml"
    try:
        write_raw_yaml(cfg_path, body.raw)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True}


@app.get("/api/instances")
def instances_list():
    hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
    hermes_profiles = list_profiles(hermes_root)
    nano_root = resolve_nanoghost_root(config_path=CONFIG_PATH)
    nanos = _list_nanoghost_instances(nano_root)

    out: list[dict] = []
    for p in hermes_profiles:
        out.append(
            {
                "runtime": "hermes",
                "name": p.name,
                "path": str(p.path),
                "is_default": p.is_default,
                "badge": _runtime_badge("hermes"),
            }
        )
    for it in nanos:
        out.append(
            {
                "runtime": "nanoghost",
                "name": it["name"],
                "path": it["path"],
                "is_default": False,
                "badge": _runtime_badge("nanoghost"),
            }
        )
    return {"ok": True, "instances": out}


@app.get("/api/instances/{runtime}/{name}/manifest")
def instance_manifest(runtime: str, name: str):
    runtime = _normalize_runtime(runtime)
    name = (name or "").strip()

    if runtime == "openclaw":
        raise HTTPException(status_code=400, detail="openclaw not implemented")

    path = _instance_path(runtime, name)
    if not path.exists():
        raise HTTPException(status_code=404, detail="instance not found")

    services: list[dict] = []
    tabs: list[str] = ["env", "skills"]

    if runtime == "hermes":
        services = [
            {"key": "gateway", "title": "Gateway"},
        ]
        tabs = ["env", "config", "soul", "memories", "skills", "channels", "cron", "logs", "sessions"]
    elif runtime == "nanoghost":
        services = [{"key": "gateway", "title": "Gateway"}]
        tabs = ["env", "skills", "memories", "prompts", "mcp", "channels"]

    return {
        "ok": True,
        "instance": {
            "runtime": runtime,
            "name": name,
            "path": str(path),
            "badge": _runtime_badge(runtime),
        },
        "services": services,
        "tabs": tabs,
    }


@app.post("/api/instances")
def instance_create(body: InstanceCreateBody):
    runtime = _normalize_runtime(body.runtime)
    name = (body.name or "").strip()
    _require_valid_instance_name(name)
    if runtime == "openclaw":
        raise HTTPException(status_code=400, detail="openclaw not implemented")
    return runtime_instance_create(runtime, RuntimeInstanceCreateBody(name=name, template_id=body.template_id))


@app.delete("/api/instances/{runtime}/{name}")
def instance_delete(runtime: str, name: str):
    runtime = _normalize_runtime(runtime)
    if runtime == "openclaw":
        raise HTTPException(status_code=400, detail="openclaw not implemented")
    return runtime_instance_delete(runtime, name)


@app.post("/api/instances/{runtime}/{name}/export-template")
def instance_export_template(runtime: str, name: str, body: ExportTemplateBody):
    runtime = _normalize_runtime(runtime)
    if runtime == "openclaw":
        raise HTTPException(status_code=400, detail="openclaw not implemented")
    name = (name or "").strip()
    _require_valid_instance_name(name)

    inst = _instance_path(runtime, name)
    if not inst.exists():
        raise HTTPException(status_code=404, detail="instance not found")

    template_name = (body.template_name or "").strip()
    _require_valid_instance_name(template_name)

    root = _require_template_root(runtime)
    tpl_dir = root / "templates" / template_name

    if tpl_dir.exists():
        if not body.overwrite:
            raise HTTPException(status_code=409, detail="template already exists")
        import shutil
        if tpl_dir.is_dir():
            shutil.rmtree(tpl_dir)
        else:
            tpl_dir.unlink()

    exclude_names = {"profiles", "templates"} if runtime == "hermes" else {"instances", "templates"}
    try:
        clone_template_dir(template_dir=inst, dest_dir=tpl_dir, exclude_names=exclude_names)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except OSError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return {
        "ok": True,
        "template": {"id": f"tpl:{template_name}", "name": template_name, "path": str(tpl_dir)},
    }


@app.post("/api/instances/{runtime}/{name}/rename")
def instance_rename(runtime: str, name: str, body: InstanceRenameBody):
    runtime = _normalize_runtime(runtime)
    if runtime == "openclaw":
        raise HTTPException(status_code=400, detail="openclaw not implemented")

    old_name = (name or "").strip()
    _require_valid_instance_name(old_name)
    new_name = (body.new_name or "").strip()
    _require_valid_instance_name(new_name)

    old_dir = _instance_path(runtime, old_name)
    new_dir = _instance_path(runtime, new_name)

    if not old_dir.exists():
        raise HTTPException(status_code=404, detail="instance not found")
    if new_dir.exists():
        raise HTTPException(status_code=409, detail="instance already exists")

    reg = load_registry(REGISTRY_PATH)

    if runtime == "hermes":
        gw = _proc_record(reg, "hermes", old_name, "gateway")
        if gw.get("pid") and is_pid_running(int(gw["pid"])):
            raise HTTPException(status_code=409, detail="instance is running")
    elif runtime == "nanoghost":
        gw = _proc_record(reg, "nanoghost", old_name, "gateway")
        if gw.get("pid") and is_pid_running(int(gw["pid"])):
            raise HTTPException(status_code=409, detail="instance is running")

    try:
        old_dir.replace(new_dir)
    except OSError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    rts = reg.setdefault("runtimes", {})
    rt = rts.setdefault(runtime, {})
    recs = rt.setdefault("instances", {})
    if not isinstance(recs, dict):
        recs = {}
        rt["instances"] = recs
    recs[new_name] = recs.pop(old_name, {})
    save_registry(REGISTRY_PATH, reg)

    return {"ok": True, "runtime": runtime, "old_name": old_name, "new_name": new_name, "path": str(new_dir)}


@app.get("/api/instances/{runtime}/{name}/env")
def instance_env_get(runtime: str, name: str):
    runtime = _normalize_runtime(runtime)
    return runtime_env_get(runtime, name)


@app.put("/api/instances/{runtime}/{name}/env")
def instance_env_put(runtime: str, name: str, body: EnvPutBody):
    runtime = _normalize_runtime(runtime)
    return runtime_env_put(runtime, name, body)


@app.put("/api/instances/{runtime}/{name}/env/batch")
def instance_env_batch_put(runtime: str, name: str, body: EnvBatchPutBody):
    runtime = _normalize_runtime(runtime)
    return runtime_env_batch_put(runtime, name, body)


@app.delete("/api/instances/{runtime}/{name}/env")
def instance_env_delete(runtime: str, name: str, body: EnvDeleteBody):
    runtime = _normalize_runtime(runtime)
    return runtime_env_delete(runtime, name, body)


@app.get("/api/instances/{runtime}/{name}/skills")
def instance_skills_get(runtime: str, name: str, platform: str | None = None):
    runtime = _normalize_runtime(runtime)
    return runtime_skills_get(name=name, runtime=runtime, platform=platform)


@app.put("/api/instances/{runtime}/{name}/skills/batch")
def instance_skills_batch_put(runtime: str, name: str, body: SkillBatchPutBody):
    runtime = _normalize_runtime(runtime)
    return runtime_skills_batch_put(name=name, runtime=runtime, body=body)


@app.get("/api/instances/{runtime}/{name}/services/{service}/status")
def instance_service_status(runtime: str, name: str, service: str):
    runtime = _normalize_runtime(runtime)
    service = (service or "").strip().lower()
    if runtime == "hermes":
        return runtime_process_status(runtime, name, service)
    if runtime == "nanoghost":
        if service != "gateway":
            raise HTTPException(status_code=404, detail="service not found")
        reg = load_registry(REGISTRY_PATH)
        rec = _proc_record(reg, "nanoghost", name, "gateway")
        status = _status_for_record(rec)
        if status["pid"] and not status["pid_running"]:
            rec["pid"] = None
            rec["started_at"] = None
            save_registry(REGISTRY_PATH, reg)
            status = _status_for_record(rec)
        return {"ok": True, **status}
    raise HTTPException(status_code=404, detail="service not found")


@app.post("/api/instances/{runtime}/{name}/services/{service}/start")
def instance_service_start(runtime: str, name: str, service: str):
    runtime = _normalize_runtime(runtime)
    service = (service or "").strip().lower()
    if runtime == "hermes":
        return runtime_process_start(runtime, name, service)
    if runtime == "nanoghost":
        if service != "gateway":
            raise HTTPException(status_code=404, detail="service not found")
        inst = _nanoghost_instance_dir(name)
        if not inst.exists():
            raise HTTPException(status_code=404, detail="instance not found")
        cfg = load_app_config(CONFIG_PATH)
        reg = load_registry(REGISTRY_PATH)
        rec = _proc_record(reg, "nanoghost", name, "gateway")
        if rec.get("pid") and is_pid_running(int(rec["pid"])):
            logger.info("nanoghost gateway %s/%s already running (pid %s)", name, "gateway", rec["pid"])
            return {"ok": True, **_status_for_record(rec)}
        used = _collect_used_ports(reg)
        if not rec.get("port"):
            rec["port"] = allocate_port(
                SERVICE_HOST,
                cfg.port_alloc.gateway_start,
                cfg.port_alloc.gateway_end,
                used=used,
            )
        run_py = _nanoghost_run_py()
        env = dict(os.environ)
        env["INSTANCE_DIR"] = str(inst)
        env_path = inst / ".env"
        keys = parse_env_keys(env_path)
        for k, v in keys.items():
            vv = (v or "").strip()
            if not vv:
                continue
            if len(vv) >= 2 and vv[0] == vv[-1] and vv[0] in ('"', "'", "`"):
                vv = vv[1:-1].strip()
            env[k] = vv
        argv = [
            _nanoghost_python(),
            str(run_py),
            "--gateway",
            "-I",
            str(inst),
            "--host",
            SERVICE_HOST,
            "--port",
            str(int(rec["port"])),
        ]
        logger.info("starting nanoghost gateway %s/%s port=%s argv=%s", name, "gateway", rec["port"], " ".join(argv))
        sr = spawn_logged(argv, cwd=str(run_py.parent), env=env, tag=f"ng-gateway-{name}")
        logger.info("nanoghost gateway %s/%s pid=%s", name, "gateway", sr.pid)
        rec["pid"] = sr.pid
        rec["started_at"] = int(time.time())
        save_registry(REGISTRY_PATH, reg)
        return {"ok": True, **_status_for_record(rec), "argv": argv}
    raise HTTPException(status_code=404, detail="service not found")


@app.post("/api/instances/{runtime}/{name}/services/{service}/stop")
def instance_service_stop(runtime: str, name: str, service: str):
    runtime = _normalize_runtime(runtime)
    service = (service or "").strip().lower()
    if runtime == "hermes":
        return runtime_process_stop(runtime, name, service)
    if runtime == "nanoghost":
        if service != "gateway":
            raise HTTPException(status_code=404, detail="service not found")
        reg = load_registry(REGISTRY_PATH)
        rec = _proc_record(reg, "nanoghost", name, "gateway")
        pid = rec.get("pid")
        if not pid:
            return {"ok": False, "error": "no pid recorded"}
        kill_pid_tree(int(pid))
        rec["pid"] = None
        rec["started_at"] = None
        save_registry(REGISTRY_PATH, reg)
        return {"ok": True}
    raise HTTPException(status_code=404, detail="service not found")


@app.post("/api/instances/{runtime}/{name}/services/{service}/restart")
def instance_service_restart(runtime: str, name: str, service: str):
    runtime = _normalize_runtime(runtime)
    service = (service or "").strip().lower()
    if runtime == "hermes":
        if service == "gateway":
            gateway_stop(name)
            return gateway_start(name)
        raise HTTPException(status_code=404, detail="service not found")
    if runtime == "nanoghost":
        if service != "gateway":
            raise HTTPException(status_code=404, detail="service not found")
        instance_service_stop(runtime, name, service)
        return instance_service_start(runtime, name, service)
    raise HTTPException(status_code=404, detail="service not found")


@app.get("/api/instances/{runtime}/{name}/channels")
def instance_channels_get(runtime: str, name: str):
    runtime = _normalize_runtime(runtime)
    name = (name or "").strip()
    if runtime == "hermes":
        return channels_get(name)
    if runtime == "nanoghost":
        inst = _nanoghost_instance_dir(name)
        if not inst.exists():
            raise HTTPException(status_code=404, detail="instance not found")
        ch_path = inst / "channel_directory.json"
        if ch_path.exists():
            try:
                raw = json.loads(ch_path.read_text(encoding="utf-8"))
            except Exception:
                raw = {}
        else:
            raw = {}
        if not isinstance(raw, dict):
            raw = {}
        raw.setdefault("updated_at", None)
        channels = raw.get("channels")
        if not isinstance(channels, dict):
            channels = {}
            raw["channels"] = channels
        channels.setdefault("feishu", {"enabled": False})
        channels.setdefault("cli", {"enabled": True})
        return {"ok": True, "path": str(ch_path), "config": raw}
    raise HTTPException(status_code=400, detail="openclaw not implemented")


@app.put("/api/instances/{runtime}/{name}/channels")
def instance_channels_put(runtime: str, name: str, body: ChannelConfigPutBody):
    runtime = _normalize_runtime(runtime)
    name = (name or "").strip()
    if runtime != "nanoghost":
        raise HTTPException(status_code=404, detail="channels not supported")
    inst = _nanoghost_instance_dir(name)
    if not inst.exists():
        raise HTTPException(status_code=404, detail="instance not found")
    ch_path = inst / "channel_directory.json"
    cfg = body.config if isinstance(body.config, dict) else {}
    cfg.setdefault("channels", {})
    if not isinstance(cfg.get("channels"), dict):
        cfg["channels"] = {}
    cfg["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    ch_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = ch_path.with_suffix(ch_path.suffix + ".tmp")
    tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(ch_path)
    return {"ok": True}


@app.get("/api/instances/{runtime}/{name}/prompts")
def instance_prompts_list(runtime: str, name: str):
    runtime = _normalize_runtime(runtime)
    name = (name or "").strip()
    if runtime != "nanoghost":
        raise HTTPException(status_code=404, detail="not supported")
    inst = _nanoghost_instance_dir(name)
    if not inst.exists():
        raise HTTPException(status_code=404, detail="instance not found")
    prompts_dir = inst / "prompts"
    files = []
    if prompts_dir.is_dir():
        for f in sorted(prompts_dir.iterdir()):
            if f.is_file() and f.suffix == ".md":
                files.append({
                    "name": f.name,
                    "path": str(f),
                    "size": f.stat().st_size,
                    "mtime": f.stat().st_mtime,
                })
    return {"ok": True, "items": files, "dir": str(prompts_dir)}


@app.get("/api/instances/{runtime}/{name}/prompts/{filename:path}")
def instance_prompt_get(runtime: str, name: str, filename: str):
    runtime = _normalize_runtime(runtime)
    name = (name or "").strip()
    if runtime != "nanoghost":
        raise HTTPException(status_code=404, detail="not supported")
    inst = _nanoghost_instance_dir(name)
    if not inst.exists():
        raise HTTPException(status_code=404, detail="instance not found")
    file_path = (inst / "prompts" / filename).resolve()
    prompts_dir = (inst / "prompts").resolve()
    if not str(file_path).startswith(str(prompts_dir)):
        raise HTTPException(status_code=403, detail="path traversal denied")
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="prompt not found")
    return {"ok": True, "name": filename, "path": str(file_path), "raw": file_path.read_text(encoding="utf-8")}


class PromptPutBody(BaseModel):
    raw: str


@app.put("/api/instances/{runtime}/{name}/prompts/{filename:path}")
def instance_prompt_put(runtime: str, name: str, filename: str, body: PromptPutBody):
    runtime = _normalize_runtime(runtime)
    name = (name or "").strip()
    if runtime != "nanoghost":
        raise HTTPException(status_code=404, detail="not supported")
    inst = _nanoghost_instance_dir(name)
    if not inst.exists():
        raise HTTPException(status_code=404, detail="instance not found")
    file_path = (inst / "prompts" / filename).resolve()
    prompts_dir = (inst / "prompts").resolve()
    if not str(file_path).startswith(str(prompts_dir)):
        raise HTTPException(status_code=403, detail="path traversal denied")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(body.raw, encoding="utf-8")
    return {"ok": True}


@app.get("/api/manager/config/raw")
def manager_config_raw_get():
    return {"ok": True, "path": str(CONFIG_PATH), "raw": read_raw_yaml(CONFIG_PATH)}


@app.put("/api/manager/config/raw")
def manager_config_raw_put(body: ConfigRawPutBody):
    try:
        write_raw_yaml(CONFIG_PATH, body.raw)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True}


@app.get("/api/hermes/mcp/config/raw")
def hermes_mcp_config_raw_get():
    hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
    p = hermes_config_path(hermes_root=hermes_root)
    return {"ok": True, "path": str(p), "raw": read_hermes_config_raw(hermes_root=hermes_root)}


@app.put("/api/hermes/mcp/config/raw")
def hermes_mcp_config_raw_put(body: ConfigRawPutBody):
    hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
    try:
        write_hermes_config_raw(hermes_root=hermes_root, raw=body.raw)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True}


@app.get("/api/hermes/mcp/config")
def hermes_mcp_config_get():
    hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
    raw = read_hermes_config_raw(hermes_root=hermes_root)
    data = hermes_mcp_config_summary(hermes_root=hermes_root)
    return {"ok": True, "path": str(hermes_config_path(hermes_root=hermes_root)), "raw": raw, "servers": data["servers"]}


@app.get("/api/hermes/mcp/probe")
def hermes_mcp_probe():
    hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
    raw = read_hermes_config_raw(hermes_root=hermes_root)
    try:
        items = probe_mcp_servers(hermes_root=hermes_root, raw=raw)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {
        "ok": True,
        "items": [
            {
                "id": it.server_id,
                "enabled": it.enabled,
                "transport": it.transport,
                "url": it.url,
                "ok": it.ok,
                "status_code": it.status_code,
                "error": it.error,
            }
            for it in items
        ],
    }


@app.get("/api/nanoghost/mcp/config/raw")
def nanoghost_mcp_config_raw_get():
    p = nanoghost_global_config_path()
    return {"ok": True, "path": str(p), "raw": read_nanoghost_global_config_raw()}


@app.put("/api/nanoghost/mcp/config/raw")
def nanoghost_mcp_config_raw_put(body: ConfigRawPutBody):
    try:
        write_nanoghost_global_config_raw(body.raw)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True}


@app.get("/api/nanoghost/mcp/config")
def nanoghost_mcp_config_get():
    raw = read_nanoghost_global_config_raw()
    data = nanoghost_mcp_config_summary()
    return {"ok": True, "path": str(nanoghost_global_config_path()), "raw": raw, "servers": data["servers"]}


@app.get("/api/nanoghost/mcp/instances/{name}/allowlist")
def nanoghost_mcp_allowlist_get(name: str):
    name = (name or "").strip()
    inst = _nanoghost_instance_dir(name)
    if not inst.exists():
        raise HTTPException(status_code=404, detail="instance not found")
    cfg_path = inst / "config.yaml"
    return {"ok": True, "path": str(cfg_path), "enabled_only": read_instance_enabled_only(instance_dir=inst)}


@app.put("/api/nanoghost/mcp/instances/{name}/allowlist")
def nanoghost_mcp_allowlist_put(name: str, body: NanoGhostMcpAllowlistPutBody):
    name = (name or "").strip()
    inst = _nanoghost_instance_dir(name)
    if not inst.exists():
        raise HTTPException(status_code=404, detail="instance not found")
    write_instance_enabled_only(instance_dir=inst, enabled_only=body.enabled_only or [])
    return {"ok": True}


@app.get("/api/nanoghost/mcp/probe")
def nanoghost_mcp_probe(instance: str | None = None):
    raw = read_nanoghost_global_config_raw()
    try:
        servers = parse_global_mcp_servers(raw)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    allow: set[str] | None = None
    inst_dir: Path | None = None
    if instance is not None:
        inst_name = (instance or "").strip()
        inst_dir = _nanoghost_instance_dir(inst_name)
        if not inst_dir.exists():
            raise HTTPException(status_code=404, detail="instance not found")
        allow = set(read_instance_enabled_only(instance_dir=inst_dir))

    targets = sorted([sid for sid, scfg in servers.items() if isinstance(scfg, dict) and scfg.get("enabled", True) is not False])
    items: list[dict] = []
    for sid in targets:
        scfg = servers.get(sid) if isinstance(servers.get(sid), dict) else {}
        enabled = bool(scfg.get("enabled", True))
        transport = str(scfg.get("transport") or "http_sse").strip() or "http_sse"
        url = scfg.get("url") if isinstance(scfg.get("url"), str) else None
        timeout_seconds = float(scfg.get("timeout_seconds") or 30)

        if allow is not None and sid not in allow:
            items.append({"id": sid, "enabled": enabled, "transport": transport, "url": url, "ok": False, "status": "disabled_or_not_allowed", "error": None, "duration_ms": 0})
            continue
        if not enabled:
            items.append({"id": sid, "enabled": enabled, "transport": transport, "url": url, "ok": False, "status": "disabled", "error": "disabled", "duration_ms": 0})
            continue
        if transport != "http_sse":
            items.append({"id": sid, "enabled": enabled, "transport": transport, "url": url, "ok": False, "status": "unsupported", "error": "unsupported transport", "duration_ms": 0})
            continue
        if not url or not url.strip():
            items.append({"id": sid, "enabled": enabled, "transport": transport, "url": None, "ok": False, "status": "invalid", "error": "missing url", "duration_ms": 0})
            continue

        headers = scfg.get("headers") if isinstance(scfg.get("headers"), dict) else {}
        headers2 = {str(k): str(v) for k, v in headers.items() if v is not None}
        ok, status, err, dur = probe_http_sse(url=url, headers=headers2, timeout_seconds=timeout_seconds)
        items.append({"id": sid, "enabled": enabled, "transport": transport, "url": url, "ok": ok, "status": status, "error": err, "duration_ms": int(dur or 0)})

    return {"ok": True, "instance": str(inst_dir) if inst_dir else None, "items": items}


@app.get("/api/nanoghost/mcp/instances/{name}/tools")
def nanoghost_mcp_tools_get(name: str, server_id: str):
    name = (name or "").strip()
    server_id = (server_id or "").strip()
    if not server_id:
        raise HTTPException(status_code=400, detail="server_id required")
    inst = _nanoghost_instance_dir(name)
    if not inst.exists():
        raise HTTPException(status_code=404, detail="instance not found")

    allow = set(read_instance_enabled_only(instance_dir=inst))
    if server_id not in allow:
        raise HTTPException(status_code=400, detail="server not allowed")

    raw = read_nanoghost_global_config_raw()
    try:
        servers = parse_global_mcp_servers(raw)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    scfg = servers.get(server_id)
    if not isinstance(scfg, dict):
        raise HTTPException(status_code=404, detail="server not found")
    if scfg.get("enabled", True) is False:
        raise HTTPException(status_code=400, detail="server disabled")
    transport = str(scfg.get("transport") or "http_sse").strip() or "http_sse"
    if transport != "http_sse":
        raise HTTPException(status_code=400, detail="unsupported transport")
    url = scfg.get("url") if isinstance(scfg.get("url"), str) else ""
    url = url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="missing url")
    headers = scfg.get("headers") if isinstance(scfg.get("headers"), dict) else {}
    headers2 = {str(k): str(v) for k, v in headers.items() if v is not None}
    timeout_seconds = float(scfg.get("timeout_seconds") or 30)

    ok, result, err, dur = list_tools_http_sse(url=url, headers=headers2, timeout_seconds=timeout_seconds)
    tools = result.get("tools") if isinstance(result, dict) else None
    return {
        "ok": True,
        "server_id": server_id,
        "probe_ok": bool(ok),
        "duration_ms": int(dur or 0),
        "error": err,
        "tools": tools if isinstance(tools, list) else [],
    }


@app.get("/api/global-registry/{runtime}/skills")
def global_registry_skills(runtime: str):
    runtime = _normalize_runtime(runtime)
    if runtime == "nanoghost":
        shared_dir = resolve_shared_skills_root(config_path=CONFIG_PATH)
    elif runtime == "hermes":
        shared_dir = resolve_hermes_root(config_path=CONFIG_PATH) / "skills"
    else:
        raise HTTPException(status_code=400, detail="openclaw not implemented")
    items = list_global_skills_runtime(shared_dir)
    return {"ok": True, "runtime": runtime, "skills_dir": str(shared_dir), "count": len(items), "items": items}


@app.get("/api/global-registry/{runtime}/mcp/config")
def global_registry_mcp_config(runtime: str):
    runtime = _normalize_runtime(runtime)
    if runtime == "hermes":
        hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
        raw = read_hermes_config_raw(hermes_root=hermes_root)
        data = hermes_mcp_config_summary(hermes_root=hermes_root)
        return {"ok": True, "runtime": "hermes", "path": str(hermes_config_path(hermes_root=hermes_root)), "raw": raw, "servers": data["servers"]}
    if runtime == "nanoghost":
        raw = read_nanoghost_global_config_raw()
        data = nanoghost_mcp_config_summary()
        return {"ok": True, "runtime": "nanoghost", "path": str(nanoghost_global_config_path()), "raw": raw, "servers": data["servers"]}
    raise HTTPException(status_code=400, detail="openclaw not implemented")


@app.put("/api/global-registry/{runtime}/mcp/config")
def global_registry_mcp_config_put(runtime: str, body: ConfigRawPutBody):
    runtime = _normalize_runtime(runtime)
    if runtime == "hermes":
        hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
        try:
            write_hermes_config_raw(hermes_root=hermes_root, raw=body.raw)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        return {"ok": True}
    if runtime == "nanoghost":
        try:
            write_nanoghost_global_config_raw(body.raw)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        return {"ok": True}
    raise HTTPException(status_code=400, detail="openclaw not implemented")


@app.get("/api/runtimes")
def runtimes_get():
    cfg = load_app_config(CONFIG_PATH)
    return {
        "ok": True,
        "items": [
            {"name": "hermes", "title": "Hermes", "root": str(resolve_hermes_root(config_path=CONFIG_PATH))},
            {"name": "nanoghost", "title": "NanoGhost", "root": str(resolve_nanoghost_root(config_path=CONFIG_PATH))},
            {"name": "openclaw", "title": "OpenClaw", "root": str(resolve_openclaw_root(config_path=CONFIG_PATH))},
        ],
        "bind_host": cfg.bind_host,
        "bind_port": cfg.bind_port,
    }


@app.get("/api/runtimes/{runtime}/instances")
def runtime_instances_get(runtime: str):
    runtime = (runtime or "").strip().lower()
    if runtime == "hermes":
        hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
        profiles = list_profiles(hermes_root)
        return {
            "ok": True,
            "runtime": "hermes",
            "root": str(hermes_root),
            "instances": [{"name": p.name, "path": str(p.path), "is_default": p.is_default} for p in profiles],
        }
    if runtime == "nanoghost":
        root = resolve_nanoghost_root(config_path=CONFIG_PATH)
        return {
            "ok": True,
            "runtime": "nanoghost",
            "root": str(root),
            "instances": _list_nanoghost_instances(root),
        }
    if runtime == "openclaw":
        return {"ok": True, "runtime": "openclaw", "root": None, "instances": []}
    raise HTTPException(status_code=404, detail="runtime not found")


@app.post("/api/runtimes/{runtime}/instances")
def runtime_instance_create(runtime: str, body: RuntimeInstanceCreateBody):
    runtime = (runtime or "").strip().lower()
    name = (body.name or "").strip()
    _require_valid_instance_name(name)
    if runtime == "hermes":
        hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
        if not hermes_root.exists():
            raise HTTPException(status_code=400, detail="hermes_root does not exist")
        profiles_root = hermes_root / "profiles"
        profiles_root.mkdir(parents=True, exist_ok=True)
        profile_dir = profiles_root / name
        if profile_dir.exists():
            raise HTTPException(status_code=409, detail="profile already exists")
        tpl_dir = _template_dir("hermes", body.template_id)
        try:
            clone_template_dir(
                template_dir=tpl_dir,
                dest_dir=profile_dir,
                exclude_names={"profiles", "templates"},
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except FileExistsError as e:
            raise HTTPException(status_code=409, detail=str(e)) from e
        except OSError as e:
            raise HTTPException(status_code=500, detail=str(e)) from e
        for sub in ["memories", "sessions", "skills", "skins", "logs", "plans", "workspace", "cron", "home"]:
            (profile_dir / sub).mkdir(parents=True, exist_ok=True)
        return {"ok": True, "name": name, "path": str(profile_dir)}
    if runtime == "nanoghost":
        root = resolve_nanoghost_root(config_path=CONFIG_PATH)
        if not root.exists():
            raise HTTPException(status_code=400, detail="nanoghost_root does not exist")

        instances_root = root / "instances"
        instances_root.mkdir(parents=True, exist_ok=True)

        inst = instances_root / name
        if inst.exists():
            raise HTTPException(status_code=409, detail="instance already exists")

        tpl_dir = _template_dir("nanoghost", body.template_id)
        try:
            clone_template_dir(template_dir=tpl_dir, dest_dir=inst, exclude_names={"instances", "templates"})
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except FileExistsError as e:
            raise HTTPException(status_code=409, detail=str(e)) from e
        except OSError as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

        for sub in ["data", "work", "prompts", "skills", "skills.disabled"]:
            (inst / sub).mkdir(parents=True, exist_ok=True)

        env_path = inst / ".env"
        if not env_path.exists():
            src_env = _nanoghost_repo_dir() / ".env" if _nanoghost_repo_dir() else None
            if src_env and src_env.is_file():
                env_path.write_text(src_env.read_text(encoding="utf-8"), encoding="utf-8")
            else:
                env_path.write_text("", encoding="utf-8")

        prompts_dir = inst / "prompts"
        src_prompts = (_nanoghost_repo_dir() / "prompts") if _nanoghost_repo_dir() else None
        if src_prompts and src_prompts.is_dir():
            for f in src_prompts.iterdir():
                if f.is_file() and f.suffix == ".md":
                    dest = prompts_dir / f.name
                    if not dest.exists():
                        dest.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")

        return {"ok": True, "name": name, "path": str(inst)}
    if runtime == "openclaw":
        raise HTTPException(status_code=400, detail="openclaw not implemented")
    raise HTTPException(status_code=404, detail="runtime not found")


@app.delete("/api/runtimes/{runtime}/instances/{name}")
def runtime_instance_delete(runtime: str, name: str):
    runtime = (runtime or "").strip().lower()
    name = (name or "").strip()
    if runtime == "hermes":
        hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
        profile_dir = hermes_root / "profiles" / name
        if not profile_dir.exists():
            raise HTTPException(status_code=404, detail="profile not found")
        import shutil
        shutil.rmtree(profile_dir)
        reg = load_registry(REGISTRY_PATH)
        hermes_instances = ((reg.get("runtimes") or {}).get("hermes") or {}).get("instances")
        if isinstance(hermes_instances, dict):
            hermes_instances.pop(name, None)
        save_registry(REGISTRY_PATH, reg)
        return {"ok": True}
    if runtime == "nanoghost":
        inst = _nanoghost_instance_dir(name)
        if not inst.exists():
            raise HTTPException(status_code=404, detail="instance not found")
        reg = load_registry(REGISTRY_PATH)
        recs = ((reg.get("runtimes") or {}).get("nanoghost") or {}).get("instances")
        imap = recs.get(name) if isinstance(recs, dict) else None
        if isinstance(imap, dict):
            for proc in ("cli", "feishu"):
                r = imap.get(proc)
                if isinstance(r, dict) and r.get("pid") and is_pid_running(int(r["pid"])):
                    raise HTTPException(status_code=409, detail="instance is running")
        import shutil
        shutil.rmtree(inst)
        if isinstance(recs, dict):
            recs.pop(name, None)
            save_registry(REGISTRY_PATH, reg)
        return {"ok": True}
    if runtime == "openclaw":
        raise HTTPException(status_code=400, detail="openclaw not implemented")
    raise HTTPException(status_code=404, detail="runtime not found")


@app.get("/api/runtimes/{runtime}/instances/{name}/env")
def runtime_env_get(runtime: str, name: str):
    runtime = (runtime or "").strip().lower()
    name = (name or "").strip()
    if runtime == "hermes":
        return env_get(name)
    if runtime == "nanoghost":
        inst = _nanoghost_instance_dir(name)
        if not inst.exists():
            raise HTTPException(status_code=404, detail="instance not found")
        env_path = inst / ".env"
        keys = parse_env_keys(env_path)
        return {
            "ok": True,
            "path": str(env_path),
            "items": [{"key": k, "is_set": v != "", "value": v} for k, v in keys.items()],
        }
    raise HTTPException(status_code=404, detail="runtime not found")


@app.put("/api/runtimes/{runtime}/instances/{name}/env")
def runtime_env_put(runtime: str, name: str, body: EnvPutBody):
    runtime = (runtime or "").strip().lower()
    name = (name or "").strip()
    if runtime == "hermes":
        return env_put(name, body)
    if runtime == "nanoghost":
        inst = _nanoghost_instance_dir(name)
        if not inst.exists():
            raise HTTPException(status_code=404, detail="instance not found")
        env_path = inst / ".env"
        set_env_kv(env_path, body.key, body.value)
        return {"ok": True}
    raise HTTPException(status_code=404, detail="runtime not found")


@app.put("/api/runtimes/{runtime}/instances/{name}/env/batch")
def runtime_env_batch_put(runtime: str, name: str, body: EnvBatchPutBody):
    runtime = (runtime or "").strip().lower()
    name = (name or "").strip()
    if runtime == "hermes":
        return env_batch_put(name, body)
    if runtime == "nanoghost":
        inst = _nanoghost_instance_dir(name)
        if not inst.exists():
            raise HTTPException(status_code=404, detail="instance not found")
        env_path = inst / ".env"
        for k, v in body.items.items():
            set_env_kv(env_path, k, v)
        return {"ok": True}
    raise HTTPException(status_code=404, detail="runtime not found")


@app.delete("/api/runtimes/{runtime}/instances/{name}/env")
def runtime_env_delete(runtime: str, name: str, body: EnvDeleteBody):
    runtime = (runtime or "").strip().lower()
    name = (name or "").strip()
    if runtime == "hermes":
        return env_delete(name, body)
    if runtime == "nanoghost":
        inst = _nanoghost_instance_dir(name)
        if not inst.exists():
            raise HTTPException(status_code=404, detail="instance not found")
        env_path = inst / ".env"
        delete_env_key(env_path, body.key)
        return {"ok": True}
    raise HTTPException(status_code=404, detail="runtime not found")


@app.get("/api/runtimes/{runtime}/instances/{name}/skills")
def runtime_skills_get(name: str, runtime: str, platform: str | None = None):
    runtime = (runtime or "").strip().lower()
    name = (name or "").strip()
    if runtime == "hermes":
        return skills_get(name, platform=platform)
    if runtime == "nanoghost":
        inst = _nanoghost_instance_dir(name)
        if not inst.exists():
            raise HTTPException(status_code=404, detail="instance not found")
        shared_dir = resolve_shared_skills_root(config_path=CONFIG_PATH)
        items = list_skills_nanoghost(inst, platform=platform, shared_dir=shared_dir)
        return {
            "ok": True,
            "items": [
                {
                    "name": i.name,
                    "path": str(i.path),
                    "enabled": i.enabled,
                    "description": i.description,
                    "category": i.category,
                    "source": i.source,
                }
                for i in items
            ],
        }
    raise HTTPException(status_code=404, detail="runtime not found")


@app.put("/api/runtimes/{runtime}/instances/{name}/skills/batch")
def runtime_skills_batch_put(name: str, runtime: str, body: SkillBatchPutBody):
    runtime = (runtime or "").strip().lower()
    name = (name or "").strip()
    if runtime == "hermes":
        return skills_batch_put(name, body)
    if runtime == "nanoghost":
        inst = _nanoghost_instance_dir(name)
        if not inst.exists():
            raise HTTPException(status_code=404, detail="instance not found")
        for skill_name, enabled in body.items.items():
            try:
                set_skill_enabled_nanoghost(inst, skill_name, enabled)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e)) from e
        return {"ok": True}
    raise HTTPException(status_code=404, detail="runtime not found")


@app.post("/api/runtimes/{runtime}/instances/{name}/processes/{proc}/start")
def runtime_process_start(runtime: str, name: str, proc: str):
    runtime = (runtime or "").strip().lower()
    name = (name or "").strip()
    proc = (proc or "").strip().lower()
    if runtime == "hermes":
        if proc == "gateway":
            return gateway_start(name)
        raise HTTPException(status_code=404, detail="process not found")
    if runtime == "nanoghost":
        if proc not in ("cli", "feishu"):
            raise HTTPException(status_code=404, detail="process not found")
        inst = _nanoghost_instance_dir(name)
        if not inst.exists():
            raise HTTPException(status_code=404, detail="instance not found")
        run_py = _nanoghost_run_py()
        reg = load_registry(REGISTRY_PATH)
        rec = _proc_record(reg, "nanoghost", name, proc)
        if rec.get("pid") and is_pid_running(int(rec["pid"])):
            logger.info("nanoghost %s/%s already running (pid %s)", name, proc, rec["pid"])
            return {"ok": True, **_status_for_record(rec)}
        env = dict(os.environ)
        env["INSTANCE_DIR"] = str(inst)
        env_path = inst / ".env"
        keys = parse_env_keys(env_path)
        for k, v in keys.items():
            vv = (v or "").strip()
            if not vv:
                continue
            if len(vv) >= 2 and vv[0] == vv[-1] and vv[0] in ('"', "'", "`"):
                vv = vv[1:-1].strip()
            env[k] = vv
        if proc == "feishu":
            env["AGENT_MODE"] = "feishu"
        else:
            env.pop("AGENT_MODE", None)
        argv = [_nanoghost_python(), str(run_py), "-I", str(inst)]
        logger.info("starting nanoghost %s/%s argv=%s", name, proc, " ".join(argv))
        sr = spawn_logged(argv, cwd=str(run_py.parent), env=env, tag=f"ng-{proc}-{name}")
        logger.info("nanoghost %s/%s pid=%s", name, proc, sr.pid)
        rec["pid"] = sr.pid
        rec["started_at"] = int(time.time())
        save_registry(REGISTRY_PATH, reg)
        return {"ok": True, **_status_for_record(rec), "argv": argv}
    raise HTTPException(status_code=404, detail="runtime not found")


@app.post("/api/runtimes/{runtime}/instances/{name}/processes/{proc}/stop")
def runtime_process_stop(runtime: str, name: str, proc: str):
    runtime = (runtime or "").strip().lower()
    name = (name or "").strip()
    proc = (proc or "").strip().lower()
    if runtime == "hermes":
        if proc == "gateway":
            return gateway_stop(name)
        raise HTTPException(status_code=404, detail="process not found")
    if runtime == "nanoghost":
        if proc not in ("cli", "feishu"):
            raise HTTPException(status_code=404, detail="process not found")
        reg = load_registry(REGISTRY_PATH)
        rec = _proc_record(reg, "nanoghost", name, proc)
        pid = rec.get("pid")
        if not pid:
            return {"ok": False, "error": "no pid recorded"}
        kill_pid_tree(int(pid))
        rec["pid"] = None
        rec["started_at"] = None
        save_registry(REGISTRY_PATH, reg)
        return {"ok": True}
    raise HTTPException(status_code=404, detail="runtime not found")


@app.get("/api/runtimes/{runtime}/instances/{name}/processes/{proc}/status")
def runtime_process_status(runtime: str, name: str, proc: str):
    runtime = (runtime or "").strip().lower()
    name = (name or "").strip()
    proc = (proc or "").strip().lower()
    if runtime == "hermes":
        if proc == "gateway":
            return gateway_status(name)
        raise HTTPException(status_code=404, detail="process not found")
    if runtime == "nanoghost":
        if proc not in ("cli", "feishu"):
            raise HTTPException(status_code=404, detail="process not found")
        reg = load_registry(REGISTRY_PATH)
        rec = _proc_record(reg, "nanoghost", name, proc)
        status = _status_for_record(rec)
        if status["pid"] and not status["pid_running"]:
            rec["pid"] = None
            rec["started_at"] = None
            save_registry(REGISTRY_PATH, reg)
            status = _status_for_record(rec)
        return {"ok": True, **status}
    raise HTTPException(status_code=404, detail="runtime not found")


@app.get("/api/instances/nanoghost/{name}/memory/raw")
def ng_memory_raw_get(name: str):
    inst = _nanoghost_instance_dir(name)
    if not inst.exists():
        raise HTTPException(status_code=404, detail="instance not found")
    md_path = _nanoghost_memory_md_path(name)
    raw = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
    return {"ok": True, "raw": raw, "path": str(md_path)}


class NgMemRawBody(BaseModel):
    raw: str


@app.put("/api/instances/nanoghost/{name}/memory/raw")
def ng_memory_raw_put(name: str, body: NgMemRawBody):
    inst = _nanoghost_instance_dir(name)
    if not inst.exists():
        raise HTTPException(status_code=404, detail="instance not found")
    md_path = _nanoghost_memory_md_path(name)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(body.raw, encoding="utf-8")
    return {"ok": True}


@app.get("/api/instances/nanoghost/{name}/memory/cards")
def ng_memory_cards_get(name: str):
    inst = _nanoghost_instance_dir(name)
    if not inst.exists():
        raise HTTPException(status_code=404, detail="instance not found")
    db_path = _nanoghost_agent_db_path(name)
    if not db_path.exists():
        return {"ok": True, "cards": []}
    import sqlite3
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        # Support both old and new schema
        cols = [r[1] for r in c.execute("PRAGMA table_info(agent_memory_cards)").fetchall()]
        if "session" in cols:
            c.execute("""SELECT session as user_input, agent_output,
                             total_steps, success_count, approve_count, reject_count, trigger_count,
                             finished_at
                             FROM agent_memory_cards ORDER BY finished_at DESC""")
        else:
            c.execute("""SELECT intent_summary as user_input, steps_json as agent_output,
                             total_rounds as total_steps, success_count, approved_count as approve_count,
                             rejected_count as reject_count, trigger_count,
                             created_at as finished_at
                             FROM agent_memory_cards ORDER BY created_at DESC""")
        cards = [dict(r) for r in c.fetchall()]
        conn.close()
        import re as _re
        import json as _json
        for card in cards:
            for k in ("user_input", "agent_output"):
                v = card.get(k) or ""
                if k == "agent_output" and isinstance(v, str) and v.startswith("["):
                    try:
                        steps = _json.loads(v)
                        v = "\n".join(s.get("path", s.get("method", ""))[:80] for s in steps[:5])
                        if len(steps) > 5:
                            v += "\n..."
                    except:
                        pass
                v = _re.sub(r"<[^>]+>", "", v)
                if len(v) > 120:
                    v = v[:117] + "..."
                card[k] = v
            ts = card.get("finished_at")
            if ts:
                import datetime
                try:
                    card["finished_at"] = datetime.datetime.fromtimestamp(int(ts)).strftime("%Y/%m/%d %H:%M:%S")
                except:
                    pass
        return {"ok": True, "cards": cards}
    except Exception as e:
        return {"ok": True, "cards": [], "error": str(e)}


@app.get("/api/instances/nanoghost/{name}/memory/graph")
def ng_memory_graph_get(name: str):
    inst = _nanoghost_instance_dir(name)
    if not inst.exists():
        raise HTTPException(status_code=404, detail="instance not found")
    db_path = _nanoghost_agent_db_path(name)
    if not db_path.exists():
        return {"ok": True, "nodes": [], "edges": []}
    import sqlite3
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""SELECT from_method, from_path, to_method, to_path,
                     relation_type, total_count, approved_count
                     FROM agent_memory_edges ORDER BY total_count DESC""")
        edge_rows = [dict(r) for r in c.fetchall()]
        conn.close()
        import hashlib
        def _safe_id(s):
            return "n" + hashlib.md5((s or "").encode()).hexdigest()[:12]
        nodes_map = {}
        edges = []
        for r in edge_rows:
            from_id = _safe_id(r["from_path"])
            if from_id not in nodes_map:
                nodes_map[from_id] = {"id": from_id, "method": r["from_method"], "path": r["from_path"],
                    "label": (r["from_method"] or "?") + "\n" + ((r["from_path"] or "")[:80])}
            to_id = _safe_id(r["to_path"])
            if to_id not in nodes_map:
                nodes_map[to_id] = {"id": to_id, "method": r["to_method"], "path": r["to_path"],
                    "label": (r["to_method"] or "?") + "\n" + ((r["to_path"] or "")[:80])}
            edges.append({
                "from": from_id, "to": to_id,
                "label": r["relation_type"] or "FOLLOWS",
                "total_count": r["total_count"] or 1,
                "approved_count": r["approved_count"] or 0,
            })
        return {"ok": True, "nodes": list(nodes_map.values()), "edges": edges}
    except Exception as e:
        return {"ok": True, "nodes": [], "edges": [], "error": str(e)}
