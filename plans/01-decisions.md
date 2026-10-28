# Decisions log

Newest first. Each entry: date, decision, reason, and what it affects.

| Date | Decision | Reason | Affects |
| --- | --- | --- | --- |
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
- [ ] Mac memory size (24 GB or 48 GB); either fits all candidates
