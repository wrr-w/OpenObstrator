# Task6 - 创建实例弹窗模板下拉 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 前端“新增实例”弹窗增加“模板”下拉（随 runtime 切换）；创建实例时 `POST /api/instances` body 带 `template_id`（默认 `root`）；并回归 `pytest` 全绿。

**Architecture:** 在现有原生 DOM 弹窗（`openCreateModal()`）基础上增加一个模板 `<select>`，runtime 切换时拉取 `GET /api/templates/{runtime}/list` 并刷新选项；`createInstance()` 扩展参数并透传到后端。

**Tech Stack:** Jinja2 模板（index.html 不改），原生 DOM + fetch（server/static/app.js），pytest。

---

## Files

- Modify: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/app.js`
- Test: `python -m pytest -q`

---

### Task 1: 增加模板列表 API 封装（GET /api/templates/{runtime}/list）

**Files:**
- Modify: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/app.js`

- [ ] **Step 1: 新增 templatesList(runtime)**

在 `app.js` 现有 templates API 封装附近新增：

```js
async function templatesList(runtime) {
  return apiJson(`/api/templates/${encodeURIComponent(runtime)}/list`, { method: "GET" })
}
```

- [ ] **Step 2: 手工快速验证（可选）**

打开页面后在控制台执行：
- `templatesList("hermes")`

Expected:
- 返回体包含 `items`，其中 `id` 至少包含 `root`

---

### Task 2: 创建实例 API 透传 template_id（默认 root）

**Files:**
- Modify: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/app.js`

- [ ] **Step 1: 扩展 createInstance() 签名与 body**

将：

```js
async function createInstance(runtime, name) {
  return apiJson("/api/instances", { method: "POST", body: JSON.stringify({ runtime, name }) })
}
```

改为：

```js
async function createInstance(runtime, name, template_id) {
  return apiJson("/api/instances", {
    method: "POST",
    body: JSON.stringify({ runtime, name, template_id: (template_id || "root").trim() || "root" }),
  })
}
```

---

### Task 3: “新增实例”弹窗增加模板下拉（方案 C 展示）

**Files:**
- Modify: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/app.js`

- [ ] **Step 1: 在 openCreateModal() 增加模板 select**

目标 UI：
- root 展示：`默认(root)`，value：`root`
- 命名模板展示：`t1`，value：`tpl:t1`

实现要点：
- 新增 `tmplSel = document.createElement("select")`
- 新增 `refreshTemplates()`：
  - 调用 `templatesList(sel.value)`
  - 清空 `tmplSel` 并重建 options
  - 默认选中 `root`
  - 失败时：`setToast(String(e))`，并至少保留 `默认(root)` 一个选项
- runtime `<select>` 的 `change` 事件里调用 `refreshTemplates()`
- 弹窗初始化时（append 到 DOM 后）调用一次 `refreshTemplates()`

- [ ] **Step 2: close() 返回 template_id**

将原 `close({ runtime, name })` 改为：

```js
close({ runtime, name, template_id: tmplSel.value || "root" })
```

---

### Task 4: 创建动作调用 createInstance(runtime, name, template_id)

**Files:**
- Modify: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/static/app.js`

- [ ] **Step 1: 修改 bindActions() 中创建按钮逻辑**

将：

```js
await createInstance(r.runtime, r.name)
```

改为：

```js
await createInstance(r.runtime, r.name, r.template_id)
```

---

### Task 5: 手工冒烟（描述）

**Steps:**
- [ ] 进入管理台页面
- [ ] 点击“新增实例”
- [ ] 确认弹窗内出现“模板”下拉，且默认选中 `默认(root)`
- [ ] 切换 runtime（例如 hermes ↔ nanoghost），确认模板下拉随 runtime 刷新且仍默认 `默认(root)`
- [ ] 若存在命名模板（例如 `tpl:t1`），确认下拉显示为 `t1`，创建时提交 value 为 `tpl:t1`
- [ ] 点击“创建”，确认实例创建成功并自动选中该实例

---

### Task 6: pytest 全量回归

- [ ] **Step 1: 运行 pytest**

Run:

```bash
python -m pytest -q
```

Expected:
- Exit code 0

