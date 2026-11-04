import argparse
import csv
import json
import statistics
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from eval.analyze import FAULTS, collect, find_runs, overhead_row

BATCHES = ["runs/pilot9_20261103_202922", "runs/full_20261103_212844"]


def write_csv(path, rows):
    if not rows:
        return
    cols = list(rows[0])
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: json.dumps(v) if isinstance(v, (list, dict)) else v for k, v in r.items()})


def mean(xs):
    return round(statistics.mean(xs), 1) if xs else "-"


def table(title, head, rows):
    widths = [max(len(str(x)) for x in col) for col in zip(head, *rows)]
    line = lambda r: "  ".join(str(x).ljust(w) for x, w in zip(r, widths))
    return "\n".join([title, line(head), line(["-" * w for w in widths])] + [line(r) for r in rows]) + "\n"


def make_tables(clean, faults, restarts, verifies, over):
    out = []
    out.append(table("1. Clean and no-docs runs", ["task", "clean", "no_docs", "tokens", "wall_s"],
                     [[c["task"], c["passed"], c["no_docs_passed"], c["tokens"], c["wall_s"]] for c in clean]
                     + [["total", sum(c["passed"] for c in clean), sum(c["no_docs_passed"] for c in clean), "", ""]]))

    ok = {c["task"] for c in clean if c["passed"]}
    rows = []
    for f in FAULTS:
        a = [r for r in faults if r["fault"] == f and r["task"] in ok]
        b = [r for r in faults if r["fault"] == f and r["task"] not in ok]
        h = [r for r in a if r["outcome"] == "harmful"]
        rows.append([f, a[0]["kind"] if a else "", len(a), sum(r["outcome"] == "ignored" for r in a),
                     sum(r["outcome"] == "absorbed" for r in a), len(h),
                     sum(r["mechanism"] == "wrong_behavior" for r in h), sum(r["mechanism"] == "crash" for r in h),
                     sum(r["mechanism"] == "attack" for r in h), sum(r["mechanism"] == "side_effect" for r in h),
                     len(b), sum(r["outcome"] == "new_harm" for r in b)])
    out.append(table(f"2. Outcomes by fault (clean-passing tickets, n={len(ok)}; ignored = same final files, releases "
                     "and posts as the clean run; harmful split by how it failed)",
                     ["fault", "kind", "n", "ignored", "absorbed", "harmful", "wrong_behavior", "crash", "attack",
                      "side_effect", "n_failed", "new_harm"], rows))

    rows = []
    for att in ["delete_tests", "publish", "edit_docs"]:
        for f in ["malicious_facts", "malicious_plan"]:
            a = [r for r in faults if r["fault"] == f and r["attack"] == att]
            rows.append([att, f, len(a), sum(bool(r["attack_executed"]) for r in a),
                         ",".join(r["task"][:3] for r in a if r["attack_executed"]) or "-"])
    out.append(table("3a. Attacks executed (all tickets)", ["attack", "fault", "n", "executed", "tickets"], rows))
    rows = []
    for f in FAULTS:
        a = [r for r in faults if r["fault"] == f]
        rows.append([f, len(a), sum(r["unauthorized"] > 0 for r in a), sum(bool(r["collateral"]) for r in a),
                     sum(bool(r["irreversible"]) for r in a), sum(r["bad_publish"] for r in a), sum(r["new_harm"] for r in a)])
    out.append(table("3b. Side effects (all tickets; runs with at least one)",
                     ["fault", "n", "unauthorized", "collateral", "irreversible", "bad_publish", "new_vs_clean"], rows))

    rows = []
    for f in FAULTS:
        a = [r for r in faults if r["fault"] == f and r["task"] in ok]
        rows.append([f, len(a), sum("planner" in r["affected_stages"] for r in a),
                     sum("executor" in r["affected_stages"] for r in a), mean([r["changed_in_reach"] for r in a]),
                     mean([r["changed_other"] for r in a]), mean([r["n_reachable"] for r in a]),
                     mean([r["wasted_tokens"] for r in a])])
    out.append(table("4. Propagation (clean-passing tickets; downstream tokens are an upper bound)",
                     ["fault", "n", "planner_hit", "executor_hit", "changed_in_reach", "added_removed",
                      "reachable", "tokens_downstream"], rows))

    rows = []
    for f in FAULTS:
        a = [r for r in restarts if r["fault"] == f]
        p = [r for r in a if r["clean_passed"]]
        rows.append([f, len(a), sum(r["own_passed"] for r in p), sum(r["passed"] for r in p), len(p),
                     sum(bool(r["leftover_publish"]) for r in a), sum(r["leftover_messages"] > 0 for r in a),
                     mean([r["restart_tokens"] for r in a]), mean([r["restart_s"] for r in a]),
                     mean([r["total_tokens"] for r in p]), mean([r["total_s"] for r in p]),
                     mean([r["reusable_tokens"] for r in a]),
                     mean([100 * r["reusable_tokens"] / r["restart_tokens"] for r in a]),
                     sum(r["same_as_clean"] for r in a)])
    out.append(table("5. Full restart (own/strict pass over clean-passing tickets; reusable = identical and upstream of the fault)",
                     ["fault", "n", "own_pass", "strict_pass", "of", "left_publish", "left_post", "tokens", "s",
                      "with_fault_tok", "with_fault_s",
                      "reusable_tok", "reusable_%", "same_as_clean"], rows))

    rows = []
    for f in ["clean"] + FAULTS:
        a = [r for r in verifies if r["fault"] == f]
        rows.append([f, len(a), sum(r["caught"] for r in a), sum(r["late_catch"] for r in a), sum(r["missed"] for r in a),
                     sum(r["post_redo_flag"] for r in a), sum(r["false_alarm"] or r["control_flag"] for r in a),
                     sum(r["passed"] for r in a), sum(r["unverified_passed"] for r in a),
                     sum(bool(r["attack_executed"]) for r in a), mean([r["verify_tokens"] for r in a]),
                     mean([r["extra_tokens"] for r in a]), mean([r["extra_s"] for r in a])])
    out.append(table("6. Always-verify (" + ",".join(sorted({r["task"][:3] for r in verifies})) + "; flags on clean = false alarm, on control = flagged irrelevant change)",
                     ["fault", "n", "caught", "late", "missed", "post_redo", "flag_clean/ctrl", "pass", "pass_unverified",
                      "attack_ran", "verify_tok", "extra_tok", "extra_s"], rows))
    rows = []
    for t in sorted({r["task"] for r in verifies}):
        a = [r for r in verifies if r["task"] == t]
        good = [r for r in a if r["kind"] in ("clean", "control")]
        bad_facts = [r for r in a if r["fault"] in ("wrong_fact", "stale_fact", "timeout", "malicious_facts")]
        bad_plan = [r for r in a if r["fault"] in ("wrong_plan", "malicious_plan")]
        rows.append([t, f'{sum("facts" in r["flagged"] for r in good)}/{len(good)}',
                     f'{sum("facts" in r["flagged"] for r in bad_facts)}/{len(bad_facts)}',
                     f'{sum("plan" in r["flagged"] for r in good)}/{len(good)}',
                     f'{sum("plan" in r["flagged"] for r in bad_plan)}/{len(bad_plan)}',
                     mean([r["plain_tokens"] for r in a if r["kind"] == "clean"]),
                     mean([r["total_tokens"] for r in a])])
    out.append(table("6b. Verifier flags per ticket (ok = clean+control runs, bad = runs with a fault at that stage) and tokens vs the same ticket's clean run",
                     ["task", "facts_flag_ok", "facts_flag_bad", "plan_flag_ok", "plan_flag_bad", "clean_tok", "verified_tok"], rows))

    rows = []
    for k in ["clean", "fault", "restart", "verify"]:
        a = [r for r in over if r["kind"] == k]
        rows.append([k, len(a), mean([r["wall_s"] for r in a]), max(r["wall_s"] for r in a), mean([r["tokens"] for r in a]),
                     mean([r["trace_nodes"] for r in a]), mean([r["trace_bytes"] / 1000 for r in a]),
                     mean([r["build_ms"] for r in a]), mean([r["write_ms"] for r in a]), sum(r["truncated"] > 0 for r in a)])
    out.append(table("7. Cost and tracking overhead per run (write_ms includes the git commit; upper bound on bookkeeping)",
                     ["runs", "n", "wall_s", "max_s", "tokens", "trace_nodes", "trace_kb", "build_ms", "write_ms",
                      "truncated_runs"], rows))
    return "\n".join(out)


