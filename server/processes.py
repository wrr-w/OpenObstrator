from __future__ import annotations

import csv
import logging
import os
import subprocess
import threading
import time
from dataclasses import dataclass
from io import StringIO
from typing import Mapping, Sequence


def is_pid_running(pid: int) -> bool:
    if not pid:
        return False
    r = subprocess.run(
        ["tasklist", "/FI", f"PID eq {int(pid)}", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
        check=False,
    )
    out = (r.stdout or "").strip()
    if not out or out.startswith("INFO:"):
        return False
    try:
        row = next(csv.reader(StringIO(out)))
    except Exception:
        return False
    if len(row) < 2:
        return False
    try:
        return int(row[1]) == int(pid)
    except ValueError:
        return False


def kill_pid_tree(pid: int) -> None:
    subprocess.run(
        ["taskkill", "/PID", str(int(pid)), "/T", "/F"],
        capture_output=True,
        text=True,
        check=False,
    )


def _norm_path(p) -> str:
    try:
        return os.path.normcase(os.path.abspath(str(p)))
    except Exception:
        return ""


def find_nanoghost_processes(exe_path=None) -> list[dict]:
    """列出本机正在跑的 NanoGhost 进程。

    升级要覆盖某个**具体目录**里的 exe，所以先按可执行文件路径精确匹配 ——
    停错进程等于白停（文件仍被占用，覆盖脚本报 FAIL:copy）。返回项里的 exe 可能
    是空串：进程属于别的账号时 psutil 读不到路径（AccessDenied），这种情况只有
    exe_path=None 的机器级扫描才认得出来。

    exe_path=None 时退化成"凡是叫 NanoGhost.exe 的都算" —— 用来抓注册簿里没有
    记录的野进程。这一档是机器级的，会连别的安装目录一起抓。
    """
    import psutil

    want = _norm_path(exe_path) if exe_path else ""
    out: list[dict] = []
    for proc in psutil.process_iter(["pid", "name", "exe"]):
        try:
            info = proc.info or {}
            pid = int(info.get("pid") or 0)
            if not pid or pid == os.getpid():
                continue
            exe = str(info.get("exe") or "")
            name = str(info.get("name") or "")
            if want:
                if not exe or _norm_path(exe) != want:
                    continue
            elif name.lower() != "nanoghost.exe":
                continue
            out.append({"pid": pid, "exe": exe, "name": name})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    out.sort(key=lambda x: x["pid"])
    return out


@dataclass(frozen=True)
class SpawnResult:
    pid: int
    argv: list[str]


def spawn(argv: Sequence[str]) -> SpawnResult:
    p = subprocess.Popen(
        list(argv),
        cwd=None,
        env=None,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return SpawnResult(pid=int(p.pid), argv=list(argv))


def spawn_with(
    argv: Sequence[str],
    *,
    cwd: str | None = None,
    env: Mapping[str, str] | None = None,
) -> SpawnResult:
    p = subprocess.Popen(
        list(argv),
        cwd=cwd,
        env=dict(env) if env is not None else None,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return SpawnResult(pid=int(p.pid), argv=list(argv))


def spawn_logged(
    argv: Sequence[str],
    *,
    cwd: str | None = None,
    env: Mapping[str, str] | None = None,
    tag: str = "",
    capture_seconds: float = 3.0,
) -> SpawnResult:
    """Spawn a process, capture startup stderr, and log it.

    A background thread reads stderr for up to *capture_seconds*.
    Any output collected is written to the application log buffer.
    Returns immediately (the thread is a daemon).
    """
    logger = logging.getLogger(f"spawn.{tag}" if tag else "spawn")
    p = subprocess.Popen(
        list(argv),
        cwd=cwd,
        env=dict(env) if env is not None else None,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    sr = SpawnResult(pid=int(p.pid), argv=list(argv))

    buf: list[str] = []
    stop = False

    def _reader():
        while not stop:
            try:
                line = p.stderr.readline()
            except Exception:
                break
            if not line:
                break
            buf.append(line.decode("utf-8", errors="replace").rstrip("\r\n"))

    t = threading.Thread(target=_reader, daemon=True)
    t.start()
    time.sleep(capture_seconds)
    stop = True
    try:
        p.stderr.close()
    except Exception:
        pass

    for text in buf:
        if text:
            logger.warning("[%s] %s", tag or "stderr", text)
    return sr
