# Step 2: Model pilot

**Question:** can a model solve tiny coding tickets reliably enough that faults have
something to break? **Go/no-go: Oct 29.**

**Where:** `scripts/pilot/`. Commit the results. The Phase 1 writeup must justify the model
choice, and this is the evidence.

## Candidates (same quantization, Q4_K_M)

| Model | Size | Why |
| --- | --- | --- |
| Qwen3.5 4B | 4B | Top CPU pick; small agents with tight prompts |
| Phi-4-mini-instruct | ~4B | Instruction following and structured (JSON) output |
| Qwen3.5 9B or Qwen3 8B | 8–9B | Step up if the 4B models fail; slower |
| TritonAI model | Large | Fallback; the course's LLM API. Check its model list. |

RAM: 4B models are in the ~16 GB tier and 8–9B in the ~32 GB tier (approximate).
Sources in `../context/references.md`.

## Steps

1. **Fake codebase (~1 h).** One package, 3–4 small plain-Python files, e.g.
   `billing/payments.py`, `billing/config.py`, `billing/client.py`.
2. **Two internal docs (~20 min).** `docs/conventions.md` ("money is integer cents"),
   `docs/api.md` ("`get_client()` requires `region=`", "config key is `timeout_s`").
3. **Five pilot tickets with hidden tests (~1.5 h).** Each needs one doc fact, changes 5–20
   lines, and has 2–3 hidden pytest tests.
4. **Test A, model alone (~1 h).** One prompt with the docs, the file and the ticket. Ask for
   the full new file, write it, run the hidden tests. Measures raw ability.
5. **Test B, three chained prompts (~2 h).** Researcher, planner, executor, passing JSON. No
   tracing yet. Measures whether the hand-offs work.
6. **Record per model:** hidden-test pass rate for A and B (5 tasks × 3 runs), valid-JSON rate
   per agent, tokens/s and wall time per task, and failure type (wrong fact, wrong plan,
   broken code).

## Decision rule

- Test B ≥ 60% (9/15) and under 2–3 min per task: pick the fastest model that qualifies.
- A passes, B fails: the model is fine; simplify the prompts and hand-offs.
- Both fail on all local models: use TritonAI and note it in the writeup.

Speed matters as much as accuracy. The full run is about 40 tasks × several faults × 4
conditions.

## Done when

- A results table in `scripts/pilot/RESULTS.md`, with the chosen model, its pinned file hash,
  and the llama.cpp commit.
- The decision recorded in `../01-decisions.md`.

## Where it runs

On the owner's M4 Pro MacBook Pro (macOS 15.1), llama.cpp via Homebrew with Metal.
Record `llama-server --version` and the model's `shasum -a 256` in `RESULTS.md`.
Pilot speeds are Mac speeds; final runs move to AWS (see `../01-decisions.md`).

## Progress

- [x] 2026-10-27: llama.cpp installed (Homebrew 0.7.0, build 11669, commit `620d2225c`)
- [x] 2026-10-27: Qwen3.5 4B Q4_K_M downloaded to `~/models/`
  - repo `bartowski/Qwen_Qwen3.5-4B-GGUF`, revision `4168f45a16a1290d65a4ec0fa312ae917a4c15d6`
  - file `Qwen_Qwen3.5-4B-Q4_K_M.gguf`, sha256 `13c16f426047e2de38cd075bdade4a7bcbc8c774384876f677740cda65f8a983`
- [x] 2026-10-27: smoke test on Metal: valid JSON at temp 0, ~41 tok/s generation
  - server: `llama-server -m ~/models/Qwen_Qwen3.5-4B-Q4_K_M.gguf --port 8080 -ngl 99 -c 8192`
  - requests send `"chat_template_kwargs": {"enable_thinking": false}`
- [x] 2026-10-27: fake codebase `scripts/pilot/codebase/` (`billing/` errors, config, client,
  payments) and `docs/conventions.md`, `docs/api.md`
- [x] 2026-10-27: five tickets in `scripts/pilot/tickets.jsonl`, hidden tests in `hidden_tests/`,
  reference fixes in `solutions/`. `check_tickets.py` confirms each test fails on the original
  and passes with its fix. Fixes are 1–8 lines, smaller than the planned 5–20.
  `doc_fact` in each ticket is for labeling failures and must not be shown to the agents.
- [x] 2026-10-27: Python 3.11 `.venv` built from a conda `py311` env (no system 3.11 on the Mac)
- [ ] Test A, Test B, `RESULTS.md`, decision
