from pathlib import Path

from fastapi.testclient import TestClient

import server.app as app_mod


def _write_manager_config(*, path: Path, nanoghost_root: Path) -> None:
    escaped_root = str(nanoghost_root).replace("\\", "\\\\")
    path.write_text(f'nanoghost_root: "{escaped_root}"\n', encoding="utf-8")


def test_template_env_put_and_get_nanoghost(tmp_path: Path, monkeypatch):
    nano_root = tmp_path / "nanoghost"
    nano_root.mkdir(parents=True, exist_ok=True)

    cfg = tmp_path / "manager-config.yaml"
    _write_manager_config(path=cfg, nanoghost_root=nano_root)
    monkeypatch.setattr(app_mod, "CONFIG_PATH", cfg)

    client = TestClient(app_mod.app)

    r = client.get("/api/templates/nanoghost/env")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["items"] == []

    r = client.put("/api/templates/nanoghost/env", json={"key": "K", "value": "V"})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert (nano_root / ".env").read_text(encoding="utf-8") == "K=V\n"

    r = client.get("/api/templates/nanoghost/env")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["items"] == [{"key": "K", "is_set": True, "value": "V"}]


def test_create_instance_inherits_template_env_nanoghost(tmp_path: Path, monkeypatch):
    nano_root = tmp_path / "nanoghost"
    nano_root.mkdir(parents=True, exist_ok=True)

    cfg = tmp_path / "manager-config.yaml"
    _write_manager_config(path=cfg, nanoghost_root=nano_root)
    monkeypatch.setattr(app_mod, "CONFIG_PATH", cfg)

    client = TestClient(app_mod.app)

    r = client.put("/api/templates/nanoghost/env", json={"key": "K", "value": "V"})
    assert r.status_code == 200

    r = client.post("/api/runtimes/nanoghost/instances", json={"name": "n1"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True

    inst = nano_root / "instances" / "n1"
    assert inst.is_dir()
    assert (inst / ".env").read_text(encoding="utf-8") == "K=V\n"


def test_template_env_put_and_get_named_template_nanoghost(tmp_path: Path, monkeypatch):
    nano_root = tmp_path / "nanoghost"
    (nano_root / "templates" / "t1").mkdir(parents=True, exist_ok=True)

    cfg = tmp_path / "manager-config.yaml"
    _write_manager_config(path=cfg, nanoghost_root=nano_root)
    monkeypatch.setattr(app_mod, "CONFIG_PATH", cfg)

    client = TestClient(app_mod.app)

    r = client.get("/api/templates/nanoghost/env?template_id=tpl:t1")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["items"] == []

    r = client.put("/api/templates/nanoghost/env?template_id=tpl:t1", json={"key": "K", "value": "V"})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert (nano_root / "templates" / "t1" / ".env").read_text(encoding="utf-8") == "K=V\n"

    r = client.get("/api/templates/nanoghost/env")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["items"] == []

    r = client.get("/api/templates/nanoghost/manifest?template_id=tpl:t1")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["instance"]["path"] == str(nano_root / "templates" / "t1")
