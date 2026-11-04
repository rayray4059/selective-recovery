import copy
import json
import time
from pathlib import Path

from agents.executor import execute
from agents.planner import plan_change
from agents.researcher import research
from agents.verifier import check_stage
from env.tools import Environment
from env.trace import build_trace
from env.workspace import Workspace
from eval.check import check
from tasks.schema import TASKS_DIR


def save_jsonl(path, rows):
    with open(path, "w") as f:
        for row in rows:
            f.write(json.dumps(row, default=str) + "\n")


def agent_totals(calls):
    totals = {}
    for c in calls:
        t = totals.setdefault(c["agent"], {"calls": 0, "wall_s": 0.0, "prompt_tokens": 0, "completion_tokens": 0})
        t["calls"] += 1
        for k in ("wall_s", "prompt_tokens", "completion_tokens"):
            t[k] += c["stats"][k]
    for t in totals.values():
        t["wall_s"] = round(t["wall_s"], 2)
    return totals


def run_task(task, llm, run_dir, hook=None, fault=None, env=None, verify=False):
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    if env is None:
        env = Environment(Workspace(run_dir / "ws", source=TASKS_DIR / task.codebase))
    if fault:
        hook = fault.hook
        fault.setup(env)
    hook = hook or (lambda stage, x: x)
    label = fault.name if fault else "hook"
    injected = {}
    checks = []
    start = time.time()

    env.step = 1
    facts, calls = research(env, llm, task)
    before = copy.deepcopy(facts)
    facts = hook("facts", facts)
    if facts != before:
        injected["facts"] = label
    if verify:
        ok, problems, more = check_stage(env, llm, task, "facts", facts)
        calls += more
        checks.append({"stage": "facts", "ok": ok, "problems": problems, "redone": not ok})
        if not ok:
            facts, more = research(env, llm, task, feedback=problems)
            calls += more
    env.step = 2
    plan, more = plan_change(env, llm, task, facts)
    calls += more
    before = copy.deepcopy(plan)
    plan = hook("plan", plan)
    if plan != before:
        injected["plan"] = label
    if verify:
        ok, problems, more = check_stage(env, llm, task, "plan", facts, plan)
        calls += more
        checks.append({"stage": "plan", "ok": ok, "problems": problems, "redone": not ok})
        if not ok:
            plan, more = plan_change(env, llm, task, facts, feedback=problems)
            calls += more
    env.step = 3
    actions, more = execute(env, llm, task, plan, facts)
    calls += more
    wall_s = round(time.time() - start, 2)

    res = check(task, env)
    res.update({"task": task.id, "wall_s": wall_s, "agents": agent_totals(calls),
                "registry": env.registry, "channel": env.channel,
                "fault": fault.info() if fault else None, "injected": injected})
    if verify:
        res["verify"] = checks
    (run_dir / "config.json").write_text(json.dumps({
        "task": task.id, "model": llm.model, "seed": llm.seed,
        "temperature": llm.temperature, "max_tokens": llm.max_tokens, "verify": verify,
    }, indent=2))
    (run_dir / "artifacts.json").write_text(json.dumps({"facts": facts, "plan": plan, "actions": actions}, indent=2))
    save_jsonl(run_dir / "llm_calls.jsonl", calls)
    save_jsonl(run_dir / "tool_log.jsonl", env.log)
    t0 = time.time()
    nodes = build_trace(env.log, calls, actions, facts, plan, injected)
    save_jsonl(run_dir / "trace.jsonl", nodes)
    res["trace"] = {
        "nodes": len(nodes),
        "bytes": (run_dir / "trace.jsonl").stat().st_size + (run_dir / "tool_log.jsonl").stat().st_size,
        "build_ms": round((time.time() - t0) * 1000, 2),
    }
    (run_dir / "result.json").write_text(json.dumps(res, indent=2, default=str))
    return res
