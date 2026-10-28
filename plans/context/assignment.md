# What Option 5 requires

Condensed from the course PDF (CSE 291A Fall 2026, Course Projects). Quotes are exact.

## The question

> "Can tracking dependencies between agent results support efficient recovery while
> preserving correct and safe task execution?"

Example from the PDF: a researcher gives a planner a fabricated fact, an executor acts on the
plan, and once the researcher's result is known to be faulty the system must decide which
later outputs are still usable and which must be recomputed.

## Setup

- Run inference, orchestration and simulated tools on small AWS CPU instances or laptops.
- "Build a small workflow, such as researcher–planner–executor, with programmatically
  checkable outcomes." The domain is our choice.
- Compute: $50 AWS credits per student, $3 daily spending limit, credits stack within a team.
  Use TritonAI for LLM API usage.

## Phase 1 (due Nov 4): fault injection and propagation measurement

- Build and measure a clean baseline workflow.
- Inject faults at controlled stages: incorrect results, malicious instructions, timeouts,
  stale outputs. **Keep accidental and adversarial faults separate.**
- Record messages, intermediate artifacts, tool actions and dependencies.
- Measure: clean task success, failure propagation, unauthorized actions, affected stages,
  wasted work, end-to-end latency.
- "Determine whether the workload actually depends on the injected result; an ignored
  message is not evidence of robust recovery."
- Baselines: **full restart**, plus **always verifying** intermediate results, counting its
  extra inference cost.
- Report: 1–2 pages plus an appendix with timeline and milestones.

## Phase 2 (due Dec 10): selective recovery

- One focused mechanism. Suggested default: dependency-aware invalidation. Tag results with
  sources, find downstream results of a faulty output, restore affected simulated state, rerun
  only what's needed.
- Give every recovery method the identity of the faulty result (recovery is judged apart
  from detection). Automated detection is optional and must report false positives and
  misses separately.
- Harder case: the environment has changed (files overwritten, browser state). Snapshots
  with a VM, MicroVM or container are one approach.
- Compare against full restart and verification under identical fault schedules and budgets.
- "Report actions that cannot be undone rather than counting recomputation as complete
  recovery."
- Measure: recovered correctness, unauthorized actions, recomputed stages, retained valid
  work, recovery latency, inference cost, tracking overhead. Check that reused results really
  remain valid.
- Submit: workflow, injection harness, dependency/recovery mechanism, traces, analysis.

## How it's graded

- Strong submissions "distinguish detection from recovery, demonstrate meaningful propagation
  paths, handle shared-state dependencies, and explain the tradeoff between recovery precision
  and bookkeeping overhead."
- General criteria: baseline reproduction and measurement quality; Phase 2 design and
  implementation; controls and comparisons; depth of analysis; reproducibility and clarity.
- Use separate development and evaluation workloads. Pin model, runtime, dataset and code
  versions. Record failed runs and timeouts. Repeat stochastic runs and report variability.
- "Distinguish a model's inability to complete a task from successful protection."
- Starting resources listed: TAMAS (Threats and Attacks in Multi-Agent Systems), A2ASecBench.
