# Hermes 实例管理台 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在当前项目中新建一个 FastAPI 管理台，独立于 Hermes 源码，通过 `hermes` CLI + 读写各 profile 目录，实现 profiles 列表、dashboard/gateway 启停、`.env/config.yaml` 编辑、skills 启用禁用。

**Architecture:** FastAPI 提供 REST + 简单页面（Jinja2 + 少量 JS）。Hermes root 由 `data/config.yaml`（优先）/`HERMES_HOME`/`~/.hermes` 决定。端口自动分配并持久化到 `data/registry.json`。进程控制通过 `subprocess.Popen` + Windows `taskkill`。

**Tech Stack:** Python 3.11+、FastAPI、Uvicorn、Jinja2、PyYAML、psutil、pytest

---

## 文件结构（将创建）

- Create: `e:\OperationsAssistantORIG\Tech\Code\OpenObstrator\server\app.py`
- Create: `e:\OperationsAssistantORIG\Tech\Code\OpenObstrator\server\settings.py`
- Create: `e:\OperationsAssistantORIG\Tech\Code\OpenObstrator\server\profiles.py`
- Create: `e:\OperationsAssistantORIG\Tech\Code\OpenObstrator\server\registry.py`
- Create: `e:\OperationsAssistantORIG\Tech\Code\OpenObstrator\server\ports.py`
- Create: `e:\OperationsAssistantORIG\Tech\Code\OpenObstrator\server\processes.py`
- Create: `e:\OperationsAssistantORIG\Tech\Code\OpenObstrator\server\envfile.py`
- Create: `e:\OperationsAssistantORIG\Tech\Code\OpenObstrator\server\configfile.py`
- Create: `e:\OperationsAssistantORIG\Tech\Code\OpenObstrator\server\skills.py`
- Create: `e:\OperationsAssistantORIG\Tech\Code\OpenObstrator\server\templates\index.html`
- Create: `e:\OperationsAssistantORIG\Tech\Code\OpenObstrator\server\templates\profile.html`
- Create: `e:\OperationsAssistantORIG\Tech\Code\OpenObstrator\server\static\app.js`
- Create: `e:\OperationsAssistantORIG\Tech\Code\OpenObstrator\requirements.txt`
- Create: `e:\OperationsAssistantORIG\Tech\Code\OpenObstrator\data\config.yaml`
- Create: `e:\OperationsAssistantORIG\Tech\Code\OpenObstrator\data\registry.json`
- Test: `e:\OperationsAssistantORIG\Tech\Code\OpenObstrator\tests\test_settings.py`
- Test: `e:\OperationsAssistantORIG\Tech\Code\OpenObstrator\tests\test_envfile.py`
- Test: `e:\OperationsAssistantORIG\Tech\Code\OpenObstrator\tests\test_ports.py`

---

### Task 1: 初始化项目骨架与依赖

**Files:**
- Create: `requirements.txt`
- Create: `server/app.py`
- Create: `server/settings.py`
- Create: `data/config.yaml`
- Create: `data/registry.json`
- Create: `tests/test_settings.py`

- [ ] **Step 1: 写依赖文件**

`requirements.txt` 内容：

```txt
fastapi==0.115.0
uvicorn[standard]==0.30.6
jinja2==3.1.4
pyyaml==6.0.2
psutil==6.0.0
pytest==8.3.2
httpx==0.27.2
```

- [ ] **Step 2: 写默认配置文件**

`data/config.yaml` 内容：

```yaml
hermes_root: null
port_alloc:
  dashboard_start: 18000
  dashboard_end: 18999
  gateway_start: 19000
  gateway_end: 19999
bind_host: 127.0.0.1
bind_port: 8088
```

- [ ] **Step 3: 写空 registry**

`data/registry.json` 内容：

```json
{
  "version": 1,
  "profiles": {}
}
```

- [ ] **Step 4: 写 settings（先写测试驱动）**

`tests/test_settings.py`：

