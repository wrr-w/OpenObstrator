# Hermes 实例管理台（独立于 Hermes 源码）— 设计文档

日期：2026-05-18

## 目标

- 在“当前项目”内实现一个前后端产品，用于管理本机所有 Hermes profiles（实例）。
- 支持最小可用（MVP）能力：
  - 实例启停：Dashboard / Gateway 的启动、停止、状态展示
  - 配置编辑：每个 profile 的 `.env` 与 `config.yaml`（Raw YAML）
  - Skills 管理：skills 列表、启用/禁用（先不做安装/重置）
- Windows 友好：Hermes 通过 PATH 可执行 `hermes`；管理台以 `subprocess` 控制进程。
- 支持自定义 Hermes 根目录（profiles root）：优先读取管理台配置文件，其次读取 `HERMES_HOME`，最后回退 `~/.hermes`。

## 非目标（MVP 不做）

- 权限控制 / 登录鉴权（默认都能访问）。
- “按 skill 限制文件访问路径”的沙箱/ACL（Hermes profile 不是沙箱；这类需求属于 terminal backend 级隔离）。
- skills 安装、skills reset、MCP server 管理、OAuth 登录流程可视化。
- 跨机器远程管理（仅本机 localhost 管理）。

## 背景与现状（Hermes 自带多实例机制）

- Hermes 的“多实例”通过 Profiles 实现：每个 profile 是一个独立的 `HERMES_HOME`，内部包含 `config.yaml/.env/SOUL.md/sessions/memories/skills/...`。
- Hermes Dashboard（`hermes dashboard`）与 Gateway（`hermes gateway ...`）本质是独立进程；profile 通过 `-p <name>`（或 wrapper alias）切换。
- Hermes 自带 Dashboard API 主要面向“当前 profile”，跨 profile 的配置/密钥编辑端点并未提供；因此本管理台选择“独立实现”，不修改 Hermes 源码目录。

## 总体架构

- `Hermes Instance Manager`（本项目）
  - Backend：FastAPI（REST）
  - Frontend：轻量化页面（先使用 Jinja2 模板 + 少量 JS，后续可升级 React）
  - State：本项目内持久化 `data/registry.json`（记录端口分配与本管理台启动的进程 PID）
- 被管理对象：
  - Hermes profiles（default + named profiles）
  - 每个 profile 的文件：`.env`、`config.yaml`、`skills/`
  - 每个 profile 的进程：dashboard（`hermes dashboard`）与 gateway（`hermes gateway run`）

## 目录与配置

### 管理台自身目录（本项目内）

- `data/config.yaml`：管理台配置
- `data/registry.json`：运行态登记簿（端口分配、PID、最后一次启动时间）
- `data/logs/`：管理台记录的启动/停止日志（可选）

### Hermes Root 解析规则（支持自定义）

按优先级：

1. `data/config.yaml` 中的 `hermes_root`
2. 环境变量 `HERMES_HOME`
3. 默认 `~/.hermes`

约束与解释：

- 这里的 “hermes_root” 指 Hermes 默认 root（即 default profile 的目录），named profiles 在 `<root>/profiles/<name>/`。
- 如果用户配置了 `HERMES_HOME` 指向 `<root>/profiles/<name>` 这种 profile 目录，管理台仍把 `<root>` 当作根（等价于 Hermes 的 `get_default_hermes_root()` 语义），以便枚举所有 profiles。

## 数据模型（Backend）

### Config（data/config.yaml）

字段：

- `hermes_root: string | null`
- `port_alloc:`
  - `dashboard_start: int`（默认 18000）
  - `dashboard_end: int`（默认 18999）
  - `gateway_start: int`（默认 19000）
  - `gateway_end: int`（默认 19999）
- `bind_host: string`（默认 `127.0.0.1`，管理台自身监听地址）
- `bind_port: int`（默认 8088，管理台自身端口）

说明：

- Dashboard 与 Gateway 分开端口段，降低冲突概率。
- 端口段可调整，但默认足够覆盖几十个 profiles。

### Registry（data/registry.json）

示例结构（可扩展）：

```json
{
  "version": 1,
  "profiles": {
    "default": {
      "dashboard": { "port": 18001, "pid": 1234, "started_at": 1710000000 },
      "gateway": { "port": 19001, "pid": 2345, "started_at": 1710000000 }
    },
    "coder": {
      "dashboard": { "port": 18002, "pid": null, "started_at": null },
      "gateway": { "port": 19002, "pid": null, "started_at": null }
    }
  }
}
```

规则：

- `port` 一旦分配，长期固定；pid 是运行态，可为空。
- pid 只对“由本管理台启动的进程”可信；若用户手动启动 Hermes，我们会在 status 探测阶段尝试识别，但不会强依赖。

## 端口分配策略（A：自动分配）

### Dashboard 端口

- 初次启动某 profile dashboard 时：
  - 若 registry 已有 port，复用
  - 否则从 `dashboard_start..dashboard_end` 线性扫描，找到第一个空闲端口
  - 写回 registry

### Gateway 端口

- 同理从 `gateway_start..gateway_end` 分配
- 注意：Hermes Gateway 本身可能还会暴露更多内部端口/状态，但这里我们仅管理启动命令与主进程 PID。

### 空闲端口判断

- 使用 TCP connect 检测 `127.0.0.1:port` 是否可连接（可连接视为已占用）。
- 仅考虑 localhost 范围（避免把服务暴露到局域网）。

## 进程管理设计（Windows）

### Dashboard

启动命令（示例）：

```text
hermes -p <profile> dashboard --host 127.0.0.1 --port <port> --no-open --skip-build
```

停止：

