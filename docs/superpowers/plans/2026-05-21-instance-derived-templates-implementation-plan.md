# Instance-Derived Templates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 支持从实例导出命名模板（`<root>/templates/<tpl>`），创建实例时可选模板（默认 root 模板），并在左侧实例列表提供“…”菜单（删除/设为模板/编辑模板/重命名）。

**Architecture:** 后端在每个 runtime root 下新增 `templates/` 目录作为命名模板容器；模板通过 `template_id` 标识（`root` 或 `tpl:<name>`）。现有 `/api/templates/{runtime}/*` 统一支持 `template_id` 查询参数。创建实例的 `/api/instances` 增加 `template_id`，实例创建与导出模板都复用模板复制 helper 并排除容器目录。前端在实例列表行内新增“…”菜单和创建弹窗模板下拉；模板管理弹窗增加模板选择。

**Tech Stack:** FastAPI, Pydantic, PyYAML, stdlib pathlib/shutil, vanilla JS.

---

## File Map

**Modify**
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/app.py`
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/template_copy.py`
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/app.js`
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/templates/index.html`

**Create**
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/tests/test_templates_list.py`
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/tests/test_instance_export_template.py`
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/tests/test_instance_rename.py`
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/tests/test_instance_create_with_template.py`

---

### Task 1: 后端模板路径解析与模板列表接口

**Files:**
- Modify: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/app.py`
- Create: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/tests/test_templates_list.py`

- [ ] **Step 1: 定义 template_id 解析与模板目录定位**

在 `server/app.py` 增加：

```python
def _template_dir(runtime: str, template_id: str | None) -> Path:
    runtime = _normalize_runtime(runtime)
    root = _template_root(runtime)
    tid = (template_id or "root").strip()
    if tid == "root":
        return root
    if tid.startswith("tpl:"):
        name = tid[4:]
        _require_valid_instance_name(name)
        return root / "templates" / name
    raise HTTPException(status_code=400, detail="invalid template_id")
```

- [ ] **Step 2: 新增模板列表接口**

在 `server/app.py` 增加：

`GET /api/templates/{runtime}/list`

返回 `root` + `<root>/templates/*` 目录。

- [ ] **Step 3: 写失败测试（先写）**

`tests/test_templates_list.py`：

```python
from pathlib import Path
from fastapi.testclient import TestClient
import server.app as app_mod


def test_templates_list_includes_root_and_named_templates(tmp_path: Path, monkeypatch):
    hermes_root = tmp_path / "hermes"
    (hermes_root / "templates" / "t1").mkdir(parents=True)
    (hermes_root / "templates" / "t1" / ".env").write_text("A=B\n", encoding="utf-8")

    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(f'hermes_root: "{str(hermes_root).replace("\\\\", "\\\\\\\\")}"\n', encoding="utf-8")
    monkeypatch.setattr(app_mod, "CONFIG_PATH", cfg)

    c = TestClient(app_mod.app)
    r = c.get("/api/templates/hermes/list")
    assert r.status_code == 200
    items = r.json()["items"]
    ids = [it["id"] for it in items]
    assert "root" in ids
    assert "tpl:t1" in ids
```

- [ ] **Step 4: 跑测试确认失败**

Run: `python -m pytest -q tests/test_templates_list.py -q`
Expected: FAIL（接口不存在/或逻辑未实现）

- [ ] **Step 5: 实现最小代码使其通过**

- [ ] **Step 6: 跑全量测试**

Run: `python -m pytest -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add server/app.py tests/test_templates_list.py
git commit -m "feat: list runtime templates"
```

---

### Task 2: 模板接口支持 template_id（root 与 tpl:<name>）

**Files:**
- Modify: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/app.py`
- Modify: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/tests/test_templates.py`

- [ ] **Step 1: 扩展模板接口签名**

为以下接口增加 `template_id: str | None = None` 参数，并将 `root = _require_template_root(runtime)` 改为：

```python
tpl = _template_dir(runtime, template_id)
if not tpl.exists() or not tpl.is_dir():
    raise HTTPException(status_code=404, detail="template not found")
```

覆盖：
- `/api/templates/{runtime}/manifest`
- `/api/templates/{runtime}/env` + batch + delete
- `/api/templates/{runtime}/skills` + batch
- `/api/templates/{runtime}/channels`
- `/api/templates/{runtime}/config/raw`