```python
from pathlib import Path

from server.settings import resolve_hermes_root


def test_resolve_hermes_root_prefers_manager_config(tmp_path, monkeypatch):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("hermes_root: D:\\\\HermesData\n", encoding="utf-8")
    monkeypatch.delenv("HERMES_HOME", raising=False)
    root = resolve_hermes_root(config_path=cfg)
    assert str(root) == "D:\\HermesData"


def test_resolve_hermes_root_falls_back_to_env(monkeypatch, tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("hermes_root: null\n", encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", "D:\\\\HermesEnv")
    root = resolve_hermes_root(config_path=cfg)
    assert str(root) == "D:\\HermesEnv"


def test_resolve_hermes_root_falls_back_to_home(monkeypatch, tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("hermes_root: null\n", encoding="utf-8")
    monkeypatch.delenv("HERMES_HOME", raising=False)
    root = resolve_hermes_root(config_path=cfg)
    assert root.name == ".hermes"
```

- [ ] **Step 5: 最小实现 settings.py**

`server/settings.py`：

```python
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class PortAlloc:
    dashboard_start: int = 18000
    dashboard_end: int = 18999
    gateway_start: int = 19000
    gateway_end: int = 19999


@dataclass(frozen=True)
class AppConfig:
    hermes_root: str | None
    port_alloc: PortAlloc
    bind_host: str = "127.0.0.1"
    bind_port: int = 8088


def load_app_config(config_path: Path) -> AppConfig:
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    if not isinstance(raw, dict):
        raw = {}
    pa_raw = raw.get("port_alloc", {}) if isinstance(raw.get("port_alloc"), dict) else {}
    port_alloc = PortAlloc(
        dashboard_start=int(pa_raw.get("dashboard_start", 18000)),
        dashboard_end=int(pa_raw.get("dashboard_end", 18999)),
        gateway_start=int(pa_raw.get("gateway_start", 19000)),
        gateway_end=int(pa_raw.get("gateway_end", 19999)),
    )
    hermes_root = raw.get("hermes_root")
    hermes_root = str(hermes_root) if hermes_root not in (None, "", "null") else None
    return AppConfig(
        hermes_root=hermes_root,
        port_alloc=port_alloc,
        bind_host=str(raw.get("bind_host") or "127.0.0.1"),
        bind_port=int(raw.get("bind_port") or 8088),
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
```

- [ ] **Step 6: 运行测试**

Run:

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\pytest -q
```

Expected: PASS

---

### Task 2: Profiles 枚举与路径推导

**Files:**
- Create: `server/profiles.py`
- Modify: `server/app.py`

- [ ] **Step 1: 添加 ProfileInfo 与扫描逻辑**

`server/profiles.py`：

```python
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
    if hermes_root.is_dir():
        result.append(ProfileInfo(name="default", path=hermes_root, is_default=True))
    profiles_root = hermes_root / "profiles"
    if profiles_root.is_dir():
        for entry in sorted(profiles_root.iterdir()):
            if entry.is_dir():
                result.append(ProfileInfo(name=entry.name, path=entry, is_default=False))
    return result
```

- [ ] **Step 2: 写 app.py 的基础 FastAPI 入口（健康检查 + profiles 列表）**

`server/app.py`：

```python
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from server.profiles import list_profiles
from server.settings import resolve_hermes_root


APP_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = APP_ROOT / "data"
CONFIG_PATH = DATA_DIR / "config.yaml"

app = FastAPI()


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/profiles")
def api_profiles():
    hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
    profiles = list_profiles(hermes_root)
    return {
        "hermes_root": str(hermes_root),
        "profiles": [{"name": p.name, "path": str(p.path), "is_default": p.is_default} for p in profiles],
    }
```

- [ ] **Step 3: 手动启动服务验证**

Run:

```powershell
.\.venv\Scripts\uvicorn server.app:app --host 127.0.0.1 --port 8088
```

Expected:
- `GET http://127.0.0.1:8088/api/health` 返回 `{"ok": true}`
- `GET http://127.0.0.1:8088/api/profiles` 返回 default + profiles 列表（若存在）

---

### Task 3: Registry（端口分配与 PID 记录）

**Files:**
- Create: `server/registry.py`
- Create: `tests/test_ports.py`
- Create: `server/ports.py`

- [ ] **Step 1: 实现 registry 读写（原子写）**

`server/registry.py`：

