import sys
from pathlib import Path

import pytest

from env.tools import Environment, ToolError
from env.workspace import Workspace

PILOT = Path(__file__).resolve().parent.parent / "scripts" / "pilot"


def make_env(tmp_path, strict=False):
    src = tmp_path / "src"
    (src / "billing").mkdir(parents=True)
    (src / "docs").mkdir()
    (src / "billing" / "money.py").write_text("def add(a, b):\n    return a + b\n")
    (src / "docs" / "rules.md").write_text("money is cents\n")
    return Environment(Workspace(tmp_path / "ws", source=src), strict=strict)


def add_tests(env, body):
    env.call("write_file", "executor", path="tests/test_money.py",
             text="from billing.money import add\n\n\ndef test_add():\n    " + body + "\n")


def test_read_and_list(tmp_path):
    env = make_env(tmp_path)
    assert env.call("list_files", "researcher") == ["billing/money.py", "docs/rules.md"]
    assert env.call("read_file", "planner", path="docs/rules.md") == "money is cents\n"
    assert env.unauthorized() == []


def test_write_commits_and_is_logged(tmp_path):
    env = make_env(tmp_path)
    env.step = 3
    res = env.call("write_file", "executor", path="billing/money.py", text="x = 1\n")
    rec = env.log[-1]
    assert rec["status"] == "ok" and rec["step"] == 3 and rec["flags"] == []
    assert rec["commit_before"] != rec["commit_after"] == res["commit"]
    assert env.ws.changed_files(rec["commit_before"], rec["commit_after"]) == ["billing/money.py"]


def test_delete_file(tmp_path):
    env = make_env(tmp_path)
    env.call("delete_file", "executor", path="billing/money.py")
    assert "billing/money.py" not in env.ws.files()
    with pytest.raises(ToolError):
        env.call("delete_file", "executor", path="billing/money.py")


def test_researcher_write_is_flagged_but_happens(tmp_path):
    env = make_env(tmp_path)
    env.call("write_file", "researcher", path="billing/new.py", text="x = 1\n")
    assert (env.ws.path / "billing" / "new.py").exists()
    assert env.unauthorized()[0]["flags"] == ["tool_not_allowed"]


def test_protected_path_is_flagged(tmp_path):
    env = make_env(tmp_path)
    env.call("delete_file", "executor", path="docs/rules.md")
    assert env.unauthorized()[0]["flags"] == ["protected_path"]
    assert "docs/rules.md" not in env.ws.files()


def test_strict_mode_blocks(tmp_path):
    env = make_env(tmp_path, strict=True)
    with pytest.raises(ToolError):
        env.call("write_file", "researcher", path="billing/new.py", text="x")
    with pytest.raises(ToolError):
        env.call("delete_file", "executor", path="docs/rules.md")
    assert [r["status"] for r in env.log] == ["blocked", "blocked"]
    assert env.ws.files() == ["billing/money.py", "docs/rules.md"]
    assert len(env.unauthorized()) == 2


@pytest.mark.parametrize("path", ["../evil.txt", "/tmp/evil.txt", ".git/config"])
def test_outside_workspace_is_always_an_error(tmp_path, path):
    env = make_env(tmp_path)
    with pytest.raises(ToolError):
        env.call("write_file", "executor", path=path, text="x")
    assert env.log[-1]["status"] == "error"
    assert not (tmp_path / "evil.txt").exists()


def test_bad_calls_are_logged_errors(tmp_path):
    env = make_env(tmp_path)
    with pytest.raises(ToolError):
        env.call("rm_rf", "executor")
    with pytest.raises(ToolError):
        env.call("read_file", "executor", path="nope.py")
    with pytest.raises(ToolError):
        env.call("read_file", "executor", file="docs/rules.md")
    assert [r["status"] for r in env.log] == ["error", "error", "error"]


def test_run_tests(tmp_path):
    env = make_env(tmp_path)
    assert env.call("run_tests", "executor")["passed"] is None
    add_tests(env, "assert add(2, 3) == 5")
    assert env.call("run_tests", "executor")["passed"] is True
    add_tests(env, "assert add(2, 3) == 6")
    assert env.call("run_tests", "executor")["passed"] is False
    assert env.ws.git("status", "--porcelain") == ""


def test_rollback_does_not_undo_publish_or_post(tmp_path):
    env = make_env(tmp_path)
    env.call("write_file", "executor", path="billing/money.py", text="broken\n")
    rel = env.call("publish_release", "executor", version="1.0.1")
    env.call("post_message", "executor", channel="releases", text="1.0.1 is out")
    env.ws.rollback(env.ws.init_commit)
    assert "broken" not in env.call("read_file", "executor", path="billing/money.py")
    assert env.registry == [rel] and rel["commit"] != env.ws.init_commit
    assert len(env.channel) == 1


def test_second_ticket_sees_first_tickets_files(tmp_path):
    env = make_env(tmp_path)
    env.step = 1
    env.call("write_file", "executor", path="billing/fees.py", text="FEE = 30\n")
    env.step = 2
    assert env.call("read_file", "researcher", path="billing/fees.py") == "FEE = 30\n"


def test_pilot_ticket_solved_through_tools(tmp_path):
    sys.path.insert(0, str(PILOT))
    from check_tickets import run_hidden_test

    env = Environment(Workspace(tmp_path / "ws", source=PILOT / "codebase"))
    fix = (PILOT / "solutions" / "t1_config_timeout" / "billing" / "config.py").read_text()
    assert not run_hidden_test(env.ws.path, PILOT / "hidden_tests" / "test_t1_config_timeout.py")
    env.call("write_file", "executor", path="billing/config.py", text=fix)
    assert run_hidden_test(env.ws.path, PILOT / "hidden_tests" / "test_t1_config_timeout.py")
    assert env.unauthorized() == []
