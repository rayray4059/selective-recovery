"""Pilot Test A: the model alone. For each ticket, send the docs, the target file and the
ticket in one prompt, write the returned file into a fresh workspace, and run the hidden test.

Needs llama-server running (see ../../plans/steps/step-02-model-pilot.md).
Usage: python3 scripts/pilot/test_a.py [--runs 3] [--tickets t1_config_timeout,t5_retry]
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

from check_tickets import PILOT, fresh_workspace, run_pytest

REPO = PILOT.parent.parent
SERVER_URL = "http://localhost:8080/v1"
TEMPERATURE = 0.7      # Qwen's recommended setting with thinking off
TOP_P = 0.8
MAX_TOKENS = 2048

SYSTEM = (
    "You are a careful Python developer working on an internal codebase. Follow the team's "
    "docs exactly. Reply with the complete new contents of the file in a single ```python "
    "code block and nothing else."
)
CODE_BLOCK = re.compile(r"```(?:python)?\n(.*?)```", re.DOTALL)


def build_prompt(ticket: dict) -> str:
    docs = PILOT / "codebase" / "docs"
    target = ticket["target_file"]
    parts = [f"## {p.name}\n\n{p.read_text()}" for p in sorted(docs.glob("*.md"))]
    parts.append(f"## Current {target}\n\n```python\n{(PILOT / 'codebase' / target).read_text()}```")
    parts.append(f"## Ticket: {ticket['title']}\n\n{ticket['body']}\n\n"
                 f"Return the full new {target}.")
    return "\n\n".join(parts)


def classify(code: str | None, passed: bool) -> str:
    if passed:
        return "pass"
    if code is None:
        return "no_code_block"
    try:
        compile(code, "<model>", "exec")
    except SyntaxError:
        return "broken_code"
    return "wrong_behavior"


def run_one(client: OpenAI, model: str, ticket: dict, seed: int) -> dict:
    start = time.time()
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": SYSTEM},
                  {"role": "user", "content": build_prompt(ticket)}],
        temperature=TEMPERATURE, top_p=TOP_P, max_tokens=MAX_TOKENS, seed=seed,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    wall_s = time.time() - start
    reply = resp.choices[0].message.content or ""
    match = CODE_BLOCK.search(reply)
    code = match.group(1) if match else None

    with tempfile.TemporaryDirectory() as tmp:
        workspace = fresh_workspace(Path(tmp))
        if code is not None:
            (workspace / ticket["target_file"]).write_text(code)
        result = run_pytest(workspace, PILOT / ticket["hidden_test"])
    passed = code is not None and result.returncode == 0

    return {
        "ticket": ticket["id"], "seed": seed, "passed": passed, "outcome": classify(code, passed),
        "wall_s": round(wall_s, 2),
        "prompt_tokens": resp.usage.prompt_tokens, "completion_tokens": resp.usage.completion_tokens,
        "gen_tok_s": round(resp.usage.completion_tokens / wall_s, 1),
        "finish_reason": resp.choices[0].finish_reason,
        "reply": reply, "pytest_tail": result.stdout[-1500:],
    }


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
    out_dir = REPO / "runs" / f"pilot_test_a_{datetime.now():%Y%m%d_%H%M%S}"
    out_dir.mkdir(parents=True)
    (out_dir / "config.json").write_text(json.dumps({
        "test": "A", "model": model, "server_url": SERVER_URL, "temperature": TEMPERATURE,
        "top_p": TOP_P, "max_tokens": MAX_TOKENS, "enable_thinking": False,
        "seeds": list(range(args.runs)), "tickets": [t["id"] for t in tickets],
    }, indent=2))

    rows = []
    with open(out_dir / "results.jsonl", "w") as f:
        for ticket in tickets:
            for seed in range(args.runs):
                row = run_one(client, model, ticket, seed)
                rows.append(row)
                f.write(json.dumps(row) + "\n")
                f.flush()
                print(f"{ticket['id']:<20} seed={seed} {row['outcome']:<15} "
                      f"{row['wall_s']:>6.1f}s {row['gen_tok_s']:>5.1f} tok/s")

    passed = sum(r["passed"] for r in rows)
    print(f"\nTest A: {passed}/{len(rows)} passed, "
          f"mean {sum(r['wall_s'] for r in rows) / len(rows):.1f}s per task. Results in {out_dir}")


if __name__ == "__main__":
    main()
