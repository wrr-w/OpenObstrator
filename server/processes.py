from __future__ import annotations

import csv
import logging
import subprocess
import threading
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
) -> SpawnResult:
    """Spawn a process and log its stderr in a background daemon thread.

    Returns immediately (non-blocking).  Any stderr output from the
    spawned process appears in the application log buffer so you can
    see startup errors or runtime diagnostics.
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

    def _reader():
        with p.stderr:
            for line in iter(p.stderr.readline, b""):
                text = line.decode("utf-8", errors="replace").rstrip("\r\n")
                if text:
                    logger.warning("[%s] %s", tag or "stderr", text)

    t = threading.Thread(target=_reader, daemon=True)
    t.start()
    return sr
