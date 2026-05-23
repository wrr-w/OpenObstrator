# Instance-Derived Templates Design

Date: 2026-05-21

## Goal

- Support multiple templates per runtime, stored under each runtime root directory.
- Allow exporting any instance as a template.
- Allow creating a new instance by selecting a template (defaulting to the runtime root template).
- Add a per-instance “…” actions menu in the left instance list (delete, export as template, edit template, rename).
- Keep existing “root template” behavior:
  - The runtime root directory remains a valid template source.
  - Root templates are managed via “模板管理”.

## Non-Goals

- Automatic migration of legacy instance directories.
- Cross-runtime templates.
- Template versioning/history.

## Directory Layout

### Instances (unchanged)

- Hermes instances: `<hermes_root>/profiles/<name>/` (discovered only from `profiles/`)
- NanoGhost instances: `<nanoghost_root>/instances/<name>/` (discovered only from `instances/`)

### Templates (new)

Templates are stored per runtime under a dedicated folder at the runtime root.

- Hermes templates: `<hermes_root>/templates/<tpl>/`
- NanoGhost templates: `<nanoghost_root>/templates/<tpl>/`

Rules:
- `<tpl>` uses the same naming rule as instances (`^[a-z0-9][a-z0-9_-]{0,63}$`).
- Templates are never treated as instances and are never scanned as instances.

## Template Sources

We identify a template source by a `(runtime, template_id)` pair.

`template_id` can be:
- `root`: runtime root directory (existing root template)
- `tpl:<name>`: a named template directory under `templates/<name>`

Mapping:
- `template_dir(runtime, "root") = <runtime_root>`
- `template_dir(runtime, "tpl:<name>") = <runtime_root>/templates/<name>`

## Copy Semantics

### Export Instance As Template

Given an instance directory and a template directory:
- Copy instance dir to `<runtime_root>/templates/<tpl>`
- Exclude container dirs that may exist inside the instance:
  - Hermes: exclude `profiles/`, `templates/`
  - NanoGhost: exclude `instances/`, `templates/`
- Also exclude tool/system dirs: `.git`, `.venv`, `__pycache__`, `.pytest_cache`, `.mypy_cache`
- Default overwrite policy:
  - If destination template exists, return 409 unless `overwrite=true` explicitly provided.

### Create Instance From Template

Creation remains in the instance container directory:
- Hermes: `<hermes_root>/profiles/<name>`
- NanoGhost: `<nanoghost_root>/instances/<name>`

Copy from the selected `template_dir` into the new instance directory:
- Exclude instance container dirs:
  - Hermes: exclude `profiles/`, `templates/`
  - NanoGhost: exclude `instances/`, `templates/`
- Same tool/system excludes as above

## API Design

### List Templates

- `GET /api/templates/{runtime}/list`

Returns:
```json
{
  "ok": true,
  "runtime": "hermes",
  "items": [
    { "id": "root", "name": "root", "path": "D:\\HermesRoot" },
    { "id": "tpl:demo", "name": "demo", "path": "D:\\HermesRoot\\templates\\demo" }
  ]
}
```

### Template Content Endpoints (Extend Existing)

Existing endpoints operate on the root template:
- `/api/templates/{runtime}/env`
- `/api/templates/{runtime}/skills`
- `/api/templates/{runtime}/channels`
- `/api/templates/{runtime}/config/raw`
- `/api/templates/{runtime}/manifest`

Extend them to accept an optional query parameter:
- `?template_id=root` (default)
- `?template_id=tpl:<name>`

Example:
- `GET /api/templates/hermes/env?template_id=tpl:demo`

### Export Instance As Template

- `POST /api/instances/{runtime}/{name}/export-template`

Body:
```json
{ "template_name": "demo", "overwrite": false }
```

Returns:
```json
{ "ok": true, "template": { "id": "tpl:demo", "name": "demo", "path": "..." } }
```

### Rename Instance

- `POST /api/instances/{runtime}/{name}/rename`

Body:
```json
{ "new_name": "new_name" }
```

Rules:
- Validate new name with the same instance name regex.
- Refuse if instance is running:
  - Hermes: if registry says dashboard/gateway running for that instance
  - NanoGhost: if gateway running for that instance
- Perform filesystem rename (directory rename) within the instance container:
  - Hermes: `<hermes_root>/profiles/<name>` → `<hermes_root>/profiles/<new_name>`
  - NanoGhost: `<nanoghost_root>/instances/<name>` → `<nanoghost_root>/instances/<new_name>`
- Update registry records: move per-instance entries to the new key and clear any paths cached in responses.

### Create Instance With Template Selection

Extend the existing instance create endpoint:

- `POST /api/instances`

Body:
```json
{ "runtime": "nanoghost", "name": "n1", "template_id": "root" }
```

Rules:
- `template_id` optional; default is `root`.
- Validate `template_id`:
  - `root` or `tpl:<name>`
  - `tpl:<name>` must exist under `<runtime_root>/templates/<name>` or return 404.

## UI Design

### Left Instance List “…” Menu

Each instance row adds a “…” menu with:
- 删除实例
- 设为模板
- 编辑模板
- 重命名实例

Behavior:
- 菜单只作用于当前实例所属 runtime。
- “设为模板”默认使用实例名作为模板名（可编辑）。
- “编辑模板”打开“模板管理”并选中 `tpl:<name>`（若不存在则先提示导出/创建）。

### Create Instance Modal: Template Selection

新增实例弹窗增加“模板”下拉（同 runtime）：
- 默认选：root
- 列表来自 `GET /api/templates/{runtime}/list`
- 创建提交时携带 `template_id`

### Template Manager

现有“模板管理”弹窗升级为：
- runtime 选择
- template 选择（root + templates/<tpl>）
- tab 仍按 `GET /api/templates/{runtime}/manifest?template_id=...` 的 `tabs` 渲染
- 保存调用同一批 `/api/templates/*` 接口，但加上 `template_id` 参数

## Testing

- API tests:
  - `/api/templates/{runtime}/list` returns `root` and template items under `templates/`
  - export-template creates template directory and excludes container dirs
  - create-instance with `template_id=tpl:<name>` clones content into new instance
  - rename refuses when running and succeeds otherwise
- UI smoke:
  - Create modal shows template dropdown and creates correctly
  - Template manager can switch between root and a named template
  - Instance “…” menu actions work

