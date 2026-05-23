# NanoGhost 全局 MCP 注册表 + 实例白名单 Spec（无 UI 版）

**目标**：NanoGhost 以“全局 MCP 注册表（一次配置，多实例复用）+ 实例白名单（只控制可见性）”的方式接入 MCP。运行时仅连接白名单内的 MCP servers，将其 tools 注入 tool_calls；不实现 MCPList UI，以 CLI/日志提供可观测性与运维操作。

---

## 1. 目标与非目标

### 1.1 目标

- 支持在“全局位置”集中配置 MCP servers（像共享 skills 一样）。
- 每个实例仅配置“允许哪些 MCP servers 可见”（白名单）。
- NanoGhost 运行时仅连接白名单内 server，获取 tools schema 并注入 LLM tool_calls（function calling）。
- 维护全局探测缓存与熔断策略，适应远端 server 不可控（断连/变更/超时）。
- 不依赖任何业务约定（纯 MCP；动作协议唯一 tool_calls）。
- 提供 CLI 命令替代 UI，支持 list/probe/tools/reload。

### 1.2 非目标

- 不实现 MCPList UI 页面。
- 不实现 stdio transport（本期只做 HTTP/SSE）。
- 不要求在 prompts 注入业务 API 文档（以 MCP tool schema 为规范来源）。

---

## 2. 配置分层（核心）

### 2.1 全局 MCP 注册表（一次配置，多实例复用）

全局配置文件建议路径：

- Windows：`%USERPROFILE%\\.nanoghost\\config.yaml`
- macOS/Linux：`~/.nanoghost/config.yaml`

新增键：`mcp_servers`

```yaml
mcp_servers:
  github:
    enabled: true
    transport: http_sse
    url: "https://mcp.github.com"
    headers:
      Authorization: "Bearer ${GITHUB_TOKEN}"
    timeout_seconds: 30

  capture:
    enabled: true
    transport: http_sse
    url: "http://127.0.0.1:9000"
    headers:
      Authorization: "Bearer ${CAPTURE_MCP_TOKEN}"
    timeout_seconds: 30
```

字段定义：

- `enabled`：全局层面的开关（false 表示任何实例都不可用）。
- `transport`：本期固定 `http_sse`。
- `url`：server base URL。
- `headers`：可选，支持 `${ENV_VAR}` 插值。
- `timeout_seconds`：可选，默认 30。

安全要求：

- secrets 必须通过环境变量注入（`${...}`），不允许明文写入仓库/模板。
- 仅显式声明在 `headers` 的 env var 会被传入请求，避免意外泄漏。

### 2.2 实例可见性白名单（只控制“可见/不可见”）

实例配置文件：`<instance_dir>/config.yaml`

新增键：`mcp.enabled_only`

```yaml
mcp:
  enabled_only:
    - capture
    - github
```

规则：

- 仅允许 `enabled_only` 中列出的 servers 在该实例可见（并会被连接/注入 tools）。
- 若 `enabled_only` 为空或缺失：默认“全部禁用”（最安全）。
- 实例白名单只引用全局 `mcp_servers` 的 server_id；实例配置不重复写 url/token。

---

## 3. 运行时行为（无 UI）

### 3.1 选择要连接的 servers

对每个实例：

1) 读取全局 `mcp_servers`
2) 读取实例 `mcp.enabled_only`
3) 计算 `effective_servers = {id in enabled_only} ∩ {global.enabled=true}`
4) 仅对 `effective_servers` 执行 probe/list_tools/注册

### 3.2 工具注入（tool_calls）

- 每次调用 LLM 时，必须携带当前实例“可用 MCP tools”的 tools schema。
- 命名强制：`mcp.<server_id>.<tool_name>`
- tool schema 由 MCP server 提供，直接映射为 OpenAI tools 参数 schema。

### 3.3 探测缓存（全局共享，避免每实例重复探测）

维护一个全局缓存（进程内即可；可选落盘）：

- key：`server_id`
- value：
  - `status`: `connected | unreachable | error`
  - `last_probe_at`: timestamp
  - `last_error`: string
  - `tools_snapshot`: tools 列表 + schema hash（可选）
  - `cooldown_until`: timestamp（熔断冷却）

TTL 建议：

- `probe_ttl_seconds = 60`（默认）

刷新触发点：

- 实例启动时（只对 effective_servers）
- TTL 过期时的惰性刷新（下次需要注入/调用前刷新一次）
- tool 调用失败后进入熔断冷却，冷却到期后允许一次半开探测

### 3.4 熔断与重试（适配远端不可控）

建议策略：

- 连续失败计数达到阈值（例如 3 次）→ 打开熔断
- 熔断冷却（例如 60 秒）期间：
  - 不再尝试连接/调用该 server 的 tools
  - 注入阶段不注册该 server tools（减少模型撞墙）
- 冷却到期：
  - 允许一次“半开探测”；成功则恢复，失败则继续熔断

---

## 4. 可观测性与运维（CLI 代替 UI）

必须提供 CLI 子命令（示例命名，可调整）：

1) `nanoghost mcp list`

- 输出全局 `mcp_servers` 列表（id、url、enabled、transport）

2) `nanoghost mcp probe [--server <id>]`

- 对指定 server 或对“全局 enabled 的 servers”进行探测
- 输出 status、last_error、tools_count、耗时

3) `nanoghost mcp tools <server_id>`

- 输出该 server 的 tools 列表（name、description、schema 摘要）

4) `nanoghost mcp reload`

- 重新加载全局 config（以及实例 config）
- 刷新缓存（按需或全量）

日志要求：

- 每个 server 的连接/断连/刷新必须有结构化日志（含 server_id、错误摘要、耗时）。

---

## 5. 验收标准（可测）

1) 全局配置存在，但某实例白名单为空：

- 实例不连接任何 MCP server
- LLM tools 中不出现 mcp.* 工具

2) 实例白名单包含 2 个 server：

- 启动时仅探测这 2 个 server
- 成功的 server 的 tools 注入到 LLM tool schema
- tools 名为 `mcp.<server_id>.<tool_name>`

3) server 下线：

- 不影响核心对话
- 缓存中状态变为 unreachable/error，并进入冷却
- 冷却期间不再反复重连

4) CLI 可用：

- list/probe/tools/reload 可正确工作，输出与运行时一致

