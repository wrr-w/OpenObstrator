# OpenObstrator（Hermes 实例管理台）

本项目是一个独立于 Hermes 源码的本机管理台，用于管理本机所有 Hermes profiles（实例）。

## 功能（MVP）

- 实例启停：Dashboard / Gateway 的启动、停止、状态展示
- 配置编辑：每个 profile 的 `.env` 与 `config.yaml`（Raw 编辑）
- Skills 管理：skills 列表、启用/禁用
- Hermes Root 解析优先级：`data/config.yaml` → 环境变量 `HERMES_HOME` → `~/.hermes`

## 目录说明

- `server/`：FastAPI 后端 + 前端模板与静态资源
- `data/config.yaml`：管理台配置（Hermes 根目录、端口分配范围、管理台监听地址等）
- `data/registry.json`：运行态登记簿（端口分配、PID、最后一次启动时间）
- `tests/`：单测

## 环境要求

- Python 3.10+
- Windows 环境优先（也可在其他平台运行，但以 Windows 路径与启动方式为主）
- Hermes 已安装且命令行可执行 `hermes`（确保在 PATH 中）

## 配置

管理台配置文件：`data/config.yaml`

- `hermes_root`：Hermes 根目录（default profile 的目录），可为 `null`
- `bind_host` / `bind_port`：管理台自身监听地址与端口
- `port_alloc`：Dashboard/Gateway 的端口分配范围

若不配置 `hermes_root`，程序会尝试读取 `HERMES_HOME`，否则回退到 `~/.hermes`。

## 启动

在项目根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

启动服务（端口建议与 `data/config.yaml` 中的 `bind_port` 保持一致）：

```powershell
.\.venv\Scripts\uvicorn server.app:app --host 127.0.0.1 --port 8091
```

启动后访问：

- Web：`http://127.0.0.1:8091/`
- 健康检查：`GET http://127.0.0.1:8091/api/health`

## 测试

```powershell
.\.venv\Scripts\pytest
```

