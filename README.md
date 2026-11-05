# selective-recovery

CSE 291A Fall 2026 project (option 5). Fault propagation and recovery in a
researcher -> planner -> executor coding workflow.

## setup

python 3.11 + llama.cpp (we used 0.7.0, build 11669, commit 620d2225c on an M4 Pro macbook)

```
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m pytest -q tests
```

## rebuild our results

doesn't need the model. all our phase 1 runs are in data/phase1_runs.tar.gz, this regenerates
results/ (tables.txt is what the report numbers come from)

```
mkdir -p runs && tar xzf data/phase1_runs.tar.gz -C runs
python3 scripts/analyze.py
```

## rerun the experiment

download the model (sha256 should be 13c16f426047e2de38cd075bdade4a7bcbc8c774384876f677740cda65f8a983)

```
mkdir -p ~/models
curl -L -o ~/models/Qwen_Qwen3.5-4B-Q4_K_M.gguf https://huggingface.co/bartowski/Qwen_Qwen3.5-4B-GGUF/resolve/4168f45a16a1290d65a4ec0fa312ae917a4c15d6/Qwen_Qwen3.5-4B-Q4_K_M.gguf
shasum -a 256 ~/models/Qwen_Qwen3.5-4B-Q4_K_M.gguf
```

start the server in another terminal

```
llama-server -m ~/models/Qwen_Qwen3.5-4B-Q4_K_M.gguf --port 8080 -ngl 99 -c 16384
```

then run everything (all faults + restart on the 10 dev tickets, then verify on 4 of them).
took us about 2 hrs total

```
python3 scripts/run_faults.py --restart --tag phase1
python3 scripts/run_faults.py --from runs/phase1_<timestamp> --ids t01_late_fee,t02_refund_window,t03_min_charge,t10_ship_helper --verify
python3 scripts/analyze.py runs/phase1_<timestamp> --out results_new
```

temp 0 and seed 0 so you should get the same runs with the same model/build/hardware, but
different hardware can change the replies. if it stops partway just rerun with --from and it
picks up where it left off.

our data is actually two batches (pilot9 = t02, t03, t10 and full = the rest). runs that hit
harness bugs got moved out and rerun with --from. batch.json in each batch has every command,
commit and server version. the nov 4 reruns say git_dirty: true since they started before we
committed the changes after a09ab31 and b4f8d30.

## other scripts

```
python3 scripts/run_tasks.py --tasks tasks/dev.jsonl
python3 scripts/show_trace.py <run dir>
python3 scripts/pilot/check_tickets.py
python3 scripts/pilot/test_a.py
python3 scripts/pilot/test_b.py
```
