import hashlib
import json
import os
from collections import deque

READ_TOOLS = ("read_file", "list_files")
WRITE_TOOLS = ("write_file", "delete_file")


def digest(x):
    if not isinstance(x, str):
        x = json.dumps(x, sort_keys=True, default=str)
    return hashlib.sha256(x.encode()).hexdigest()[:16]


def stable(rec):
    if rec is None:
        return None
    result = rec.get("result")
    if isinstance(result, dict):
        result = {k: v for k, v in result.items() if k != "commit"}
    return [rec["tool"], rec["args"], rec.get("status"), result, rec.get("error")]


def path_of(rec):
    p = rec["args"].get("path")
    return os.path.normpath(p) if p else None


def build_trace(log, calls=(), actions=(), facts=None, plan=None, injected=None):
    injected = injected or {}
    nodes = []
    last_write = {}
    reads = {"researcher": [], "planner": [], "executor": []}
    made = {}
    turns = []
    llm = {"researcher": [c for c in calls if c["agent"] == "researcher"],
           "planner": [c for c in calls if c["agent"] == "planner"],
           "executor": [c for c in calls if c["agent"] == "executor"]}
    acts = sorted(actions, key=lambda a: a["turn"])
    by_log = {a["log_i"]: a for a in acts if a.get("log_i") is not None}
    next_act = 0

    def add(kind, actor, step, label, inputs, content, log_i=None, call=None):
        node = {"id": f"n{len(nodes)}", "kind": kind, "actor": actor, "step": step, "label": label,
                "inputs": [i for i in inputs if i], "hash": digest(content), "log_i": log_i,
                "tokens": 0, "wall_s": 0.0}
        if call:
            node["tokens"] = call["stats"]["prompt_tokens"] + call["stats"]["completion_tokens"]
            node["wall_s"] = call["stats"]["wall_s"]
        nodes.append(node)
        return node["id"]

    def make_facts():
        if "facts" not in made and llm["researcher"]:
            call = llm["researcher"][0]
            made["facts"] = add("facts", "researcher", 1, "facts", reads["researcher"],
                                facts if facts is not None else call["reply"], call=call)
            if "facts" in injected:
                nodes[-1]["injected"] = injected["facts"]

    def make_plan():
        make_facts()
        if "plan" not in made and llm["planner"]:
            call = llm["planner"][0]
            made["plan"] = add("plan", "planner", 2, "plan", [made.get("facts")] + reads["planner"],
                               plan if plan is not None else call["reply"], call=call)
            if "plan" in injected:
                nodes[-1]["injected"] = injected["plan"]

    def make_turn(a, rec=None):
        make_plan()
        call = llm["executor"][a["turn"]] if a["turn"] < len(llm["executor"]) else None
        inputs = [made.get("facts"), made.get("plan")] + reads["executor"] + turns
        label = a["tool"] or "bad_reply"
        if rec:
            p = path_of(rec)
            label += " " + (p or str(rec["args"].get("version", rec["args"].get("channel", ""))))
            if rec["tool"] in READ_TOOLS and p:
                inputs.append(last_write.get(p))
        content = [call["reply"] if call else "", stable(rec) if rec else a.get("feedback", "")]
        nid = add("action", "executor", 3, label.strip(), inputs, content, log_i=a.get("log_i"), call=call)
        turns.append(nid)
        if rec and rec["tool"] in WRITE_TOOLS and rec.get("status") == "ok":
            last_write[path_of(rec)] = nid

    for i, rec in enumerate(log):
        if rec["actor"] == "planner":
            make_facts()
        if i in by_log:
            while next_act < len(acts) and acts[next_act] is not by_log[i]:
                make_turn(acts[next_act])
                next_act += 1
            make_turn(by_log[i], rec)
            next_act += 1
            continue
        if rec["actor"] == "executor" and llm["executor"]:
            make_plan()
        p = path_of(rec)
        if rec["tool"] in READ_TOOLS:
            inputs = [last_write.get(p)] if p else list(last_write.values())
            nid = add("read", rec["actor"], rec["step"], f"{rec['tool']} {p or ''}".strip(), inputs,
                      rec.get("result", rec.get("error")), log_i=i)
            reads.setdefault(rec["actor"], []).append(nid)
        else:
            nid = add("tool", rec["actor"], rec["step"], f"{rec['tool']} {p or ''}".strip(), [],
                      stable(rec), log_i=i)
            if rec["tool"] in WRITE_TOOLS and rec.get("status") == "ok":
                last_write[p] = nid
    make_plan()
    for a in acts[next_act:]:
        make_turn(a)
    return nodes


def downstream(nodes, node_id):
    children = {}
    for n in nodes:
        for i in n["inputs"]:
            children.setdefault(i, []).append(n["id"])
    seen, out, todo = {node_id}, [], deque([node_id])
    while todo:
        for c in children.get(todo.popleft(), []):
            if c not in seen:
                seen.add(c)
                out.append(c)
                todo.append(c)
    order = {n["id"]: k for k, n in enumerate(nodes)}
    return sorted(out, key=order.get)


def node_keys(nodes):
    counts, keys = {}, []
    for n in nodes:
        base = f"{n['kind']}/{n['actor']}/{n['label']}"
        counts[base] = counts.get(base, 0) + 1
        keys.append(f"{base}#{counts[base]}")
    return keys


def compare(nodes_a, nodes_b):
    a = dict(zip(node_keys(nodes_a), nodes_a))
    b = dict(zip(node_keys(nodes_b), nodes_b))
    changed = [k for k in a if k not in b or a[k]["hash"] != b[k]["hash"]]
    return changed + [k for k in b if k not in a]
