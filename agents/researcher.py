import json
from pathlib import Path

PROMPT = (Path(__file__).parent / "prompts" / "researcher.txt").read_text()
SCHEMA = {
    "type": "object",
    "properties": {
        "facts": {
            "type": "array", "maxItems": 5,
            "items": {
                "type": "object",
                "properties": {"fact": {"type": "string"}, "source": {"type": "string"}},
                "required": ["fact", "source"],
            },
        },
    },
    "required": ["facts"],
}


def research(env, llm, task, feedback=None):
    docs = []
    for f in env.call("list_files", "researcher"):
        if f.startswith("docs/"):
            docs.append(f"## {f}\n\n" + env.call("read_file", "researcher", path=f))
    user = "\n\n".join(docs) + f"\n\n## Ticket: {task.title}\n\n{task.instruction}"
    if feedback:
        user += "\n\n## A reviewer found these problems with an earlier answer\n\n" + "\n".join("- " + x for x in feedback)
    messages = [{"role": "system", "content": PROMPT}, {"role": "user", "content": user}]
    reply, stats = llm.chat(messages, schema=SCHEMA)
    try:
        facts = json.loads(reply)["facts"]
    except (json.JSONDecodeError, KeyError, TypeError):
        facts = []
    return facts, [{"agent": "researcher", "messages": messages, "reply": reply, "stats": stats}]
