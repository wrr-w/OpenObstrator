from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import server.app as app_mod
from server.configfile import read_raw_yaml, validate_yaml_mapping, write_raw_yaml


def test_validate_yaml_mapping_accepts_empty_and_mapping():
    assert validate_yaml_mapping("") == {}
    assert validate_yaml_mapping(" \n") == {}
    assert validate_yaml_mapping("a: 1\n") == {"a": 1}


def test_validate_yaml_mapping_rejects_non_mapping():
    with pytest.raises(ValueError):
        validate_yaml_mapping("- a\n- b\n")


def test_write_raw_yaml_preserves_raw(tmp_path: Path):
    p = tmp_path / "config.yaml"
    raw = "a: 1\nb:\n  c: 2\n"
    write_raw_yaml(p, raw)
    assert read_raw_yaml(p) == raw


def test_api_config_raw_roundtrip(tmp_path: Path, monkeypatch):
    hermes_root = tmp_path / "hermes"
    profile_dir = hermes_root / "profiles" / "p1"
    profile_dir.mkdir(parents=True, exist_ok=True)

    cfg = tmp_path / "manager-config.yaml"
    escaped_root = str(hermes_root).replace("\\", "\\\\")
    cfg.write_text(f'hermes_root: "{escaped_root}"\n', encoding="utf-8")
    monkeypatch.setattr(app_mod, "CONFIG_PATH", cfg)

    client = TestClient(app_mod.app)

    raw = "a: 1\nb:\n  c: 2\n"
    r = client.put("/api/profiles/p1/config/raw", json={"raw": raw})
    assert r.status_code == 200
    assert (profile_dir / "config.yaml").read_text(encoding="utf-8") == raw

    rg = client.get("/api/profiles/p1/config/raw")
    assert rg.status_code == 200
    assert rg.json()["raw"] == raw

    bad = "- a\n- b\n"
    rb = client.put("/api/profiles/p1/config/raw", json={"raw": bad})
    assert rb.status_code == 400
