from pathlib import Path

from fastapi.testclient import TestClient

import server.app as app_mod
from server.soulfile import read_raw_text, write_raw_text


def test_write_raw_text_roundtrip(tmp_path: Path):
    p = tmp_path / "SOUL.md"
    raw = "hello\nworld\n"
    write_raw_text(p, raw)
    assert read_raw_text(p) == raw


def test_api_soul_raw_roundtrip(tmp_path: Path, monkeypatch):
    hermes_root = tmp_path / "hermes"
    profile_dir = hermes_root / "profiles" / "p1"
    profile_dir.mkdir(parents=True, exist_ok=True)

    cfg = tmp_path / "manager-config.yaml"
    escaped_root = str(hermes_root).replace("\\", "\\\\")
    cfg.write_text(f'hermes_root: "{escaped_root}"\n', encoding="utf-8")
    monkeypatch.setattr(app_mod, "CONFIG_PATH", cfg)

    client = TestClient(app_mod.app)

    raw = "You are a helpful assistant.\n"
    r = client.put("/api/profiles/p1/soul/raw", json={"raw": raw})
    assert r.status_code == 200
    assert (profile_dir / "SOUL.md").read_text(encoding="utf-8") == raw

    g = client.get("/api/profiles/p1/soul/raw")
    assert g.status_code == 200
    body = g.json()
    assert body["raw"] == raw
    assert body["exists"] is True
