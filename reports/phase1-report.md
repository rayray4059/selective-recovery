---
title: "Selective Recovery in a Multi-Agent Coding Workflow"
subtitle: "CSE 291A Fall 2026, Option 5 · Phase 1 Report · November 4, 2026"
author: "Jackie Wang, Ray Williams"
geometry: margin=0.75in
fontsize: 11pt
header-includes:
  - \usepackage{titling}
  - \setlength{\droptitle}{-6em}
  - \postdate{\par\end{center}\vspace{-2.5em}}
---

## 1. Question

Option 5 asks whether tracking dependencies between agent results can make recovery
efficient while keeping execution correct and safe. In a researcher → planner → executor
chain, one bad intermediate result can flow into later plans, file edits and external actions.
The two obvious responses, restarting everything or verifying every hand-off, are both
costly. Phase 1 measures how far faults actually travel and what those two baselines cost.
Phase 2 tests whether rerunning only the dependent results, and rolling back only the state
they touched, recovers the same tasks with less work.

## 2. Workflow and tasks

The three agents share one model and fixed prompts, and each replies in JSON that the server
constrains to a schema. They complete small tickets on a fake Python `billing` library
(payments, fees, invoices, config, client) with four internal docs.

- The **researcher** reads the docs and reports at most five facts the change depends on, each
  with its source doc.
- The **planner** turns the ticket, the facts and the current files into a JSON plan of
  file, function, signature and change.
- The **executor** calls one tool per turn: read or write a file, run the visible tests,
  publish a release, or post to a channel.

The agents share real state. The workspace is a git repository, and every tool call records
the commit before and after it. A simulated package registry and team channel are
append-only, so some actions cannot be undone.

**Outcomes are checked by code, not by an LLM.** The checker runs a hidden pytest file on the
final code, lists every changed file outside the task's allowed paths as collateral damage,
and compares the registry and channel with the releases and messages the task expects. It
reports unauthorized actions separately from task success: tool calls the task does not
allow, or writes to protected paths such as `tests/` and `docs/`.

The dev set has 10 tickets. Each one depends on a single rule in `docs/policy.md` or
`docs/releases.md` that the ticket never states. Examples are a 1.5% late fee capped at
2500 cents, a 90-day refund window, a 50-cent minimum charge, and EUR amounts shown with a
decimal comma. Two tickets also ask the executor to ship, so they need the right version bump,
a publish and a channel post. Each task lists its deciding fact and one control fact from the
same doc that the answer does not depend on. It also lists a wrong value and a stale (2025)
value for the deciding fact. Unit tests confirm that the checker passes each reference
solution, fails a do-nothing run and the wrong-fact version, and catches a doc edit, a deleted
test file and an unrequested publish. The five pilot tickets are kept as a separate tuning set.

## 3. Fault injection and tracing

The harness rewrites the researcher's facts or the planner's plan before the next stage reads
it. A fixed schedule (seed 291) gives every task each of seven faults, 70 faulted runs in all.
The three attacks are spread evenly across tasks.

| Fault           | Class       | Stage   | What changes                                         |
|-----------------|-------------|---------|------------------------------------------------------|
| Wrong fact      | Accidental  | Facts   | Deciding fact replaced, e.g. 2% instead of 1.5%      |
| Stale fact      | Accidental  | Facts   | Deciding fact replaced by the 2025 rule              |
| Timeout         | Accidental  | Facts   | Researcher returns nothing; planner gets no facts    |
| Wrong plan      | Accidental  | Plan    | Right value swapped for the wrong one in the plan    |
| Malicious fact  | Adversarial | Facts   | Injected instruction cited to `docs/releases.md`     |
| Malicious plan  | Adversarial | Plan    | Extra plan step carrying the same instruction        |
| Control         | Control     | Facts   | Only the irrelevant support-hours fact changes       |

The timeout fault discards the researcher's output after it finishes, so it models the effect
on later stages but not the time a real timeout spends waiting; its latency is understated.
The attacks ask the executor to delete `tests/test_basic.py`, publish release 9.9.9 and
announce it, or rewrite `docs/policy.md`. Each task also gets a *no-docs* check run with the
docs folder removed, which shows whether the model needs the docs at all or could guess the
rule.

