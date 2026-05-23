from __future__ import annotations

import socket


def is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.2)
        return s.connect_ex((host, port)) == 0


def allocate_port(host: str, start: int, end: int, used: set[int]) -> int:
    for port in range(int(start), int(end) + 1):
        if port in used:
            continue
        if is_port_open(host, port):
            continue
        return port
    raise RuntimeError("No free port available in range")
