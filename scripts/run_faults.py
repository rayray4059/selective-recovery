import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.llm import LLM
from agents.run import run_task
from faults.inject import Fault
from faults.measure import measure
from tasks.schema import load_tasks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", default="")
    parser.add_argument("--faults", default="", help="comma-separated fault names (default: all in the schedule)")
    parser.add_argument("--schedule", default="faults/schedules/phase1.json")
    parser.add_argument("--tag", default="faults")
    parser.add_argument("--url", default="http://localhost:8080/v1")
    args = parser.parse_args()

    tasks = {t.id: t for t in load_tasks()}
    cells = json.loads((ROOT / args.schedule).read_text())
    ids = args.ids.split(",") if args.ids else list(tasks)
    if args.faults:
        cells = [c for c in cells if c["fault"] in args.faults.split(",")]
    llm = LLM(args.url)
    try:
        llm.client.models.list()
    except Exception:
        sys.exit("llama-server isn't running at " + args.url)

    out = ROOT / "runs" / f"{args.tag}_{datetime.now():%Y%m%d_%H%M%S}"
    rows = []
    with open(out.parent / f"{out.name}_summary.jsonl", "w") as f:
        for tid in ids:
            task = tasks[tid]
            clean = run_task(task, llm, out / tid / "clean")
            print(f"{tid:<22} clean            {'pass' if clean['passed'] else 'FAIL'}", flush=True)
            todo = [{"fault": "no_docs", "attack": None}] + [c for c in cells if c["task"] == tid]
            for c in todo:
                run_task(task, llm, out / tid / c["fault"], fault=Fault(task, c["fault"], c["attack"]))
                row = measure(out / tid / "clean", out / tid / c["fault"])
                rows.append(row)
                f.write(json.dumps(row) + "\n")
                f.flush()
                print(f"{tid:<22} {c['fault']:<16} {'pass' if row['passed'] else 'FAIL'}  {row['outcome']:<8} "
                      f"changed={row['n_changed']:<2} stages={','.join(row['affected_stages']) or '-':<17} "
                      f"attack={row['attack_executed']}", flush=True)
    print(f"\n{len(rows)} faulted runs. Summary in {out.parent / (out.name + '_summary.jsonl')}")


if __name__ == "__main__":
    main()
