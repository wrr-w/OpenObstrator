from pathlib import Path

from fastapi.testclient import TestClient

import server.app as app_mod


def test_templates_list_includes_root_and_named_templates(tmp_path: Path, monkeypatch):
    hermes_root = tmp_path / "hermes"
    (hermes_root / "templates" / "t1").mkdir(parents=True)
    (hermes_root / "templates" / "t1" / ".env").write_text("A=B\n", encoding="utf-8")

    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(
        f"hermes_root: '{hermes_root.as_posix()}'\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(app_mod, "CONFIG_PATH", cfg)

    c = TestClient(app_mod.app)
    r = c.get("/api/templates/hermes/list")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True

    items = body["items"]
    ids = [it["id"] for it in items]
    assert "root" in ids
    assert "tpl:t1" in ids
