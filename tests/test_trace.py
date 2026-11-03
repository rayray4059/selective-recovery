import json

from agents.run import run_task
from env.tools import Environment
from env.trace import build_trace, compare, downstream
from env.workspace import Workspace
from fakes import DONE, FakeLLM
from tasks.schema import TASKS_DIR, load_tasks

TASK = {t.id: t for t in load_tasks()}["t03_min_charge"]
FIX = (TASKS_DIR / "solutions" / "t03_min_charge" / "billing" / "payments.py").read_text()
FACTS = json.dumps({"facts": [{"fact": "The minimum charge is 50 cents (amount_too_small).", "source": "docs/policy.md"}]})
PLAN = json.dumps({"steps": [{"file": "billing/payments.py", "function": "charge",
                              "new_signature": "def charge(client, amount_cents, currency, idempotency_key=None):",
                              "change": "raise amount_too_small under 50 cents"}]})
WRITE = '{"tool": "write_file", "path": "billing/payments.py"}\n```python\n' + FIX + "```"


def load(run_dir):
    return [json.loads(line) for line in (run_dir / "trace.jsonl").read_text().splitlines()]


def run(tmp_path, name="run", replies=None, hook=None):
    res = run_task(TASK, FakeLLM(replies or [FACTS, PLAN, WRITE, DONE]), tmp_path / name, hook=hook)
    return res, load(tmp_path / name)


def find(nodes, kind, label=None, actor=None):
    return [n for n in nodes if n["kind"] == kind and (label is None or n["label"] == label)
            and (actor is None or n["actor"] == actor)]


def test_nodes_and_inputs(tmp_path):
    res, nodes = run(tmp_path)
    facts, plan = find(nodes, "facts")[0], find(nodes, "plan")[0]
    doc_reads = [n for n in find(nodes, "read", actor="researcher") if "docs/" in n["label"]]
    planner_read = find(nodes, "read", "read_file billing/payments.py", "planner")[0]
    exec_read = find(nodes, "read", "read_file billing/payments.py", "executor")[0]
    write, done = find(nodes, "action")
    assert len(doc_reads) == 4 and set(n["id"] for n in doc_reads) <= set(facts["inputs"])
    assert plan["inputs"] == [facts["id"], planner_read["id"]]
    assert write["label"] == "write_file billing/payments.py"
    assert {facts["id"], plan["id"], exec_read["id"]} <= set(write["inputs"])
    assert done["label"] == "done" and write["id"] in done["inputs"]
    assert facts["tokens"] == 2 and res["trace"]["nodes"] == len(nodes)


def test_downstream(tmp_path):
    _, nodes = run(tmp_path)
    facts, plan = find(nodes, "facts")[0], find(nodes, "plan")[0]
    actions = [n["id"] for n in find(nodes, "action")]
    assert downstream(nodes, facts["id"]) == [plan["id"]] + actions
    assert downstream(nodes, plan["id"]) == actions
    policy = find(nodes, "read", "read_file docs/policy.md")[0]
    assert set([facts["id"], plan["id"]] + actions) <= set(downstream(nodes, policy["id"]))


def test_read_links_to_the_write_that_made_it(tmp_path):
    env = Environment(Workspace(tmp_path / "ws", source=TASKS_DIR / "codebase"))
    env.step = 3
    env.call("write_file", "executor", path="billing/x.py", text="X = 1\n")
    env.step = 1
    env.call("read_file", "researcher", path="billing/x.py")
    env.call("read_file", "researcher", path="docs/policy.md")
    nodes = build_trace(env.log)
    write, read_x, read_doc = nodes
    assert read_x["inputs"] == [write["id"]] and read_doc["inputs"] == []
    assert downstream(nodes, write["id"]) == [read_x["id"]]


def test_executor_read_after_its_own_write(tmp_path):
    replies = [FACTS, PLAN, WRITE, '{"tool": "read_file", "path": "billing/payments.py"}', DONE]
    _, nodes = run(tmp_path, replies=replies)
    write, read, _ = find(nodes, "action")
    assert read["label"] == "read_file billing/payments.py" and write["id"] in read["inputs"]


def test_bad_turns_are_nodes(tmp_path):
    _, nodes = run(tmp_path, replies=[FACTS, PLAN, "not json", WRITE, DONE])
    assert [n["label"] for n in find(nodes, "action")] == ["bad_reply", "write_file billing/payments.py", "done"]


def test_compare_clean_vs_swapped_facts(tmp_path):
    _, clean = run(tmp_path, "clean")
    _, same = run(tmp_path, "same")
    swapped = lambda stage, x: [{"fact": "The minimum charge is 25 cents.", "source": "docs/policy.md"}] if stage == "facts" else x
    _, faulted = run(tmp_path, "faulted", hook=swapped)
    assert compare(clean, same) == []
    assert compare(clean, faulted) == ["facts/researcher/facts#1"]


def test_overhead_recorded(tmp_path):
    res, _ = run(tmp_path)
    assert res["trace"]["bytes"] > 0 and res["trace"]["build_ms"] >= 0
    saved = json.loads((tmp_path / "run" / "result.json").read_text())
    assert saved["trace"]["nodes"] == res["trace"]["nodes"]
