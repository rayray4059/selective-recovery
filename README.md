# selective-recovery

CSE 291A Fall 2026 project (Option 5): fault propagation and recovery in a
researcher -> planner -> executor coding workflow.

## Setup

Needs Python 3.11 and llama.cpp. We used llama.cpp version 0.7.0 (build 11669, commit
620d2225c) on an M4 Pro MacBook Pro.

```
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m pytest -q tests
```

## Rebuild our results (no model needed)

`data/phase1_runs.tar.gz` has every Phase 1 run (traces, tool logs, model replies, results).
This rebuilds `results/` (csv files and `tables.txt`, which the report uses):

```
mkdir -p runs && tar xzf data/phase1_runs.tar.gz -C runs
python3 scripts/analyze.py
```

## Rerun the experiment

1. Get the model and check the hash:

```
mkdir -p ~/models
curl -L -o ~/models/Qwen_Qwen3.5-4B-Q4_K_M.gguf https://huggingface.co/bartowski/Qwen_Qwen3.5-4B-GGUF/resolve/4168f45a16a1290d65a4ec0fa312ae917a4c15d6/Qwen_Qwen3.5-4B-Q4_K_M.gguf
shasum -a 256 ~/models/Qwen_Qwen3.5-4B-Q4_K_M.gguf
# 13c16f426047e2de38cd075bdade4a7bcbc8c774384876f677740cda65f8a983
```

2. Start the server in another terminal:

```
llama-server -m ~/models/Qwen_Qwen3.5-4B-Q4_K_M.gguf --port 8080 -ngl 99 -c 16384
```

3. Run all 10 dev tickets with every fault and the full restart, then always-verify on the
four verify tickets, then analyze the new batch (about 2 hours on our laptop):

```
python3 scripts/run_faults.py --restart --tag phase1
python3 scripts/run_faults.py --from runs/phase1_<timestamp> --ids t01_late_fee,t02_refund_window,t03_min_charge,t10_ship_helper --verify
python3 scripts/analyze.py runs/phase1_<timestamp> --out results_new
```

Runs use temperature 0 and seed 0, so the same model, llama.cpp build and hardware should
give the same runs. Other hardware or builds can change the model's replies. A stopped run can
be resumed by rerunning the same command with `--from`.

Our data came from two batches (`pilot9` = t02, t03, t10 and `full` = the other 7 tickets).
Runs hit by harness bugs were moved out and rerun with `--from`. Each batch's `batch.json`
logs every command, git commit and server version. The Nov 4 reruns show `git_dirty: true`
because they started before the changes after a09ab31 and b4f8d30 were committed.

## Other scripts

```
python3 scripts/run_tasks.py --tasks tasks/dev.jsonl
python3 scripts/show_trace.py <run dir>
python3 scripts/pilot/check_tickets.py
python3 scripts/pilot/test_a.py
python3 scripts/pilot/test_b.py
```
