import json
import re
from pathlib import Path

from agents.planner import show_files
from env.tools import ToolError

PROMPT = (Path(__file__).parent / "prompts" / "executor.txt").read_text()
CODE_BLOCK = re.compile(r"```(?:python)?\n(.*?)```", re.DOTALL)
MAX_TURNS = 6


def parse_action(reply, targets):
    code = CODE_BLOCK.search(reply)
    head = reply.split("```")[0]
    action = None
    in_block = False
    for body in (reply.strip(), head[head.find("{"):head.rfind("}") + 1]):
        try:
            action = json.loads(body)
            break
        except json.JSONDecodeError:
            pass
    if action is None and code and code.group(1).strip().startswith('{"tool"'):
        try:
            action = json.loads(code.group(1).strip())
            in_block = True
        except json.JSONDecodeError:
            pass
    if action is None:
        if code and code.group(1).strip().startswith('{"tool"'):
            return None, "that JSON is not valid; send the JSON line first, then the file in a ```python block"
        if code and len(targets) == 1:
            return {"tool": "write_file", "path": targets[0], "text": code.group(1)}, None
        return None, "start your reply with a JSON line like {\"tool\": ...}"
    if not isinstance(action, dict) or "tool" not in action:
        return None, "the JSON needs a \"tool\" field"
    if "content" in action and "text" not in action:
        action["text"] = action.pop("content")
    if action["tool"] == "write_file" and "text" not in action:
        if not code or in_block:
            return None, "write_file needs the whole file in a ```python block after the JSON line"
        action["text"] = code.group(1)
    return action, None


def execute(env, llm, task, plan, facts):
    fact_lines = "\n".join(f"- {f.get('fact', '')} ({f.get('source', '')})" for f in facts) or "(none)"
    user = (f"## Ticket: {task.title}\n\n{task.instruction}\n\n## Facts from the researcher\n\n{fact_lines}\n\n"
            f"## Plan\n\n{json.dumps(plan, indent=2)}\n\n" + show_files(env, "executor", task.target_files))
    messages = [{"role": "system", "content": PROMPT}, {"role": "user", "content": user}]
    actions, calls = [], []
    for turn in range(MAX_TURNS):
        reply, stats = llm.chat(messages)
        calls.append({"agent": "executor", "turn": turn, "messages": list(messages), "reply": reply, "stats": stats})
        messages.append({"role": "assistant", "content": reply})
        action, error = parse_action(reply, task.target_files)
        if action and action["tool"] == "done":
            actions.append({"turn": turn, "tool": "done"})
            break
        log_i = None
        if error:
            feedback = "Error: " + error
        else:
            args = {k: v for k, v in action.items() if k != "tool"}
            log_i = len(env.log)
            try:
                result = env.call(action["tool"], "executor", **args)
                if isinstance(result, dict):
                    result = {k: v for k, v in result.items() if k != "commit"}
                feedback = "Result: " + json.dumps(result)[:1000]
            except ToolError as e:
                feedback = "Error: " + str(e)
        actions.append({"turn": turn, "tool": action["tool"] if action else None, "log_i": log_i,
                        "feedback": feedback[:300]})
        messages.append({"role": "user", "content": feedback})
    return actions, calls
