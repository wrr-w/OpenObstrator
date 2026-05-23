from pathlib import Path

from fastapi.testclient import TestClient

import server.app as app_mod


def _write_manager_config(*, path: Path, nanoghost_root: Path) -> None:
    escaped_root = str(nanoghost_root).replace("\\", "\\\\")
    path.write_text(f'nanoghost_root: "{escaped_root}"\n', encoding="utf-8")


def test_nanoghost_list_strictly_scans_instances_dir(tmp_path: Path, monkeypatch):
    nano_root = tmp_path / "nanoghost"
    nano_root.mkdir(parents=True, exist_ok=True)

    (nano_root / "legacy-flat").mkdir(parents=True, exist_ok=True)

    (nano_root / "instances" / "ok1").mkdir(parents=True, exist_ok=True)
    (nano_root / "instances" / "ok1" / "marker.txt").write_text("ok\n", encoding="utf-8")

    cfg = tmp_path / "manager-config.yaml"
    _write_manager_config(path=cfg, nanoghost_root=nano_root)
    monkeypatch.setattr(app_mod, "CONFIG_PATH", cfg)

    client = TestClient(app_mod.app)

    r = client.get("/api/runtimes/nanoghost/instances")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert [it["name"] for it in body["instances"]] == ["ok1"]


def test_nanoghost_create_clones_root_template_excluding_instances(tmp_path: Path, monkeypatch):
    nano_root = tmp_path / "nanoghost"
    nano_root.mkdir(parents=True, exist_ok=True)
    (nano_root / "TEMPLATE.txt").write_text("hello\n", encoding="utf-8")
    (nano_root / ".env").write_text("K=V\n", encoding="utf-8")

    (nano_root / "instances").mkdir(parents=True, exist_ok=True)
    (nano_root / "instances" / "should_not_copy").mkdir(parents=True, exist_ok=True)
    (nano_root / "instances" / "should_not_copy" / "x.txt").write_text("nope\n", encoding="utf-8")

    cfg = tmp_path / "manager-config.yaml"
    _write_manager_config(path=cfg, nanoghost_root=nano_root)
    monkeypatch.setattr(app_mod, "CONFIG_PATH", cfg)

    client = TestClient(app_mod.app)

    r = client.post("/api/runtimes/nanoghost/instances", json={"name": "n1"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True

    inst = nano_root / "instances" / "n1"
    assert inst.is_dir()
    assert (inst / "TEMPLATE.txt").read_text(encoding="utf-8") == "hello\n"
    assert (inst / ".env").read_text(encoding="utf-8") == "K=V\n"
    assert not (inst / "instances").exists()
    assert (inst / "data").is_dir()
    assert (inst / "work").is_dir()
    assert (inst / "prompts").is_dir()
    assert (inst / "skills").is_dir()
    assert (inst / "skills.disabled").is_dir()

