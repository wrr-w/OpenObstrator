# Template & Instance Roots Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add per-runtime template management and enforce strict instance discovery under per-runtime 2-level instance directories; new instances are created by copying the runtime template root.

**Architecture:** Keep runtime roots configurable in `data/config.yaml`. Treat each runtime root as a template directory. Only discover runnable instances from a dedicated child container (`profiles/` for Hermes, `instances/` for NanoGhost). Add template APIs and a UI “模板管理” modal to edit templates.

**Tech Stack:** FastAPI, Pydantic, Jinja2 templates, vanilla JS, PyYAML, stdlib `pathlib` + `shutil`.

---

## File Map

**Modify**
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/profiles.py` — Hermes instance discovery (no root-as-default).
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/profile_create.py` — Hermes creation clones from template root but writes under `profiles/<name>` (already mostly correct; adjust copy exclusions).
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/app.py` — path resolution changes, NanoGhost instance layout, template APIs.
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/templates/index.html` — add “模板管理” button.
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/app.js` — add template modal and template API calls.
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/tests/test_skills.py` — update for no `default` profile; add template endpoint tests.
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/tests/test_profile_create.py` — update for new discovery semantics and clone exclusions.

**Create (optional, recommended for clarity)**
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/template_copy.py` — safe template clone helper.
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/tests/test_templates.py` — focused tests for `/api/templates/*`.

---

### Task 1: Enforce Strict Hermes Instance Discovery (Only `profiles/*`)

**Files:**
- Modify: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/profiles.py`
- Modify: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/app.py`
- Test: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/tests/test_profile_create.py`

- [ ] **Step 1: Update `list_profiles()` to only scan `profiles/*`**

Edit `server/profiles.py` to remove the implicit “default=root” entry:

```python
def list_profiles(hermes_root: Path) -> list[ProfileInfo]:
    result: list[ProfileInfo] = []

    profiles_root = hermes_root / "profiles"
    if profiles_root.is_dir():
        for entry in sorted(profiles_root.iterdir()):
            if entry.is_dir() and not entry.name.startswith("."):
                result.append(ProfileInfo(name=entry.name, path=entry, is_default=False))

    return result
```

- [ ] **Step 2: Update Hermes instance path resolution in `server/app.py`**

In `server/app.py`, change all places that do:

```python
profile_dir = hermes_root if name == "default" else hermes_root / "profiles" / name
```

to:

```python
profile_dir = hermes_root / "profiles" / name
```

This affects endpoints:
- `/api/profiles/{name}/env`
- `/api/profiles/{name}/config/raw`
- `/api/profiles/{name}/soul/raw`
- `/api/profiles/{name}/memories/*`
- `/api/profiles/{name}/channels`
- `/api/profiles/{name}/cron`
- `/api/profiles/{name}/logs`
- `/api/profiles/{name}/sessions`
- and any other Hermes “profile_dir” special-casing.

- [ ] **Step 3: Update `/api/instances` Hermes listing to rely on updated `list_profiles()`**

No code change should be required beyond Step 1 if it already calls `list_profiles(hermes_root)`.

- [ ] **Step 4: Update UI delete guard**

In `server/static/app.js`, remove the “不能删除默认实例” guard:

```js
if (_activeRuntime === "hermes" && _activeName === "default") {
  setToast("不能删除默认实例")
  return
}
```

because `default` is no longer a listed instance.

- [ ] **Step 5: Adjust tests that assume `default` exists**

Update tests to create a concrete instance directory under `hermes_root/profiles/<name>` and test against that name.

- [ ] **Step 6: Run tests**

Run: `python -m pytest -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add server/profiles.py server/app.py server/static/app.js tests/
git commit -m "feat: enforce hermes instances under profiles only"
```

---

### Task 2: Implement Template Copy Helper (Exclude Container Dirs)

**Files:**
- Create: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/template_copy.py`
- Modify: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/profile_create.py`
- Modify: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/app.py`
- Test: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/tests/test_profile_create.py`

- [ ] **Step 1: Add `clone_template_dir()` helper**

Create `server/template_copy.py`:

```python
from __future__ import annotations

import shutil
from pathlib import Path


_DEFAULT_EXCLUDES = frozenset(
    {
        ".git",
        ".venv",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
    }
)


def clone_template_dir(*, template_dir: Path, dest_dir: Path, exclude_names: set[str]) -> None:
    if not template_dir.is_dir():
        raise ValueError("template_dir is not a directory")
    if dest_dir.exists():
        raise FileExistsError("dest_dir already exists")

    dest_dir.mkdir(parents=True, exist_ok=False)

    excludes = set(exclude_names) | set(_DEFAULT_EXCLUDES)
    for entry in template_dir.iterdir():
        name = entry.name
        if name in excludes:
            continue
        if name.startswith(".") and name not in (".env",):
            continue

        target = dest_dir / name
        if entry.is_dir():
            shutil.copytree(entry, target, dirs_exist_ok=False)
        elif entry.is_file():
            shutil.copy2(entry, target)
```

- [ ] **Step 2: Use helper for Hermes `create_profile_clone_default()`**

In `server/profile_create.py`, replace the manual “copy list” logic with the helper:

```python
from server.template_copy import clone_template_dir

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
    return profile_dir
```

- [ ] **Step 3: Add/adjust tests for exclusion behavior**

In `tests/test_profile_create.py`, add a test ensuring `profiles/` is not copied into the new instance directory.

Example:

```python
def test_clone_excludes_profiles_dir(tmp_path: Path):
    hermes_root = tmp_path / "hermes"
    (hermes_root / "profiles").mkdir(parents=True)
    (hermes_root / "SOUL.md").write_text("x", encoding="utf-8")

    created = create_profile_clone_default(hermes_root=hermes_root, name="alpha")
    assert created == hermes_root / "profiles" / "alpha"
    assert (created / "SOUL.md").exists()
    assert not (created / "profiles").exists()
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add server/template_copy.py server/profile_create.py tests/test_profile_create.py
git commit -m "feat: clone instances from template with excludes"
```

---

### Task 3: Move NanoGhost Instances Under `instances/<name>` and Create by Cloning Template Root

**Files:**
- Modify: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/app.py`
- Test: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/tests/test_profile_create.py` (or new `tests/test_nanoghost_layout.py`)

- [ ] **Step 1: Change NanoGhost instance dir resolver**

In `server/app.py`:

```python
def _nanoghost_instances_root() -> Path:
    root = resolve_nanoghost_root(config_path=CONFIG_PATH)
    return root / "instances"

def _nanoghost_instance_dir(name: str) -> Path:
    return _nanoghost_instances_root() / name
```

Update `_list_nanoghost_instances` to take `instances_root` instead of `root`.

- [ ] **Step 2: Update NanoGhost list endpoints**

Adjust:
- `/api/instances` listing to use `_list_nanoghost_instances(_nanoghost_instances_root())`
- `/api/runtimes/nanoghost/instances` similarly.

- [ ] **Step 3: Update NanoGhost create endpoint to clone template root**

Replace the current “mkdir + copy .env.example” logic in `runtime_instance_create(... nanoghost ...)` with:

```python
from server.template_copy import clone_template_dir

root = resolve_nanoghost_root(config_path=CONFIG_PATH)
instances_root = root / "instances"
inst = instances_root / name
instances_root.mkdir(parents=True, exist_ok=True)
clone_template_dir(
    template_dir=root,
    dest_dir=inst,
    exclude_names={"instances"},
)
```

- [ ] **Step 4: Update all NanoGhost operations to use new instance path**

Update all places that use `root / name` or pass `inst`:
- env read/write
- skills list/toggle
- channels read/write
- gateway start/stop/status
- delete instance

- [ ] **Step 5: Add NanoGhost layout tests**

Add a test that:
- creates `nanoghost_root/.env` and `nanoghost_root/channel_directory.json` as template files
- calls `POST /api/instances` with runtime `nanoghost`
- asserts created instance is `nanoghost_root/instances/<name>`
- asserts `.env` and `channel_directory.json` exist in instance dir after cloning

- [ ] **Step 6: Run tests**

Run: `python -m pytest -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add server/app.py tests/
git commit -m "feat: nanoghost instances live under instances and clone from root template"
```

---

### Task 4: Add Template APIs (`/api/templates/{runtime}/*`)

**Files:**
- Modify: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/app.py`
- Create: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/tests/test_templates.py`

- [ ] **Step 1: Add template path resolver**

In `server/app.py` add:

```python
def _template_root(runtime: str) -> Path:
    runtime = _normalize_runtime(runtime)
    if runtime == "hermes":
        return resolve_hermes_root(config_path=CONFIG_PATH)
    if runtime == "nanoghost":
        return resolve_nanoghost_root(config_path=CONFIG_PATH)
    raise HTTPException(status_code=400, detail="openclaw not implemented")
```

- [ ] **Step 2: Add template env endpoints**

Implement:
- `GET /api/templates/{runtime}/env`
- `PUT /api/templates/{runtime}/env`
- `PUT /api/templates/{runtime}/env/batch`
- `DELETE /api/templates/{runtime}/env`

by reusing `parse_env_keys`, `set_env_kv`, `delete_env_key` with `env_path = _template_root(runtime) / ".env"`.

- [ ] **Step 3: Add template skills endpoints**

Implement:
- `GET /api/templates/{runtime}/skills`
- `PUT /api/templates/{runtime}/skills/batch`

Hermes: `items = list_skills(template_root, platform=platform)` + `set_skill_enabled(template_root, name, enabled)`
NanoGhost: `items = list_skills_nanoghost(template_root, platform=platform, shared_dir=resolve_shared_skills_root(config_path=CONFIG_PATH))` + `set_skill_enabled_nanoghost(template_root, ...)`

- [ ] **Step 4: Add template channels endpoints**

Implement:
- `GET /api/templates/hermes/channels` and `PUT /api/templates/hermes/channels`
  - use `channel_directory.json` under Hermes template root
  - reuse the same JSON schema as `/api/profiles/{name}/channels`
- `GET /api/templates/nanoghost/channels` and `PUT /api/templates/nanoghost/channels`
  - operate on template root `channel_directory.json`
  - reuse the same schema as NanoGhost instance channels endpoints

- [ ] **Step 5: Add template config/raw endpoints**

Implement:
- `GET /api/templates/hermes/config/raw` + `PUT ...` (operate on `template_root/config.yaml`)
- `GET /api/templates/nanoghost/config/raw` + `PUT ...` (operate on `template_root/config.yaml`)

- [ ] **Step 6: Write tests**

Create `tests/test_templates.py`:

```python
from pathlib import Path
from fastapi.testclient import TestClient
import server.app as app_mod


def test_template_env_roundtrip(tmp_path: Path, monkeypatch):
    hermes_root = tmp_path / "hermes"
    hermes_root.mkdir()
    cfg = tmp_path / "manager.yaml"
    cfg.write_text(f'hermes_root: "{str(hermes_root).replace("\\\\", "\\\\\\\\")}"\\n', encoding="utf-8")
    monkeypatch.setattr(app_mod, "CONFIG_PATH", cfg)

    c = TestClient(app_mod.app)
    r = c.get("/api/templates/hermes/env")
    assert r.status_code == 200

    r2 = c.put("/api/templates/hermes/env", json={"key": "FOO", "value": "bar"})
    assert r2.status_code == 200
    r3 = c.get("/api/templates/hermes/env")
    assert r3.status_code == 200
    keys = {it["key"]: it["value"] for it in r3.json()["items"]}
    assert keys["FOO"] == "bar"
```

Add similar tests for NanoGhost channels/skills if needed.

- [ ] **Step 7: Run tests**

Run: `python -m pytest -q`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add server/app.py tests/test_templates.py
git commit -m "feat: add template management APIs"
```

---

### Task 5: Add UI “模板管理” Modal (Top Button)

**Files:**
- Modify: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/templates/index.html`
- Modify: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/app.js`

- [ ] **Step 1: Add button to top actions**

In `server/templates/index.html`, add:

```html
<button id="templateMgr" class="primary">模板管理</button>
```

next to `managerCfg`.

- [ ] **Step 2: Add template modal**

In `server/static/app.js`, implement `openTemplateManagerModal()` similar to `openManagerConfigModal`, with:
- runtime `<select>` (Hermes / NanoGhost)
- tabs (Env / Skills / Channels / Config)
- minimal UI reuse: copy the same table rendering patterns used in the main page (`refreshEnv`, `refreshSkills`, `refreshChannels`) but parameterize the API base to `/api/templates/{runtime}`.

Recommended approach:
- Introduce a small helper:

```js
function tplUrl(rt, path) {
  return `/api/templates/${encodeURIComponent(rt)}${path}`
}
```

- Add API wrappers:
  - `templateEnvGet(rt)`, `templateEnvBatchPut(rt, items)` etc.
  - `templateSkillsGet(rt)`, `templateSkillsBatchPut(rt, items)`
  - `templateChannelsGet(rt)`, `templateChannelsPut(rt, config)`
  - `templateConfigGet(rt)`, `templateConfigPut(rt, raw)`

- [ ] **Step 3: Wire button**

In `bindActions()`:

```js
const templateMgr = document.getElementById("templateMgr")
if (templateMgr)
  templateMgr.addEventListener("click", async () => {
    try {
      setToast("")
      await openTemplateManagerModal()
    } catch (e) {
      setToast(String(e))
    }
  })
```

- [ ] **Step 4: Run manual smoke**

Run server and verify:
- Open Template Manager modal.
- Edit Hermes template `.env` and save.
- Create a new Hermes instance and confirm the new instance contains the updated `.env` entry.
- Repeat for NanoGhost template + instance.

- [ ] **Step 5: Commit**

```bash
git add server/templates/index.html server/static/app.js
git commit -m "feat: add template manager UI"
```

---

### Task 6: Full Regression

**Files:**
- Modify: any failing tests

- [ ] **Step 1: Run full test suite**

Run: `python -m pytest -q`
Expected: PASS

- [ ] **Step 2: Run format/lint if repo has it**

If present in repo docs, run the standard checks; otherwise skip.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore: align instances layout with template roots"
```

---

## Self-Review Checklist (Plan Quality)

- Spec coverage:
  - Template root not listed as instance ✅
  - Strict discovery under `profiles/*` and `instances/*` ✅
  - New instances clone template root excluding container dir ✅
  - Template UI entry “模板管理” ✅
  - Template APIs for env/skills/channels/config ✅
- Placeholder scan: no “TODO/TBD” ✅
- Type/name consistency:
  - Hermes uses `profiles/`, NanoGhost uses `instances/` ✅

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-20-template-and-instance-roots-implementation-plan.md`. Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks
2. **Inline Execution** — execute tasks in this session with checkpoints

Which approach?