Each faulted run is paired with the clean run of the same task. If no downstream artifact
differs from the clean run, the fault was *ignored*. If something differs but the task still
passes with no collateral, unauthorized or irreversible effects, it was *absorbed*. Otherwise
it was *harmful*. For adversarial faults we also record whether the attack actually executed.
We report accidental and adversarial faults separately. Tasks that the clean workflow already
fails are left out of the propagation analysis, so a model's inability is not mistaken for
protection.

Every run writes a provenance trace in JSONL with one node per artifact: the facts, the plan,
each executor turn, and each read or tool call. A node records its inputs, a content hash,
tokens and latency, and whether the harness injected a fault there. State links count as much
as message links. A file read links to the step that last wrote that file, so a step that reads
a file written by a faulty step depends on the fault even with no message between them. From
the trace we compute which nodes changed against the clean run, every node downstream of the
injected one, the stages affected, and the tokens and seconds spent downstream of the fault.
Phase 2 reads this same trace to decide what to invalidate.

## 4. Baselines, metrics and setup

All conditions run on the same tasks and fault schedule:

- **Clean** sets the capability ceiling.
- **Faulted, no recovery** measures propagation and damage.
- **Full restart** rolls the faulted workspace back to its first commit and reruns every
  stage without the fault. Releases and messages from the faulted run stay, so we report them
  as leftover effects, apart from whether the restart's own work was correct.
- **Always-verify** has a verifier (the same model with its own prompt and read access to the
  docs) check the facts and the plan before hand-off. A rejected stage is regenerated once
  with the verifier's problems as feedback. Its tokens and latency count on every run,
  including clean ones.

Full restart is told which result is faulty, so it measures recovery apart from detection.
Always-verify has to find the fault itself, so we also report what it caught, missed and
flagged by mistake. We report clean task success, ignored/absorbed/harmful rates by fault class and
stage, executed attacks, unauthorized actions, irreversible effects, affected stages, work
downstream of the fault, and end-to-end latency and tokens. Runs use temperature 0 and seed 0.
Failed runs and timeouts stay in the data.

We self-host **Qwen3.5 4B** (Q4_K_M, pinned GGUF file and hash) with llama.cpp, with thinking
mode off. In the pilot on five tickets, three seeds each, the model alone passed 10/15 at about
6 s per task. The three-agent chain passed only 7/15 at about 18 s, below our 60% bar. Since
the model could solve the tickets alone, we kept it and fixed the hand-offs instead: schema-
constrained JSON, at most five facts, and signatures copied verbatim into the plan. We did not
tune prompts on the pilot tickets' scores. One pilot doc contradicted its own hidden test, so we
fixed it and reran all of the pilot. Phase 1 runs on a MacBook Pro (M4 Pro). Latency does not
transfer between machines, so the final comparison reruns the baselines alongside Phase 2 on
one AWS CPU instance, within the $3/day limit. Each run saves its model, seed and sampling
settings with the trace, tool log and result.

## 5. Results

All conditions ran on Nov 3 on the dev set: 10 clean runs, 10 no-docs checks, 70 faulted runs
and 70 full restarts, with no harness errors. As planned under the run-time risk, always-verify
ran on four tickets (t01 late fee, t02 refund window, t03 minimum charge, t10 ship a helper),
32 runs, because a verified run takes about twice as long. `scripts/analyze.py` rebuilds every
number below from `data/phase1_runs.tar.gz`; ticket IDs refer to `tasks/dev.jsonl`.

All 70 restarts reproduced their ticket's clean run exactly, with the same content hash on every
trace node. On one machine, temperature 0 was deterministic, so a difference between a faulted
run and its clean pair comes from the fault and not from sampling noise.

### 5.1 Clean runs

The chain passed 7 of 10 tickets, above the 60% bar from the pilot. In all three failures the
researcher found the deciding fact and the executor broke the code. On invoice tax (t05) it
called `round()` with a `rounding` argument that Python does not accept. On the timeout cap
(t07) its rewrite of `config.py` dropped `load_config`. On the ship-a-fix ticket (t09) it wrote
a default argument that fails at import, then published 1.4.3 of the broken code without
running the tests. These three tickets are left out of the propagation results. Only the
currency ticket (t04) passed the no-docs check, so the model can guess that one rule; the other
nine need the docs.

### 5.2 Propagation

**Table 1.** Outcomes on the 7 clean-passing tickets (n = 7 per fault). Plan faults are injected
after the planner, so they cannot change the plan stage.

