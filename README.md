# selective-recovery

CSE 291A Fall 2026 project (Option 5): fault propagation and recovery in a
researcher -> planner -> executor coding workflow.

## Setup

```
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Model: Qwen3.5 4B Q4_K_M served with llama.cpp:

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

Phase 1 runs (traces, tool logs, results, no workspaces) are in `data/phase1_runs.tar.gz`.
Unpack into `runs/` and run `scripts/analyze.py` to rebuild `results/`.

## Pilot

```
python3 scripts/pilot/check_tickets.py
python3 scripts/pilot/test_a.py
python3 scripts/pilot/test_b.py
```
