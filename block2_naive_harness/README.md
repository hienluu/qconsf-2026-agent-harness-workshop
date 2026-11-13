# Block 2: Build the Naive Harness

> **In this block (35 min)**
>
> | Part | Time | What happens |
> |---|---|---|
> | Intro | 3 min | The presenter sets up the block and the exercise |
> | Hands-on | 26 min | Steps 1 to 4 below |
> | Discussion | 6 min | The questions under "Discussion" at the end of this page |
>
> **If you're behind:** if you haven't reached Step 4 fifteen minutes into
> the hands-on, stop typing, switch to `solution/harness.py` (same two
> arguments) and go straight to Step 4. The discussion starts on time,
> whether or not everyone has finished.

You'll finish a minimal agent harness, check it on a one-line bug, then
hand it a migration across 149 Python files. Block 1 listed seven parts of a harness;
this one has two, the loop and tool dispatch. The point is to see what the
other five would have done for you, so that Block 3 can measure it.

Cost: about $1 to $2 in total. Everything runs with `uv run`, so there's
no virtualenv to create or activate.

## What's missing, on purpose

`harness_skeleton.py` is a working loop with two gaps to fill and no
protections. Here's what that looks like in practice:

| Missing | What you'll see |
|---|---|
| Limits on tool output | One `run_tests` call returns every traceback in full, and it stays in the conversation |
| Context compaction | The conversation only grows, and all of it is re-sent every turn |
| A record of progress | The agent's plan and progress exist only in the conversation |
| Error recovery | One malformed tool call kills the process |
| Budget awareness | It has 20 turns and nothing tracks how much work is left |

## Exercise

Run every command from `block2_naive_harness/`. From the repo root:

```bash
cd block2_naive_harness
```

### Step 0: Check your setup (at home)

You did this at home, as the last line of Setup in the repo README. If you
didn't, run it during Block 1, not now:

```bash
uv run ../setup/check_setup.py
```

Expect `ALL GREEN`. If not, fix what it tells you, or flag a helper.

### Step 1: Read what you were given (2 min)

- `tools.py`: five tools, `list_files`, `read_file`, `write_file`, `search`
  and `run_tests`. A path check keeps them inside the workspace. Nothing
  else limits them: no cap on output size, nothing on what they return.
- `harness_skeleton.py`: the client, system prompt and tool schemas are
  done. The two things that make it an agent aren't.

### Step 2: Fill in the two TODOs (8 min)

- **TODO 1, ask the model what to do next** (~4 lines): send the whole
  conversation plus the tool schemas.
- **TODO 2, run the tool and feed the result back** (~5 lines): look up
  the tool, call it, append the result to the conversation.

The comments show what to write. TODO 2 runs once per tool call, so keep
it indented inside the `for call in msg.tool_calls:` loop. If the append
lands outside it, only the last call gets a result and the next model
call fails. Stuck? `solution/harness.py` is the
finished version and takes the same arguments, so it works in place of
yours in every command below.

### Step 3: A short task (3 min)

See the bug first:

```bash
uv run python -m pytest tasks/short/01_fix_bug/workspace -q
```

`2 failed, 2 passed`. `moving_average([1, 2, 3, 4], 2)` returns
`[1.5, 2.5]`: the loop on line 6 of `stats.py` stops one window short.
Keep `stats.py` open in your editor and you'll see the fix land. You may
also see it wiped first: `write_file` replaces the whole file, so if the
agent writes only a fragment, that's all the file holds until it writes
it again. Nothing in this harness checks an edit before it lands.

Now run your agent. It takes two arguments: the workspace (the only files
its tools can see) and the task in quotes, which becomes its first
message.

```bash
uv run harness_skeleton.py tasks/short/01_fix_bug/workspace \
  "Two tests fail. Find the bug and fix it. Do not modify the tests."
```

5 to 8 turns, under a minute. It does what you just did: runs the tests,
reads the failure, reads the loop, edits. Then check it yourself. The
agent's summary isn't evidence; the tests are:

