"""查 GitHub release，拿升级包 / 安装包地址。

什么时候需要这个模块：**本机没有 NanoGhost 可执行文件**的时候（也就是"安装"场景）。
只要解析到了程序，就该优先问程序自己（`NanoGhost.exe update --check --json`）——
那条路已经跑通，而且它用的是自己那份配置。

资产筛选规则必须和 `src/agent_core/update.py:_check_github` 保持一致。两边规则
一旦分叉，就会出现"控制台说能升、程序说不能升"这种最难查的分歧，而用户看到的
只是一个转圈不动的按钮。

`download_base` / `repo` / `asset_prefix` 也**读同一个配置文件**
（`~/.nanoghost/update.json`），理由是同一个：两侧必须是同一个答案。
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# 和 update.py:DEFAULT_REPO / _check_github 的默认值保持一致
DEFAULT_REPO = "wrr-w/NanoGhost"
DEFAULT_ASSET_PREFIX = "nanoghost"
# 安装包的前缀。Inno Setup 的 OutputBaseFilename 是 NanoGhostSetup-<version>
# （scripts/installer.iss:28），所以小写后是 nanoghostsetup。
INSTALLER_PREFIX = "nanoghostsetup"

CACHE_TTL = 300.0
_API_TIMEOUT = 15.0

_CACHE_LOCK = threading.Lock()
_CACHE: dict = {"key": None, "at": 0.0, "data": None}


class ReleaseError(Exception):
    """查 release 失败。

    消息是**给界面直接显示的中文**。上层不要再包一层英文前缀 —— 这个错误最终会
    出现在弹窗里给使用者看，他需要知道"该做什么"，而不是"哪个异常被抛了"。
    """


# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

def update_config_path() -> Path:
    """和 update.py:_config_path() 同一个文件。"""
    return Path(os.path.expanduser("~")) / ".nanoghost" / "update.json"


def read_update_config() -> dict:
    """读 NanoGhost 自己的更新配置。

    读坏了退回默认值（和 update.py:33 的行为一致）—— 不因为一个手滑的逗号让
    整个升级功能失效。
    """
    p = update_config_path()
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _apply_download_base(url: str, cfg: dict) -> str:
    """按 download_base 改写下载地址前缀。规则和 update.py:38 逐字一致。

    客户机器直连 github.com 可能不通（UPDATING.md 实测本机就是单点阻断），
    把下载源指到自建服务器或加速代理。配置的是"到 releases/download 为止"的前缀。

    安装包也走这个改写 —— 恰恰是"连不上 github.com 的机器"最需要装得上。
    """
    base = (cfg.get("download_base") or "").strip().rstrip("/")
    if not base:
        return url
    marker = "/releases/download/"
    i = url.find(marker)
    if i < 0:
        return url          # 不是标准 release 地址，不认识就别乱改
    return f"{base}/{url[i + len(marker):]}"


# ---------------------------------------------------------------------------
# 版本比较
# ---------------------------------------------------------------------------

def compare_versions(v1: str, v2: str) -> int:
    """v1 < v2 → -1，相等 → 0，v1 > v2 → 1。语义和 agent_core/version.py 一致。"""
    try:
        parts1 = [int(x) for x in str(v1).split(".")]
        parts2 = [int(x) for x in str(v2).split(".")]
        for a, b in zip(parts1, parts2):
            if a < b:
                return -1
            if a > b:
                return 1
        if len(parts1) != len(parts2):
            return -1 if len(parts1) < len(parts2) else 1
        return 0
    except Exception:
        if v1 == v2:
            return 0
        return -1 if str(v1) < str(v2) else 1


# ---------------------------------------------------------------------------
# 查 release
# ---------------------------------------------------------------------------

def clear_cache() -> None:
    with _CACHE_LOCK:
        _CACHE.update(key=None, at=0.0, data=None)


def cached_latest() -> dict | None:
    """上一次 fetch_latest 的结果（过期也算），没查过返回 None。

    给"打开弹窗"那条必须**离线且快**的路径用：界面想显示"最新 1.0.1"，但打开
    弹窗不能打网络 —— 网络不通时那会让弹窗卡十几秒才出来。所以有缓存就顺手显示，
    没有就空着，等用户真点「检查更新」。
    """
    with _CACHE_LOCK:
        data = _CACHE["data"]
        return dict(data) if data else None


def _pick_assets(assets: list[tuple[str, str, int, str]], prefix: str
                 ) -> tuple[str, str, str, str, int, str]:
    """按 update.py:_check_github 的规则挑包，返回 (zip_name, zip_url, exe_name, exe_url)。

    zip 的挑选**必须**保留"挑不到前缀就退回第一个 .zip"这条兜底 —— 那是程序自己的
    行为，控制台不跟上的话两边就会给出不同的答案。

    安装包则**刻意不兜底**。多挑一个 exe 出来比挑不到更坏：它会装上一个来路不明的
    可执行文件。挑不到就是 None，界面据此把「下载并安装」置灰并说明原因 —— release
    里确实可能没有安装包（v1.0.0 就没有，见 UPDATING.md）。
    """
    zip_name = zip_url = ""
    if prefix:
        for name, url, _size, _dig in assets:
            if url and name.endswith(".zip") and name.startswith(prefix):
                zip_name, zip_url = name, url
                break
    if not zip_url:
        for name, url, _size, _dig in assets:
            if url and name.endswith(".zip"):
                zip_name, zip_url = name, url
                break

    exe_name = exe_url = ""
    exe_size = 0
    exe_digest = ""
    for name, url, size, dig in assets:
        if url and name.endswith(".exe") and name.startswith(INSTALLER_PREFIX):
            exe_name, exe_url, exe_size, exe_digest = name, url, size, dig
            break

    return zip_name, zip_url, exe_name, exe_url, exe_size, exe_digest


def _rate_limit_hint(resp: httpx.Response) -> str:
    reset = (resp.headers.get("X-RateLimit-Reset") or "").strip()
    try:
        when = time.strftime("%H:%M", time.localtime(int(reset)))
    except (TypeError, ValueError):
        return ""
    return f"，{when} 左右自动恢复"


def fetch_latest(repo: str | None = None, *, timeout: float = _API_TIMEOUT,
                 force: bool = False) -> dict:
    """查最新 release，返回一个直接能塞进 JSON 响应的字典。

    repo 为 None 时用配置里的 repo，再退回 DEFAULT_REPO —— 和程序自己一致。

    force=False 时走 300 秒缓存。**轮询循环永远不要传 force**：GitHub 未登录的
    API 每小时只有 60 次，弹窗每秒钟问一次会在一分钟内把配额烧光，然后界面开始
    显示限流错误 —— 用户会以为网络坏了。
    """
    cfg = read_update_config()
    repo = (repo or str(cfg.get("repo") or DEFAULT_REPO)).strip()
    prefix = str(cfg.get("asset_prefix") or DEFAULT_ASSET_PREFIX).strip().lower()

    key = f"{repo}|{prefix}"
    if not force:
        with _CACHE_LOCK:
            fresh = (_CACHE["key"] == key and _CACHE["data"] is not None
                     and (time.time() - _CACHE["at"]) < CACHE_TTL)
            if fresh:
                return dict(_CACHE["data"])

    data = _fetch_remote(repo, prefix, cfg, timeout)
    with _CACHE_LOCK:
        _CACHE.update(key=key, at=time.time(), data=dict(data))
    return data


def _fetch_remote(repo: str, prefix: str, cfg: dict, timeout: float) -> dict:
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    try:
        resp = httpx.get(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "OpenObstrator",
            },
            timeout=timeout,
            follow_redirects=True,
        )
    except httpx.TimeoutException:
        raise ReleaseError(
            f"连接 GitHub API 超时（{int(timeout)} 秒）。本机网络可能到不了 "
            f"api.github.com —— 在 {update_config_path()} 里把 repo 指向一个可达的"
            f"镜像仓库，或者稍后重试。"
        )
    except httpx.HTTPError as e:
        raise ReleaseError(f"连不上 api.github.com：{e}。检查本机网络或代理设置。")

    if resp.status_code in (403, 429):
        raise ReleaseError(
            "GitHub API 限流" + _rate_limit_hint(resp)
            + "。未登录的请求每小时只有 60 次，等一会儿再试。"
        )
    if resp.status_code == 404:
        raise ReleaseError(
            f"仓库 {repo} 不存在，或者它还没发布过任何 release。"
            f"检查 {update_config_path()} 里的 repo 配置。"
        )
    if resp.status_code >= 400:
        raise ReleaseError(f"GitHub API 返回 HTTP {resp.status_code}。")

    try:
        data = resp.json()
    except Exception:
        # 状态码 200 但内容不是 JSON —— 中间有代理/网关塞了错误页进来。只看状态码
        # 会当成"查到版本了"，然后拿着空 version 往下走，报错指向完全错误的地方。
        raise ReleaseError(
            f"GitHub 返回的不是 JSON（HTTP {resp.status_code}）。"
            f"多半是网络中间有代理或网关把它换成了错误页，换个网络再试。"
        )
    if not isinstance(data, dict):
        raise ReleaseError("GitHub 返回的 JSON 结构不对（不是对象）。")

    tag = str(data.get("tag_name") or "").strip().lstrip("v")
    if not tag:
        raise ReleaseError(f"release {data.get('name') or ''} 没有 tag_name，拿不到版本号。")

    assets = [
        (str(a.get("name") or "").lower(),
         str(a.get("browser_download_url") or ""),
         int(a.get("size") or 0),
         str(a.get("digest") or ""))
        for a in (data.get("assets") or [])
        if isinstance(a, dict)
    ]
    zip_name, zip_url, exe_name, exe_url, exe_size, exe_digest = _pick_assets(assets, prefix)

    if not zip_url and not exe_url:
        raise ReleaseError(
            f"release {tag} 里既没有 .zip 升级包也没有安装包，没法用。"
            f"（资产：{', '.join(n for n, *_ in assets) or '空'}）"
        )

    return {
        "ok": True,
        "repo": repo,
        "version": tag,
        "zip_name": zip_name,
        "zip_url": _apply_download_base(zip_url, cfg) if zip_url else "",
        "installer_name": exe_name,
        "installer_url": _apply_download_base(exe_url, cfg) if exe_url else "",
        "installer_size": exe_size,
        "installer_digest": exe_digest,
        "notes": str(data.get("body") or "")[:2000],
        "published_at": str(data.get("published_at") or ""),
        "html_url": str(data.get("html_url") or ""),
        "fetched_at": int(time.time()),
    }
