# Template & Instance Roots Design

Date: 2026-05-20

## Goal

- Make Hermes and NanoGhost follow a consistent storage model:
  - A per-runtime root directory exists (configurable in manager config).
  - The root directory is treated as the runtime’s **template** (not listed as an instance).
  - All runnable instances live under a dedicated **2-level** instance directory and are discovered only from there.
  - Creating a new instance means creating a new instance directory and copying template contents into it.
- Keep Hermes existing runtime behavior usable after the change, but enforce strict discovery rules (no legacy paths).
- Add “Template Management” in UI so editing the template affects subsequent instance creation.

## Non-Goals

- Automatic migration of legacy directory layouts.
- Backward compatibility for legacy discovery (anything not in the configured instance directory is ignored).
- Changing runtime semantics (Hermes dashboard/gateway behavior, NanoGhost gateway behavior stay as-is).

## Directory Layout (Strict)

### Hermes

- Root (template): `<hermes_root>/`
- Instances container: `<hermes_root>/profiles/`
- Instance directory: `<hermes_root>/profiles/<name>/`
- Discovery: only scan `<hermes_root>/profiles/*` (directories only; ignore dot-prefixed).

Notes:
- The “default instance” is not a runnable instance here; it is the template at `<hermes_root>/`.
- Instances should contain all per-instance content in one place (env/config/memories/skills/etc.) under the instance directory.

### NanoGhost

- Root (template): `<nanoghost_root>/`
- Instances container: `<nanoghost_root>/instances/`
- Instance directory: `<nanoghost_root>/instances/<name>/`
- Discovery: only scan `<nanoghost_root>/instances/*` (directories only; ignore dot-prefixed).

Notes:
- Anything at `<nanoghost_root>/<name>` (legacy flat layout) is ignored.

## Template Management (UI)

### Entry

- Add a top-level button: “模板管理” (Template Management), next to existing global actions (e.g. “管理台配置”).

### Behavior

- Opens a modal.
- Select runtime: Hermes / NanoGhost.
- Shows editable sections driven by the same manifest-driven UI model:
  - If a runtime supports an area, show it; otherwise hide it.
  - The template is edited through dedicated template APIs (see below), not through the normal instance APIs.

### What can be edited

- Hermes template:
  - env (.env)
  - config (config.yaml)
  - soul/memories/raw
  - skills toggles (updates template config.yaml’s skills.* fields)
  - channels (if supported by Hermes template the same way as instances)
- NanoGhost template:
  - env (.env)
  - skills toggles (updates template config.yaml’s skills.disabled)
  - channels config (channel_directory.json) editing
  - other config files if present (config.yaml raw editor)

## Instance Creation (Copy From Template)

### Required semantics

- Create instance under the runtime’s instance directory:
  - Hermes: `<hermes_root>/profiles/<name>/`
  - NanoGhost: `<nanoghost_root>/instances/<name>/`
- Copy template contents from root into the new instance directory.
- Do not copy the instances container itself (to avoid recursive copy):
  - Hermes: exclude `profiles/` from template copy.
  - NanoGhost: exclude `instances/` from template copy.

### Copy policy

- Preferred: directory tree copy with explicit excludes:
  - Exclude container dirs: `profiles/` or `instances/`.
  - Exclude ephemeral/unsafe dirs if present at template root: `.git/`, `.venv/`, `__pycache__/`, `.pytest_cache/`, etc.
- Preserve file timestamps where possible; overwrite behavior:
  - New instance directory must not exist; if exists -> 409.
- After copy:
  - Ensure required per-instance subdirs exist if runtime expects them (only if the template didn’t provide them).

### Template readiness

- If template root does not exist or is not a directory: return a clear 400 error.
- If instances container directory does not exist: create it (container only), but do not generate template content.

## API Design

### Runtime root remains configurable

- `hermes_root`, `nanoghost_root`, `openclaw_root` remain in manager config.
- `shared_skills_root` remains for shared skills directory scanning.

### New template endpoints (manager-scoped)

These endpoints operate on the runtime template root directory (not an instance).

- `GET /api/templates/{runtime}/manifest`
  - Same structure as instance manifest; may be identical to runtime manifest.
- `GET /api/templates/{runtime}/env`
- `PUT /api/templates/{runtime}/env`
- `PUT /api/templates/{runtime}/env/batch`
- `DELETE /api/templates/{runtime}/env`
- `GET /api/templates/{runtime}/skills`
- `PUT /api/templates/{runtime}/skills/batch`
- `GET /api/templates/{runtime}/config/raw` (where applicable)
- `PUT /api/templates/{runtime}/config/raw`
- `GET /api/templates/{runtime}/channels` (where applicable)
- `PUT /api/templates/{runtime}/channels`

Response shape matches existing instance endpoints (`ok`, `path`, `items`, etc.) for UI reuse.

### Instance endpoints changes (path resolution only)

- Hermes:
  - Any place that previously treated `default` as `<hermes_root>` now treats every Hermes instance as `<hermes_root>/profiles/<name>`.
  - `/api/profiles/*` endpoints are updated accordingly so they also use the new path resolution.
- NanoGhost:
  - `_nanoghost_instance_dir(name)` becomes `<nanoghost_root>/instances/<name>`.
  - Listing uses `<nanoghost_root>/instances`.
  - Create/delete/env/skills/channels/services/gateway updated to use the new path.

## Compatibility Rules (Strict)

- The UI left list shows only:
  - Hermes: directories under `<hermes_root>/profiles`
  - NanoGhost: directories under `<nanoghost_root>/instances`
- Root template directories are never listed as instances.
- Legacy layouts are ignored without warning (per requirement).

## Security & Safety

- Copy logic must not follow symlinks that escape the template root.
- Avoid copying hidden/system folders that may contain secrets or source control metadata.
- Never log env values.

## Testing

- Unit tests:
  - Hermes list_profiles only scans `profiles/` and does not include root-as-default.
  - Hermes profile_dir resolution always maps to `profiles/<name>`.
  - NanoGhost instance_dir resolution maps to `instances/<name>`.
  - Create instance clones template while excluding container dirs.
  - Template endpoints read/write the correct root files.
- Integration tests via FastAPI TestClient:
  - Template edit -> subsequent create uses edited value (e.g. template .env carries into created instance .env).

## Rollout / Operator Steps

- Prepare template roots:
  - Hermes: ensure `<hermes_root>` contains intended template content.
  - NanoGhost: ensure `<nanoghost_root>` contains intended template content.
- Ensure instance containers exist:
  - Hermes: create `<hermes_root>/profiles/` and place instances there.
  - NanoGhost: create `<nanoghost_root>/instances/` and place instances there.
- Legacy paths will not be visible after this change.

