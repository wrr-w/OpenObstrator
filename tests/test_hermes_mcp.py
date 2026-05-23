from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import server.app as app_mod


def test_hermes_mcp_config_raw_roundtrip(tmp_path: Path):
    hermes_root = tmp_path / ".hermes"
    hermes_root.mkdir(parents=True, exist_ok=True)
    hermes_cfg = hermes_root / "config.yaml"
    hermes_cfg.write_text("mcp_servers: {}\n", encoding="utf-8")

    manager_cfg = tmp_path / "manager_config.yaml"
    manager_cfg.write_text(f"hermes_root: {hermes_root}\n", encoding="utf-8")

    old_cfg_path = app_mod.CONFIG_PATH
    app_mod.CONFIG_PATH = manager_cfg
    try:
        c = TestClient(app_mod.app)
        r = c.get("/api/hermes/mcp/config/raw")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert Path(data["path"]).name == "config.yaml"
        assert "mcp_servers" in data["raw"]

        next_raw = (
            "mcp_servers:\n"
            "  demo:\n"
            "    enabled: true\n"
            "    url: http://127.0.0.1:1\n"
            "    connect_timeout: 0.2\n"
        )
        r2 = c.put("/api/hermes/mcp/config/raw", json={"raw": next_raw})
        assert r2.status_code == 200

        assert "demo" in hermes_cfg.read_text(encoding="utf-8")

        r3 = c.get("/api/hermes/mcp/probe")
        assert r3.status_code == 200
        items = r3.json()["items"]
        assert any(it["id"] == "demo" for it in items)
    finally:
        app_mod.CONFIG_PATH = old_cfg_path

