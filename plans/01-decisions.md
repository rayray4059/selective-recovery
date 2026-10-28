# Decisions log

Newest first. Each entry: date, decision, reason, and what it affects.

| Date | Decision | Reason | Affects |
| --- | --- | --- | --- |
| 2026-10-27 | Fixed pilot ticket t4 after the first Test A run: `api.md` now shows `idempotency_key=None`; reran all of Test A | The doc gave the key as a required positional argument, contradicting its own rule to raise `BillingError` when it's missing, so the hidden test was unpassable for a model that followed the signature (0/3). Rerun of all tickets because the doc is in every prompt. Mention in the writeup: ticket changed after seeing scores | Step 2, writeup |
| 2026-10-27 | Pilot starts with Qwen3.5 4B Q4_K_M from `bartowski/Qwen_Qwen3.5-4B-GGUF` (pinned revision); thinking mode off via `chat_template_kwargs` | No official Qwen GGUF; bartowski is recent and also publishes Phi-4-mini, so candidates come from one source. Thinking is slow and breaks JSON | Step 2, run configs |
| 2026-10-27 | Phase 1 runs on the owner's M4 Pro MacBook Pro (llama.cpp with Metal); final comparisons (Phase 1 baselines rerun + Phase 2) on AWS for standardization | Free and fast while the harness changes; accuracy transfers between machines, latency doesn't | Steps 2, 10; run configs must hold server URL, model file and hardware label |
| 2026-10-27 | Keep all plans in `plans/`, one file per step | Preserve context without re-deriving it | Process |
| 2026-10-27 | Run a model pilot before building the full harness; go/no-go Oct 29 | Coding with a small model risks low clean success, and faults need something to break | Step 2, model choice |
| 2026-10-27 | Candidates: Qwen3.5 4B, Phi-4-mini-instruct, Qwen3.5 9B or Qwen3 8B (all Q4_K_M); TritonAI as fallback | Current CPU-friendly models; same quantization for a fair comparison | Step 2 |
| 2026-10-27 | **Scenario: coding workflow** on a small fake Python codebase (switched from customer support) | Stronger resume story; file rollback fits the PDF's shared-state hint | Steps 3–7, `context/scenario.md` |
| 2026-10-27 | Repo: `rayray4059/selective-recovery`, commits authored as rayray4059 | Owner's preference | All commits |
| 2026-10-27 | Self-host the model with llama.cpp on AWS CPU; develop on a laptop | Pins model version, seed and sampling; fits the $3/day limit | Steps 2, 10 |
| 2026-10-27 | Phase 1 deadline confirmed as **Nov 4** | Confirmed by owner | Timeline |
| 2026-10-27 | Project: **Option 5**, failure propagation and recovery | Clear question, finishable in time, good resume value | Everything |

## Open

- [ ] Team size and owners per area
- [ ] Final model (after the pilot)
- [ ] Whether always-verify uses the same model or a separate one
- [x] Mac memory size: 24 GB (checked 2026-10-27); fits all candidates
