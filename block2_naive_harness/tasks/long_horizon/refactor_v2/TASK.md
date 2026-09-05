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

## What to watch for

- Every `run_tests` call feeds the FULL pytest output (dozens of long
  tracebacks) back into the conversation — the transcript balloons.
- The agent must hold 14 rename rules and per-file progress in its head.
  Watch for files revisited, renames re-applied or reverted, and progress
  that oscillates instead of converging.
- Compare with a short task: same harness, same model, same tools. The only
  thing that changed is the horizon.

## Maintenance

`workspace/` is generated — never edit it by hand. The v2 ground truth lives
in `reference/` (tests green by construction). To change the task, edit
`reference/` and re-run `python scripts/derive_workspace.py` from the repo
root.
