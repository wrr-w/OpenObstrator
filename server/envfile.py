from __future__ import annotations

import re
from pathlib import Path

_LINE_RE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$")


def parse_env_keys(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = _LINE_RE.match(line)
        if not m:
            continue
        out[m.group(1)] = m.group(2).strip()
    return out


def set_env_kv(path: Path, key: str, value: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines(True) if path.exists() else []
    replaced = False
    newline = _detect_newline(lines)

    new_lines: list[str] = []
    for raw in lines:
        line = raw.rstrip("\r\n")
        m = _LINE_RE.match(line)
        if m and m.group(1) == key and not replaced:
            new_lines.append(f"{key}={value}{newline}")
            replaced = True
        else:
            new_lines.append(raw if raw.endswith(("\n", "\r\n")) else raw + newline)

    if not replaced:
        if new_lines and not new_lines[-1].endswith(("\n", "\r\n")):
            new_lines[-1] += newline
        new_lines.append(f"{key}={value}{newline}")

    _atomic_write(path, "".join(new_lines))


def delete_env_key(path: Path, key: str) -> None:
    if not path.exists():
        return

    lines = path.read_text(encoding="utf-8").splitlines(True)
    out: list[str] = []
    for raw in lines:
        line = raw.rstrip("\r\n")
        m = _LINE_RE.match(line)
        if m and m.group(1) == key:
            continue
        out.append(raw)
    _atomic_write(path, "".join(out))


def _detect_newline(lines: list[str]) -> str:
    for line in lines:
        if line.endswith("\r\n"):
            return "\r\n"
        if line.endswith("\n"):
            return "\n"
    return "\n"


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)
