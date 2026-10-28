# Step 1: Repo scaffold (done Oct 27)

## Outcome

- Layout: `agents/ env/ tasks/ faults/ recovery/ eval/ runs/ docker/ scripts/ tests/`
- `README.md` with a status checklist, `.gitignore` (excludes weights, `runs/`, secrets),
  `.python-version` (3.11), `requirements.txt`.
- `env/state_store.py`: versioned key-value store with an append-only write log and
  `rollback_to(version)`. Still useful after the scenario change.
- `env/tools.py`: five customer-support tools. **To be replaced in step 3** with coding tools.
- `tests/test_env.py`: 8 tests, passing.
- First commit `f7c796b` on `main`, authored as rayray4059.
