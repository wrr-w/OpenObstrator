"""OpenObstrator 在线自更新 —— 最小实现。

目标就两件事：**能在线更新** + **装完自动重启**。不引入任何更新框架。

流程：
    1. 查自己的 GitHub release，和 VERSION 比大小
    2. 下新安装器（校验 size + sha256）
    3. **脱离当前进程组**静默启动安装器，然后本进程退出 → 释放 exe
    4. 安装器覆盖安装，装完由它把新版本拉起来（installer.iss 的 [Run]）

为什么必须由安装器来做替换：Windows 上正在运行的 exe 不能被覆盖，替换只能发生在
本进程退出之后。安装器就是这个应用**自己的**安装器，不是外部依赖。

私有仓库：本仓默认是 private，匿名 API 会 404。token 从环境变量
（OPENOBSTRATOR_GITHUB_TOKEN / GITHUB_TOKEN / GH_TOKEN）或 config.yaml 的
`github_token:` 读取；**公开仓库不需要 token**。
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import httpx

log = logging.getLogger(__name__)

REPO = "wrr-w/OpenObstrator"
_API = f"https://api.github.com/repos/{REPO}/releases/latest"
_ASSET_HINT = "openobstratorsetup"        # 安装器资产名（小写前缀匹配）

_CREATE_NO_WINDOW = 0x08000000
_DETACHED_PROCESS = 0x00000008
_CREATE_NEW_PROCESS_GROUP = 0x00000200


def _app_dir() -> Path:
    """exe 所在目录（打包后）；开发态退回仓库根。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def current_version() -> str:
    """读版本号。不启动任何进程。"""
    cands: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", "")
    if meipass:
        cands.append(Path(meipass) / "VERSION")
    cands += [_app_dir() / "VERSION", Path(__file__).resolve().parent.parent / "VERSION"]
    for c in cands:
        try:
            if c.is_file():
                v = c.read_text(encoding="utf-8", errors="ignore").strip()
                if v:
                    return v.lstrip("vV")
        except OSError:
            pass
    return "0.0.0"


def _token(config_path: str | os.PathLike | None = None) -> str:
    """GitHub token：先环境变量，再 config.yaml 的 github_token。公开仓库可留空。"""
    for k in ("OPENOBSTRATOR_GITHUB_TOKEN", "GITHUB_TOKEN", "GH_TOKEN"):
        v = os.environ.get(k)
        if v and v.strip():
            return v.strip()
    if config_path:
        try:
            raw = Path(config_path).read_text(encoding="utf-8", errors="ignore")
            m = re.search(r"^\s*github_token\s*:\s*['\"]?([^'\"\s#]+)", raw, re.M)
            if m:
                return m.group(1).strip()
        except OSError:
            pass
    return ""


def _headers(token: str, *, raw: bool = False) -> dict:
    h = {"User-Agent": "OpenObstrator"}
    h["Accept"] = "application/octet-stream" if raw else "application/vnd.github+json"
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _vt(s: str) -> tuple[int, int, int, int]:
    parts: list[int] = []
    for p in (s or "").lstrip("vV").split("."):
        parts.append(int(p) if p.isdigit() else 0)
    return tuple((parts + [0, 0, 0, 0])[:4])  # type: ignore[return-value]


