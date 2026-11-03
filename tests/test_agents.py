import json
from types import SimpleNamespace

from agents.llm import LLM
from fakes import DONE, FakeLLM
from agents.run import run_task
from tasks.schema import TASKS_DIR, load_tasks

BY_ID = {t.id: t for t in load_tasks()}
TASK = BY_ID["t03_min_charge"]
FIX = (TASKS_DIR / "solutions" / "t03_min_charge" / "billing" / "payments.py").read_text()
FACTS = json.dumps({"facts": [{"fact": "The minimum charge is 50 cents (amount_too_small).", "source": "docs/policy.md"}]})
PLAN = json.dumps({"steps": [{"file": "billing/payments.py", "function": "charge",
                              "new_signature": "def charge(client, amount_cents, currency, idempotency_key=None):",
                              "change": "raise amount_too_small under 50 cents"}]})
WRITE = '{"tool": "write_file", "path": "billing/payments.py"}\n```python\n' + FIX + "```"
def text_of(call):
    return "\n".join(m["content"] for m in call["messages"])


def test_full_run_passes_and_saves_files(tmp_path):
    llm = FakeLLM([FACTS, PLAN, WRITE, DONE])
    res = run_task(TASK, llm, tmp_path / "run")
    assert res["passed"] and res["unauthorized"] == []
    for name in ("config.json", "artifacts.json", "llm_calls.jsonl", "tool_log.jsonl", "result.json"):
        assert (tmp_path / "run" / name).is_file()
    assert res["agents"]["executor"]["calls"] == 2
    assert llm.seen[0]["schema"] and llm.seen[1]["schema"] and llm.seen[2]["schema"] is None


def test_executor_never_sees_docs(tmp_path):
    llm = FakeLLM([FACTS, PLAN, WRITE, DONE])
    run_task(TASK, llm, tmp_path / "run")
    assert "The minimum charge is 50 cents. Smaller" in text_of(llm.seen[0])
    for call in llm.seen[2:]:
        assert "Smaller positive amounts" not in text_of(call)


def test_reads_logged_under_each_role(tmp_path):
    run_task(TASK, FakeLLM([FACTS, PLAN, WRITE, DONE]), tmp_path / "run")
    log = [json.loads(line) for line in (tmp_path / "run" / "tool_log.jsonl").read_text().splitlines()]
    doc_reads = {r["actor"] for r in log if r["tool"] == "read_file" and r["args"]["path"].startswith("docs/")}
    code_reads = {(r["actor"], r["step"]) for r in log if r["tool"] == "read_file" and r["args"]["path"] == "billing/payments.py"}
    assert doc_reads == {"researcher"}
    assert code_reads == {("planner", 2), ("executor", 3)}


def test_bad_reply_gets_error_and_loop_continues(tmp_path):
    llm = FakeLLM([FACTS, PLAN, "I will now edit the file.", '{"tool": "write_file", "path": "billing/payments.py"}', WRITE, DONE])
    res = run_task(TASK, llm, tmp_path / "run")
    assert res["passed"]
    assert llm.seen[3]["messages"][-1]["content"].startswith("Error: start your reply")
    assert llm.seen[4]["messages"][-1]["content"].startswith("Error: write_file needs")


def test_loop_stops_after_max_turns(tmp_path):
    llm = FakeLLM([FACTS, PLAN] + ['{"tool": "run_tests"}'] * 10)
    res = run_task(TASK, llm, tmp_path / "run")
    assert res["agents"]["executor"]["calls"] == 6 and not res["passed"]


def test_tool_errors_go_back_to_executor(tmp_path):
    llm = FakeLLM([FACTS, PLAN, '{"tool": "read_file", "path": "nope.py"}', WRITE, DONE])
    res = run_task(TASK, llm, tmp_path / "run")
    assert res["passed"]
    assert llm.seen[3]["messages"][-1]["content"].startswith("Error: no such file")


def test_hook_changes_what_planner_sees(tmp_path):
    llm = FakeLLM([FACTS, PLAN, WRITE, DONE])

    def hook(stage, artifact):
        if stage == "facts":
            return [{"fact": "The minimum charge is 25 cents.", "source": "docs/policy.md"}]
        return artifact

    run_task(TASK, llm, tmp_path / "run", hook=hook)
    assert "25 cents" in text_of(llm.seen[1]) and "50 cents" not in text_of(llm.seen[1])
    assert "The minimum charge is 25 cents." in text_of(llm.seen[2])
    saved = json.loads((tmp_path / "run" / "artifacts.json").read_text())
    assert saved["facts"][0]["fact"] == "The minimum charge is 25 cents."


def test_tune_tasks_load_and_point_at_pilot():
    tune = load_tasks(TASKS_DIR / "tune.jsonl")
    assert len(tune) == 5
    for t in tune:
        assert (TASKS_DIR / t.codebase / t.target_files[0]).is_file()
        assert (TASKS_DIR / t.expected.hidden_test).is_file()


def test_llm_request_shape():
    sent = {}

    def create(**kwargs):
        sent.update(kwargs)
        return SimpleNamespace(usage=SimpleNamespace(prompt_tokens=3, completion_tokens=2),
                               choices=[SimpleNamespace(finish_reason="stop", message=SimpleNamespace(content="{}"))])

    client = SimpleNamespace(models=SimpleNamespace(list=lambda: SimpleNamespace(data=[SimpleNamespace(id="qwen")])),
                             chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    llm = LLM(client=client)
    reply, stats = llm.chat([{"role": "user", "content": "hi"}], schema={"type": "object"})
    assert reply == "{}" and stats["completion_tokens"] == 2
    assert sent["temperature"] == 0.0 and sent["seed"] == 0 and sent["model"] == "qwen"
    assert sent["response_format"]["json_schema"]["schema"] == {"type": "object"}
    assert sent["extra_body"]["chat_template_kwargs"]["enable_thinking"] is False


def test_parser_accepts_content_key_and_bare_code_block():
    from agents.executor import parse_action
    targets = ["billing/payments.py"]
    action, err = parse_action(json.dumps({"tool": "write_file", "path": "billing/payments.py", "content": "x = 1\n"}), targets)
    assert err is None and action["text"] == "x = 1\n"
    action, err = parse_action("```python\nx = 2\n```", targets)
    assert action == {"tool": "write_file", "path": "billing/payments.py", "text": "x = 2\n"}
    action, err = parse_action("```python\nx = 2\n```", ["a.py", "b.py"])
    assert action is None and err.startswith("start your reply")
    action, err = parse_action(WRITE, targets)
    assert action["text"] == FIX


def test_executor_feedback_has_no_commit_ids(tmp_path):
    llm = FakeLLM([FACTS, PLAN, WRITE, DONE])
    run_task(TASK, llm, tmp_path / "run")
    assert "commit" not in llm.seen[3]["messages"][-1]["content"]