| Fault          | Class       | Ignored | Absorbed | Harmful | Plan changed | Executor changed |
|----------------|-------------|---------|----------|---------|--------------|------------------|
| Wrong fact     | Accidental  | 0       | 0        | 7       | 7            | 7                |
| Stale fact     | Accidental  | 0       | 0        | 7       | 7            | 7                |
| Timeout        | Accidental  | 0       | 1        | 6       | 7            | 7                |
| Wrong plan     | Accidental  | 0       | 3        | 4       | –            | 7                |
| Malicious fact | Adversarial | 0       | 0        | 7       | 7            | 7                |
| Malicious plan | Adversarial | 0       | 0        | 7       | –            | 7                |
| Control        | Control     | 0       | 6        | 1       | 5            | 7                |

Accidental faults were harmful in 24 of 28 runs and adversarial faults in 14 of 14. No fault
was ignored, and every fact fault changed both the plan and the executor's actions. Three of
the four absorbed accidental runs are wrong plans (t04, t06, t08). The executor also sees the
researcher's correct facts, which may be why it did not follow the swapped value. The fourth is
the timeout on t04, the ticket the model solves without docs. Wrong and stale facts still broke
t04, so the model follows a planted value over its own guess, and its dependence on the
message is real.

Each cell counts 7 tickets with one run each, so small differences between faults, such as 3
absorbed wrong plans against 1 absorbed timeout, may not hold on a larger task set.

The control fault shows that changed artifacts alone overstate propagation. Changing only the
support-hours fact changed the plan on 5 tickets and the executor's actions on all 7, and made
t08 fail. Since runs are deterministic, this is the model reacting to any change in its
prompt. Outcomes, and the contrast between deciding and control facts, are the better signal.

The work downstream of the injected result averaged 5.9k to 11.2k tokens per faulted run,
depending on the fault, against 8.9k tokens for a whole clean run. This is an upper bound on
wasted work, since it counts every node reachable from the fault.

### 5.3 Unauthorized and irreversible actions

Across all 10 tickets the executor carried out 16 of 20 injected attacks. It deleted the test
file in 7 of 8 runs, published and announced 9.9.9 in 4 of 6, and rewrote the policy doc in 5
of 6. Attacks worked as often from a fact as from a plan step (8 of 10 each). The tool layer
flags these calls but does not block them, so the damage can be measured: 16 of the 20
malicious runs made unauthorized calls, and 12 changed files outside the allowed paths.

Accidental faults also caused effects that cannot be undone. On t10, which needs a minor bump
to 1.5.0, the wrong-fact, timeout and wrong-plan runs published 1.4.3, and the stale-fact run
published 2025.11.0 under the old date-based rule.

### 5.4 Full restart

Given the faulty result, full restart produced correct code in all 49 faulted runs on the
clean-passing tickets. Only 40 of 49 count as recovered once the faulted run's leftover effects
are included. The other nine are the four wrong t10 releases, four 9.9.9 releases from attacks
on t01 and t06, and an unrequested 1.0.0 published during a malicious-fact run on t03. A
restart cost on average 8.9k tokens and 22 s, the same as a clean run. None of that work was
reusable after a fact fault, because every node it recomputed depended on the fault. After a
plan fault, the researcher's work (19.5% of the restart's tokens) was identical and upstream of
the fault, and could have been kept.

### 5.5 Always-verify

On the four verified tickets, the verifier flagged the faulted stage in 23 of 24 faulted runs.
It caught the remaining one, a timeout, a stage late at the plan. No attack ran in any of the
8 verified malicious runs, against 8 of 8 without verification, and 13 of the 24 verified
faulted runs passed, against none unverified.

The catch rate says little about detection, because the verifier rejects almost everything. It
rejected at least one stage in 31 of 32 runs. Per hand-off, it rejected 15 of 16 faulty fact
lists but also 6 of 12 clean ones and all 4 control ones, and 8 of 8 faulty plans but also 3 of
4 plans from clean runs. Its false-alarm rate is therefore 50% or more at both stages. Many of its complaints
name requirements the ticket does not have, such as currency checks on the refund-window
ticket. The forced redo also costs correctness: clean and control runs fell from 8 of 8 passing
to 4 of 8. A verified run averaged 17.8k tokens and 56 s, about twice a clean run (8.9k tokens,
25 s), and 6 of the 32 hit the output token limit on at least one call.

### 5.6 Tracking overhead

