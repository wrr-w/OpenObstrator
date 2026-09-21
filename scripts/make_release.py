r"""把 dist/OpenObstrator.exe 打成 GitHub Releases 用的分发件。

用法:
    python scripts/make_release.py            # 只打包
    python scripts/make_release.py --publish  # 打包并调 gh 发布 Release

产出（dist/release/）：
    OpenObstrator-v{VERSION}-win64.zip    绿色包：exe + 默认配置
发布时同时上传安装器 dist/installer/OpenObstratorSetup-{VERSION}.exe。

为什么不能直接右键压缩：
1. zip 里**不能多一层 OpenObstrator\ 目录** —— 解压出来必须就是 exe 所在的那一层。
2. 绝不能把 .env / 私钥混进去：这些都是公开下载的。命中直接失败，不做静默过滤。
"""
from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")
EXE = os.path.join(DIST, "OpenObstrator.exe")
DEFAULT_CONFIG = os.path.join(ROOT, "scripts", "config.default.yaml")
INSTALLER_DIR = os.path.join(DIST, "installer")
RELEASE_DIR = os.path.join(DIST, "release")

REPO = "wrr-w/OpenObstrator"

# 绝不能进包的东西。命中就报错，不静默过滤。
FORBIDDEN_NAMES = {".env"}
FORBIDDEN_DIRS = {"instances", ".git", "__pycache__", ".venv", "venv"}
FORBIDDEN_SUFFIXES = (".pfx", ".p12", ".keystore", ".jks")
PRIVATE_KEY_MARKERS = (
    b"PRIVATE KEY", b"-----BEGIN RSA ", b"-----BEGIN DSA ",
    b"-----BEGIN EC ", b"-----BEGIN OPENSSH ", b"PuTTY-User-Key-File",
)


def read_version() -> str:
    path = os.path.join(ROOT, "VERSION")
    if not os.path.isfile(path):
        sys.exit("[ERROR] 找不到 VERSION 文件")
    return open(path, encoding="utf-8").read().strip()


def secret_reason(path: str, name: str) -> str | None:
    low = name.lower()
    if low in FORBIDDEN_NAMES:
        return "文件名本身就是凭据文件"
    if low.endswith(FORBIDDEN_SUFFIXES):
        return "密钥库格式"
    if low.endswith((".pem", ".key", ".crt", ".cer")):
        try:
            head = open(path, "rb").read(65536)
        except OSError:
            return None
        if any(m in head for m in PRIVATE_KEY_MARKERS):
            return "内容含私钥"
    return None


def build_zip(version: str) -> str:
    if not os.path.isfile(EXE):
        sys.exit(f"[ERROR] 找不到 {EXE}，先跑 build.bat / build_installer.bat")
    if not os.path.isfile(DEFAULT_CONFIG):
        sys.exit(f"[ERROR] 找不到 {DEFAULT_CONFIG}")

    os.makedirs(RELEASE_DIR, exist_ok=True)
    out = os.path.join(RELEASE_DIR, f"OpenObstrator-v{version}-win64.zip")

    # (归档内路径, 本地文件)
    entries = [
        ("OpenObstrator.exe", EXE),
        ("data/config.yaml", DEFAULT_CONFIG),
    ]
    for rel, src in entries:
        reason = secret_reason(src, os.path.basename(src))
        if reason:
            sys.exit(f"[ERROR] 包里出现敏感文件: {rel} ({reason})")
        top = rel.split("/")[0]
        if top in FORBIDDEN_DIRS:
            sys.exit(f"[ERROR] 包里出现不该打的目录: {rel}")

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for rel, src in entries:
            z.write(src, rel)

    digest = hashlib.sha256(open(out, "rb").read()).hexdigest()
    print(f"[OK] {out}")
    print(f"     {os.path.getsize(out)} bytes  sha256={digest}")
    return out


def find_installer(version: str) -> str | None:
    path = os.path.join(INSTALLER_DIR, f"OpenObstratorSetup-{version}.exe")
    return path if os.path.isfile(path) else None


def publish(version: str, zip_path: str, notes: str) -> None:
    tag = f"v{version}"
    assets = [zip_path]
    inst = find_installer(version)
    if inst:
        assets.append(inst)
    else:
        print(f"[WARN] 没找到安装器 OpenObstratorSetup-{version}.exe，只发 zip")

    cmd = ["gh", "release", "create", tag, *assets,
           "--repo", REPO, "--title", f"OpenObstrator {version}"]
    cmd += ["--notes", notes or f"OpenObstrator {version}"]
    print("[..] " + " ".join(cmd))
    r = subprocess.run(cmd, cwd=ROOT)
    sys.exit(r.returncode)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true", help="打包后调用 gh release create 发布")
    ap.add_argument("--notes", default="", help="Release 说明")
    args = ap.parse_args()

    version = read_version()
    print(f"version = {version}")
    zip_path = build_zip(version)

    if args.publish:
        publish(version, zip_path, args.notes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
