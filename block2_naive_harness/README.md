# Block 2 — Build the Naive Harness

**Why this block:** Block 1 listed seven things a harness does — the loop,
tool dispatch, context management, memory, sandboxing, guardrails,
observability. This block builds an agent with only the first two, then
puts it under enough load to make the absence of the other five visible.
You can't reason about a protection you've never missed; the fastest way
to understand what a harness buys is to spend an hour without one. Block 3
then adds them back, one at a time, and measures what each is worth.

Time: ~55 minutes. Everything runs locally against your provider API key.
Cost for the whole exercise: roughly $1–2.

The plan: complete a minimal agent harness, verify it handles a short task,
then give it a task sized past its design limits and characterize how it
fails. The failure modes you observe here are what Block 3 fixes and
measures.

Everything below runs via `uv run` — no virtualenv to create or activate, ever. uv finds the
project environment itself and installs anything missing on first run, so
shell aliases and forgotten activations can't bite you.

## The harness you're completing

`harness_skeleton.py` is a complete agent loop with two gaps for you to
fill. It has no protections of any kind — that's the point of the block:

| Missing component | Symptom you'll see |
|---|---|
| Tool-output limits | Full pytest tracebacks flood the context every test run |
| Context compaction | Transcript grows monotonically until quality degrades or the request fails |
| Durable memory / plan | Rename rules and per-file progress live only in the transcript |
| Error recovery | A malformed tool call or transient API error derails the run |
| Loop budget & progress detection | The agent can redo and undo the same work indefinitely |

## Exercise flow

**Run every command in this section from the `block2_naive_harness/`
directory** — the paths below are relative to it, and they will fail from
anywhere else:

```
cd block2_naive_harness   # from the repo root
pwd                       # .../agent-harness-workshop/block2_naive_harness
```

Every command on this page, including the reset scripts, runs from here —
nothing requires switching directories mid-exercise.

### Step 0 — Confirm you're ready (2 min)

```
uv run ../setup/check_setup.py
```

Expect `ALL GREEN`. If not, fix what it tells you (or flag a helper).

### Step 1 — Read the code you were given (5 min)

Open `tools.py`. Your agent gets five tools: `list_files`, `read_file`,
`write_file`, `search`, `run_tests`. Notice what they DON'T do: no output
truncation, no size limits, no permissions. Remember that.

Open `harness_skeleton.py`. The client, system prompt, and tool schemas are
done. Two things are missing — the two things that make it an agent.

### Step 2 — Complete the harness (10 min)

The agent loop is scaffolded in `harness_skeleton.py`; you fill in the two
moments that matter:

- **TODO 1 — ask the model what to do next** (~4 lines): the API call that
  sends the full conversation plus the tool schemas.
- **TODO 2 — execute the tool and feed the result back** (~5 lines): look
  up the tool, invoke it, append the result to the transcript.

Each TODO comment shows you exactly what to write. If you're stuck or short
on time, copy from `solution/harness.py` and move on — the point of this
block is what happens next, not the typing.

### Step 3 — Run it on a small task (5 min)

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

