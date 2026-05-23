from pathlib import Path

import yaml
from fastapi.testclient import TestClient

import server.app as app_mod


def test_api_skills_list_and_toggle(tmp_path: Path, monkeypatch):
    hermes_root = tmp_path / "hermes"
    profile_dir = hermes_root / "profiles" / "p1"
    (profile_dir / "skills" / "foo").mkdir(parents=True, exist_ok=True)
    (profile_dir / "skills" / "bar" / "baz").mkdir(parents=True, exist_ok=True)
    (profile_dir / "skills" / "foo" / "SKILL.md").write_text("# foo\n", encoding="utf-8")
    (profile_dir / "skills" / "bar" / "baz" / "SKILL.md").write_text("# bar/baz\n", encoding="utf-8")

    (profile_dir / "config.yaml").write_text("a: 1\nskills:\n  disabled:\n    - foo\n", encoding="utf-8")

    cfg = tmp_path / "manager-config.yaml"
    escaped_root = str(hermes_root).replace("\\", "\\\\")
    cfg.write_text(f'hermes_root: "{escaped_root}"\n', encoding="utf-8")
    monkeypatch.setattr(app_mod, "CONFIG_PATH", cfg)

    client = TestClient(app_mod.app)

    r = client.get("/api/profiles/p1/skills")
    assert r.status_code == 200
    items = {x["name"]: x for x in r.json()["items"]}
    assert items["foo"]["enabled"] is False
    assert items["baz"]["enabled"] is True

    rt = client.put("/api/profiles/p1/skills/toggle", json={"name": "foo", "enabled": True})
    assert rt.status_code == 200

    raw = (profile_dir / "config.yaml").read_text(encoding="utf-8")
    parsed = yaml.safe_load(raw)
    assert parsed["a"] == 1
    assert parsed["skills"]["disabled"] == []

    r2 = client.get("/api/profiles/p1/skills")
    assert r2.status_code == 200
    items2 = {x["name"]: x for x in r2.json()["items"]}
    assert items2["foo"]["enabled"] is True


def test_api_skills_toggle_creates_config(tmp_path: Path, monkeypatch):
    hermes_root = tmp_path / "hermes"
    profile_dir = hermes_root / "profiles" / "p1"
    (profile_dir / "skills" / "foo").mkdir(parents=True, exist_ok=True)
    (profile_dir / "skills" / "foo" / "SKILL.md").write_text("# foo\n", encoding="utf-8")

    cfg = tmp_path / "manager-config.yaml"
    escaped_root = str(hermes_root).replace("\\", "\\\\")
    cfg.write_text(f'hermes_root: "{escaped_root}"\n', encoding="utf-8")
    monkeypatch.setattr(app_mod, "CONFIG_PATH", cfg)

    client = TestClient(app_mod.app)

    rt = client.put("/api/profiles/p1/skills/toggle", json={"name": "foo", "enabled": False})
    assert rt.status_code == 200

    raw = (profile_dir / "config.yaml").read_text(encoding="utf-8")
    parsed = yaml.safe_load(raw)
    assert parsed["skills"]["disabled"] == ["foo"]


def test_api_skills_includes_external_dirs(tmp_path: Path, monkeypatch):
    hermes_root = tmp_path / "hermes"
    profile_dir = hermes_root / "profiles" / "p1"
    (profile_dir / "skills" / "local").mkdir(parents=True, exist_ok=True)
    (profile_dir / "skills" / "local" / "SKILL.md").write_text("name: local\n", encoding="utf-8")

    ext = tmp_path / "extskills"
    (ext / "alpha").mkdir(parents=True, exist_ok=True)
    (ext / "alpha" / "SKILL.md").write_text("name: alpha\n", encoding="utf-8")

    escaped_ext = str(ext).replace("\\", "\\\\")
    (profile_dir / "config.yaml").write_text(f"skills:\n  external_dirs:\n    - \"{escaped_ext}\"\n", encoding="utf-8")

    cfg = tmp_path / "manager-config.yaml"
    escaped_root = str(hermes_root).replace("\\", "\\\\")
    cfg.write_text(f'hermes_root: "{escaped_root}"\n', encoding="utf-8")
    monkeypatch.setattr(app_mod, "CONFIG_PATH", cfg)

    client = TestClient(app_mod.app)
    r = client.get("/api/profiles/p1/skills")
    assert r.status_code == 200
    names = {x["name"] for x in r.json()["items"]}
    assert names.issuperset({"local", "alpha"})
