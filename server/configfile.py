from __future__ import annotations

from pathlib import Path

import yaml


def read_raw_yaml(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def validate_yaml_mapping(yaml_text: str) -> dict:
    if not yaml_text.strip():
        return {}

    try:
        parsed = yaml.safe_load(yaml_text)
    except yaml.YAMLError as e:
        raise ValueError(str(e)) from e

    if parsed is None:
        parsed = {}

    if not isinstance(parsed, dict):
        raise ValueError("YAML must be a mapping")

    return parsed


def write_raw_yaml(path: Path, yaml_text: str) -> None:
    validate_yaml_mapping(yaml_text)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(yaml_text, encoding="utf-8")
    tmp.replace(path)
