import json
from pathlib import Path

import httpx
import pytest

from server import releases


@pytest.fixture(autouse=True)
def _isolate(monkeypatch, tmp_path: Path):
    """每个用例一个空的配置目录 + 清干净的缓存。

    必须隔离配置路径：否则会读到开发机真实的 ~/.nanoghost/update.json，
    用例的结果就取决于那台机器上装了什么。
    """
    cfg = tmp_path / "update.json"
    monkeypatch.setattr(releases, "update_config_path", lambda: cfg)
    releases.clear_cache()
    yield cfg
    releases.clear_cache()


def _fake_get(payload, *, status=200, headers=None, calls=None, exc=None):
    def _get(url, **kwargs):
        if calls is not None:
            calls.append(url)
        if exc is not None:
            raise exc
        return httpx.Response(
            status, json=payload, headers=headers or {},
            request=httpx.Request("GET", url),
        )
    return _get


def _release(assets, tag="v1.0.1"):
    return {
        "tag_name": tag,
        "assets": [
            {"name": n, "browser_download_url": u} for n, u in assets
        ],
    }


def test_picks_prefixed_zip_and_installer(monkeypatch):
    monkeypatch.setattr(releases.httpx, "get", _fake_get(_release([
        ("Source code.zip", "https://x/src.zip"),
        ("NanoGhost-v1.0.1-win64.zip", "https://x/ng.zip"),
        ("NanoGhostSetup-1.0.1.exe", "https://x/setup.exe"),
    ])))
    d = releases.fetch_latest()
    assert d["version"] == "1.0.1"          # tag 的 v 前缀被剥掉
    assert d["zip_name"] == "nanoghost-v1.0.1-win64.zip"
    assert d["zip_url"] == "https://x/ng.zip"
    assert d["installer_name"] == "nanoghostsetup-1.0.1.exe"
    assert d["installer_url"] == "https://x/setup.exe"


def test_zip_falls_back_to_first_zip(monkeypatch):
    """和 update.py:_check_github 的兜底一致 —— 两边规则分叉就会出现
    "控制台说能升、程序说不能升"。"""
    monkeypatch.setattr(releases.httpx, "get", _fake_get(_release([
        ("Release-v9.zip", "https://x/other.zip"),
    ])))
    assert releases.fetch_latest()["zip_url"] == "https://x/other.zip"


def test_installer_does_not_fall_back(monkeypatch):
    """安装包刻意不兜底：多挑一个 exe 就是装一个来路不明的可执行文件。"""
    monkeypatch.setattr(releases.httpx, "get", _fake_get(_release([
        ("NanoGhost-v1.0.1-win64.zip", "https://x/ng.zip"),
        ("some-other-tool.exe", "https://x/other.exe"),
    ])))
    d = releases.fetch_latest()
    assert d["zip_url"] == "https://x/ng.zip"
    assert d["installer_url"] == ""


def test_only_installer_is_enough(monkeypatch):
    """只有安装包也算查到了 —— 新机器安装场景不需要 zip。"""
    monkeypatch.setattr(releases.httpx, "get", _fake_get(_release([
        ("NanoGhostSetup-1.0.1.exe", "https://x/setup.exe"),
    ])))
    d = releases.fetch_latest()
    assert d["zip_url"] == ""
    assert d["installer_url"] == "https://x/setup.exe"


def test_no_usable_asset_raises(monkeypatch):
    monkeypatch.setattr(releases.httpx, "get", _fake_get(_release([
        ("README.md", "https://x/readme"),
    ])))
    with pytest.raises(releases.ReleaseError) as e:
        releases.fetch_latest()
    assert "既没有" in str(e.value)


def test_rate_limit_has_readable_chinese_error(monkeypatch):
    monkeypatch.setattr(releases.httpx, "get", _fake_get(
        {"message": "API rate limit exceeded"}, status=403,
        headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1700000000"},
    ))
    with pytest.raises(releases.ReleaseError) as e:
        releases.fetch_latest()
    assert "限流" in str(e.value)


