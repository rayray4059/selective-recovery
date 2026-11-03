from env.state_store import StateStore


def test_store_versions_and_log():
    s = StateStore()
    assert s.version == 0
    s.set("a", 1, actor="x")
    s.set("a", 2, actor="y")
    assert s.version == 2 and s.key_version("a") == 2
    assert [e.actor for e in s.log] == ["x", "y"]
    assert s.log[1].old == 1 and s.log[1].new == 2


def test_store_rollback_restores_old_values_and_removes_new_keys():
    s = StateStore()
    s.set("a", 1, actor="seed")
    v = s.version
    s.set("a", 2, actor="bad")
    s.set("b", 9, actor="bad")
    s.rollback_to(v)
    assert s.get("a") == 1 and not s.exists("b")
    assert s.version == v and len(s.log) == 1


def test_store_returns_copies():
    s = StateStore()
    s.set("a", {"x": 1}, actor="seed")
    got = s.get("a")
    got["x"] = 99
    assert s.get("a") == {"x": 1}