- [ ] **Step 2: 增加测试覆盖 template_id=tpl:<name>**

在 `tests/test_templates.py` 增加：
- 创建 `templates/t1/.env`
- 调用 `PUT /api/templates/{runtime}/env?template_id=tpl:t1` 写入一个键
- 再 `GET` 确认读取到

- [ ] **Step 3: 跑全量测试**

Run: `python -m pytest -q`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add server/app.py tests/test_templates.py
git commit -m "feat: support template_id for template endpoints"
```

---

### Task 3: 创建实例支持 template_id（默认 root）

**Files:**
- Modify: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/app.py`
- Create: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/tests/test_instance_create_with_template.py`

- [ ] **Step 1: 扩展创建实例 body**

在 `server/app.py`：

```python
class InstanceCreateBody(BaseModel):
    runtime: str
    name: str
    template_id: str | None = None
```

并在 `instance_create()` 透传 `template_id` 给 `runtime_instance_create()`（需要扩展 `RuntimeInstanceCreateBody` 同样字段）。

- [ ] **Step 2: 修改 Hermes/NanoGhost 创建逻辑使用选定模板**

Hermes：模板源 `tpl_dir = _template_dir("hermes", template_id)`，目标仍为 `hermes_root/profiles/<name>`；调用 `clone_template_dir(... exclude_names={"profiles","templates"})`。

NanoGhost：模板源 `tpl_dir = _template_dir("nanoghost", template_id)`，目标仍为 `nanoghost_root/instances/<name>`；调用 `clone_template_dir(... exclude_names={"instances","templates"})`。

- [ ] **Step 3: 新增测试：使用命名模板创建**

`tests/test_instance_create_with_template.py`：

```python
from pathlib import Path
from fastapi.testclient import TestClient
import server.app as app_mod


def test_create_instance_from_named_template_nanoghost(tmp_path: Path, monkeypatch):
    root = tmp_path / "ng"
    (root / "templates" / "t1").mkdir(parents=True)
    (root / "templates" / "t1" / ".env").write_text("A=B\n", encoding="utf-8")
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(f'nanoghost_root: "{str(root).replace("\\\\", "\\\\\\\\")}"\n', encoding="utf-8")
    monkeypatch.setattr(app_mod, "CONFIG_PATH", cfg)

    c = TestClient(app_mod.app)
    r = c.post("/api/instances", json={"runtime": "nanoghost", "name": "n1", "template_id": "tpl:t1"})
    assert r.status_code == 200
    assert (root / "instances" / "n1" / ".env").read_text(encoding="utf-8") == "A=B\n"
```

- [ ] **Step 4: 跑全量测试**

Run: `python -m pytest -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add server/app.py tests/test_instance_create_with_template.py
git commit -m "feat: create instances from selected template"
```

---

### Task 4: 导出实例为模板

**Files:**
- Modify: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/app.py`
- Create: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/tests/test_instance_export_template.py`

- [ ] **Step 1: 新增 Pydantic body**

```python
class ExportTemplateBody(BaseModel):
    template_name: str
    overwrite: bool = False
```

- [ ] **Step 2: 新增接口**

`POST /api/instances/{runtime}/{name}/export-template`

逻辑：
- 找到实例目录 `inst = _instance_path(runtime, name)`，不存在 404
- `tpl_dir = _template_root(runtime) / "templates" / template_name`
- 若 `tpl_dir` 存在且 `overwrite` 为 False -> 409
- 若 `overwrite` True：先删除旧 `tpl_dir` 再复制
- 复制策略：
  - Hermes exclude：`{"profiles","templates"}`
  - NanoGhost exclude：`{"instances","templates"}`
  - 调用 `clone_template_dir(template_dir=inst, dest_dir=tpl_dir, exclude_names=...)`

- [ ] **Step 3: 写测试**

`tests/test_instance_export_template.py`：
- 构造一个 nanoghost 实例目录 `instances/n1` 并写入 `X.txt`
- 调用 export-template 导出为 `templates/t1`
- 断言 `templates/t1/X.txt` 存在
- 再次导出同名且 overwrite=false 返回 409

- [ ] **Step 4: 跑全量测试**

Run: `python -m pytest -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add server/app.py tests/test_instance_export_template.py
git commit -m "feat: export instance as named template"
```

---

### Task 5: 重命名实例（并迁移 registry 记录）

**Files:**
- Modify: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/app.py`
- Create: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/tests/test_instance_rename.py`

- [ ] **Step 1: 新增 Pydantic body**

```python
class InstanceRenameBody(BaseModel):
    new_name: str
