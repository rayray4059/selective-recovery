# Roadmap

Phase 1 is due Nov 4. Steps are in build order. Dates are targets.

| # | Step | Target | Status | Plan |
| --- | --- | --- | --- | --- |
| 1 | Repo scaffold | Oct 27 | Done | `steps/step-01-repo.md` |
| 2 | Model pilot: can a model solve tiny coding tickets? | Oct 29 | **In progress** | `steps/step-02-model-pilot.md` |
| 3 | Coding environment: workspace as a git repo, file and test tools, registry and channel | Oct 30 | Not started | (to write) |
| 4 | Tasks (tickets), hidden tests, and the outcome checker | Oct 31 | Not started | `steps/step-04-tasks.md` |
| 5 | Agents: researcher, planner, executor with fixed prompts and JSON outputs | Oct 31 | Not started | (to write) |
| 6 | Tracing: provenance record for every artifact and tool call | Nov 1 | Not started | (to write) |
| 7 | Fault injector: five fault types, seeded schedule, control faults | Nov 1 | Not started | (to write) |
| 8 | Recovery baselines: full restart and always-verify | Nov 2 | Not started | (to write) |
| 9 | Pilot matrix on 5 tasks across all conditions | Nov 2 | Not started | (to write) |
| 10 | Full dev-set runs on AWS | Nov 3 | Not started | (to write) |
| 11 | Analysis script: every table and plot from traces | Nov 3 | Not started | (to write) |
| 12 | Phase 1 report (1–2 pages plus timeline appendix) and README | Nov 4 | Not started | (to write) |

**Phase 2 (Nov 5 – Dec 10):** selective invalidation (Nov 5–17), state rollback and
irreversible effects (Nov 12–24), held-out evaluation (Nov 23–Dec 3), final report (Dec 1–9).

**If time slips:** run always-verify on a subset, or cut the dev set to 20 tasks.
Never cut tracing or the paired clean runs, because Phase 2 depends on both.

**Note on step 3:** `env/tools.py` currently holds customer-support tools from before the
scenario change. `env/state_store.py` (versioned store with rollback) stays useful for small
shared state such as a simulated ticket tracker.
