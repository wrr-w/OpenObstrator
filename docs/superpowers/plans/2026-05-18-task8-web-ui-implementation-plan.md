# Task8 Web UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (recommended) or implement inline. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为现有 FastAPI 管理接口增加基于 Jinja2Templates 的网页入口（首页 + Profile 详情页），并通过静态 JS 调用现有 /api/* 完成 profiles 列表、dashboard/gateway 启停、Env/Config/Skills 基本操作。

**Architecture:** FastAPI 挂载 `StaticFiles` 提供 `/static/*`，使用 `Jinja2Templates` 渲染 `index.html` 与 `profile.html`。页面本身不新增业务 API，仅通过 `fetch` 调用已有 API，做到低侵入且不影响现有 pytest 覆盖面。

**Tech Stack:** FastAPI, Starlette StaticFiles, Jinja2, 原生浏览器 Fetch API

---

### Task 1: 页面资源与路由挂载

**Files:**
- Create: `server/templates/index.html`
- Create: `server/templates/profile.html`
- Create: `server/static/app.js`
- Modify: `server/app.py`
- Test: `pytest -q`

- [ ] **Step 1: 新增模板与静态目录文件**

- [ ] **Step 2: 修改 `server/app.py`**
  - 初始化 `Jinja2Templates(directory=...)`
  - `app.mount("/static", StaticFiles(...), name="static")`
  - 新增页面路由：
    - `GET /` → `index.html`
    - `GET /profiles/{name}` → `profile.html`

- [ ] **Step 3: 页面 JS 对接已有 API**
  - 首页：加载 profiles 列表、展示 dashboard/gateway 状态、支持启停
  - Profile：加载 Env/Config/Skills、支持写入/删除/保存与 toggle、支持 dashboard/gateway 启停

- [ ] **Step 4: 运行测试**

Run: `pytest -q`  
Expected: PASS