def test_timeout_mentions_network(monkeypatch):
    monkeypatch.setattr(releases.httpx, "get", _fake_get(
        None, exc=httpx.ConnectTimeout("timed out")))
    with pytest.raises(releases.ReleaseError) as e:
        releases.fetch_latest()
    assert "超时" in str(e.value)


def test_connection_error(monkeypatch):
    monkeypatch.setattr(releases.httpx, "get", _fake_get(
        None, exc=httpx.ConnectError("no route")))
    with pytest.raises(releases.ReleaseError) as e:
        releases.fetch_latest()
    assert "连不上" in str(e.value)


def test_404_names_the_repo(monkeypatch):
    monkeypatch.setattr(releases.httpx, "get", _fake_get({"message": "Not Found"}, status=404))
    with pytest.raises(releases.ReleaseError) as e:
        releases.fetch_latest("someone/private")
    assert "someone/private" in str(e.value)


def test_non_json_body_is_not_reported_as_success(monkeypatch):
    """200 但内容是代理塞的错误页。只看状态码会当成查到版本，然后拿着空 version
    往下走，报错指向完全错误的地方。"""
    def _get(url, **kwargs):
        return httpx.Response(200, text="<html>blocked</html>",
                              request=httpx.Request("GET", url))
    monkeypatch.setattr(releases.httpx, "get", _get)
    with pytest.raises(releases.ReleaseError) as e:
        releases.fetch_latest()
    assert "不是 JSON" in str(e.value)


def test_cache_avoids_refetch_but_force_refreshes(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(releases.httpx, "get", _fake_get(
        _release([("NanoGhost-v1.0.1-win64.zip", "https://x/ng.zip")]), calls=calls))
    releases.fetch_latest()
    releases.fetch_latest()
    assert len(calls) == 1                  # 轮询不该烧掉 GitHub 的 60 次/小时配额
    releases.fetch_latest(force=True)
    assert len(calls) == 2                  # 用户点按钮才真查


def test_config_supplies_repo_prefix_and_download_base(monkeypatch, _isolate):
    """两侧读同一个配置文件，否则会出现"控制台说能升、程序说不能升"。"""
    _isolate.write_text(json.dumps({
        "repo": "mirror-org/NanoGhost",
        "asset_prefix": "nanoghost",
        "download_base": "https://dl.example.com/nanoghost",
    }), encoding="utf-8")
    calls: list[str] = []
    monkeypatch.setattr(releases.httpx, "get", _fake_get(_release([
        ("NanoGhost-v1.0.1-win64.zip", "https://github.com/wrr-w/NanoGhost/releases/download/v1.0.1/ng.zip"),
        ("NanoGhostSetup-1.0.1.exe", "https://github.com/wrr-w/NanoGhost/releases/download/v1.0.1/setup.exe"),
    ]), calls=calls))
    d = releases.fetch_latest()
    assert calls[0].endswith("/repos/mirror-org/NanoGhost/releases/latest")
    assert d["repo"] == "mirror-org/NanoGhost"
    # 装不上的那台机器恰恰最需要镜像 —— 安装包也要走同一个改写
    assert d["zip_url"] == "https://dl.example.com/nanoghost/v1.0.1/ng.zip"
    assert d["installer_url"] == "https://dl.example.com/nanoghost/v1.0.1/setup.exe"


def test_broken_config_falls_back_to_defaults(monkeypatch, _isolate):
    """一个手滑的逗号不该让整个升级功能失效（和 update.py 的行为一致）。"""
    _isolate.write_text("{ not json", encoding="utf-8")
    calls: list[str] = []
    monkeypatch.setattr(releases.httpx, "get", _fake_get(
        _release([("NanoGhost-v1.0.1-win64.zip", "https://x/ng.zip")]), calls=calls))
    releases.fetch_latest()
    assert f"/repos/{releases.DEFAULT_REPO}/" in calls[0]


def test_compare_versions():
    assert releases.compare_versions("1.0.0", "1.0.1") == -1
    assert releases.compare_versions("1.0.1", "1.0.1") == 0
    assert releases.compare_versions("1.10.0", "1.9.0") == 1
    assert releases.compare_versions("2.0", "2.0.0") == -1
