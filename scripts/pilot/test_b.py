"""Pilot Test B: three chained prompts. A researcher reads the docs and reports facts, a
planner turns facts and the current file into a JSON plan, and an executor, which never sees
the docs, writes the new file from the plan. Then the hidden test runs.

Needs llama-server running (see ../../plans/steps/step-02-model-pilot.md).
Usage: python3 scripts/pilot/test_b.py [--runs 3] [--tickets t1_config_timeout,t5_retry]
"""
from __future__ import annotations

import argparse
import json
import re
import tempfile
import time
from datetime import datetime
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from check_tickets import PILOT, fresh_workspace, run_pytest
from test_a import CODE_BLOCK, REPO, SERVER_URL, TEMPERATURE, TOP_P, MAX_TOKENS, classify

CODEBASE = PILOT / "codebase"


class Fact(BaseModel):
    fact: str
    source: str


class Research(BaseModel):
    facts: list[Fact]


class Step(BaseModel):
    function: str
    new_signature: str
    change: str


class Plan(BaseModel):
    file: str
    steps: list[Step]


RESEARCHER = (
    "You are the researcher on a software team. Read the team's docs and report every fact "
    "the ticket's change depends on, quoting exact names, signatures, error codes and numbers. "
    "Cite the doc each fact comes from. Do not plan or write code. Reply with only JSON: "
    '{"facts": [{"fact": "...", "source": "<doc file name>"}]}'
)
PLANNER = (
    "You are the planner on a software team. Given a ticket, the researcher's facts and the "
    "current file, decide exactly which functions to change and how. Give each changed "
    "function's full new signature. Do not write the code. Reply with only JSON: "
    '{"file": "<path>", "steps": [{"function": "...", "new_signature": "...", "change": "..."}]}'
)
EXECUTOR = (
    "You are the executor on a software team. Implement the plan exactly in the given file. "
    "Reply with the complete new contents of the file in a single ```python code block and "
    "nothing else."
)


def ask(client: OpenAI, model: str, system: str, user: str, seed: int) -> tuple[str, dict]:
    start = time.time()
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=TEMPERATURE, top_p=TOP_P, max_tokens=MAX_TOKENS, seed=seed,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    stats = {"wall_s": round(time.time() - start, 2),
             "prompt_tokens": resp.usage.prompt_tokens,
             "completion_tokens": resp.usage.completion_tokens,
             "finish_reason": resp.choices[0].finish_reason}
    return resp.choices[0].message.content or "", stats


def parse_json(reply: str, schema: type[BaseModel]) -> BaseModel | None:
    """Parse the reply as JSON, allowing a ```json fence or text around the object."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", reply.strip())
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        return schema.model_validate(json.loads(text[start:end + 1]))
    except (json.JSONDecodeError, ValidationError):
        return None


def ticket_text(ticket: dict) -> str:
    return f"## Ticket: {ticket['title']}\n\n{ticket['body']}\n\nTarget file: {ticket['target_file']}"


def current_file(ticket: dict) -> str:
    target = ticket["target_file"]
    return f"## Current {target}\n\n```python\n{(CODEBASE / target).read_text()}```"


def run_one(client: OpenAI, model: str, ticket: dict, seed: int) -> dict:
    row = {"ticket": ticket["id"], "seed": seed, "passed": False, "agents": {}}

    def finish(outcome: str) -> dict:
        row["outcome"] = outcome
        row["wall_s"] = round(sum(a["wall_s"] for a in row["agents"].values()), 2)
        return row

    docs = "\n\n".join(f"## {p.name}\n\n{p.read_text()}" for p in sorted((CODEBASE / "docs").glob("*.md")))
    reply, stats = ask(client, model, RESEARCHER, f"{docs}\n\n{ticket_text(ticket)}", seed)
    research = parse_json(reply, Research)
    row["agents"]["researcher"] = {**stats, "valid_json": research is not None, "reply": reply}
    if research is None:
        return finish("invalid_json_researcher")

    facts = "\n".join(f"- {f.fact} ({f.source})" for f in research.facts)
    reply, stats = ask(client, model, PLANNER,
                       f"{ticket_text(ticket)}\n\n## Facts from the researcher\n\n{facts}\n\n{current_file(ticket)}",
                       seed)
    plan = parse_json(reply, Plan)
    row["agents"]["planner"] = {**stats, "valid_json": plan is not None, "reply": reply}
    if plan is None:
        return finish("invalid_json_planner")

    reply, stats = ask(client, model, EXECUTOR,
                       f"{ticket_text(ticket)}\n\n## Plan\n\n{plan.model_dump_json(indent=2)}\n\n{current_file(ticket)}",
                       seed)
    match = CODE_BLOCK.search(reply)
    code = match.group(1) if match else None
    row["agents"]["executor"] = {**stats, "reply": reply}

    with tempfile.TemporaryDirectory() as tmp:
        workspace = fresh_workspace(Path(tmp))
        if code is not None:
            (workspace / ticket["target_file"]).write_text(code)
        result = run_pytest(workspace, PILOT / ticket["hidden_test"])
    row["passed"] = code is not None and result.returncode == 0
    row["pytest_tail"] = result.stdout[-1500:]
    return finish(classify(code, row["passed"]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--tickets", default="", help="comma-separated ticket ids (default: all)")
    args = parser.parse_args()

    tickets = [json.loads(line) for line in (PILOT / "tickets.jsonl").read_text().splitlines() if line]
    if args.tickets:
        wanted = set(args.tickets.split(","))
        tickets = [t for t in tickets if t["id"] in wanted]

    client = OpenAI(base_url=SERVER_URL, api_key="none")
    model = client.models.list().data[0].id
    out_dir = REPO / "runs" / f"pilot_test_b_{datetime.now():%Y%m%d_%H%M%S}"
    out_dir.mkdir(parents=True)
    (out_dir / "config.json").write_text(json.dumps({
        "test": "B", "model": model, "server_url": SERVER_URL, "temperature": TEMPERATURE,
        "top_p": TOP_P, "max_tokens": MAX_TOKENS, "enable_thinking": False,
        "seeds": list(range(args.runs)), "tickets": [t["id"] for t in tickets],
        "prompts": {"researcher": RESEARCHER, "planner": PLANNER, "executor": EXECUTOR},
    }, indent=2))

    rows = []
    with open(out_dir / "results.jsonl", "w") as f:
        for ticket in tickets:
            for seed in range(args.runs):
                row = run_one(client, model, ticket, seed)
                rows.append(row)
                f.write(json.dumps(row) + "\n")
                f.flush()
                print(f"{ticket['id']:<20} seed={seed} {row['outcome']:<24} {row['wall_s']:>6.1f}s")

    passed = sum(r["passed"] for r in rows)
    print(f"\nTest B: {passed}/{len(rows)} passed, "
          f"mean {sum(r['wall_s'] for r in rows) / len(rows):.1f}s per task. Results in {out_dir}")
    for agent in ("researcher", "planner"):
        ran = [r["agents"][agent] for r in rows if agent in r["agents"]]
        print(f"  {agent} valid JSON: {sum(a['valid_json'] for a in ran)}/{len(ran)}")


if __name__ == "__main__":
    main()
