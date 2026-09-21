"""飞书进程槽改造：从"自己起一个进程"改成"让 gateway 去孵 worker"。

改造前的行为是对同一个机器人开**第二条** WebSocket 长连接 —— gateway 不知道它
存在，它也不受 gateway 那个 30 秒体检保护。所以这几个用例钉的是"有没有走
gateway"，而不只是"接口返回 200"。
"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import server.app as A


@pytest.fixture
def env(tmp_path: Path, monkeypatch):
    cfg = tmp_path / "config.yaml"
    reg = tmp_path / "registry.json"
    monkeypatch.setattr(A, "CONFIG_PATH", cfg)
    monkeypatch.setattr(A, "REGISTRY_PATH", reg)
    monkeypatch.setattr(A, "DATA_DIR", tmp_path)
    # 默认 nanoghost_root = config_path.parent / "nanoghost"，实例就落在 tmp 里，
    # 不会碰真实机器的 ~/.nanoghost/instances
    inst = tmp_path / "nanoghost" / "instances" / "demo"
    inst.mkdir(parents=True)
    return {"inst": inst, "path": inst / "channel_directory.json",
            "registry": reg, "client": TestClient(A.app)}


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _gateway_up(env) -> None:
    """让注册簿里有一条**在跑**的 gateway 记录。

    光把 is_pid_running 打成 True 不够：_gateway_running 先看记录里有没有 pid。
    """
    env["registry"].write_text(json.dumps({
        "version": 2,
        "runtimes": {"nanoghost": {"instances": {"demo": {
            "gateway": {"pid": 111, "port": 19100, "started_at": 1},
        }}}},
    }), encoding="utf-8")


def test_start_enables_channel_and_asks_gateway(env, monkeypatch):
    calls = []
    _gateway_up(env)
    monkeypatch.setattr(A, "is_pid_running", lambda pid: True)
    monkeypatch.setattr(A, "_gateway_http",
                        lambda rec, method, path, timeout=8.0: calls.append((method, path)) or {"workers": {}})
    monkeypatch.setattr(A, "instance_service_start",
                        lambda *a: pytest.fail("gateway 已经在跑，不该再起一个"))

    r = env["client"].post("/api/runtimes/nanoghost/instances/demo/processes/feishu/start")
    assert r.status_code == 200 and r.json()["via"] == "gateway"
    assert calls == [("POST", "/api/start")]
    assert _read(env["path"])["channels"]["feishu"]["enabled"] is True


def test_start_raises_gateway_when_it_is_not_running(env, monkeypatch):
    """gateway 没在跑就起 gateway —— 它启动时会自己读 channel_directory.json
    并孵化 feishu worker，不需要再单独起一个进程。"""
    started = []
    monkeypatch.setattr(A, "is_pid_running", lambda pid: False)
    monkeypatch.setattr(A, "instance_service_start",
                        lambda rt, name, svc: started.append((rt, name, svc)) or {"ok": True, "pid": 42})
    monkeypatch.setattr(A, "_gateway_http",
                        lambda *a, **k: pytest.fail("gateway 不在跑，不该去调它的 HTTP 接口"))

    r = env["client"].post("/api/runtimes/nanoghost/instances/demo/processes/feishu/start")
    assert r.status_code == 200 and r.json()["via"] == "gateway-started"
    assert started == [("nanoghost", "demo", "gateway")]
    assert _read(env["path"])["channels"]["feishu"]["enabled"] is True


def test_stop_disables_and_stops_worker(env, monkeypatch):
    _gateway_up(env)
    monkeypatch.setattr(A, "is_pid_running", lambda pid: True)
    calls = []
    monkeypatch.setattr(A, "_gateway_http",
                        lambda rec, method, path, timeout=8.0: calls.append((method, path)) or {"workers": {}})

    r = env["client"].post("/api/runtimes/nanoghost/instances/demo/processes/feishu/stop")
    assert r.status_code == 200
    # 用 /api/stop（就是 gateway 的 stop_feishu），不是 /api/start —— 后者会对
    # 所有通道按配置启停，会顺带碰别的通道
    assert calls == [("POST", "/api/stop")]
    assert _read(env["path"])["channels"]["feishu"]["enabled"] is False


def test_stop_without_gateway_only_writes_config(env, monkeypatch):
    monkeypatch.setattr(A, "is_pid_running", lambda pid: False)
    monkeypatch.setattr(A, "_gateway_http", lambda *a, **k: pytest.fail("不该调 gateway"))
    r = env["client"].post("/api/runtimes/nanoghost/instances/demo/processes/feishu/stop")
    assert r.status_code == 200 and r.json()["via"] == "config-only"
    assert _read(env["path"])["channels"]["feishu"]["enabled"] is False


def test_status_reads_worker_state_from_gateway(env, monkeypatch):
    _gateway_up(env)
    monkeypatch.setattr(A, "is_pid_running", lambda pid: True)
    monkeypatch.setattr(A, "_gateway_http", lambda rec, method, path, timeout=8.0: {
        "workers": {"feishu": {"enabled": True, "running": True, "pid": 777}},
    })
    r = env["client"].get("/api/runtimes/nanoghost/instances/demo/processes/feishu/status")
    body = r.json()
    assert r.status_code == 200
    assert body["running"] is True and body["worker_pid"] == 777


def test_status_reports_gateway_down_instead_of_guessing(env, monkeypatch):
    monkeypatch.setattr(A, "is_pid_running", lambda pid: False)
    body = env["client"].get(
        "/api/runtimes/nanoghost/instances/demo/processes/feishu/status").json()
    assert body["running"] is False
    assert "gateway" in body["detail"]


def test_status_does_not_lie_when_gateway_port_is_dead(env, monkeypatch):
    """gateway 进程在、端口不通（刚起或正在崩）—— 如实说，不要报成在跑。"""
    _gateway_up(env)
    monkeypatch.setattr(A, "is_pid_running", lambda pid: True)

    def _boom(*a, **k):
        raise A.HTTPException(status_code=502, detail="连不上 gateway")

    monkeypatch.setattr(A, "_gateway_http", _boom)
    body = env["client"].get(
        "/api/runtimes/nanoghost/instances/demo/processes/feishu/status").json()
    assert body["workers"] is None
    assert "连不上" in body["detail"]


def test_cli_slot_is_gone(env):
    """cli 在 NanoGhost 的 CHANNEL_REGISTRY 里没有 worker_key，它本质是终端 ——
    无终端时 input() 立刻 EOFError 退出，托管不了。三个动作一起下线。"""
    c = env["client"]
    base = "/api/runtimes/nanoghost/instances/demo/processes/cli"
    assert c.post(f"{base}/start").status_code == 404
    assert c.post(f"{base}/stop").status_code == 404
    assert c.get(f"{base}/status").status_code == 404


def test_unknown_slot_is_404(env):
    c = env["client"]
    assert c.post(
        "/api/runtimes/nanoghost/instances/demo/processes/nope/start").status_code == 404


def test_missing_instance_is_404(env):
    r = env["client"].post("/api/runtimes/nanoghost/instances/ghost/processes/feishu/start")
    assert r.status_code == 404


def test_channel_config_keeps_other_channels(env):
    env["path"].write_text(json.dumps({
        "channels": {"cli": {"enabled": True}, "feishu": {"enabled": False}},
        "updated_at": None,
    }), encoding="utf-8")
    A._set_channel_enabled(env["inst"], "feishu", True)
    cfg = _read(env["path"])
    assert cfg["channels"]["feishu"]["enabled"] is True
    assert cfg["channels"]["cli"]["enabled"] is True      # 不许顺手把别人删了
    assert cfg["updated_at"]
