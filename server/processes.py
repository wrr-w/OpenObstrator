from __future__ import annotations

import csv
import logging
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
