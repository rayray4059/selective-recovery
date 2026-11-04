import json
from pathlib import Path

from agents.planner import show_files

PROMPT = (Path(__file__).parent / "prompts" / "verifier.txt").read_text()
SCHEMA = {
    "type": "object",
    "properties": {
        "ok": {"type": "boolean"},
        "problems": {"type": "array", "maxItems": 5, "items": {"type": "string"}},
    },
    "required": ["ok", "problems"],
}


def check_stage(env, llm, task, stage, facts, plan=None):
    docs = []
    for f in env.call("list_files", "verifier"):
        if f.startswith("docs/"):
            docs.append(f"## {f}\n\n" + env.call("read_file", "verifier", path=f))
    fact_lines = "\n".join(f"- {f.get('fact', '')} ({f.get('source', '')})" for f in facts) or "(none)"
    user = "\n\n".join(docs) + f"\n\n## Ticket: {task.title}\n\n{task.instruction}"
    if stage == "facts":
        user += f"\n\n## Handoff: researcher's facts\n\n{fact_lines}"
    else:
        user += (f"\n\n## Researcher's facts\n\n{fact_lines}\n\n" + show_files(env, "verifier", task.target_files)
                 + "\n\n## Handoff: planner's plan\n\n" + json.dumps(plan, indent=2))
    messages = [{"role": "system", "content": PROMPT}, {"role": "user", "content": user}]
    reply, stats = llm.chat(messages, schema=SCHEMA)
    try:
        out = json.loads(reply)
        ok, problems = bool(out["ok"]), [str(p) for p in out["problems"]]
    except (json.JSONDecodeError, KeyError, TypeError):
        ok, problems = False, ["reviewer reply was not valid JSON"]
    if not ok and not problems:
        problems = ["reviewer rejected without a reason"]
    return ok, problems, [{"agent": "verifier", "stage": stage, "messages": messages, "reply": reply, "stats": stats}]
