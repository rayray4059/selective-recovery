# selective-recovery

CSE 291A Fall 2026 project (Option 5): fault propagation and recovery in a
researcher -> planner -> executor coding workflow.

## Setup

```
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Model: Qwen3.5 4B Q4_K_M (`Qwen_Qwen3.5-4B-Q4_K_M.gguf` from `bartowski/Qwen_Qwen3.5-4B-GGUF`
at revision `4168f45a16a1290d65a4ec0fa312ae917a4c15d6`, sha256
`13c16f426047e2de38cd075bdade4a7bcbc8c774384876f677740cda65f8a983`), served with llama.cpp
version 0.7.0 (build 11669, commit 620d2225c):

```
llama-server -m ~/models/Qwen_Qwen3.5-4B-Q4_K_M.gguf --port 8080 -ngl 99 -c 16384
```

## Running

```
python3 -m pytest -q tests
python3 scripts/run_tasks.py --tasks tasks/dev.jsonl
python3 scripts/run_faults.py --restart --verify --ids t01_late_fee
python3 scripts/analyze.py
```

## Phase 1 data

The Phase 1 runs came from two batches over the 10 dev tickets (`pilot9` is the first 3 dev
tickets, not the model pilot):

```
python3 scripts/run_faults.py --ids t03_min_charge,t10_ship_helper,t02_refund_window --restart --verify --tag pilot9
python3 scripts/run_faults.py --ids t01_late_fee,t04_currency,t05_invoice_tax,t06_eur_format,t07_timeout_cap,t08_region_currency,t09_ship_fix --restart --tag full
python3 scripts/run_faults.py --from runs/full_<timestamp> --ids t01_late_fee --verify
```

Runs hit by harness bugs were moved out and rerun with `--from`. Every command, commit and
server version is logged in each batch's `batch.json`. The Nov 4 reruns show `git_dirty: true`
because they were started before the changes after a09ab31 and b4f8d30 were committed.

The runs (traces, tool logs, model replies, results, no workspaces) are in
`data/phase1_runs.tar.gz`. To rebuild `results/`:

```
mkdir -p runs && tar xzf data/phase1_runs.tar.gz -C runs
python3 scripts/analyze.py
```

## Pilot

```
python3 scripts/pilot/check_tickets.py
python3 scripts/pilot/test_a.py
python3 scripts/pilot/test_b.py
```
