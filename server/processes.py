from __future__ import annotations

import csv
import subprocess
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


def spawn_healthy(
    argv: Sequence[str],
    *,
    cwd: str | None = None,
    env: Mapping[str, str] | None = None,
    port: int | None = None,
    host: str = "127.0.0.1",
    timeout: float = 7.0,
) -> tuple[SpawnResult, str | None]:
    """Spawn a process, capture stderr, and confirm it stays healthy.

    Polls PID and optionally *port* for up to *timeout* seconds.

    Returns ``(SpawnResult, None)`` if the process stays alive (and the
    port opens, if given).  Returns ``(SpawnResult, error_msg)`` if the
    process dies within the window — *error_msg* includes stderr output.
    """
    from server.ports import is_port_open

    p = subprocess.Popen(
        list(argv),
        cwd=cwd,
        env=dict(env) if env is not None else None,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    sr = SpawnResult(pid=int(p.pid), argv=list(argv))
    deadline = time.time() + timeout

    while time.time() < deadline:
        ret = p.poll()
        if ret is not None:
            err = _read_stderr(p)
            return sr, f"exited code {ret}" + (f":\n{err}" if err else "")
        if not is_pid_running(sr.pid):
            err = _read_stderr(p)
            return sr, f"process died" + (f":\n{err}" if err else "")
        if port is not None and is_port_open(host, port):
            p.stderr.close()
            return sr, None
        time.sleep(0.4)

    # Timeout reached — final check
    if port is not None and not is_port_open(host, port):
        p.stderr.close()
        return sr, f"port {port} did not open within {timeout}s"
    if not is_pid_running(sr.pid):
        err = _read_stderr(p)
        return sr, f"process died" + (f":\n{err}" if err else "")
    p.stderr.close()
    return sr, None


def _read_stderr(p: subprocess.Popen) -> str:
    _, err = p.communicate()
    return (err or b"").decode("utf-8", errors="replace").strip()
