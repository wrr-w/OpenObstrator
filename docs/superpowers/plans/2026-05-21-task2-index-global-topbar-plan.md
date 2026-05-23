# Task2 Index Global Topbar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 主页面 `index.html` 增加顶部全局 bar（刷新/模板管理/管理台配置/日志管理），移除主页面实例信息区右侧 `topActions` 按钮区（含删除实例按钮），并更新 `app.js` 绑定；pytest 通过。

**Architecture:** 仅调整主页面 DOM 与事件绑定；“刷新”不 reload 页面，复用现有 `refreshAll` 的数据刷新逻辑；其余入口统一 `window.open('/pages/*', '_blank')` 打开独立页面。

**Tech Stack:** Jinja2 templates, vanilla JS.

---

## File Map

**Modify**
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/templates/index.html`
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/app.js`

---

### Task 1: index.html 增加顶部全局 bar，并移除 topActions 按钮区

**Files:**
- Modify: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/templates/index.html`

- [ ] **Step 1: 新增全局 bar DOM**
  - 在 `<body>` 内 `.app` 之前新增一个全局 bar（例如 `header` 或 `div`）。
  - 左侧：标题 “智能体 管理台”
  - 右侧按钮（建议 id）：
    - `globalRefresh`
    - `globalTemplates`
    - `globalManagerConfig`
    - `globalLogs`

- [ ] **Step 2: 移除实例信息 topbar 内的 topActions 按钮区**
  - 删除原 `.topActions` 及其内部按钮（`refreshAll / managerCfg / templateMgr / deleteProfile`）。
  - 保留实例信息区左侧（实例名、path 等）。

---

### Task 2: app.js 绑定顶部全局 bar 按钮行为

**Files:**
- Modify: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/app.js`

- [ ] **Step 1: 抽取 refreshAll 现有点击逻辑为可复用函数**
  - 现有 `refreshAll` click handler 中的逻辑抽成 `async function refreshAllFlow()`（或等效命名）。
  - `refreshAllFlow()` 内执行：刷新侧边栏、服务状态、env、skills、channels（可选）、hermes extras（可选）。

- [ ] **Step 2: 绑定全局 bar 的刷新按钮**
  - `globalRefresh` 点击时调用 `refreshAllFlow()`。

- [ ] **Step 3: 绑定全局 bar 的三个“新标签页入口”按钮**
  - `globalTemplates` → `window.open("/pages/templates", "_blank")`
  - `globalManagerConfig` → `window.open("/pages/manager-config", "_blank")`
  - `globalLogs` → `window.open("/pages/logs", "_blank")`

- [ ] **Step 4: 删除/清理已移除元素的绑定代码**
  - 移除对 `managerCfg / templateMgr / deleteProfile` 的绑定变量与事件处理（或保留判空但不再使用）。

---

### Task 3: 运行测试

**Files:**
- Test: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/tests/*`

- [ ] **Step 1: 运行 pytest**

Run: `python -m pytest -q`  
Expected: PASS

