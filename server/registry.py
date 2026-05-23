from __future__ import annotations

import json
from pathlib import Path


def _default_registry() -> dict:
    return {
        "version": 2,
        "runtimes": {
            "hermes": {"instances": {}},
            "nanoghost": {"instances": {}},
            "openclaw": {"instances": {}},
        },
        "profiles": {},
    }


def _normalize_registry(raw: dict) -> dict:
    raw.setdefault("version", 1)
    if not isinstance(raw.get("version"), int):
        raw["version"] = 1

    runtimes = raw.get("runtimes")
    if not isinstance(runtimes, dict):
        profiles = raw.get("profiles")
        profiles = profiles if isinstance(profiles, dict) else {}
        raw["runtimes"] = {
            "hermes": {"instances": profiles},
            "nanoghost": {"instances": {}},
            "openclaw": {"instances": {}},
        }
        raw["version"] = 2
        runtimes = raw["runtimes"]

    for rt in ("hermes", "nanoghost", "openclaw"):
        r = runtimes.get(rt)
        if not isinstance(r, dict):
            r = {}
            runtimes[rt] = r
        inst = r.get("instances")
        if not isinstance(inst, dict):
            r["instances"] = {}

    hermes_instances = runtimes["hermes"]["instances"]
    raw["profiles"] = hermes_instances if isinstance(hermes_instances, dict) else {}
    if raw.get("version") < 2:
        raw["version"] = 2
    return raw


def load_registry(path: Path) -> dict:
    if not path.exists():
        return _default_registry()
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return _default_registry()
    return _normalize_registry(raw)


def save_registry(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