```python
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ProcRecord:
    port: int | None = None
    pid: int | None = None
    started_at: int | None = None


@dataclass
class ProfileRuntime:
    dashboard: ProcRecord
    gateway: ProcRecord


def _default_registry() -> dict:
    return {"version": 1, "profiles": {}}


def load_registry(path: Path) -> dict:
    if not path.exists():
        return _default_registry()
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return _default_registry()
    raw.setdefault("version", 1)
    raw.setdefault("profiles", {})
    if not isinstance(raw["profiles"], dict):
        raw["profiles"] = {}
    return raw


def save_registry(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
```

- [ ] **Step 2: 端口探测与分配**

`server/ports.py`：

```python
from __future__ import annotations

import socket


def is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.2)
        return s.connect_ex((host, port)) == 0


def allocate_port(host: str, start: int, end: int, used: set[int]) -> int:
    for port in range(start, end + 1):
        if port in used:
            continue
        if is_port_open(host, port):
            continue
        return port
    raise RuntimeError("No free port available in range")
```

- [ ] **Step 3: 测试端口分配**

`tests/test_ports.py`：

```python
from server.ports import allocate_port


def test_allocate_port_skips_used_set(monkeypatch):
    def fake_open(host: str, port: int) -> bool:
        return False

    monkeypatch.setattr("server.ports.is_port_open", fake_open)
    p = allocate_port("127.0.0.1", 18000, 18002, used={18000})
    assert p == 18001
```

- [ ] **Step 4: 运行测试**

Run:

```powershell
.\.venv\Scripts\pytest -q
```

Expected: PASS

---

### Task 4: Windows 进程管理（dashboard/gateway 启停）

**Files:**
- Create: `server/processes.py`
- Modify: `server/app.py`

- [ ] **Step 1: 实现 PID 存活判断与 taskkill**

`server/processes.py`：

```python
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Sequence

import psutil


def is_pid_running(pid: int) -> bool:
    try:
        p = psutil.Process(pid)
        return p.is_running() and p.status() != psutil.STATUS_ZOMBIE
    except psutil.Error:
        return False


def kill_pid_tree(pid: int) -> None:
    subprocess.run(
        ["taskkill", "/PID", str(pid), "/T", "/F"],
        capture_output=True,
        text=True,
        check=False,
    )


@dataclass(frozen=True)
class SpawnResult:
    pid: int
    argv: list[str]


def spawn(argv: Sequence[str]) -> SpawnResult:
    p = subprocess.Popen(list(argv), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return SpawnResult(pid=int(p.pid), argv=list(argv))
```

- [ ] **Step 2: 在 API 中增加 dashboard/gateway start/stop（先只做最小）**

在 `server/app.py` 中新增常量与 registry 路径：

```python
REGISTRY_PATH = DATA_DIR / "registry.json"
```

并新增端点（示例，具体实现按后续 Tasks 拆文件完善）：

```python
from server.registry import load_registry, save_registry
from server.ports import allocate_port
from server.processes import is_pid_running, kill_pid_tree, spawn
from server.settings import load_app_config


@app.post("/api/profiles/{name}/dashboard/start")
def dashboard_start(name: str):
    hermes_root = resolve_hermes_root(config_path=CONFIG_PATH)
    cfg = load_app_config(CONFIG_PATH)
    reg = load_registry(REGISTRY_PATH)
    pmap = reg["profiles"].setdefault(name, {})
    dash = pmap.setdefault("dashboard", {"port": None, "pid": None, "started_at": None})

    used = {
        int(v.get("port"))
        for v in (reg.get("profiles") or {}).values()
        for k, v in (v or {}).items()
        if isinstance(v, dict) and v.get("port")
    }
    if not dash.get("port"):
        dash["port"] = allocate_port("127.0.0.1", cfg.port_alloc.dashboard_start, cfg.port_alloc.dashboard_end, used)

    argv = [
        "hermes",
        "-p",
        name,
        "dashboard",
        "--host",
        "127.0.0.1",
        "--port",
        str(dash["port"]),
        "--no-open",
        "--skip-build",
    ]
    sr = spawn(argv)
    dash["pid"] = sr.pid
    dash["started_at"] = 0
    save_registry(REGISTRY_PATH, reg)
    return {"ok": True, "port": dash["port"], "pid": dash["pid"], "argv": argv}


@app.post("/api/profiles/{name}/dashboard/stop")
def dashboard_stop(name: str):
    reg = load_registry(REGISTRY_PATH)
    dash = ((reg.get("profiles") or {}).get(name) or {}).get("dashboard") or {}
    pid = dash.get("pid")
    if not pid:
        return {"ok": False, "error": "no pid recorded"}
    kill_pid_tree(int(pid))
    dash["pid"] = None
    save_registry(REGISTRY_PATH, reg)
    return {"ok": True}
```