Leave the fix to the agent — the point of this step is establishing the
before-state yourself. (Full explanation in the task's `TASK.md`.)

**Open `tasks/short/01_fix_bug/workspace/stats.py` in your editor and keep
it visible.** Look at line 6 — the buggy loop bound. Your editor will
reload the file the moment the agent rewrites it, so you can watch the
edit land.

**Now run your agent against it.** The harness takes two arguments — the
workspace directory (the only files the agent's tools can see) and the task
prompt (`uv run harness_skeleton.py --help` for details):

```
uv run harness_skeleton.py tasks/short/01_fix_bug/workspace \
  "One test fails. Find the bug and fix it. Do not modify the tests."
```

Watch the turns print. Expected: ~5 turns, under a minute. Notice the agent
does exactly what you just did — runs the tests, reads the diff, reads the
loop — then edits.

**Verify the result yourself** — an agent's self-report is not evidence;
the test suite is. Run the following from the block2_naive_harness
directory:

```
uv run python -m pytest tasks/short/01_fix_bug/workspace -q
```

`4 passed`. Red before, green after, confirmed by your own checker rather
than the agent's summary — that verification habit is the one to keep. The
harness that did this is about 40 lines. Optional: run
`tasks/short/02_add_function` and `03_small_rename` the same way (see each
TASK.md for the run command).

**Want to run it again?** The agent edited the workspace, so the bug is
gone. Put every task workspace back to its starting state from anywhere in
the repo:

```
uv run ../scripts/reset.py
```

Re-run the pytest command above to confirm you're back to `2 failed,
2 passed`. Worth doing if you copied from `solution/harness.py` earlier and
now want to watch your own version work.

### Step 4 — Run it on a long task (10 min)

**What changes in this step:** nothing except the size of the job. Same
harness you just built, same model, same five tools, same prompt style.
The only variable is how much work the task takes — which is exactly the
variable a harness exists to survive.

**The task.** `tasks/long_horizon/refactor_v2/workspace/` holds *pyledger*,
a small double-entry bookkeeping library: 149 Python files, 35 tests. Its
test suite has already been updated to a new v2 API, but the source code
still uses the old v1 names, so nothing imports and nothing runs. The
agent has to rename every v1 identifier across the codebase until the
tests pass. Three things make that harder than it sounds:

- `MIGRATION.md` (inside the workspace, so the agent can read it) documents
  **8 of the 14 renames**. The rest have to be discovered from the failing
  tests.
- The renames touch definitions, imports, call sites, dataclass fields, and
  dict keys — so a careless find-and-replace breaks things elsewhere.
- One function is deliberately out of scope: `webhook.py`'s `post()` is an
  HTTP verb, not the ledger API. `MIGRATION.md` says so. A blind rename
  breaks its tests.

**See the starting state first**, the same way you did in Step 3:

```
uv run python -m pytest tasks/long_horizon/refactor_v2/workspace -q
```

`1 error during collection` — the tests can't even import the code yet.
That's the before-state.

**Now run the agent on it.** This costs roughly $0.50 per attempt (the
20-turn budget bounds the spend) — **run it once**, not five times:

```
uv run harness_skeleton.py tasks/long_horizon/refactor_v2/workspace \
  "Migrate the source code to the v2 API following MIGRATION.md until all tests pass. Do not modify the tests."
```

**What a typical run looks like.** A full run of this task, turn by turn:

| Turns | What the agent does |
|---|---|
| 1–4 | Lists the workspace, reads `MIGRATION.md`, then every test file and the core modules |
| 5–15 | Reads the rest of the source — 106 files in all — plus 12 searches for the old names. Batches grow from 3 files per turn to 13 |
| 16 | *"I now have the complete picture."* Writes its first 17 files — core, reports, CLI |
| 17–20 | Bulk-writes the repetitive integration families, 14 per turn: auditors, reconcilers, snapshots, limits |
| — | **Budget exhausted.** 73 files written of roughly 130 that needed it |

The scoreboard prints two call-outs on the same turn, and together they
are the whole lesson:

```
   ▸ first edit — 15 turns went to reading before anything changed
   ▸ 4 turns left, and nothing is tracking how much work remains
```

It started working at the moment it ran out of room to work. Three more
things from that run:

- **It never ran the tests. Not once in 20 turns.** `run_tests` was there
  the whole time. It planned to read everything, write everything, then
  verify — and never reached the verify.
- **The transcript ended at ~39,000 tokens; the run was billed 469,341
  input tokens** — roughly twelve times the conversation's final size,
  because every turn re-sent all of it. Output was 16,278 tokens: you paid
  about 29 tokens of input for every token the model actually wrote.
- **The arithmetic was never going to work.** Reading took 15 turns;
  writing ~130 files at 14 per turn needs ~10 more; verifying needs at
  least one. That is 26+ turns against a budget of 20 — and nothing in the
  system was tracking that, least of all the agent.

Your run will differ in the details. The shape rarely does.

**Watch these four things while it runs** — each one is a harness
component doing nothing, because your harness doesn't have it:

| What you'll see | What's missing |
|---|---|
| Every file it reads stays in the conversation forever, and the whole conversation is re-sent on the next turn | Context compaction |
| One `run_tests` call returns every failing test's full traceback — thousands of characters, kept in full | Tool-output limits |
| Write batches grow as it tries to edit many files in one turn | Nothing bounds what the model must produce in a single reply |
| It re-reads files it already handled, because the only record of its progress is the conversation | Durable memory |

**What to expect: failure**, in one of two ways.

- **The budget runs out** — the common case. Twenty turns spent, the
  codebase partly migrated, the suite still red.
- **A crash** — a raw Python traceback mid-run. The model tried to write
  many large files in one turn, hit its output limit partway through, and
  sent a truncated tool call. Your harness calls `json.loads` on it with
  nothing to catch the error, so the process dies.

Note what failure does *not* mean here: the agent read correctly, planned
sensibly, and every file it wrote was correct. It simply could not fit the
job into the turns and tokens available — and nothing in the system was
measuring whether it would.

**Reset before any second attempt.** The agent edits files on disk, so a
stranded run leaves real work behind — and if you re-run without
resetting, the next agent inherits it and may finish what the first one
started. That looks like success but isn't: it's two runs' worth of turns
and tokens to do one task, with neither agent aware the other existed.
(We did exactly this by accident while building the workshop: run one
stranded 56 files, run two picked them up and reported "all 35 tests
pass.") Run `uv run ../scripts/reset.py`, then
`uv run ../scripts/check_fixtures.py` to confirm.

**Record three numbers before moving on**: which outcome you got, the turn
it ended on, and the wall time. Block 3 runs this same task through
protected harnesses and compares against exactly these.

**Then look at what it left behind:**

```
uv run python -m pytest tasks/long_horizon/refactor_v2/workspace -q
```

A failed run usually leaves the codebase partially migrated — real work
completed, then stranded with no record of what was done or what remained.
That stranded state is the point: the agent didn't run out of *ability*,
it ran out of the things a harness provides.

## Debrief questions

Standard incident-review questions, applied to your run — a postmortem on
an agent instead of an outage. Answer for yourself before the group
discussion:

1. What was the *proximate* cause of death in YOUR run? (Read the last few
   lines of output.)
2. Where did most of the context go? (Reads? Search results? Test output?
   The agent's own file rewrites?)
3. What did the agent "know" at turn 5 that it had effectively lost by the
   time it died?
4. Which of these would a better *model* fix? Which need a better *harness*?

The table at the top of this page maps each failure to the harness
component that was missing. Block 3 adds those components one at a time —
and measures what each is worth.

## Starting over

The agent edits the task workspaces as it works, so re-running any task
needs a reset first. From this directory:

```
uv run ../scripts/reset.py          # restore every task workspace
uv run ../scripts/check_fixtures.py # confirm: ALL FIXTURES OK
```

The reset prints what it restored. Then pick up from Step 3.
