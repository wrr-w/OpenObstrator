"""解析器是防"版本错位"的唯一一道闸，所以三级优先级每一级都要单独钉住。

错位的失败模式是：控制台启动 A、升级打在 B —— 点完更新、重启后还是旧版本，
而且**没有任何报错**。这种故障没有测试就只能靠人肉发现。
"""
from pathlib import Path

import pytest

from server import settings


def _touch(p: Path) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"MZ")
    return p


@pytest.fixture
def cfg(tmp_path: Path) -> Path:
    return tmp_path / "config.yaml"


def test_config_wins_over_everything(cfg: Path, tmp_path: Path, monkeypatch):
    manual = _touch(tmp_path / "manual" / "NanoGhost.exe")
    _touch(tmp_path / "repo" / "dist" / "NanoGhost" / "NanoGhost.exe")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "localappdata"))
    # 单引号：YAML 双引号里 \U 是转义序列，Windows 路径放进去会直接扫不动
    cfg.write_text(f"nanoghost_program: '{manual}'\n", encoding="utf-8")

    p, src = settings.locate_nanoghost_program(
        config_path=cfg, repo_dir=tmp_path / "repo")
    assert p == manual
    assert src == settings.PROGRAM_SOURCE_CONFIG


def test_config_expands_env_vars(cfg: Path, tmp_path: Path, monkeypatch):
    """配置里写 %VAR% 是运维的常规写法，不展开就等于配置没生效。"""
    _touch(tmp_path / "ngroot" / "NanoGhost.exe")
    monkeypatch.setenv("NG_TEST_ROOT", str(tmp_path / "ngroot"))
    cfg.write_text("nanoghost_program: '%NG_TEST_ROOT%/NanoGhost.exe'\n", encoding="utf-8")

    p, src = settings.locate_nanoghost_program(config_path=cfg)
    assert p == tmp_path / "ngroot" / "NanoGhost.exe"
    assert src == settings.PROGRAM_SOURCE_CONFIG


def test_config_points_nowhere_raises_instead_of_falling_back(cfg: Path, tmp_path: Path, monkeypatch):
    """**不能**静默退回下一级：用户改了配置却看到行为没变，会以为配置生效了，
    比直接报错难查得多。"""
    _touch(tmp_path / "localappdata" / "Programs" / "NanoGhost" / "NanoGhost.exe")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "localappdata"))
    cfg.write_text('nanoghost_program: "C:\\\\definitely\\\\missing.exe"\n', encoding="utf-8")

    with pytest.raises(FileNotFoundError):
        settings.locate_nanoghost_program(config_path=cfg)


def test_installed_beats_source_dist(cfg: Path, tmp_path: Path, monkeypatch):
    """机器上装了正式版就该用正式版。继续跑源码 dist 的 exe 正是错位的来源。"""
    inst = _touch(tmp_path / "localappdata" / "Programs" / "NanoGhost" / "NanoGhost.exe")
    _touch(tmp_path / "repo" / "dist" / "NanoGhost" / "NanoGhost.exe")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "localappdata"))

    p, src = settings.locate_nanoghost_program(config_path=cfg, repo_dir=tmp_path / "repo")
    assert p == inst
    assert src == settings.PROGRAM_SOURCE_INSTALLED


def test_source_dist_is_the_last_resort(cfg: Path, tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "localappdata"))
    dist = _touch(tmp_path / "repo" / "dist" / "NanoGhost" / "NanoGhost.exe")

    p, src = settings.locate_nanoghost_program(config_path=cfg, repo_dir=tmp_path / "repo")
    assert p == dist
    assert src == settings.PROGRAM_SOURCE_SOURCE_DIST


def test_nothing_found_is_a_legal_state_not_an_error(cfg: Path, tmp_path: Path, monkeypatch):
    """返回 None 而不是抛异常：上层据此把"升级"降级成"安装"，这条分支必须好走。"""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "localappdata"))
    p, src = settings.locate_nanoghost_program(config_path=cfg, repo_dir=tmp_path / "repo")
    assert p is None
    assert src == settings.PROGRAM_SOURCE_NONE
    assert settings.resolve_nanoghost_program(config_path=cfg, repo_dir=tmp_path / "repo") is None


def test_no_localappdata_does_not_crash(cfg: Path, tmp_path: Path, monkeypatch):
    """服务账号下 LOCALAPPDATA 可能压根没有。缺变量不是崩溃理由。"""
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    assert settings.locate_nanoghost_program(config_path=cfg)[0] is None


def test_shorthand_returns_path_only(cfg: Path, tmp_path: Path):
    manual = _touch(tmp_path / "manual" / "NanoGhost.exe")
    cfg.write_text(f"nanoghost_program: '{manual}'\n", encoding="utf-8")
    assert settings.resolve_nanoghost_program(config_path=cfg) == manual


def test_empty_string_config_means_unset(cfg: Path, tmp_path: Path, monkeypatch):
    """YAML 里写 nanoghost_program: "" 或 null 是"没配"，不是"配了个空路径"。"""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "localappdata"))
    inst = _touch(tmp_path / "localappdata" / "Programs" / "NanoGhost" / "NanoGhost.exe")
    for text in ('nanoghost_program: ""\n', "nanoghost_program: null\n"):
        cfg.write_text(text, encoding="utf-8")
        assert settings.locate_nanoghost_program(config_path=cfg)[0] == inst
