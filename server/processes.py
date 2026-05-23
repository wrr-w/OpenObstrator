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


def spawn_capture(
    argv: Sequence[str],
    *,
    grace_period: float = 1.5,
) -> tuple[SpawnResult, str | None]:
    """Spawn without custom env, capturing stderr."""
    return spawn_with_capture(argv, cwd=None, env=None, grace_period=grace_period)


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


def spawn_with_capture(
    argv: Sequence[str],
    *,
    cwd: str | None = None,
    env: Mapping[str, str] | None = None,
    grace_period: float = 1.5,
) -> tuple[SpawnResult, str | None]:
    """Spawn a process with stderr captured.

    If the process exits within *grace_period* seconds, returns
    ``(result, stderr_text)`` so the caller can inspect startup errors.

    If the process is still running after the grace period, returns
    ``(result, None)`` — the process appears to have started OK.
    """
    p = subprocess.Popen(
        list(argv),
        cwd=cwd,
        env=dict(env) if env is not None else None,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    sr = SpawnResult(pid=int(p.pid), argv=list(argv))
    try:
        _, err = p.communicate(timeout=grace_period)
    except subprocess.TimeoutExpired:
        p.stderr.close()
        return sr, None
    text = (err or b"").decode("utf-8", errors="replace").strip()
    return sr, text or None
