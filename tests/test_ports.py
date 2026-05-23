from server.ports import allocate_port


def test_allocate_port_skips_used_set(monkeypatch):
    def fake_open(host: str, port: int) -> bool:
        return False

    monkeypatch.setattr("server.ports.is_port_open", fake_open)
    p = allocate_port("127.0.0.1", 18000, 18002, used={18000})
    assert p == 18001
