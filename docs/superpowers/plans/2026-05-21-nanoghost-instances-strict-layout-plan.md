# NanoGhost Strict `instances/` Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 NanoGhost 实例目录严格切换为 `nanoghost_root/instances/<name>`，并将创建实例改为从 `nanoghost_root/` 模板克隆（排除 `instances/`），补充测试并保证 `pytest` 通过。

**Architecture:** 统一通过 `server/app.py` 内部的 `_nanoghost_instance_dir()` / `_list_nanoghost_instances()` 做路径与发现规则；创建实例使用现有 `server/template_copy.py:clone_template_dir()` 从 runtime root 作为模板克隆到 `instances/<name>`，并显式 `exclude_names={"instances"}`，严格忽略旧平铺 `nanoghost_root/<name>`。

**Tech Stack:** FastAPI, Pydantic, pathlib, shutil, pytest, fastapi.testclient

---

## File Map

**Modify**
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/app.py` — NanoGhost 实例路径、列表、创建逻辑

**Create**
- `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/tests/test_nanoghost_instances.py` — NanoGhost strict layout 行为测试

---

### Task 1: 切换 NanoGhost 实例路径到 `instances/<name>`

**Files:**
- Modify: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/app.py`

- [ ] **Step 1: 修改 `_nanoghost_instance_dir()` 返回 `root / "instances" / name`**
- [ ] **Step 2: 修改 `_list_nanoghost_instances(root)` 仅扫描 `root / "instances"`**
- [ ] **Step 3: 调整所有调用 `_list_nanoghost_instances()` 的位置传入 runtime root（函数内部再拼 `instances/`），或直接传入 instances root（保持一致即可）**

---

### Task 2: 创建实例改为从模板克隆（排除 `instances/`）

**Files:**
- Modify: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/server/app.py`

- [ ] **Step 1: `POST /api/runtimes/nanoghost/instances` 创建目标目录改为 `nanoghost_root/instances/<name>`**
- [ ] **Step 2: 使用 `clone_template_dir(template_dir=nanoghost_root, dest_dir=dest, exclude_names={"instances"})`**
- [ ] **Step 3: 若 `nanoghost_root` 不存在则返回 400；若 `nanoghost_root/instances` 不存在则创建容器目录**

---

### Task 3: 补充测试覆盖 strict layout + template clone

**Files:**
- Create: `e:/OperationsAssistantORIG/Tech/Code/OpenObstrator/tests/test_nanoghost_instances.py`

- [ ] **Step 1: 写测试：列表只返回 `nanoghost_root/instances/*`，忽略旧 `nanoghost_root/<name>`**
- [ ] **Step 2: 写测试：创建实例会把模板文件复制到 `instances/<name>`，且不会递归复制 `instances/`**

---

### Task 4: 运行测试

- [ ] **Step 1: 运行 `python -m pytest -q`**
  - Expected: PASS

