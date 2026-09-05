# Long-horizon task: the pyledger v2 migration

This is the task that breaks the naive harness — on purpose.

The `workspace/` contains **pyledger**, a small double-entry bookkeeping
library (~20 source files), whose test suite was already updated to the v2
API. The source still uses legacy v1 names. `workspace/MIGRATION.md` lists
the 14 rename rules. The agent must apply them across every file until
`pytest` is green. Do not modify the tests.

Run it (from `block2_naive_harness/`):

```
python solution/harness.py tasks/long_horizon/refactor_v2/workspace \
  "Migrate the source code to the v2 API following MIGRATION.md until all tests pass."
```

## What to watch for (observed in live tuning runs, Sep 2026, GLM-5.3)

- The codebase (~150 files) cannot be read-and-rewritten inside one context
  window, and the changelog is incomplete — the agent must search, sample,
  and iterate rather than one-pass a plan.
- `search` results spanning 149 files and full pytest tracebacks are context
  bombs the naive harness feeds back whole.
- When the agent batches many large `write_file` calls in one turn, the
  model can hit its output ceiling mid-batch and emit a truncated tool
  call. The naive harness has no error recovery: `json.loads` raises, the
  run dies with a raw traceback, and the workspace is stranded
  half-migrated. This exact death occurred at turn 11 of the first live
  v0.3 run — 6 files migrated, suite still red, money spent.
- Also possible: context-length API error late in the run, or the 40-turn
  cap with tests still failing. All three deaths are harness-caused, not
  model-caused — the same model solved the small tasks flawlessly.
- Compare with a short task: same harness, same model, same tools. The only
  thing that changed is the horizon.

## Maintenance

`workspace/` is generated — never edit it by hand. The v2 ground truth lives
in `reference/` (tests green by construction). To change the task, edit
`reference/` and re-run `python scripts/derive_workspace.py` from the repo
root.
