from __future__ import annotations

import logging
import threading
import time
from collections import deque


class LogBufferHandler(logging.Handler):
    def __init__(self, *, max_lines: int = 2000) -> None:
        super().__init__()
        self._max_lines = int(max_lines)
        self._lock = threading.Lock()
        self._lines: deque[str] = deque(maxlen=self._max_lines)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record.created))
            msg = record.getMessage()
            msg = msg.replace("\r", "").replace("\n", "\\n")
            line = f"{ts} {record.levelname} {record.name}: {msg}"
        except Exception:
            return
        with self._lock:
            self._lines.append(line)

    def get_lines(self, *, limit: int = 500) -> list[str]:
        lim = max(1, int(limit))
        with self._lock:
            if lim >= len(self._lines):
                return list(self._lines)
            return list(self._lines)[-lim:]


_handler: LogBufferHandler | None = None
_installed = False


def install_log_buffer(*, max_lines: int = 2000) -> None:
    global _installed, _handler
    if _installed:
        return
    _installed = True
    _handler = LogBufferHandler(max_lines=max_lines)
    _handler.setLevel(logging.INFO)
    root = logging.getLogger()
    root.addHandler(_handler)
    root.setLevel(logging.INFO)


def get_log_lines(*, limit: int = 500) -> list[str]:
    if _handler is None:
        return []
    return _handler.get_lines(limit=limit)

