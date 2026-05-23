from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient

import server.app as app_mod


def test_nanoghost_mcp_global_and_allowlist(tmp_path: Path):
    ng_root = tmp_path / "nanoghost"
    inst = ng_root / "instances" / "demo1"
    inst.mkdir(parents=True, exist_ok=True)
    (inst / "config.yaml").write_text("mcp:\n  enabled_only: []\n", encoding="utf-8")

    manager_cfg = tmp_path / "manager_config.yaml"
    manager_cfg.write_text(f"nanoghost_root: {ng_root}\n", encoding="utf-8")

    global_cfg = tmp_path / "ng_global.yaml"
    global_cfg.write_text("mcp_servers: {}\n", encoding="utf-8")

    old_env = os.environ.get("NANOGHOST_GLOBAL_CONFIG")
    os.environ["NANOGHOST_GLOBAL_CONFIG"] = str(global_cfg)

    old_cfg_path = app_mod.CONFIG_PATH
    app_mod.CONFIG_PATH = manager_cfg
    try:
        c = TestClient(app_mod.app)
        r = c.get("/api/nanoghost/mcp/config/raw")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert Path(data["path"]).name.endswith(".yaml")

        next_raw = (
            "mcp_servers:\n"
            "  demo:\n"
            "    enabled: true\n"
            "    transport: http_sse\n"
            "    url: http://127.0.0.1:1/\n"
            "    timeout_seconds: 0.2\n"
        )
        r2 = c.put("/api/nanoghost/mcp/config/raw", json={"raw": next_raw})
        assert r2.status_code == 200
        assert "demo" in global_cfg.read_text(encoding="utf-8")

        r3 = c.get("/api/nanoghost/mcp/config")
        assert r3.status_code == 200
        servers = r3.json()["servers"]
        assert any(s.get("id") == "demo" for s in servers)

        r4 = c.put("/api/nanoghost/mcp/instances/demo1/allowlist", json={"enabled_only": ["demo"]})
        assert r4.status_code == 200

        r5 = c.get("/api/nanoghost/mcp/instances/demo1/allowlist")
        assert r5.status_code == 200
        assert "demo" in (r5.json().get("enabled_only") or [])

        r6 = c.get("/api/nanoghost/mcp/probe?instance=demo1")
        assert r6.status_code == 200
        items = r6.json()["items"]
        assert any(it.get("id") == "demo" for it in items)
    finally:
        app_mod.CONFIG_PATH = old_cfg_path
        if old_env is None:
            os.environ.pop("NANOGHOST_GLOBAL_CONFIG", None)
        else:
            os.environ["NANOGHOST_GLOBAL_CONFIG"] = old_env

