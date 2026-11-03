import argparse
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.llm import LLM
from agents.run import run_task
from tasks.schema import load_tasks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", default="tasks/dev.jsonl")
    parser.add_argument("--ids", default="")
    parser.add_argument("--tag", default="clean")
    parser.add_argument("--url", default="http://localhost:8080/v1")
    args = parser.parse_args()

    tasks = load_tasks(ROOT / args.tasks)
    if args.ids:
        tasks = [t for t in tasks if t.id in args.ids.split(",")]
    llm = LLM(args.url)
    try:
        llm.client.models.list()
    except Exception:
        sys.exit("llama-server isn't running at " + args.url)

    out = ROOT / "runs" / f"{args.tag}_{datetime.now():%Y%m%d_%H%M%S}"
    results = []
    for t in tasks:
        res = run_task(t, llm, out / t.id)
        results.append(res)
        print(f"{t.id:<22} {'pass' if res['passed'] else 'FAIL'}  tests={res['tests_passed']!s:<5} "
              f"unauthorized={len(res['unauthorized'])}  {res['wall_s']:6.1f}s")
    passed = sum(r["passed"] for r in results)
    print(f"\n{passed}/{len(results)} passed, mean {sum(r['wall_s'] for r in results) / len(results):.1f}s. Runs in {out}")


if __name__ == "__main__":
    main()
