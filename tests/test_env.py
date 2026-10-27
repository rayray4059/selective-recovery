import pytest

from env.state_store import StateStore
from env.tools import Environment, ToolError


def make_env(tmp_path):
    store = StateStore()
    store.set("order:1", {"status": "shipped", "total": 40.0}, actor="seed")
    store.set("cust:1", {"name": "Ada", "address": "1 Main St"}, actor="seed")
    return Environment(store=store, workspace=tmp_path / "ws")


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


def test_update_record_is_logged_and_reversible(tmp_path):
    env = make_env(tmp_path)
    v0 = env.store.version
    env.call("update_record", actor="executor", id="order:1", field="status", value="cancelled")
    assert env.store.get("order:1")["status"] == "cancelled"
    assert env.store.writes_by("executor")[0].key == "order:1"
    env.store.rollback_to(v0)
    assert env.store.get("order:1")["status"] == "shipped"


def test_tool_errors_are_recorded(tmp_path):
    env = make_env(tmp_path)
    with pytest.raises(ToolError):
        env.call("read_record", actor="researcher", id="order:404")
    assert env.calls[-1]["status"] == "error"
    with pytest.raises(ToolError):
        env.call("no_such_tool", actor="executor")


def test_write_file_cannot_escape_workspace(tmp_path):
    env = make_env(tmp_path)
    env.call("write_file", actor="executor", path="notes/a.txt", text="hi")
    assert (env.workspace / "notes" / "a.txt").read_text() == "hi"
    with pytest.raises(ToolError):
        env.call("write_file", actor="executor", path="../evil.txt", text="x")


def test_refund_is_compensable_not_deleted(tmp_path):
    env = make_env(tmp_path)
    r = env.call("issue_refund", actor="executor", order="order:1", amount=25.0)
    env.reverse_refund(r["ledger_index"])
    assert len(env.ledger) == 2
    assert env.ledger[0]["amount"] == 25.0 and env.ledger[1]["amount"] == -25.0
    with pytest.raises(ToolError):
        env.call("issue_refund", actor="executor", order="order:1", amount=0)


def test_outbox_is_append_only(tmp_path):
    env = make_env(tmp_path)
    env.call("send_message", actor="executor", customer="cust:1", text="Refund issued")
    assert len(env.outbox) == 1
    env.store.rollback_to(0)          # state rollback does not touch the outbox
    assert len(env.outbox) == 1
