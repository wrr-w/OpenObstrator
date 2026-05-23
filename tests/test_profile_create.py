from pathlib import Path

from fastapi.testclient import TestClient

import server.app as app_mod


def test_create_profile_clone_default(tmp_path: Path, monkeypatch):
    hermes_root = tmp_path / "hermes"
    hermes_root.mkdir(parents=True, exist_ok=True)
    (hermes_root / "profiles").mkdir(parents=True, exist_ok=True)
    (hermes_root / "profiles" / "should_not_copy.txt").write_text("nope\n", encoding="utf-8")
    (hermes_root / "skills" / "demo").mkdir(parents=True, exist_ok=True)
    (hermes_root / "skills" / "demo" / "SKILL.md").write_text("x\n", encoding="utf-8")
    (hermes_root / "config.yaml").write_text("a: 1\n", encoding="utf-8")
    (hermes_root / ".env").write_text("K=V\n", encoding="utf-8")
    (hermes_root / "SOUL.md").write_text("soul\n", encoding="utf-8")

    cfg = tmp_path / "manager-config.yaml"
    escaped_root = str(hermes_root).replace("\\", "\\\\")
    cfg.write_text(f'hermes_root: "{escaped_root}"\n', encoding="utf-8")
    monkeypatch.setattr(app_mod, "CONFIG_PATH", cfg)

    client = TestClient(app_mod.app)

    r = client.post("/api/profiles", json={"name": "coder"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True

    prof_dir = hermes_root / "profiles" / "coder"
    assert prof_dir.is_dir()
    assert (prof_dir / "config.yaml").read_text(encoding="utf-8") == "a: 1\n"
    assert (prof_dir / ".env").read_text(encoding="utf-8") == "K=V\n"
    assert (prof_dir / "SOUL.md").read_text(encoding="utf-8") == "soul\n"
    assert (prof_dir / "skills" / "demo" / "SKILL.md").is_file()
    assert not (prof_dir / "profiles").exists()
    assert not (prof_dir / "should_not_copy.txt").exists()


def test_create_profile_rejects_invalid_name(tmp_path: Path, monkeypatch):
    hermes_root = tmp_path / "hermes"
    hermes_root.mkdir(parents=True, exist_ok=True)
    cfg = tmp_path / "manager-config.yaml"
    escaped_root = str(hermes_root).replace("\\", "\\\\")
    cfg.write_text(f'hermes_root: "{escaped_root}"\n', encoding="utf-8")
    monkeypatch.setattr(app_mod, "CONFIG_PATH", cfg)

    client = TestClient(app_mod.app)
    r = client.post("/api/profiles", json={"name": "BadName"})
    assert r.status_code == 400
