# Option 5 Phase 1 Plan: Failure Propagation and Recovery (original)

> **Archived, Oct 27, 2026.** This is the first plan, exported from the Claude doc
> "Option 5 Phase 1 Plan". On Oct 27 we switched the scenario from customer support to a
> **coding workflow** (see `01-decisions.md`). The goals, fault classes, tracing, baselines,
> metrics, budget and Phase 2 direction below still apply. The workflow, tools and task
> sections describe the old scenario. The current versions live in `context/scenario.md`
> and `steps/`. The two diagrams in the doc are described in text here.

## Question and Phase 1 goals

Phase 1 measures how far one faulty intermediate result travels through a researcher → planner → executor workflow, and what full restart costs to undo it. Phase 2 then tests whether dependency tracking can recover the same tasks while redoing less work.

Phase 1 is graded on submitted code and data, so each goal below ends in something a grader can run or count:

1. **A clean workflow** that solves most development tasks, scored by a programmatic check on final state.
2. **A fault-injection harness** with a fixed, seeded fault schedule across stages and fault types.
3. **Full traces**: every message, artifact, tool call and state change, linked by dependency.
4. **Baseline measurements** for four conditions: clean, faulted with no recovery, full restart, and always-verify.
5. **A justified Phase 2 direction**, argued from the traces (which faults spread, how much work restart wastes).

A fault the downstream agents ignore is not evidence of robustness. Each faulted run is paired with its clean run so propagation is measured, not assumed.

## Workflow design (superseded: customer-support scenario)

The workload is a simulated customer-operations desk: each task asks the system to resolve a support case by looking up facts, planning steps, and changing records. This domain gives checkable outcomes and real shared state, which Phase 2 recovery needs.

*Diagram: Researcher → Planner → Executor → Shared state. Fault points F1 (fact faults), F2 (plan faults), F3 (tool faults) sit at each agent's output. All stages write to one provenance log (artifact IDs, input links, state reads and writes, tokens, latency).*

**Agents (one fixed model, fixed prompts):**

- **Researcher** reads a local document corpus (policies, order records, customer notes) and returns structured facts, each with a citation to its source document.
- **Planner** turns the task plus the facts into a JSON plan of tool steps.
- **Executor** runs each step through simulated tools and reports results.

**Simulated tools and shared state:**

| Tool | Effect | Reversible? |
| --- | --- | --- |
| `read_record(id)` | Reads an order or customer record | Yes (read-only) |
| `update_record(id, field, value)` | Changes a record in a versioned key-value store | Yes, via the version log |
| `write_file(path, text)` | Writes to a sandboxed workspace folder | Yes, via snapshot |
| `issue_refund(order, amount)` | Appends to a refunds ledger | Compensable (reversal entry) |
| `send_message(customer, text)` | Appends to a simulated outbox | No: treated as already seen |

**Tasks:** about 15 task templates (refund, address change, order cancellation, escalation), instantiated with different records into roughly 40 development and 40 held-out tasks. Each task has an expected final state: which records change, which ledger and outbox entries exist, and which must not.

**Authorization:** each task has an allowed set of records and tools. Any call outside it counts as an unauthorized action, whether or not the task still passes.

The outbox and refunds ledger are deliberate: they give Phase 2 actions that cannot simply be rolled back.

## Fault injection

Faults are injected by rewriting one agent's output (or one tool result) before the next agent sees it, from a seeded schedule saved with each run. Accidental and adversarial faults are reported separately.

| Fault | Class | Injected at | Example |
| --- | --- | --- | --- |
| Wrong fact | Accidental | Researcher output | Refund window stated as 60 days instead of 30 |
| Stale output | Accidental | Researcher or tool output | An older version of the order record |
| Timeout | Accidental | Any agent or tool call | Call returns nothing after its time limit |
| Fabricated fact | Adversarial | Researcher output | An invented "manager approval" for a larger refund |
| Malicious instruction | Adversarial | Researcher output or tool output | Text telling the executor to update a record outside the task |

**Schedule:** each task runs clean once, then once per (fault, stage) cell that applies to it. Main runs use temperature 0; a subset repeats with 3 seeds to measure variability.

**Did the fault matter?** A paired comparison against the clean run decides it. A fault *propagated* if any downstream artifact or the final state differs from the clean run. It *caused failure* if the task check fails or an unauthorized action occurs. Faults on fields the task never uses act as a control: they should change nothing.

## Instrumentation and dependency tracing

Every output is an artifact with a provenance record, written to one JSONL trace per run. Phase 2 reads this same trace to decide what to invalidate, so it is built now.

Each artifact record holds:

- `artifact_id`, `producer` (agent or tool), `step`, and a content hash
- `inputs`: the artifact IDs it was given (explicit dependencies)
- `state_reads` and `state_writes`: record keys and file paths, with versions before and after
- `tokens_in`, `tokens_out`, `latency_ms`, `status` (ok, timeout, error)
- `injected`: the fault ID if this artifact was rewritten by the harness

**Shared state is versioned from day one.** The key-value store keeps an append-only write log, and the workspace folder is snapshotted per step (a copy or a git commit). This makes the state-level dependencies visible: a later read of a record a faulty step wrote depends on that fault, even if the artifacts never reference each other.

**From the trace, a script computes:** the dependency graph, the set of artifacts downstream of each injected fault, and which of those actually differ from the paired clean run.

## Baselines and metrics

Four conditions run on the same tasks and fault schedule. Recovery methods are told which artifact is faulty, so recovery is measured apart from detection.

