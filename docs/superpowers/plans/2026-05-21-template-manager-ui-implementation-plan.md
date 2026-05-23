# 模板管理 UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在管理台新增“模板管理”按钮与弹窗，在弹窗中可选择 runtime，并按模板 manifest 渲染 tabs，对 env/skills/channels/config 进行编辑并保存到 `/api/templates` 接口。

**Architecture:** 复用现有页面的样式变量与 JS 交互模式（overlay + card 弹窗）。在 `app.js` 中新增 templates API 封装与一套“模板编辑态”的渲染/保存逻辑，避免影响现有实例管理逻辑。

**Tech Stack:** Jinja2 模板（index.html），原生 DOM + fetch（server/static/app.js），FastAPI 后端接口已存在（/api/templates/*）。

---

## Files

- Modify: [index.html](file:///e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/templates/index.html)
- Modify: [app.js](file:///e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/app.js)
- Test: `pytest`

---

### Task 1: 在顶部操作区新增“模板管理”按钮

**Files:**
- Modify: [index.html](file:///e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/templates/index.html#L189-L205)

- [ ] **Step 1: 在 topActions 增加按钮**

在 `#refreshAll` 与 `#managerCfg` 附近插入：

```html
<button id="templateMgr" class="primary">模板管理</button>
```

- [ ] **Step 2: 刷新页面确认按钮样式与现有一致**

---

### Task 2: 为模板管理新增前端 API 封装

**Files:**
- Modify: [app.js](file:///e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/app.js)

- [ ] **Step 1: 添加 templates API 方法（复用 apiJson）**

新增方法（命名与现有 instances 侧保持一致）：

```js
async function templateManifest(runtime) {
  return apiJson(`/api/templates/${encodeURIComponent(runtime)}/manifest`, { method: "GET" })
}

async function templateLoadEnv(runtime) {
  return apiJson(`/api/templates/${encodeURIComponent(runtime)}/env`, { method: "GET" })
}

async function templatePutEnv(runtime, key, value) {
  return apiJson(`/api/templates/${encodeURIComponent(runtime)}/env`, { method: "PUT", body: JSON.stringify({ key, value }) })
}

async function templateBatchPutEnv(runtime, items) {
  return apiJson(`/api/templates/${encodeURIComponent(runtime)}/env/batch`, { method: "PUT", body: JSON.stringify({ items }) })
}

async function templateDeleteEnv(runtime, key) {
  return apiJson(`/api/templates/${encodeURIComponent(runtime)}/env`, { method: "DELETE", body: JSON.stringify({ key }) })
}

async function templateLoadSkills(runtime) {
  return apiJson(`/api/templates/${encodeURIComponent(runtime)}/skills`, { method: "GET" })
}

async function templateSaveSkills(runtime, items) {
  return apiJson(`/api/templates/${encodeURIComponent(runtime)}/skills/batch`, { method: "PUT", body: JSON.stringify({ items }) })
}

async function templateChannelsGet(runtime) {
  return apiJson(`/api/templates/${encodeURIComponent(runtime)}/channels`, { method: "GET" })
}

async function templateChannelsPut(runtime, config) {
  return apiJson(`/api/templates/${encodeURIComponent(runtime)}/channels`, { method: "PUT", body: JSON.stringify({ config }) })
}

async function templateConfigGet(runtime) {
  return apiJson(`/api/templates/${encodeURIComponent(runtime)}/config/raw`, { method: "GET" })
}

async function templateConfigPut(runtime, raw) {
  return apiJson(`/api/templates/${encodeURIComponent(runtime)}/config/raw`, { method: "PUT", body: JSON.stringify({ raw }) })
}
```

---

### Task 3: 实现模板管理弹窗（runtime 选择 + manifest tabs）

**Files:**
- Modify: [app.js](file:///e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/app.js)

- [ ] **Step 1: 实现 openTemplateMgrModal()（overlay + card 复用现有样式）**

弹窗结构（全部通过 DOM 创建）：
- 标题：模板管理（模板根目录编辑）
- runtime 选择：下拉（`hermes` / `nanoghost` / `openclaw`，其中 openclaw 允许展示但保存时会收到后端 400）
- tabs：根据 `/api/templates/{runtime}/manifest` 的 `tabs` 渲染按钮，并只显示允许的面板
- 面板：`env` / `skills` / `channels` / `config`
- 底部按钮：关闭

- [ ] **Step 2: runtime 切换时刷新 manifest + 当前 tab 内容**

行为：
- 选择 runtime => `templateManifest(runtime)` => 根据 `tabs` 显示/隐藏 tabBtn 与 panel
- 默认激活第一个可见 tab（优先 env）
- 每次切换 runtime 时清空 toast，并刷新当前 tab 的数据

- [ ] **Step 3: 在 bindActions() 绑定 #templateMgr 点击打开弹窗**

点击后：
- 打开弹窗
- 在弹窗内部完成 runtime 选择与编辑保存

---

### Task 4: 在弹窗内实现 env 编辑与保存（/api/templates/*）

**Files:**
- Modify: [app.js](file:///e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/app.js)

- [ ] **Step 1: 复用现有 env 表格交互模式**

UI：
- 新增 KEY/VALUE + 新增按钮
- 列表行：key + value input + 删除按钮
- 确认保存按钮：批量保存变化（对比 dataset.orig）

API：
- GET: `templateLoadEnv`
- 新增/单个写入：`templatePutEnv`
- 批量保存：`templateBatchPutEnv`
- 删除：`templateDeleteEnv`

---

### Task 5: 在弹窗内实现 skills 编辑与保存（/api/templates/*）

**Files:**
- Modify: [app.js](file:///e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/app.js)

- [ ] **Step 1: 复用现有 skills 分组渲染**

行为与现有实例 skills 一致：
- 按 `source/category` 分组
- 分组可折叠
- 组内 checkbox 切换 enabled
- 顶部过滤框过滤 name/desc
- 确认保存：收集 `.skillCb` => `templateSaveSkills(runtime, items)`

---

### Task 6: 在弹窗内实现 channels 编辑与保存（/api/templates/*）

**Files:**
- Modify: [app.js](file:///e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/app.js)

- [ ] **Step 1: nanoghost channels：复用现有 checkbox 表格**

依据 `templateChannelsGet(runtime)` 返回体包含 `config` 时走该模式：
- 渲染 `config.channels` 的 checkbox
- 保存时回写 `config.channels[k].enabled`，调用 `templateChannelsPut(runtime, nextConfig)`

- [ ] **Step 2: hermes channels：提供 JSON raw 编辑**

依据返回体包含 `platforms` 时走该模式：
- textarea 初始值为 `JSON.stringify({ updated_at, platforms }, null, 2)`
- 保存：`JSON.parse` 校验为 object，调用 `templateChannelsPut(runtime, parsed)`

---

### Task 7: 在弹窗内实现 config(raw) 编辑与保存（/api/templates/*）

**Files:**
- Modify: [app.js](file:///e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/app.js)

- [ ] **Step 1: 渲染 config.yaml raw textarea + 保存按钮**

行为：
- GET: `templateConfigGet(runtime)` => 填入 textarea
- PUT: `templateConfigPut(runtime, raw)`

---

### Task 8: 回归测试

**Files:**
- Test: `tests/`

- [ ] **Step 1: 运行全部 pytest**

Run:

```bash
pytest -q
```

Expected:
- Exit code 0

