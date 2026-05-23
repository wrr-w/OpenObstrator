# Task1 Pages Routes & Templates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 后端新增 `/pages/templates`、`/pages/manager-config`、`/pages/logs` 三个页面路由与对应 Jinja 模板（`page_base.html` + `pages/*.html`），每个页面加载各自 JS 占位文件；pytest 通过；不实现日志接口。

**Architecture:** 复用现有 FastAPI + Jinja2Templates；新增一个基础模板 `page_base.html` 提供通用 `<head>`/基础样式/布局 block；每个页面模板继承基础模板并插入页面内容容器与其专属脚本；新增 3 个静态 JS 占位文件，仅负责在页面上渲染“未实现”文本，保证不报错。

**Tech Stack:** FastAPI, Jinja2, vanilla JS.

---

## File Map

**Modify**
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/app.py`

**Create**
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/templates/page_base.html`
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/templates/pages/templates.html`
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/templates/pages/manager_config.html`
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/templates/pages/logs.html`
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/pages/templates.js`
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/pages/manager_config.js`
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/pages/logs.js`

---

### Task 1: 创建 page_base.html

**Files:**
- Create: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/templates/page_base.html`

- [ ] **Step 1: 新增基础模板结构**

基础模板提供：
- `<html lang="zh-CN">` 与 `<meta charset>`、viewport
- 最小可用的 body 容器布局（header + main）
- `block title`、`block content`、`block scripts` 以便子模板覆写

- [ ] **Step 2: 运行 pytest**

Run: `python -m pytest -q`
Expected: PASS

---

### Task 2: 创建 pages/*.html 三个页面模板

**Files:**
- Create: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/templates/pages/templates.html`
- Create: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/templates/pages/manager_config.html`
- Create: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/templates/pages/logs.html`

- [ ] **Step 1: 页面模板继承 page_base.html**

每个页面模板包含：
- title（例如“模板管理 / 管理台配置 / 日志”）
- 主体容器（例如 `<div id="pageRoot"></div>` 或各自唯一 id）
- scripts block 引入各自的静态 JS 文件：
  - `/static/pages/templates.js`
  - `/static/pages/manager_config.js`
  - `/static/pages/logs.js`

- [ ] **Step 2: 运行 pytest**

Run: `python -m pytest -q`
Expected: PASS

---

### Task 3: 新增 /pages/... 页面路由

**Files:**
- Modify: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/app.py`

- [ ] **Step 1: 添加 3 个 HTMLResponse 路由**

新增：
- `GET /pages/templates` → `templates.TemplateResponse("pages/templates.html", {"request": request})`
- `GET /pages/manager-config` → `templates.TemplateResponse("pages/manager_config.html", {"request": request})`
- `GET /pages/logs` → `templates.TemplateResponse("pages/logs.html", {"request": request})`

- [ ] **Step 2: 运行 pytest**

Run: `python -m pytest -q`
Expected: PASS

---

### Task 4: 创建 static/pages/*.js 占位脚本

**Files:**
- Create: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/pages/templates.js`
- Create: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/pages/manager_config.js`
- Create: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/pages/logs.js`

- [ ] **Step 1: 每个脚本最小可运行**

行为：
- `DOMContentLoaded` 时找到对应页面容器并写入“未实现”（不存在容器则静默返回）
- 不依赖 app.js，不污染全局，不抛异常

- [ ] **Step 2: 运行 pytest**

Run: `python -m pytest -q`
Expected: PASS

