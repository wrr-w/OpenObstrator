# -*- mode: python ; coding: utf-8 -*-

import os
import sys

# 获取 spec 文件所在目录
SPEC_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
SERVER_DIR = os.path.join(SPEC_DIR, "server")
DATA_DIR = os.path.join(SPEC_DIR, "data")
STATIC_DIR = os.path.join(SERVER_DIR, "static")
TEMPLATES_DIR = os.path.join(SERVER_DIR, "templates")

print(f"SPEC_DIR: {SPEC_DIR}")
print(f"SERVER_DIR exists: {os.path.exists(SERVER_DIR)}")
print(f"STATIC_DIR exists: {os.path.exists(STATIC_DIR)}")
print(f"TEMPLATES_DIR exists: {os.path.exists(TEMPLATES_DIR)}")
print(f"DATA_DIR exists: {os.path.exists(DATA_DIR)}")

block_cipher = None

a = Analysis(
    [os.path.join(SPEC_DIR, "main.py")],
    pathex=[SPEC_DIR, SERVER_DIR],
    binaries=[],
    datas=[
        (STATIC_DIR, os.path.join("server", "static")),
        (TEMPLATES_DIR, os.path.join("server", "templates")),
        (DATA_DIR, "data"),
    ],
    hiddenimports=[
        # FastAPI / Uvicorn
        "fastapi",
        "uvicorn",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.protocols.websockets.websockets_impl",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.loops.auto",
        "uvicorn.logging",
        # 标准库动态导入
        "jinja2",
        "jinja2.ext",
        "yaml",
        "psutil",
        "httpx",
        "httpx._transports.default",
        # pydantic
        "pydantic",
        "pydantic.deprecated.decorator",
        # server 子模块
        "server.app",
        "server.configfile",
        "server.envfile",
        "server.hermes_mcp",
        "server.logbuffer",
        "server.nanoghost_mcp",
        "server.ports",
        "server.processes",
        "server.profiles",
        "server.profile_create",
        "server.registry",
        "server.settings",
        "server.skills",
        "server.soulfile",
        "server.template_copy",
        # watchfiles / websockets (uvicorn[standard])
        "watchfiles",
        "websockets",
        "websockets.legacy",
        "websockets.legacy.server",
        "websockets.legacy.client",
        # anyio
        "anyio",
        "anyio._backends._trio",
        "anyio._backends._asyncio",
        # 其他可能缺失的依赖
        "idna",
        "h11",
        "starlette",
        "starlette.middleware",
        "starlette.middleware.cors",
        "starlette.middleware.errors",
        "starlette.routing",
        "starlette.requests",
        "starlette.responses",
        "starlette.staticfiles",
        "starlette.templating",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "PIL",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="OpenObstrator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