- [ ] **Step 3: 手动验证**

Run:
- 启动管理台后访问：
  - `POST /api/profiles/default/dashboard/start`
  - `POST /api/profiles/default/dashboard/stop`

Expected:
- start 返回 pid/port
- stop 后进程被杀死（端口不可连接）

---

### Task 5: `.env` 行级编辑（保留注释与顺序）

**Files:**
- Create: `server/envfile.py`
- Create: `tests/test_envfile.py`
- Modify: `server/app.py`

- [ ] **Step 1: 写测试（保留注释、只改目标行）**

`tests/test_envfile.py`：

```python
from pathlib import Path

from server.envfile import set_env_kv, delete_env_key, parse_env_keys


def test_set_env_preserves_comments_and_order(tmp_path: Path):
    p = tmp_path / ".env"
    p.write_text("# c1\nA=1\n\n# c2\nB=2\n", encoding="utf-8")
    set_env_kv(p, "B", "999")
    assert p.read_text(encoding="utf-8") == "# c1\nA=1\n\n# c2\nB=999\n"


def test_set_env_appends_when_missing(tmp_path: Path):
    p = tmp_path / ".env"
    p.write_text("A=1\n", encoding="utf-8")
    set_env_kv(p, "B", "2")
    assert p.read_text(encoding="utf-8") == "A=1\nB=2\n"


def test_delete_env_key(tmp_path: Path):
    p = tmp_path / ".env"
    p.write_text("A=1\nB=2\n", encoding="utf-8")
    delete_env_key(p, "A")
    assert p.read_text(encoding="utf-8") == "B=2\n"


def test_parse_env_keys(tmp_path: Path):
    p = tmp_path / ".env"
    p.write_text("# x\nA=1\nB = 2\nexport C=3\n", encoding="utf-8")
    keys = parse_env_keys(p)
    assert keys == {"A": "1", "B": "2", "C": "3"}
```

- [ ] **Step 2: 实现 envfile**

`server/envfile.py`：

```python
from __future__ import annotations

import re
from pathlib import Path


_LINE_RE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$")


def parse_env_keys(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = _LINE_RE.match(line)
        if not m:
            continue
        out[m.group(1)] = m.group(2)
    return out


def set_env_kv(path: Path, key: str, value: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines(True) if path.exists() else []
    replaced = False
    new_lines: list[str] = []
    for raw in lines:
        line = raw.rstrip("\n")
        m = _LINE_RE.match(line)
        if m and m.group(1) == key and not replaced:
            new_lines.append(f"{key}={value}\n")
            replaced = True
        else:
            new_lines.append(raw if raw.endswith("\n") else raw + "\n")
    if not replaced:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] += "\n"
        new_lines.append(f"{key}={value}\n")
    _atomic_write(path, "".join(new_lines))


def delete_env_key(path: Path, key: str) -> None:
    if not path.exists():
        return
    lines = path.read_text(encoding="utf-8").splitlines(True)
    out: list[str] = []
    for raw in lines:
        line = raw.rstrip("\n")
        m = _LINE_RE.match(line)
        if m and m.group(1) == key:
            continue
        out.append(raw)
    _atomic_write(path, "".join(out))


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)
```

- [ ] **Step 3: 接入 API（/env get/put/delete）**

在 `server/app.py` 中添加：

- `GET /api/profiles/{name}/env`：返回解析出的 key 列表与 redacted（后续再加 reveal）
- `PUT /api/profiles/{name}/env`：调用 `set_env_kv`
- `DELETE /api/profiles/{name}/env`：调用 `delete_env_key`

- [ ] **Step 4: 运行测试**

Run:

```powershell
.\.venv\Scripts\pytest -q
```

Expected: PASS

---

### Task 6: config.yaml Raw 编辑端点

**Files:**
- Create: `server/configfile.py`
- Modify: `server/app.py`

