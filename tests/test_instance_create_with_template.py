from pathlib import Path

from fastapi.testclient import TestClient

import server.app as app_mod


def _write_manager_config(*, path: Path, hermes_root: Path | None = None, nanoghost_root: Path | None = None) -> None:
    lines: list[str] = []
    if hermes_root is not None:
        lines.append(f'hermes_root: "{str(hermes_root).replace("\\", "\\\\")}"\n')
    if nanoghost_root is not None:
        lines.append(f'nanoghost_root: "{str(nanoghost_root).replace("\\", "\\\\")}"\n')
    path.write_text("".join(lines), encoding="utf-8")


def test_create_instance_from_named_template_nanoghost(tmp_path: Path, monkeypatch):
    root = tmp_path / "ng"
    (root / "templates" / "t1").mkdir(parents=True, exist_ok=True)
    (root / "templates" / "t1" / ".env").write_text("A=B\n", encoding="utf-8")

    cfg = tmp_path / "manager-config.yaml"
    _write_manager_config(path=cfg, nanoghost_root=root)
    monkeypatch.setattr(app_mod, "CONFIG_PATH", cfg)

    c = TestClient(app_mod.app)
    r = c.post("/api/instances", json={"runtime": "nanoghost", "name": "n1", "template_id": "tpl:t1"})
    assert r.status_code == 200
    assert (root / "instances" / "n1" / ".env").read_text(encoding="utf-8") == "A=B\n"
    assert not (root / "instances" / "n1" / "templates").exists()


def test_create_instance_from_named_template_hermes(tmp_path: Path, monkeypatch):
    root = tmp_path / "hermes"
    (root / "templates" / "t1").mkdir(parents=True, exist_ok=True)
    (root / "templates" / "t1" / ".env").write_text("A=B\n", encoding="utf-8")

    cfg = tmp_path / "manager-config.yaml"
    _write_manager_config(path=cfg, hermes_root=root)
    monkeypatch.setattr(app_mod, "CONFIG_PATH", cfg)

    c = TestClient(app_mod.app)
    r = c.post("/api/instances", json={"runtime": "hermes", "name": "h1", "template_id": "tpl:t1"})
    assert r.status_code == 200
    assert (root / "profiles" / "h1" / ".env").read_text(encoding="utf-8") == "A=B\n"
    assert not (root / "profiles" / "h1" / "templates").exists()
