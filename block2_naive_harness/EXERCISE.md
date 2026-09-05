# Block 2 Exercise: Build a Harness, Watch It Win, Watch It Die

Time: ~55 minutes. Everything runs locally against your provider API key.
Cost for the whole exercise: roughly $1–2.

All commands below are run from this directory (`block2_naive_harness/`)
via `uv run` — no virtualenv to create or activate, ever. uv finds the
project environment itself and installs anything missing on first run, so
shell aliases and forgotten activations can't bite you.

## Step 0 — Confirm you're ready (2 min)

```
uv run ../setup/check_setup.py
```

Expect `ALL GREEN`. If not, fix what it tells you (or flag a helper).

## Step 1 — Read the code you were given (5 min)

Open `tools.py`. Your agent gets five tools: `list_files`, `read_file`,
`write_file`, `search`, `run_tests`. Notice what they DON'T do: no output
truncation, no size limits, no permissions. Remember that.

Open `harness_skeleton.py`. The client, system prompt, and tool schemas are
done. Two things are missing — the two things that make it an agent.

## Step 2 — Complete the harness (10 min)

The agent loop is scaffolded in `harness_skeleton.py`; you fill in the two
moments that matter:

- **TODO 1 — ask the model what to do next** (~4 lines): the API call that
  sends the full conversation plus the tool schemas.
- **TODO 2 — execute the tool and feed the result back** (~5 lines): look
  up the tool, invoke it, append the result to the transcript.

Each TODO comment shows you exactly what to write. If you're stuck or short
on time, copy from `solution/harness.py` and move on — the point of this
block is what happens next, not the typing.

## Step 3 — Run it on a small task (5 min)

**First, see the bug with your own eyes.** Run the tests before the agent
touches anything:

```
uv run python -m pytest tasks/short/01_fix_bug/workspace -q
```

Expect `2 failed, 2 passed`. Read the first failure — the assertion diff
tells you everything:

```
assert [1.5, 2.5] == [1.5, 2.5, 3.5]
```

`moving_average([1, 2, 3, 4], 2)` should slide a 2-wide window and average
each one:

```
[ 1  2  3  4 ]
  └──┘            (1+2)/2 = 1.5   ✓
     └──┘         (2+3)/2 = 2.5   ✓
        └──┘      (3+4)/2 = 3.5   ✗ never computed — the loop stops early
```

The last window is dropped. Want to poke the bug directly, no test
framework in between?

```
cd tasks/short/01_fix_bug/workspace
uv run python -c "from stats import moving_average; print(moving_average([1, 2, 3, 4], 2))"
cd ../../../..
```

It prints `[1.5, 2.5]` — two windows, not three. (Rerun it after the agent
fixes the file and you'll get all three.)

Don't fix it yourself — that's the agent's job. (Full spoiler in the
task's `TASK.md` if you want it.)

**Open `tasks/short/01_fix_bug/workspace/stats.py` in your editor and keep
it visible.** Look at line 6 — the buggy loop bound. Your editor will
reload the file the moment the agent rewrites it, so you'll see the fix
land live.

**Now unleash your agent on it.** The harness takes two arguments — the
workspace directory (the only files the agent's tools can see) and the task
prompt (`uv run harness_skeleton.py --help` for details):

```
uv run harness_skeleton.py tasks/short/01_fix_bug/workspace \
  "One test fails. Find the bug and fix it. Do not modify the tests."
```

Watch the turns print. Expected: ~5 turns, under a minute. Notice the agent
does exactly what you just did — runs the tests, reads the diff, reads the
loop — then edits.

**Verify it yourself** (never take an agent's word for it):
Run the following command from the block2_naive_harness directory

```
uv run python -m pytest tasks/short/01_fix_bug/workspace -q
```

`4 passed`. You saw red, the agent worked, you saw green. You just built a
working coding agent in ~40 lines. Optional: run
`tasks/short/02_add_function` and `03_small_rename` the same way (see each
TASK.md for the run command).

## Step 4 — Run it on a long task (10 min)

Same harness. Same model. Same tools. Bigger horizon:

```
uv run harness_skeleton.py tasks/long_horizon/refactor_v2/workspace \
  "Migrate the source code to the v2 API following MIGRATION.md until all tests pass. Do not modify the tests."
```

This one costs ~$0.50–1 per attempt — **run it once**, not five times.

While it runs, skim `tasks/long_horizon/refactor_v2/workspace/MIGRATION.md`
to see what you asked for, and watch what the agent does: how many files it
reads, what its searches return, how big its write batches get.

Expected: this **usually ends badly** — a raw Python traceback mid-run (a
truncated tool call the harness couldn't parse), a context-length error, or
the 40-turn cap with tests still red. But sometimes the agent limps
through after 30+ turns and roughly a **million input tokens** (~$1 for
one task!), because the naive harness resends the entire growing
transcript on every single call.

Both outcomes are data. The crash shows fragility; the expensive "success"
shows the cost curve. Note which one YOU got, the turn count, and the
wall time — you'll compare against protected harnesses in Block 3. Check
the state:

```
uv run python -m pytest tasks/long_horizon/refactor_v2/workspace -q
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