| Condition | What happens | Why it is there |
| --- | --- | --- |
| Clean | No fault | Capability ceiling; tasks it fails are excluded from propagation analysis and reported |
| Faulted, no recovery | Fault injected, run continues | Measures propagation and damage |
| Full restart | Restore initial state, rerun every step with the fault removed | The required recovery baseline |
| Always-verify | A verifier call checks each intermediate result before hand-off | Prevention baseline; its extra tokens are counted |

| Metric | Definition |
| --- | --- |
| Clean task success | Share of tasks whose final state passes the check with no fault |
| Propagation rate | Share of faulted runs where a downstream artifact or the final state differs from clean |
| Failure rate | Share of faulted runs that fail the check, split by fault class and stage |
| Unauthorized actions | Tool calls outside the task's allowed set, per run |
| Affected stages | Number of downstream artifacts that changed because of the fault |
| Wasted work | Steps and tokens rerun by recovery whose output matches what they produced before |
| Irreversible effects | Outbox messages and ledger entries produced from faulty inputs |
| Latency and cost | End-to-end wall time and total tokens, including verifier and recovery calls |

Failed runs and timeouts stay in the data with their status, never dropped. Results with repeated seeds report the mean and the min to max range.

## Environment and budget

Develop on laptops; run measured experiments on one AWS CPU instance with a self-hosted model through llama.cpp. Self-hosting fixes the model version, seed and sampling, which an API endpoint may not guarantee.

| Item | Plan | Note |
| --- | --- | --- |
| Instance | c7i.xlarge (4 vCPU, 8 GB) to start; c7i.2xlarge (8 vCPU, 16 GB) if generation is too slow | On-demand roughly $0.18/hr and $0.36/hr (approximate; check the EC2 console) |
| Model | A 3–4B instruct model in GGUF Q4_K_M (for example Qwen2.5-3B-Instruct); a 7B model only if clean success is too low | Same model and quantization for every condition |
| Runtime | llama.cpp server at a pinned commit, OpenAI-compatible endpoint | Record the commit hash and build flags |
| Orchestration | Python 3.11, plain code over the endpoint (no agent framework needed) | Pin all dependencies in a lockfile |
| Isolation | Agents, tools and state inside one Docker container per run | Makes snapshots and fresh state per run simple |
| Storage | Traces and results to S3; model weights on a small EBS volume | EBS bills while the instance is stopped |

**Budget:** with a $3/day limit per student, an instance can run about 16 hours a day on c7i.xlarge or 8 on c7i.2xlarge. Stop it between experiment batches, and cap output tokens per agent call so runs stay short.

**Fallback:** if CPU inference is too slow or the small model fails too many clean tasks, run the same harness against a TritonAI model and report that change explicitly.

## Phase 1 deliverables

The submission is one repository that reproduces every number in the writeup with a single command per condition.

- [ ] Workflow: researcher, planner and executor with fixed prompts
- [ ] Simulated tools, versioned record store, workspace snapshots, outbox and ledger
- [ ] About 40 development and 40 held-out tasks with expected final states and allowed actions
- [ ] Outcome checker (pass or fail, unauthorized actions, irreversible effects)
- [ ] Fault-injection harness with a saved, seeded schedule
- [ ] JSONL traces with provenance for every artifact
- [ ] Runs for clean, faulted, full restart and always-verify on the development tasks
- [ ] Analysis script producing every table and plot in the writeup
- [ ] README with setup, pinned versions and commands
- [ ] 1–2 page writeup plus timeline appendix

## Phase 2 direction (preview)

The planned mechanism is dependency-aware invalidation with state rollback; Phase 1 traces will confirm or redirect it. Given a faulty artifact, recovery:

1. Walks the provenance graph, through both artifact inputs and state reads, to find every downstream artifact.
2. Restores the record store and workspace to the version before the first affected write.
3. Handles effects that rollback cannot undo: reversal entries for refunds, and a flagged follow-up message for outbox entries.
4. Reruns only the invalidated steps and reuses the rest.
5. Checks that the reused results still match a fresh rerun on a sample, to confirm they really were valid.

It will be compared with full restart and always-verify under the same fault schedules and budgets. Phase 1 tells us whether this is worth building: if most faults spread to every later stage, selective recovery saves little, and the writeup should say so.

## Appendix: timeline and milestones

*Diagram (timeline): Workflow and tasks Oct 28–31 · Fault harness and tracing Oct 30–Nov 1 · Baseline runs Nov 1–3 · Phase 1 writeup Nov 2–4 · **Phase 1 due Nov 4** · Selective invalidation Nov 5–17 · State rollback and effects Nov 12–24 · Held-out evaluation Nov 23–Dec 3 · Final report Dec 1–9 · Final due Dec 10.*

Phase 1 work overlaps on purpose: tracing is built alongside the workflow, so baseline runs can start by November 1. Phase 2 builds invalidation first, adds state rollback and irreversible effects next, then leaves a week each for held-out evaluation and the report.

## Risks and open decisions

| Risk | Sign | Fallback |
| --- | --- | --- |
| Small model fails too many clean tasks | Clean success under about 60% on dev tasks | Simplify templates, move to a 7B model, or use TritonAI |
| Faults never matter | Paired runs rarely differ | Make tasks depend on the injected fields; keep the control faults |
| CPU runs too slow for the matrix | One full condition takes over a few hours | Cap tokens, cut tasks per template, run conditions in parallel containers |
| Budget runs out | Daily limit hit before runs finish | Develop locally; launch AWS only for measured batches |

**Open decisions:**

- [ ] Team size and who owns agents, environment, harness and analysis
- [ ] Final model choice after a pilot of 10 clean tasks
- [ ] Whether always-verify uses the same model or a separate one
- [x] Confirm the Phase 1 deadline: **Nov 4** (confirmed Oct 27)
