import os
from pathlib import Path

from fastapi.testclient import TestClient

import server.app as app_mod
import server.registry as reg_mod


def _write_manager_config(*, path: Path, nanoghost_root: Path) -> None:
    escaped_root = str(nanoghost_root).replace("\\", "\\\\")
    path.write_text(f'nanoghost_root: "{escaped_root}"\n', encoding="utf-8")


def test_instance_rename_nanoghost_migrates_registry_and_dir(tmp_path: Path, monkeypatch):
    root = tmp_path / "ng"
    inst = root / "instances" / "a1"
    inst.mkdir(parents=True, exist_ok=True)

    cfg = tmp_path / "manager-config.yaml"
    _write_manager_config(path=cfg, nanoghost_root=root)
    monkeypatch.setattr(app_mod, "CONFIG_PATH", cfg)

    registry_path = tmp_path / "registry.json"
    monkeypatch.setattr(app_mod, "REGISTRY_PATH", registry_path)

    reg = reg_mod.load_registry(registry_path)
    rec = app_mod._proc_record(reg, "nanoghost", "a1", "gateway")
    rec["pid"] = None
    rec["started_at"] = None
    reg_mod.save_registry(registry_path, reg)

    c = TestClient(app_mod.app)
    r = c.post("/api/instances/nanoghost/a1/rename", json={"new_name": "a2"})
    assert r.status_code == 200

    assert not (root / "instances" / "a1").exists()
    assert (root / "instances" / "a2").is_dir()

    reg2 = reg_mod.load_registry(registry_path)
    insts = reg2["runtimes"]["nanoghost"]["instances"]
    assert "a1" not in insts
    assert "a2" in insts
    assert insts["a2"]["gateway"]["pid"] is None


def test_instance_rename_nanoghost_rejects_when_gateway_running(tmp_path: Path, monkeypatch):
    root = tmp_path / "ng"
    inst = root / "instances" / "a1"
    inst.mkdir(parents=True, exist_ok=True)

    cfg = tmp_path / "manager-config.yaml"
    _write_manager_config(path=cfg, nanoghost_root=root)
    monkeypatch.setattr(app_mod, "CONFIG_PATH", cfg)

    registry_path = tmp_path / "registry.json"
    monkeypatch.setattr(app_mod, "REGISTRY_PATH", registry_path)

    reg = reg_mod.load_registry(registry_path)
    rec = app_mod._proc_record(reg, "nanoghost", "a1", "gateway")
    rec["pid"] = int(os.getpid())
    rec["started_at"] = 123
    reg_mod.save_registry(registry_path, reg)

    c = TestClient(app_mod.app)
    r = c.post("/api/instances/nanoghost/a1/rename", json={"new_name": "a2"})
    assert r.status_code == 409

    assert (root / "instances" / "a1").is_dir()
    assert not (root / "instances" / "a2").exists()

    reg2 = reg_mod.load_registry(registry_path)
    insts = reg2["runtimes"]["nanoghost"]["instances"]
    assert "a1" in insts
    assert "a2" not in insts

