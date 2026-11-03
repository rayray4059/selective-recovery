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
llama-server -m ~/models/Qwen_Qwen3.5-4B-Q4_K_M.gguf --port 8080 -ngl 99 -c 8192
```

## Pilot

```
python3 scripts/pilot/check_tickets.py
python3 scripts/pilot/test_a.py
python3 scripts/pilot/test_b.py
```
