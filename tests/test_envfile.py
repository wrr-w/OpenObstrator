from pathlib import Path

from server.envfile import delete_env_key, parse_env_keys, set_env_kv


def test_set_env_preserves_comments_and_order(tmp_path: Path):
    p = tmp_path / ".env"
    p.write_text("# c1\nA=1\n\n# c2\nB=2\n", encoding="utf-8")
    set_env_kv(p, "B", "999")
    assert p.read_text(encoding="utf-8") == "# c1\nA=1\n\n# c2\nB=999\n"


def test_set_env_appends_when_missing(tmp_path: Path):
    p = tmp_path / ".env"
    p.write_text("A=1\n", encoding="utf-8")
    set_env_kv(p, "B", "2")
    assert p.read_text(encoding="utf-8") == "A=1\nB=2\n"


def test_delete_env_key(tmp_path: Path):
    p = tmp_path / ".env"
    p.write_text("A=1\nB=2\n", encoding="utf-8")
    delete_env_key(p, "A")
    assert p.read_text(encoding="utf-8") == "B=2\n"


def test_parse_env_keys(tmp_path: Path):
    p = tmp_path / ".env"
    p.write_text("# x\nA=1\nB = 2\nexport C=3\n", encoding="utf-8")
    keys = parse_env_keys(p)
    assert keys == {"A": "1", "B": "2", "C": "3"}
