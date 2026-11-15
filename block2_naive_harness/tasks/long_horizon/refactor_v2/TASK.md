# Long-horizon task: the pyledger v2 migration

This task is deliberately sized past the naive harness's design limits —
the failure it produces is the subject of Blocks 2 and 3.

The `workspace/` contains **pyledger**, a small double-entry bookkeeping
library (149 source files), whose test suite was already updated to the v2
API. The source still uses legacy v1 names. `workspace/MIGRATION.md` lists
the 14 rename rules. The agent must apply them across every file until
`pytest` is green. Do not modify the tests.

Run it (from `block2_naive_harness/`):

```
uv run harness_skeleton.py tasks/long_horizon/refactor_v2/workspace \
  "Migrate the source code to the v2 API following MIGRATION.md until all tests pass. Do not modify the tests."
```

(`MIGRATION.md` is inside the workspace, so the agent CAN read that one.)

## What to watch for

- The codebase (~150 files) is too big to read and rewrite comfortably in
  one pass, and the changelog is incomplete: the agent has to search,
  sample and work out 6 of the 14 renames from the failing tests.
- `search` results across 149 files and full pytest tracebacks are large,
  and the naive harness keeps them in the conversation and re-sends them
  every turn.
- When the agent writes many files in one turn, the model can hit its
  output limit mid-batch and send a cut-off tool call. The naive harness
  has no error recovery, so `json.loads` raises and the run dies.
- With Block 2's 20-turn cap, a run ends one of five ways: finished and
  said so, finished but never said so, ran out mid-job, never started
  (spent its turns reading), or crashed. See Block 2's README.
- Compare with a short task: same harness, same model, same tools. Only
  the size of the job changed.

## Maintenance

`workspace/` is generated — never edit it by hand. The v2 ground truth lives
in `reference/` (tests green by construction). To change the task, edit
`reference/` and re-run `uv run scripts/derive_workspace.py` from the repo
root.