- [ ] **Step 1: 实现读取与校验写入**

`server/configfile.py`：

```python
from __future__ import annotations

from pathlib import Path

import yaml


def read_raw_yaml(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def validate_yaml_mapping(yaml_text: str) -> dict:
    parsed = yaml.safe_load(yaml_text) if yaml_text.strip() else {}
    if parsed is None:
        parsed = {}
    if not isinstance(parsed, dict):
        raise ValueError("YAML must be a mapping")
    return parsed


def write_raw_yaml(path: Path, yaml_text: str) -> None:
    validate_yaml_mapping(yaml_text)
    tmp = path.with_suffix(path.suffix + ".tmp")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(yaml_text, encoding="utf-8")
    tmp.replace(path)
```

- [ ] **Step 2: API 接入**

在 `server/app.py` 中添加：

- `GET /api/profiles/{name}/config/raw`
- `PUT /api/profiles/{name}/config/raw`

实现时用 `<profile_dir>/config.yaml`。

- [ ] **Step 3: 手动验证**

Expected:
- PUT 一个非 mapping 的 YAML 返回 400
- PUT 合法 YAML 后文件写入成功，GET 返回原文

---

### Task 7: Skills 列表 + toggle（允许重写 YAML）

**Files:**
- Create: `server/skills.py`
- Modify: `server/app.py`

- [ ] **Step 1: 实现 skills 扫描**

`server/skills.py`：

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class SkillItem:
    name: str
    path: Path
    enabled: bool


def list_skill_md_files(profile_dir: Path) -> list[Path]:
    skills_dir = profile_dir / "skills"
    if not skills_dir.is_dir():
        return []
    return sorted(skills_dir.rglob("SKILL.md"))


def load_disabled_skills(profile_dir: Path) -> set[str]:
    cfg_path = profile_dir / "config.yaml"
    if not cfg_path.exists():
        return set()
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return set()
    skills_cfg = raw.get("skills", {}) if isinstance(raw.get("skills"), dict) else {}
    disabled = skills_cfg.get("disabled", []) if isinstance(skills_cfg.get("disabled"), list) else []
    return {str(x) for x in disabled}


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
    cfg_path.write_text(yaml.safe_dump(raw, sort_keys=False, allow_unicode=True), encoding="utf-8")
```

- [ ] **Step 2: API 接入**

在 `server/app.py` 中添加：

- `GET /api/profiles/{name}/skills`
- `PUT /api/profiles/{name}/skills/toggle`

返回结构包含：`name/path/enabled`，并在响应里带一个字段提示“toggle 会重写 config.yaml（可能丢注释）”。

---

### Task 8: 最小 UI（列表页 + 详情页）

**Files:**
- Create: `server/templates/index.html`
- Create: `server/templates/profile.html`
- Create: `server/static/app.js`
- Modify: `server/app.py`

- [ ] **Step 1: 接入 Jinja2Templates（FastAPI）**

- `GET /`：渲染 profiles 列表
- `GET /profiles/{name}`：渲染 profile 页面

- [ ] **Step 2: index.html（按钮调用 API）**

页面最小需求：
- Profiles 表格
- Dashboard start/stop
- Gateway start/stop
- 进入详情链接

- [ ] **Step 3: profile.html（Env/Config/Skills）**

页面最小需求：
- Env：key/value 表单 + 保存/删除
- Config Raw：textarea + 保存
- Skills：列表 + toggle

- [ ] **Step 4: 手动验证**

Expected:
- 浏览器打开 `http://127.0.0.1:8088/` 可以操作

---

## 自检清单（执行前）

- `data/config.yaml` 支持配置 `hermes_root`
- profile 扫描基于 `<root>/profiles`
- dashboard/gateway 默认只绑定 127.0.0.1
- `.env` 更新不破坏注释与顺序
- config raw 保存前做 YAML mapping 校验

## 执行说明

计划完成并保存到 `docs/superpowers/plans/2026-05-18-hermes-instance-manager-plan.md`。

两个执行选项：

1. Subagent-Driven（推荐）— 我按 Task 拆分逐个实现并在每个 Task 后复核
2. Inline Execution — 在当前会话里按 Task 顺序实现并随时可中断调整

你选哪个？

