# Block 2 Exercise: Build a Harness, Watch It Win, Watch It Die

Time: ~55 minutes. Everything runs locally against your provider API key.
Cost for the whole exercise: roughly $1–2.

All commands below are run from this directory (`block2_naive_harness/`),
with your virtualenv active.

## Step 0 — Confirm you're ready (2 min)

```
python ../setup/check_setup.py
```

Expect `ALL GREEN`. If not, fix what it tells you (or flag a helper).

## Step 1 — Read the code you were given (5 min)

Open `tools.py`. Your agent gets five tools: `list_files`, `read_file`,
`write_file`, `search`, `run_tests`. Notice what they DON'T do: no output
truncation, no size limits, no permissions. Remember that.

Open `harness_skeleton.py`. The client, system prompt, and tool schemas are
done. Two things are missing — the two things that make it an agent.

## Step 2 — Write the harness (15–20 min)

Complete the two TODO blocks in `harness_skeleton.py`:

- **TODO 1 — the tool dispatcher** (~10 lines): map each tool name to the
  matching `Workspace` method.
- **TODO 2 — the agent loop** (~25 lines): call the model, execute its tool
  calls, feed results back, repeat until it stops calling tools.

The comments in each block spell out every step. If you're stuck or short
on time, copy from `solution/harness.py` and move on — the point of this
block is what happens next, not the typing.

## Step 3 — Run it on a small task (5 min)

```
python harness_skeleton.py tasks/short/01_fix_bug/workspace \
  "Fix the failing test. See TASK.md in the workspace."
```

Watch the turns print. Expected: ~5 turns, under a minute, ending with a
summary and green tests. Verify yourself:

```
python -m pytest tasks/short/01_fix_bug/workspace -q
```

You just built a working coding agent in ~40 lines. Optional: run
`tasks/short/02_add_function` and `03_small_rename` the same way (see each
TASK.md for the run command).

## Step 4 — Run it on a long task (10 min)

Same harness. Same model. Same tools. Bigger horizon:

```
python harness_skeleton.py tasks/long_horizon/refactor_v2/workspace \
  "Migrate the source code to the v2 API following MIGRATION.md until all tests pass. Do not modify the tests."
```

This one costs ~$0.50–1 per attempt — **run it once**, not five times.

While it runs, skim `tasks/long_horizon/refactor_v2/workspace/MIGRATION.md`
to see what you asked for, and watch what the agent does: how many files it
reads, what its searches return, how big its write batches get.

Expected: the run **does not end well**. Typical deaths: a raw Python
traceback mid-run (a truncated tool call the harness couldn't parse), a
context-length error, or the 40-turn cap with tests still red. Check the
wreckage:

```
python -m pytest tasks/long_horizon/refactor_v2/workspace -q
```

Half-migrated. Money spent. Agent gone.

To reset the workspace for another attempt (from the repo root):

```
git checkout -- block2_naive_harness/tasks/long_horizon/refactor_v2/workspace
```

## Step 5 — The autopsy (group debrief)

Before the debrief, answer for yourself:

1. What was the *proximate* cause of death in YOUR run? (Read the last few
   lines of output.)
2. Where did most of the context go? (Reads? Search results? Test output?
   The agent's own file rewrites?)
3. What did the agent "know" at turn 5 that it had effectively lost by the
   time it died?
4. Which of these would a better *model* fix? Which need a better *harness*?

The table in `README.md` maps each failure to the missing harness
component. Block 3 adds those components — and measures them.
