import json
from pathlib import Path

PROMPT = (Path(__file__).parent / "prompts" / "planner.txt").read_text()
STEP = {
    "type": "object",
    "properties": {k: {"type": "string"} for k in ("file", "function", "new_signature", "change")},
    "required": ["file", "function", "new_signature", "change"],
}
SCHEMA = {"type": "object", "properties": {"steps": {"type": "array", "items": STEP}}, "required": ["steps"]}


def show_files(env, actor, paths):
    return "\n\n".join(f"## Current {p}\n\n```python\n{env.call('read_file', actor, path=p)}```" for p in paths)


def plan_change(env, llm, task, facts):
    fact_lines = "\n".join(f"- {f.get('fact', '')} ({f.get('source', '')})" for f in facts) or "(none)"
    user = (f"## Ticket: {task.title}\n\n{task.instruction}\n\n## Facts from the researcher\n\n{fact_lines}\n\n"
            + show_files(env, "planner", task.target_files))
    messages = [{"role": "system", "content": PROMPT}, {"role": "user", "content": user}]
    reply, stats = llm.chat(messages, schema=SCHEMA)
    try:
        plan = json.loads(reply)
        plan["steps"]
    except (json.JSONDecodeError, KeyError, TypeError):
        plan = {"steps": []}
    return plan, [{"agent": "planner", "messages": messages, "reply": reply, "stats": stats}]