- 优先按 registry 记录 pid 执行 `taskkill /PID <pid> /T /F`
- 若 pid 不存在或失败，返回错误并提示用户自行处理（MVP 不做全局扫描式 stop，避免误杀）。

状态：

- 若 registry 有 pid：
  - 检查 pid 是否存在（Windows 下用 psutil 或 `tasklist /FI "PID eq ..."`）
  - 同时检查端口是否可连接，作为补充

### Gateway

启动命令（示例）：

```text
hermes -p <profile> gateway run --quiet
```

停止与状态：

- 同 dashboard（pid 检测 + taskkill）。
- 兼容：如果 profile 目录下存在 `gateway.pid`，可作为辅助信息显示，但不作为唯一可信来源。

## 文件编辑策略

### `.env`（要求：尽量保留注释与顺序）

目标：更新/新增/删除某个 key，同时最大化保留原文件内容（注释、空行、顺序）。

规则：

- 更新：
  - 按行扫描，匹配 `^\s*KEY\s*=` 的第一行进行替换
  - 若 key 不存在，则在文件末尾追加 `KEY=value`（前面保留一个换行）
- 删除：
  - 删除匹配行（保留其他行）
- 不做 dotenv 变量展开与复杂语法解析（MVP）

### `config.yaml`（MVP：Raw YAML）

目标：支持用户直接编辑整份 YAML，并在保存前做语法校验。

规则：

- GET 返回原文
- PUT：
  - 先 `yaml.safe_load` 校验结果为 mapping（dict）
  - 校验通过则按原文写回（保留注释/格式）
  - 写入使用原子写（临时文件 + replace）

## Skills 管理（MVP：列表 + 启用/禁用）

### 列表

- 扫描 `<profile_dir>/skills/**/SKILL.md`
- 对每个 skill 读取：
  - 名称：由目录名/相对路径推导（MVP 先用 path 作为 id，后续可解析 SKILL.md header）
  - 描述：可选（后续再做）

### 启用/禁用

- Hermes 的禁用列表存储在 profile 的 `config.yaml`：
  - `skills.disabled: [name, ...]`
- MVP 行为：
  - toggle = 读 `config.yaml` -> 修改 `skills.disabled` -> 写回（raw yaml 模式下，需要“结构化写回”会破坏注释；因此 MVP 采用：
    - 如果用户使用 Raw YAML 编辑，则由用户自己维护
    - toggle API 采用结构化写回（会重写 YAML），或者我们延后 toggle，先只做只读列表

决策（MVP 推荐）：

- 为了满足 “skills 这些功能”，MVP 仍提供 toggle，但明确：
  - toggle 会做结构化写回 `config.yaml`（可能丢失注释/格式）
  - Raw YAML 编辑用于高级用户；若你非常在意注释保留，可在下一阶段实现 YAML patch（复杂度较高）

## REST API 草案（MVP）

### Profiles

- `GET /api/profiles`
  - 返回 profiles 列表（default + named），含：
    - profile_name
    - profile_dir
    - has_env
    - skill_count
    - dashboard: { port, pid, running }
    - gateway: { port, pid, running }

### Dashboard

- `POST /api/profiles/{name}/dashboard/start`
- `POST /api/profiles/{name}/dashboard/stop`
- `GET /api/profiles/{name}/dashboard/status`

### Gateway

- `POST /api/profiles/{name}/gateway/start`
- `POST /api/profiles/{name}/gateway/stop`
- `GET /api/profiles/{name}/gateway/status`

### Env

- `GET /api/profiles/{name}/env`（返回 key 列表 + is_set + redacted_value）
- `PUT /api/profiles/{name}/env`（传入 key/value；按行级写回）
- `DELETE /api/profiles/{name}/env`（传入 key；删除对应行）

### Config

- `GET /api/profiles/{name}/config/raw`
- `PUT /api/profiles/{name}/config/raw`

### Skills

- `GET /api/profiles/{name}/skills`
- `PUT /api/profiles/{name}/skills/toggle`

## UI 草案（MVP）

页面：

- `/`（Profiles 列表页）
  - 表格：Profile / Path / Skills / Env / Dashboard 状态 / Gateway 状态
  - 操作：Dashboard start/stop、Gateway start/stop、进入详情
- `/profiles/{name}`（详情页）
  - Tabs：Runtime / Env / Config / Skills

交互原则：

- 所有 Hermes 进程仅绑定 `127.0.0.1`
- 一切 “执行命令” 显示为可复制文本（方便 debug）

## 可靠性与风险

- Hermes 若由用户在外部手动启动，本管理台的 pid 可能为空；MVP 只做端口连通性探测与提示。
- Gateway/Dashboard 进程的子进程树在 Windows 需要用 `taskkill /T` 才能完整停止。
- `config.yaml` 的 “Raw YAML 编辑” 与 “skills toggle（结构化写回）”存在格式冲突：toggle 会重写 YAML（下一阶段解决）。

## 下一阶段（非 MVP）

- 权限控制：Admin Token 或角色系统（Viewer/Operator/Admin）。
- YAML patch：在保留注释的前提下修改指定字段（如 skills.disabled、terminal.cwd）。
- skills install/reset、MCP 配置可视化、OAuth 登录流程内嵌。
- 更强的“状态发现”：识别外部启动的 dashboard/gateway，并提供“接管/仅观察”选项。

## 验收标准（MVP）

- 能在管理台里看到 default + named profiles 列表。
- 能为任意 profile 一键启动/停止 dashboard，且自动分配端口并固定保存。
- 能为任意 profile 一键启动/停止 gateway（run 模式），并显示运行状态。
- 能在 UI 中编辑任意 profile 的 `.env`（保留注释顺序）与 `config.yaml`（Raw YAML）。
- 能列出任意 profile 的 skills，并能启用/禁用（可接受 YAML 重写的前提下）。