```

- [ ] **Step 2: 新增接口**

`POST /api/instances/{runtime}/{name}/rename`

规则：
- 校验新名字 `_require_valid_instance_name(new_name)`
- 目录存在性：old 必须存在，new 必须不存在
- 运行检查：
  - Hermes：dashboard/gateway 任一 pid 运行则拒绝 409
  - NanoGhost：gateway pid 运行则拒绝 409
- 执行 `old_dir.replace(new_dir)`
- registry 迁移：
  - `recs = reg["runtimes"][runtime]["instances"]`
  - `recs[new_name] = recs.pop(old_name, {})`

- [ ] **Step 3: 写测试**

`tests/test_instance_rename.py`：
- 创建 nanoghost `instances/a1` 目录
- 预置 registry：写入 `runtimes.nanoghost.instances.a1.gateway.pid = None`
- 调用 rename -> 200
- 断言目录变为 `instances/a2`
- 断言 registry key 迁移到 `a2`

- [ ] **Step 4: 跑全量测试**

Run: `python -m pytest -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add server/app.py tests/test_instance_rename.py
git commit -m "feat: rename instance and migrate registry records"
```

---

### Task 6: 前端 - 创建实例支持模板选择

**Files:**
- Modify: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/app.js`

- [ ] **Step 1: 增加模板列表 API**

在 `app.js` 增加：
- `templatesList(runtime)` -> `GET /api/templates/{runtime}/list`

- [ ] **Step 2: 扩展创建弹窗**

修改 `openCreateModal()`：
- 增加模板 `<select>`（同 runtime）
- runtime 改变时刷新模板列表并默认选 `root`
- `close({ runtime, name, template_id })`

同时修改 `createInstance(runtime, name)` -> `createInstance(runtime, name, template_id)` 并在 body 里携带。

- [ ] **Step 3: 手工冒烟**

在 UI 中：
- 先通过“设为模板”导出一个 `tpl:t1`
- 再“新增实例”选择模板 `tpl:t1` 创建，确认新实例继承模板 `.env` 或 marker 文件

---

### Task 7: 前端 - 实例列表“…”菜单（删除/设为模板/编辑模板/重命名）

**Files:**
- Modify: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/app.js`

- [ ] **Step 1: 在 renderInstanceList 行内添加按钮与浮层菜单**

每行右侧增加 “…” 按钮（不影响点击选中实例）。

- [ ] **Step 2: 实现 4 个动作的前端调用**

新增 API wrapper：
- `exportTemplate(runtime, name, template_name, overwrite)`
- `renameInstance(runtime, name, new_name)`

行为：
- 删除实例：复用现有 delete 流程
- 设为模板：弹窗输入模板名（默认实例名），调用 export-template；成功后刷新模板列表缓存（如有）
- 编辑模板：打开模板管理弹窗，并预选 runtime + `template_id=tpl:<name>`
- 重命名：弹窗输入新名，调用 rename；成功后刷新实例列表并选中新名实例

---

### Task 8: 前端 - 模板管理支持选择命名模板

**Files:**
- Modify: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/app.js`

- [ ] **Step 1: 模板管理弹窗增加模板选择**

在模板管理弹窗顶部新增模板 `<select>`：
- 选项来自 `/api/templates/{runtime}/list`
- 显示 `root` + `tpl:<name>`（UI 显示为 `root` / `<name>`）

- [ ] **Step 2: 所有模板 API 调用带上 template_id**

将模板管理弹窗内部调用：
- `templateLoadEnv/SaveEnv/...`
- `templateLoadSkills/...`
- `templateChannelsGet/Put`
- `templateConfigGet/Put`

改为附加 `?template_id=...`。

---

### Task 9: 全量回归

**Files:**
- Modify: any failing tests

- [ ] **Step 1: 跑全量测试**

Run: `python -m pytest -q`
Expected: PASS

- [ ] **Step 2: 手工冒烟**

确认：
- 实例列表 “…” 可用
- 设为模板 → 模板管理可编辑
- 创建实例可选模板且继承内容

