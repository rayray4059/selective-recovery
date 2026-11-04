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
from faults.measure import measure, measure_restart, measure_verify
from recovery.restart import restart
from tasks.schema import load_tasks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", default="")
    parser.add_argument("--faults", default="", help="comma-separated fault names (default: all in the schedule)")
    parser.add_argument("--schedule", default="faults/schedules/phase1.json")
    parser.add_argument("--tag", default="faults")
    parser.add_argument("--url", default="http://localhost:8080/v1")
    parser.add_argument("--restart", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--from", dest="old", default="", help="existing batch dir to reuse clean/fault runs from")
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

    out = Path(args.old) if args.old else ROOT / "runs" / f"{args.tag}_{datetime.now():%Y%m%d_%H%M%S}"
    files = {"faults": None, "restart": None, "verify": None}
    if not args.old:
        files["faults"] = open(out.parent / f"{out.name}_summary.jsonl", "w")
    if args.restart:
        files["restart"] = open(out.parent / f"{out.name}_restart.jsonl", "a")
    if args.verify:
        files["verify"] = open(out.parent / f"{out.name}_verify.jsonl", "a")

    def save(name, row):
        files[name].write(json.dumps(row) + "\n")
        files[name].flush()

    for tid in ids:
        task = tasks[tid]
        todo = [c for c in cells if c["task"] == tid]
        if not args.old:
            clean = run_task(task, llm, out / tid / "clean")
            print(f"{tid:<22} clean            {'pass' if clean['passed'] else 'FAIL'}", flush=True)
            for c in [{"fault": "no_docs", "attack": None}] + todo:
                run_task(task, llm, out / tid / c["fault"], fault=Fault(task, c["fault"], c["attack"]))
                row = measure(out / tid / "clean", out / tid / c["fault"])
                save("faults", row)
                print(f"{tid:<22} {c['fault']:<16} {'pass' if row['passed'] else 'FAIL'}  {row['outcome']:<8} "
                      f"changed={row['n_changed']:<2} stages={','.join(row['affected_stages']) or '-':<17} "
                      f"attack={row['attack_executed']}", flush=True)
        if args.restart:
            for c in todo:
                if not (out / tid / c["fault"] / "result.json").exists() or (out / tid / c["fault"] / "restart").exists():
                    continue
                restart(task, llm, out / tid / c["fault"])
                row = measure_restart(out / tid / "clean", out / tid / c["fault"])
                save("restart", row)
                print(f"{tid:<22} {c['fault']:<16} restart {'pass' if row['passed'] else 'FAIL'}  "
                      f"own={'pass' if row['own_passed'] else 'FAIL'}  leftover={row['leftover'] or '-'}  "
                      f"redundant={row['redundant_nodes']}/{row['nodes']}  same_as_clean={row['same_as_clean']}", flush=True)
        if args.verify:
            for c in [{"fault": "clean", "attack": None}] + todo:
                fault = None if c["fault"] == "clean" else Fault(task, c["fault"], c["attack"])
                run_task(task, llm, out / tid / (c["fault"] + "_verify"), fault=fault, verify=True)
                row = measure_verify(out / tid / c["fault"], out / tid / (c["fault"] + "_verify"))
                save("verify", row)
                print(f"{tid:<22} {c['fault']:<16} verify  {'pass' if row['passed'] else 'FAIL'}  "
                      f"flagged={','.join(row['flagged']) or '-':<11} caught={row['caught']}  "
                      f"false_alarm={row['false_alarm'] or '-'}  verify_tokens={row['verify_tokens']}", flush=True)
    for f in files.values():
        if f:
            f.close()
    print(f"\nDone. Summaries next to {out}")

if __name__ == "__main__":
    main()
