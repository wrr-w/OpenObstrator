# Top Bar Separate Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在主页面添加全局顶部 bar；除“刷新”外（模板管理/管理台配置/日志管理）均打开新标签页独立 URL 页面；主页面右侧顶部按钮区移除“删除实例/配置/模板”等入口。

**Architecture:** 复用现有 FastAPI + Jinja2；新增 3 个页面路由返回独立模板（共享基础样式与脚本基础能力）。前端将原本的弹窗逻辑拆成可复用的页面渲染函数（或新建 page 级 JS 文件）以避免重复；顶部 bar 按钮使用 `window.open('/pages/...', '_blank')`。

**Tech Stack:** FastAPI, Jinja2, vanilla JS.

---

## File Map

**Modify**
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/app.py`
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/templates/index.html`
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/app.js`

**Create**
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/templates/page_base.html`
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/templates/pages/templates.html`
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/templates/pages/manager_config.html`
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/templates/pages/logs.html`
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/pages/templates.js`
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/pages/manager_config.js`
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/pages/logs.js`

---

### Task 1: 后端新增 3 个页面路由

**Files:**
- Modify: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/app.py`
- Create: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/templates/page_base.html`
- Create: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/templates/pages/*.html`

- [ ] **Step 1: 创建 page_base.html**

`server/templates/page_base.html` 提供基础 `<head>`、基础样式（复用 index.html 的 CSS 片段）、以及一个可插入主体内容与脚本的 block。

- [ ] **Step 2: 创建三个页面模板**

- `/pages/templates` → `templates/pages/templates.html`
- `/pages/manager-config` → `templates/pages/manager_config.html`
- `/pages/logs` → `templates/pages/logs.html`

每个页面：
- 顶部显示一个轻量 title（如“模板管理”）
- 主体区域为页面专用容器（div id）
- 引入页面专用 JS（`/static/pages/...js`）

- [ ] **Step 3: 在 FastAPI 添加路由**

在 `server/app.py` 添加：

```python
@app.get("/pages/templates", response_class=HTMLResponse)
def page_templates(request: Request):
    return templates.TemplateResponse("pages/templates.html", {"request": request})
```

同理增加 `/pages/manager-config` 与 `/pages/logs`。

- [ ] **Step 4: 冒烟**

启动服务后访问三条 URL 确认能返回 HTML。

- [ ] **Step 5: 跑 pytest**

Run: `python -m pytest -q`
Expected: PASS

---

### Task 2: 主页面增加顶部 bar，并移除右侧按钮区入口

**Files:**
- Modify: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/templates/index.html`
- Modify: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/app.js`

- [ ] **Step 1: index.html 添加 top bar DOM**

在 `<body>` 的 `.app` 外层或 `.main` 之上增加顶部 bar：
- 左侧：产品标题
- 右侧按钮：刷新 / 模板管理 / 管理台配置 / 日志管理

并移除现有右侧 topActions 中的按钮（包括 deleteProfile）。

- [ ] **Step 2: app.js 绑定 top bar 按钮行为**

- 刷新：复用现有 `refreshAll` 行为（或者调用同一函数）
- 其它三个按钮：

```js
window.open("/pages/templates", "_blank")
```

等。

- [ ] **Step 3: 删除实例入口只保留在“…”菜单**

确认 `deleteProfile` 按钮已移除，且删除仍可通过“…”菜单触发。

- [ ] **Step 4: 跑 pytest**

Run: `python -m pytest -q`
Expected: PASS

---

### Task 3: 模板管理页面实现（复用现有 template API）

**Files:**
- Create: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/pages/templates.js`
- Modify: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/app.js`（抽公共 API/工具函数到可复用区域，或复制极少量逻辑）

- [ ] **Step 1: 页面 JS 基础工具**

`templates.js` 内实现：
- `apiJson`（可从 app.js 复制）
- `templatesList(runtime)`
- `templateManifest(runtime, template_id)` 等（与现有一致）

- [ ] **Step 2: 页面 UI**

在页面中渲染：
- runtime 下拉
- template 下拉（root + tpl:*）
- tabs（按 manifest.tabs）
- env/skills/channels/config 编辑区（逻辑可复用 app.js 中 template manager 的实现，允许复制）

- [ ] **Step 3: 冒烟**

手动：
- 切 runtime / 切 template
- 修改 env 保存

- [ ] **Step 4: pytest**

Run: `python -m pytest -q`
Expected: PASS

---

### Task 4: 管理台配置页面实现

**Files:**
- Create: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/pages/manager_config.js`

- [ ] **Step 1: 实现读取/保存**

调用：
- `GET /api/manager/config/raw`
- `PUT /api/manager/config/raw`

UI：
- textarea + 保存按钮

- [ ] **Step 2: pytest**

Run: `python -m pytest -q`
Expected: PASS

---

### Task 5: 日志管理页面（管理台 uvicorn 日志）

**Files:**
- Create: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/pages/logs.js`
- Modify: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/app.py`（新增日志接口，或先做占位）

- [ ] **Step 1: 确定数据源**

最小可行：
- 在管理台进程内维护一个 ring buffer（例如最近 N 行日志）
- 提供 `GET /api/manager/logs` 返回列表

若暂时不实现采集：页面先展示提示“需要以 log-capture 模式启动管理台”，并给出启动方式。

- [ ] **Step 2: 页面 UI**

按钮：刷新/复制
区域：pre/textarea 显示日志

- [ ] **Step 3: pytest**

Run: `python -m pytest -q`
Expected: PASS

