from pathlib import Path

from server.settings import resolve_hermes_root
from server.settings import resolve_shared_skills_root


def test_resolve_hermes_root_prefers_manager_config(tmp_path: Path, monkeypatch):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("hermes_root: D:\\\\HermesData\n", encoding="utf-8")
    monkeypatch.delenv("HERMES_HOME", raising=False)
    root = resolve_hermes_root(config_path=cfg)
    assert str(root) == "D:\\HermesData"


def test_resolve_hermes_root_falls_back_to_env(monkeypatch, tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("hermes_root: null\n", encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", "D:\\\\HermesEnv")
    root = resolve_hermes_root(config_path=cfg)
    assert str(root) == "D:\\HermesEnv"


def test_resolve_hermes_root_falls_back_to_home(monkeypatch, tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("hermes_root: null\n", encoding="utf-8")
    monkeypatch.delenv("HERMES_HOME", raising=False)
    root = resolve_hermes_root(config_path=cfg)
    assert root.name == ".hermes"


def test_resolve_shared_skills_root_prefers_manager_config(tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("shared_skills_root: D:\\\\SharedSkills\n", encoding="utf-8")
    root = resolve_shared_skills_root(config_path=cfg)
    assert str(root) == "D:\\SharedSkills"