def check(config_path: str | os.PathLike | None = None, timeout: float = 20.0) -> dict:
    """查最新 release。只读、不下载、不改动 —— 随时可安全调用。"""
    cur = current_version()
    token = _token(config_path)
    data = None
    last: Exception | None = None
    for attempt in range(3):                      # 到 api.github.com 的 TLS 偶发 EOF，重试
        try:
            r = httpx.get(_API, timeout=timeout, follow_redirects=True, headers=_headers(token))
            r.raise_for_status()
            data = r.json()
            break
        except Exception as e:                    # noqa: BLE001
            last = e
            time.sleep(1.5 * (attempt + 1))
    if data is None:
        tip = "" if token else "（仓库若是私有的，请配 github_token）"
        return {"ok": False, "error": f"查询失败: {last}{tip}", "current_version": cur}

    latest = str(data.get("tag_name") or "").lstrip("vV")
    asset = next((a for a in (data.get("assets") or [])
                  if str(a.get("name", "")).lower().startswith(_ASSET_HINT)), None)
    return {
        "ok": True,
        "current_version": cur,
        "latest_version": latest,
        "update_available": bool(latest) and _vt(latest) > _vt(cur),
        "installer_name": (asset or {}).get("name", ""),
        # 私有仓库要用 API 资产地址下载（browser_download_url 带不上 Bearer）
        "installer_url": (asset or {}).get("url", "") or (asset or {}).get("browser_download_url", ""),
        "installer_size": int((asset or {}).get("size") or 0),
        "installer_digest": str((asset or {}).get("digest") or ""),
        "html_url": data.get("html_url") or "",
        "notes": data.get("body") or "",
    }


def _download(url: str, dest: Path, *, token: str = "", expected_size: int = 0,
              expected_sha256: str = "", timeout: float = 600.0) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    got = 0
    last: Exception | None = None
    for attempt in range(3):
        got = 0
        try:
            with httpx.stream("GET", url, timeout=timeout, follow_redirects=True,
                              headers=_headers(token, raw=True)) as r:
                r.raise_for_status()
                with open(tmp, "wb") as f:
                    for chunk in r.iter_bytes(256 * 1024):
                        f.write(chunk)
                        got += len(chunk)
            break
        except Exception as e:                    # noqa: BLE001
            last = e
            time.sleep(1.5 * (attempt + 1))
    else:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"下载失败: {last}")
    if expected_size and got != expected_size:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"下载不完整：{got}/{expected_size} 字节")
    if expected_sha256:
        digest = hashlib.sha256(tmp.read_bytes()).hexdigest()
        if digest != expected_sha256:
            tmp.unlink(missing_ok=True)
            raise RuntimeError("安装包 sha256 校验失败，已丢弃")
    tmp.replace(dest)


def start(downloads_dir: Path, log_dir: Path | None = None,
          config_path: str | os.PathLike | None = None) -> dict:
    """下载并启动安装器；调用方随后应尽快退出（让安装器能覆盖 exe）。"""
    token = _token(config_path)
    info = check(config_path)
    if not info.get("ok"):
        return info
    if not info.get("update_available"):
        return {**info, "started": False,
                "message": f"已是最新版本（{info['current_version']}）"}
    if not info.get("installer_url"):
        return {**info, "ok": False, "started": False,
                "error": "该 release 里没有安装器资产"}

    dest = Path(downloads_dir) / (info["installer_name"]
                                 or f"OpenObstratorSetup-{info['latest_version']}.exe")
    digest = info["installer_digest"]
    if digest.startswith("sha256:"):
        digest = digest.split(":", 1)[1]

    ok_cached = (dest.is_file() and dest.stat().st_size > 1024 * 1024
                 and (not info["installer_size"]
                      or dest.stat().st_size == info["installer_size"]))
    if not ok_cached:
        _download(info["installer_url"], dest, token=token,
                  expected_size=info["installer_size"], expected_sha256=digest)

    log_path = (Path(log_dir) / "self_update.log") if log_dir else dest.with_suffix(".log")
    argv = [str(dest),
            "/VERYSILENT", "/SUPPRESSMSGBOXES", "/SP-", "/NORESTART",
            "/NOCLOSEAPPLICATIONS",      # 关不关自己由我们控制：本进程马上自己退出
            f"/LOG={log_path}"]

    # DETACHED_PROCESS + 新进程组：本进程随后退出/被关，安装器必须活下来干完活
    subprocess.Popen(
        argv,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        close_fds=True,
        creationflags=_DETACHED_PROCESS | _CREATE_NEW_PROCESS_GROUP | _CREATE_NO_WINDOW,
    )
    log.warning("self-update: launched installer %s", argv)
    return {**info, "started": True, "installer_path": str(dest),
            "message": f"已开始升级到 {info['latest_version']}，程序会自动重启"}
