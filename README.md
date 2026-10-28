# selective-recovery

Failure propagation and recovery in a multi-agent workflow (CSE 291A, Fall 2026, Option 5).

A researcher -> planner -> executor workflow completes small tickets on a fake Python
codebase. We inject faults into intermediate results, trace how they spread through artifacts
and shared state (files, a simulated registry and channel), and measure what recovery costs.

Project plans, decisions and per-step guides live in [`plans/`](plans/README.md).

- **Phase 1 (due Nov 4):** clean baseline, fault-injection harness, provenance traces,
  full-restart and always-verify baselines, measurements.
- **Phase 2 (due Dec 10):** dependency-aware invalidation with shared-state rollback,
  compared against the Phase 1 baselines.

## Layout

```
agents/      researcher.py  planner.py  executor.py  prompts/
env/         tools.py  state_store.py  snapshots.py
tasks/       templates/  dev.jsonl  heldout.jsonl
faults/      inject.py  schedules/
recovery/    full_restart.py  verify.py
eval/        check.py  analyze.py
runs/        <run_id>/trace.jsonl  result.json  config.yaml   (git-ignored)
docker/      Dockerfile  requirements.lock
scripts/     helper scripts (model server, experiment launchers)
tests/       unit tests for env, tools, checker
```

## Setup

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Model serving (llama.cpp at a pinned commit, GGUF weights) is documented in
`scripts/README.md` once added. Record the commit hash and model file hash in every run's
`config.yaml`.

## Reproducing results

Filled in as the pipeline lands. Goal: one command per condition (clean, faulted,
full restart, always-verify) and one command to regenerate every table and plot.

## Status

- [x] Repo scaffold
- [ ] Model server running locally
- [x] Simulated environment and tools (state store, five tools, unit tests)
- [ ] Tasks and outcome checker
- [ ] Agents
- [ ] Tracing
- [ ] Fault injector
- [ ] Recovery baselines
- [ ] Pilot runs, full dev-set runs on AWS
- [ ] Analysis script and Phase 1 report
