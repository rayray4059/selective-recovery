# References

## Benchmarks whose task design we borrow from

| Work | What it does | What we take |
| --- | --- | --- |
| [τ-bench](https://sierra.ai/blog/benchmarking-ai-agents) ([paper](https://export.arxiv.org/pdf/2406.12045)) | Customer-service agents with a database, tool APIs and policy docs. After the run, the final database is compared to a target goal state; the conversation isn't graded. pass^k measures success across all k repeated trials. | Policy or docs decide the answer; grade final state, not text; report reliability across repeats |
| [AppWorld](https://arxiv.org/abs/2407.18901v1) | 9 apps, 457 APIs, 750 tasks. State-based unit tests allow different valid solutions and check for collateral damage. | Check outcomes, not one call sequence; check that nothing else changed |
| [AgentDojo](https://ar5iv.labs.arxiv.org/html/2406.13352) | User tasks with a deterministic utility function and ground-truth calls; injection tasks with a security function. Code checks, not an LLM judge. Ground truth is run through its own check, and tells where to place injections. | Separate success from security; an oracle checked against the checker; know which inputs a task depends on (`deciding_facts`) |

What's new in our project: those benchmarks test a single agent. We measure how a bad result
travels between agents, hence `deciding_facts` and paired clean runs.

## Course starting resources

- TAMAS: Threats and Attacks in Multi-Agent Systems
- A2ASecBench

## Model selection (for step 2)

- [Best CPU-only local LLMs in 2026](https://www.popularai.org/p/best-cpu-only-local-llm-2026):
  Qwen3.5 4B is the top CPU pick (coding help, small agents with tight prompts); Phi-4-mini
  for instruction following and structured output; Qwen3 8B for stronger coding at the
  32 GB tier. Start at Q4_K_M.
- [Top 7 coding models you can run locally in 2026](https://www.kdnuggets.com/top-7-coding-models-you-can-run-locally-in-2026):
  Qwen3.5 9B is the smallest listed and the pick without a big GPU.