```bash
uv run python -m pytest tasks/short/01_fix_bug/workspace -q
```

`4 passed`. Optional: `02_add_function` and `03_small_rename` work the
same way, and each `TASK.md` has the command. To rerun a task, reset it
first (see "Starting over").

### Step 4: A long task (13 min)

Same harness, model and tools. Only the size of the job changes.

`tasks/long_horizon/refactor_v2/workspace/` is *pyledger*, a bookkeeping
library: 149 Python files, 35 tests. The tests use a new v2 API, but the code is
still on v1, so nothing imports. The agent has to rename every v1
identifier until the tests pass. It's harder than find-and-replace:

- `MIGRATION.md` documents 8 of the 14 renames. The other 6 have to be
  worked out from the failing tests.
- The renames hit definitions, imports, call sites, dataclass fields and
  dict keys.
- `post()` in `webhook.py` is an HTTP verb, not the ledger API, and must
  not be renamed. `MIGRATION.md` says so.

The before-state:

```bash
uv run python -m pytest tasks/long_horizon/refactor_v2/workspace -q
```

`7 errors during collection`: none of the test files can even import the
code.

Run it **once**. It costs about $0.50, and the 20-turn cap bounds that:

```bash
uv run harness_skeleton.py tasks/long_horizon/refactor_v2/workspace \
  "Migrate the source code to the v2 API following MIGRATION.md until all tests pass. Do not modify the tests."
```

**While it runs** (a few minutes). Each turn prints what the agent said,
the tool calls it made, and then a scoreboard line like this one:

```text
┈ turn 17/20 │ read 49  write 130  search 8  tests 0 │ conversation 195,454 chars (~48,863 tokens) │ sent so far 382,855 in / 21,062 out
```

| Field | What it counts | What to watch for |
|---|---|---|
| `turn 17/20` | Calls to the model so far, out of the 20 allowed | How many are left when it starts writing |
| `read 49  write 130  search 8  tests 0` | Tool calls so far, per tool, added up since turn 1. These are calls, not distinct files: reading one file twice counts 2 | A long run of reads before the first write. `tests 0` late in the run |
| `re-read 3` (purple, only if it happens) | Reads of a file the agent had already read | Fetching something it already had |
| `conversation … chars (~… tokens)` | Everything so far: your task, everything the model said, the full text of every file it wrote, and every tool result. The token figure is a rough estimate (characters ÷ 4) | It only grows. Nothing is ever dropped |
| `sent so far … in / … out` | Tokens the provider billed, as it reports them. `in` is everything sent to the model, added up over every turn; `out` is what the model wrote | `in` grows by about the whole conversation every turn |

Up to three yellow call-outs, once each: the turn of the first edit
(usually after a long stretch of reading), the turn the conversation
passes 150k characters, and the moment 4 turns are left with nothing
tracking the remaining work.

Note the turn where you'd first have guessed it was in trouble.

**How it ends.** Twenty turns is about what this job needs, with no
margin, and the model is never told how many it has. So it nearly always
uses most or all of them, and runs end differently. We've seen five
endings:

- **Finished, and said so.** Tests pass and the agent sums up. Nothing
  looks wrong.
- **Finished, but never said so.** It ran the tests on the last turn and
  had no turn left to read the result. The scoreboard runs the tests
  itself and tells you.
- **Ran out mid-job.** Partly migrated, tests still failing.
- **Never started.** It spent its turns reading, a file or two at a time,
  and ran out before the first edit. The scoreboard shows `write 0`, and
  the tests fail exactly as they did before it began.
- **Crashed.** The model hit its output limit partway through a big batch
  of writes and sent a truncated tool call. Nothing in your harness
  catches the `json.loads` error, so the process dies. Rare.

