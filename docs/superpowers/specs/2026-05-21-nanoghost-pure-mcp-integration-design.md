# NanoGhost 纯 MCP 集成 Spec（HTTP/SSE + Tool Calls + MCPList）

**目标**：NanoGhost 作为 MCP Host/Client，连接多个常驻 MCP Server（HTTP/SSE），自动发现 tools 并注入到 LLM 的 tool_calls，使模型将 MCP 工具当作原生能力调用；同时提供独立的 MCPList 页面用于查看与管理。

---

## 1. 目标与范围

### 1.1 目标

- 运行时可连接 1..N 个 MCP Server（HTTP/SSE）。
- 启动后自动获取 MCP tools，并将其注册为 LLM 可见 tools（OpenAI function/tool schema）。
- 模型通过 tool_calls 直接调用 MCP tools，结果以 tool_result 形式回灌下一轮对话。
- UI 提供独立页面 MCPList（不与 skills 混排）查看/管理 MCP servers 与 tools。

### 1.2 非目标

- 不引入业务 API spec 注入作为运行必要条件（纯 MCP：以 MCP tools schema 为规范来源）。
- 不定义或依赖任何业务 JSON 动作协议（动作协议唯一：tool_calls）。
- 不要求实现 stdio transport（本期仅 HTTP/SSE）。

---

## 2. 基本原则（硬约束）

- **动作协议唯一：tool_calls**。不解析任何业务 JSON 动作协议。
- **纯 MCP**：工具规范来自 MCP tool schema，而非额外 API 文档。
- **平台不依赖业务**：无 MCP server 时 NanoGhost 仍可对话，只是缺少 MCP tools。
- **可拔插**：MCP server 上下线不影响核心对话，仅影响相关 tools 可用性。

---

## 3. 实例级配置（生态一致：用 config 声明 servers）

实例目录 `<instance_dir>/config.yaml` 增加：

```yaml
mcp:
  servers:
    - id: "server1"
      enabled: true
      transport: "http_sse"
      url: "http://127.0.0.1:9000"
      headers:
        Authorization: "Bearer ${MCP_TOKEN}"
      timeout_seconds: 30
```

### 3.1 字段定义

- `id`：实例内唯一标识。用于工具命名与 UI 分组。
- `enabled`：是否启用。
- `transport`：本期固定 `http_sse`。
- `url`：MCP server base URL。
- `headers`：可选。支持 `${ENV_VAR}` 取值。
- `timeout_seconds`：可选，默认 30。

### 3.2 安全要求

- secrets 必须通过 `.env` 或系统环境变量注入（`${...}`），不允许明文写入仓库。
- UI 展示 headers 时需要脱敏（例如 Authorization 只显示前缀）。

---

## 4. MCP Client（HTTP/SSE）能力要求

对每个启用 server，客户端必须提供：

- `probe(server)`：连通性探测（带超时）。
- `list_tools(server)`：拉取 tools 列表与 schema。
- `call_tool(server, tool_name, args)`：调用工具并返回结果。
- SSE：第一阶段允许“聚合模式”（读完整流后一次性返回）。

---

## 5. Tools 注入（MCP → LLM tool schema）

### 5.1 注入策略（关键）

- 每次调用 LLM（chat/completions）时，都必须传递当前可用 tools 列表（包含 MCP tools）。
- 可以缓存工具列表，但最终必须体现在每轮请求的 `tools=` 参数中，否则模型看不见工具。

### 5.2 工具命名（强制、全局唯一）

- LLM 可见 tool 名：
  - `mcp.<server_id>.<tool_name>`

### 5.3 schema 映射

- 将 MCP tool 的 `inputSchema` 映射为 OpenAI tool `parameters`：
  - `type: object`
  - `properties`
  - `required`
- schema 不完整时：
  - 仍可注册，但 parameters 退化为宽松 object，并在 description 标注 “schema incomplete”。

### 5.4 description 约定

- tool description 固定前缀：
  - `[MCP:<server_id>] <original_description>`

---

## 6. tool_calls 执行与回灌

### 6.1 Dispatch 规则

- 当收到 tool_call：
  - 若 tool name 以 `mcp.` 开头：解析出 `server_id/tool_name`，路由到对应 MCP server 的 `call_tool`。
  - 非 mcp 工具：走 NanoGhost 内置工具系统。

### 6.2 tool_result 统一返回格式（强制）

MCP 调用返回统一结构（让模型稳定消费）：

```json
{
  "ok": true,
  "data": {},
  "error": null,
  "meta": {
    "server_id": "server1",
    "tool_name": "search",
    "duration_ms": 12
  }
}
```

失败时：

- `ok=false`
- `error` 必填（可读摘要）
- `data` 可选（原始响应/错误细节）
- 禁止抛异常导致 agent 崩溃或中断整个会话

---

## 7. 生命周期与降级策略

### 7.1 启动阶段

- 对所有 enabled server 并行：
  1) probe
  2) list_tools
  3) 注册 tools
- probe/list_tools 失败：
  - 默认不注册该 server 的任何 tools（减少模型撞墙）
  - 记录 `last_error`

### 7.2 运行中刷新

- 支持刷新某个 server：
  - 重新 list_tools
  - 更新注册（卸载旧 tools → 注册新 tools）

### 7.3 断连处理

- 断连不影响核心对话。
- 已注册 tools 调用失败时，返回 `ok=false` 的 tool_result，并携带错误摘要。

---

## 8. MCPList（独立 UI 页面）

### 8.1 页面定位

- 独立页面：MCPList（不与 skills 混排）
- 顶部导航入口：MCP

### 8.2 展示结构（按 server 分组）

Server 卡片显示：

- `server_id`
- `transport`
- `url`
- `enabled`
- `connection_status`：`connected | disconnected | error`
- `last_error`（若有）
- `tool_count`

展开 server 显示 tools 列表：

- `tool_name`（MCP 原名）
- `exposed_name`（`mcp.<server_id>.<tool_name>`）
- `description`
- `schema_summary`（required + 关键字段）

点击 tool 显示完整 JSON schema（只读）。

### 8.3 操作（最小集）

- Server 级：
  - Enable/Disable（写回实例 config）
  - Refresh（重新拉 tools 并更新运行时注册）
- Tool 级（可选但推荐）：
  - Test Call：输入 args JSON → 调用一次 → 展示 tool_result

### 8.4 一致性要求

- MCPList 展示必须与运行时实际注册进 LLM tools 的列表一致。

---

## 9. 验收标准（可测）

1) 配置 1 个 MCP server：
   - 启动时能拉到 tools 并注册到 LLM tools
   - 模型能 tool_calls 调用 `mcp.server1.*`
2) MCPList：
   - 正确展示 server 状态、tools 列表、schema
   - Enable/Disable/Refresh 生效
3) server 下线：
   - NanoGhost 核心对话不挂
   - MCPList 显示 error + last_error
   - tool 调用失败返回 `ok=false` tool_result
4) 多 server：
   - 工具命名无冲突
   - MCPList 按 server 分组展示