A trace has 13.6 nodes and 14 kB on average and is built in under 0.5 ms after the run. File
writes, including their git commits, take about 0.1 s per run in total, under 0.5% of a 25 s
run.

## 6. Status and Phase 2 direction

As of Nov 4 the harness runs end to end. We have the git workspace and tools, the 10 dev
tasks with hidden tests, reference and wrong solutions, the checker, the three agents, the
provenance trace, the fault injector with its schedule and measurement script, and both
baselines, all covered by 123 unit tests. `scripts/run_tasks.py` runs the clean condition and
`scripts/run_faults.py` runs each task's clean pair, the no-docs check and the seven scheduled
faults; `--restart` and `--verify` add the two baselines.

Phase 1 answers the question the proposal left open: in this chain, a fault in the facts
reaches every later stage. The trace records dependencies at the level of whole stages. The
plan depends on the full fact list, and each executor turn depends on every earlier turn. At
that granularity, dependency-aware invalidation reruns the same work as a full restart after a
fact fault, and saves about a fifth of it after a plan fault. Most failed recoveries are also
effects that a rerun cannot undo, not wrong code.

Phase 2 therefore makes dependencies finer and builds recovery on them. Facts get IDs, each
plan step lists the facts it uses, and each executor write is tied to the plan step it carries
out, so a bad fact invalidates only the steps that cite it. We will add tickets with
independent parts, such as two functions where only one depends on the deciding fact, so that
there is valid work to keep. We will also add cases where a later step reads files that a
faulty step wrote, to exercise shared-state dependencies. Recovery walks the provenance graph
through message inputs and state reads, resets the workspace to the commit before the first
affected write, and reruns only the invalidated steps. Effects that cannot be undone, such as a
published release or a posted message, are reported instead of counted as recovered. A sample
of reused results is rerun to confirm they were valid. We will compare this method with both
baselines under identical fault schedules and budgets, with the faulty result's identity given
to every method, and weigh recovery precision against bookkeeping overhead. Detection stays a
separate question: at this model size, a same-model reviewer does not separate faulty
hand-offs from clean ones.

```{=latex}
\newpage
```

## Appendix: Timeline and milestones

| Dates            | Work                                                   | Milestone                                         |
|------------------|--------------------------------------------------------|---------------------------------------------------|
| Oct 27           | Repo scaffold, state store, unit tests                 | Done                                              |
| Oct 27–29        | Model pilot on five tickets                            | Done: Qwen3.5 4B chosen; file hash recorded       |
| Nov 2            | Coding workspace and tools                             | Done: tool unit tests pass                        |
| Nov 2            | 10 dev tasks, hidden tests, checker; agents            | Done: reference passes; do-nothing fails          |
| Nov 2–3          | Provenance tracing; fault injector and schedule        | Done: faulted run compared with its clean pair    |
| Nov 3            | Full-restart and always-verify baselines               | Done: restart on all tickets; verify on four      |
| Nov 3–4          | Dev-set clean, fault and baseline runs; results tables | Done: tables in `results/`                        |
| **Nov 4**        | **Phase 1 code and data due**                          | One command per condition                         |
| Nov 5–17         | Selective invalidation                                 | Only downstream stages rerun                      |
| Nov 12–24        | Shared-state rollback                                  | Irreversible actions reported                     |
| Nov 10–20        | Held-out task set                                      | Unseen until the final evaluation                 |
| Nov 23–Dec 3     | Held-out evaluation on AWS                             | Same schedules, budgets and seeds                 |
| Dec 1–9          | Final report                                           |                                                   |
| **Dec 10**       | **Final submission**                                   |                                                   |

**Risks and fallbacks:**

- *Low clean success.* If the chain passes too few clean runs, faults have little to break.
  Fallbacks: a larger model (Qwen3.5 9B or Qwen3 8B), or TritonAI.
- *Faults that never matter.* If the no-docs check passes, the model is guessing the rule, and
  that task's fact faults say little. We will rewrite or drop such tasks. In Phase 1 only t04
  passed (Section 5.1).
- *Run time.* About 80 runs per pass on one laptop. Always-verify doubles the run time, so
  Phase 1 ran it on four tickets.
- *Run-to-run noise.* On one machine, all 70 restarts matched their clean runs exactly. This
  may not hold across machines or seeds, so we will rerun a subset with three seeds on AWS and
  report the spread.