**When it stops**, it prints a **turn-by-turn table** and then a two-line
**run summary**: how the run ended (checked by running the tests when the
agent didn't say it was done), and how much it sent against the
conversation's final size. Each row of the table is one turn:

- **sent to model:** what that turn's call cost to send, as billed. It's
  the whole conversation so far, plus the tool definitions, which go out
  with every call. The bar draws this number.
- **tool calls:** what the model asked for in reply.
- **added:** how much the turn added to the conversation (an estimate):
  the model's reply, including its tool calls and any file it wrote, plus
  the tool results. On the last turn it's just the closing message. Every
  later turn pays to send it again.

- **agent says:** its words that turn, in green, cut to fit your window.
  The full text is in the trace above the table. (In a narrow window they
  move to a line under the row.)

A row from a long run:

```text
   turn  sent to model  cached                        tool calls           added
      7         10,917     85%  ████                  search 5           +11,535
```

Turn 7 cost 10,917 tokens to send. Its five searches then added 11,535
tokens of results, so turn 8 costs about that much more, and so does every
turn after it. The big `+` numbers are where the cost comes from, and
they're what Block 3's harnesses go after.

**Read your output, whatever happened.** Three things to find in your own
table:

1. **Your most expensive result.** Find the biggest number in the `added`
   column and multiply it by the number of turns after it. That's what one
   turn's results cost you in re-sending. In one of our runs, turn 3's
   eight searches added 10,052 tokens, and the 17 turns after it sent them
   again: about 171,000 tokens, **a third of the run's 518,776**, for
   results the agent read once. What was yours: a search, a test run, a
   big read? A limit on tool output is aimed at exactly this, and it's the
   first thing Block 3 adds. (The `cached` column makes the re-sending
   cheaper, but the model still processes every token.)
2. **When it checked its work.** Find `tests` in the `tool calls` column.
   How many turns were left when it first ran them? In the same run: once,
   on turn 19 of 20. If they had failed, there was no room to fix
   anything, and nothing in the harness watches the budget or prompts the
   agent to test as it goes.
3. **What the people around you got.** Same code, model and task: compare
   endings and totals. One run tells you very little, which is where
   Block 3 starts.

**The point.** Every harness answers four questions, whether or not anyone
decided. Yours answered each the simplest way:

| Question | Your harness's answer |
|---|---|
| What goes into the conversation? | Every tool result, whole |
| How long does it stay? | Forever, re-sent every turn |
| When does the agent check its work? | Whenever the model happens to |
| Does anything watch the budget? | No |

Block 3 changes these answers one at a time and measures what each change
is worth. Block 4 shows how five production harnesses answered them for
you. Block 5's worksheet then takes your own agent to a harness decision.

**Write down** the ending, the last turn, the total sent, and your biggest
`added` with what it cost. You'll compare them with Block 3's harnesses on
the same task. (Not wall time: that mostly measures the provider.)

## Discussion (6 min)

**For the group:**

1. How did your run end, and why? How many different endings did the room
   get?
2. Which of what you saw would a better *model* fix, and which needs a
   better *harness*?
3. **Would this matter for your own agent?** If so, what would you need a
   harness to do about it, and how would you test that it does? Write your
   answer down: Block 5's worksheet starts from these notes.

**More to think about, on your own or afterwards:**

- Where did the context go: reads, searches, test output, or the agent's
  own writes? The scoreboard's tally has the counts.
- If your run finished, how would you know without taking the agent's
  word for it or running the tests by hand?

Block 3 adds the missing pieces back one at a time and measures each.

## Starting over

The tasks are fixtures: a bug that must still be there, code that must
still be on v1. After a run, they aren't. Rerun without resetting and the
next agent starts where the last one stopped, and may report a success it
didn't earn. That happened to us: one run left 56 files migrated, the next
finished the job and reported "all 35 tests pass."

```bash
uv run ../scripts/reset.py && uv run ../scripts/check_fixtures.py
```

Expect `ALL FIXTURES OK` at the end.

`reset.py` restores each workspace to its committed state, deletes files
agents created, clears Blocks 3 and 4's run copies, and archives (doesn't
delete) your Block 3 score table. `check_fixtures.py` changes nothing: it
confirms every task still fails and every reference copy still passes.
