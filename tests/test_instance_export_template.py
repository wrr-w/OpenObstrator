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


def test_export_instance_as_template_nanoghost_and_conflict(tmp_path: Path, monkeypatch):
    root = tmp_path / "ng"
    inst = root / "instances" / "n1"
    inst.mkdir(parents=True, exist_ok=True)
    (inst / "X.txt").write_text("hello\n", encoding="utf-8")
    (inst / "instances" / "nested.txt").mkdir(parents=True, exist_ok=True)
    (inst / "instances" / "nested.txt" / "X2.txt").write_text("bad\n", encoding="utf-8")
    (inst / "templates" / "nested.txt").mkdir(parents=True, exist_ok=True)
    (inst / "templates" / "nested.txt" / "X3.txt").write_text("bad\n", encoding="utf-8")

    cfg = tmp_path / "manager-config.yaml"
    _write_manager_config(path=cfg, nanoghost_root=root)
    monkeypatch.setattr(app_mod, "CONFIG_PATH", cfg)

    c = TestClient(app_mod.app)
    r1 = c.post(
        "/api/instances/nanoghost/n1/export-template",
        json={"template_name": "t1", "overwrite": False},
    )
    assert r1.status_code == 200
    assert (root / "templates" / "t1" / "X.txt").read_text(encoding="utf-8") == "hello\n"
    assert not (root / "templates" / "t1" / "instances").exists()
    assert not (root / "templates" / "t1" / "templates").exists()

    r2 = c.post(
        "/api/instances/nanoghost/n1/export-template",
        json={"template_name": "t1", "overwrite": False},
    )
    assert r2.status_code == 409

