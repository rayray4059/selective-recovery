import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import traceback
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
    out.mkdir(parents=True, exist_ok=True)
    save_batch_info(out, args)
    files = {"faults": open(out.parent / f"{out.name}_summary.jsonl", "a")}
    if args.restart:
        files["restart"] = open(out.parent / f"{out.name}_restart.jsonl", "a")
    if args.verify:
        files["verify"] = open(out.parent / f"{out.name}_verify.jsonl", "a")

    def save(name, row):
        files[name].write(json.dumps(row) + "\n")
        files[name].flush()

    def attempt(name, tid, fault, d, fn):
        if (d / "result.json").exists():
            return None
        if d.exists():
            shutil.rmtree(d)
        try:
            return fn()
        except Exception as e:
            save(name, {"task": tid, "fault": fault, "error": f"{type(e).__name__}: {e}"})
            with open(out / "errors.log", "a") as f:
                f.write(f"{tid} {fault} {name}\n{traceback.format_exc()}\n")
            print(f"{tid:<22} {fault:<16} {name} ERROR {type(e).__name__}: {e}", flush=True)
            return None

    def run_fault(task, c):
        d = out / task.id / c["fault"]
        run_task(task, llm, d, fault=Fault(task, c["fault"], c["attack"]))
        row = measure(out / task.id / "clean", d)
        save("faults", row)
        print(f"{task.id:<22} {c['fault']:<16} {'pass' if row['passed'] else 'FAIL'}  {row['outcome']:<8} "
              f"changed={row['n_changed']:<2} stages={','.join(row['affected_stages']) or '-':<17} "
              f"attack={row['attack_executed']}", flush=True)

    def run_restart(task, c):
        d = out / task.id / c["fault"]
        restart(task, llm, d)
        row = measure_restart(out / task.id / "clean", d)
        save("restart", row)
        print(f"{task.id:<22} {c['fault']:<16} restart {'pass' if row['passed'] else 'FAIL'}  "
              f"own={'pass' if row['own_passed'] else 'FAIL'}  leftover={row['leftover'] or '-'}  "
              f"redundant={row['redundant_nodes']}/{row['nodes']}  same_as_clean={row['same_as_clean']}", flush=True)

    def run_verify(task, c):
        fault = None if c["fault"] == "clean" else Fault(task, c["fault"], c["attack"])
        d = out / task.id / (c["fault"] + "_verify")
        run_task(task, llm, d, fault=fault, verify=True)
        row = measure_verify(out / task.id / c["fault"], d)
        save("verify", row)
        print(f"{task.id:<22} {c['fault']:<16} verify  {'pass' if row['passed'] else 'FAIL'}  "
              f"flagged={','.join(row['flagged']) or '-':<11} caught={row['caught']}  "
              f"false_alarm={row['false_alarm'] or '-'}  verify_tokens={row['verify_tokens']}", flush=True)

    for tid in ids:
        task = tasks[tid]
        todo = [c for c in cells if c["task"] == tid]
        clean = out / tid / "clean"
        res = attempt("faults", tid, "clean", clean, lambda: run_task(task, llm, clean))
        if res:
            print(f"{tid:<22} clean            {'pass' if res['passed'] else 'FAIL'}", flush=True)
        if not (clean / "result.json").exists():
            continue
        for c in [{"fault": "no_docs", "attack": None}] + todo:
            attempt("faults", tid, c["fault"], out / tid / c["fault"], lambda: run_fault(task, c))
        if args.restart:
            for c in todo:
                if (out / tid / c["fault"] / "result.json").exists():
                    attempt("restart", tid, c["fault"], out / tid / c["fault"] / "restart", lambda: run_restart(task, c))
        if args.verify:
            for c in [{"fault": "clean", "attack": None}] + todo:
                if (out / tid / c["fault"] / "result.json").exists():
                    attempt("verify", tid, c["fault"], out / tid / (c["fault"] + "_verify"), lambda: run_verify(task, c))
    for f in files.values():
        f.close()
    print(f"\nDone. Summaries next to {out}")


def server_info():
    ps = subprocess.run(["ps", "-axo", "args"], capture_output=True, text=True).stdout
    cmd = next((line for line in ps.splitlines() if line.startswith("llama-server") or "/llama-server " in line), "")
    parts = cmd.split()
    model = parts[parts.index("-m") + 1] if "-m" in parts else None
    sha = None
    if model and Path(model).exists():
        h = hashlib.sha256()
        with open(model, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 24), b""):
                h.update(chunk)
        sha = h.hexdigest()
    try:
        out = subprocess.run(["llama-server", "--version"], capture_output=True, text=True, timeout=30)
        version = (out.stdout + out.stderr).strip()
    except (OSError, subprocess.TimeoutExpired):
        version = None
    return {"command": cmd, "version": version, "model_sha256": sha}


def save_batch_info(out, args):
    git = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    info = {"started": datetime.now().isoformat(timespec="seconds"), "args": vars(args), "argv": sys.argv,
            "git_commit": git("rev-parse", "HEAD"), "git_dirty": git("status", "--porcelain") != "",
            "python": platform.python_version(), "server": server_info()}
    path = out / "batch.json"
    old = json.loads(path.read_text()) if path.exists() else []
    path.write_text(json.dumps(old + [info], indent=2))


if __name__ == "__main__":
    main()