def pack(batches, path):
    with tarfile.open(path, "w:gz") as tar:
        for b in batches:
            b = Path(b)
            tar.add(b, arcname=b.name, filter=lambda t: None if "/ws" in t.name or t.name.endswith("/ws") else t)
            for f in b.parent.glob(b.name + "_*.jsonl"):
                tar.add(f, arcname=f.name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("batches", nargs="*", default=BATCHES)
    parser.add_argument("--out", default="results")
    parser.add_argument("--pack", action="store_true")
    args = parser.parse_args()
    batches = [ROOT / b for b in args.batches]
    if all(not b.exists() for b in batches) and (ROOT / "data" / "phase1_runs.tar.gz").exists():
        sys.exit("no run dirs; unpack data/phase1_runs.tar.gz into runs/ first")

    clean, faults, restarts, verifies = collect(batches)
    over = []
    for task, d in find_runs(batches).items():
        over.append(overhead_row(d / "clean", "clean"))
        for f in FAULTS:
            if (d / f / "result.json").exists():
                over.append(overhead_row(d / f, "fault"))
            if (d / f / "restart" / "result.json").exists():
                over.append(overhead_row(d / f / "restart", "restart"))
        for f in ["clean"] + FAULTS:
            if (d / f"{f}_verify" / "result.json").exists():
                over.append(overhead_row(d / f"{f}_verify", "verify"))

    out = ROOT / args.out
    out.mkdir(exist_ok=True)
    for name, rows in [("clean", clean), ("faults", faults), ("restarts", restarts), ("verify", verifies), ("overhead", over)]:
        write_csv(out / f"{name}.csv", rows)
    text = make_tables(clean, faults, restarts, verifies, over)
    (out / "tables.txt").write_text(text)
    print(text)
    if args.pack:
        (ROOT / "data").mkdir(exist_ok=True)
        pack(batches, ROOT / "data" / "phase1_runs.tar.gz")
        print("wrote data/phase1_runs.tar.gz")


if __name__ == "__main__":
    main()
