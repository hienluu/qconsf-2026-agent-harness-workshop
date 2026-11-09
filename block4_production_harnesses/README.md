# Block 4: The Production Harnesses

> **In this block (35 min)**
>
> | Part | Time | What happens |
> |---|---|---|
> | Intro | 5 min | The presenter sets up the block and the exercise |
> | Hands-on | 20 min | Steps 0 to 5 under "Exercise": watch two harnesses work, design a tool, run one answer, then compare with all five |
> | Discussion | 10 min | The presenter demo (step 6), then the questions under "Discussion" |
>
> **If you're behind:** skip the optional Deep Agents run, and if step 2
> hasn't finished when the discussion starts, stop it (Ctrl-C) and use
> the reference table in step 5. The discussion starts on time, whether or
> not everyone has finished.

In Blocks 2 and 3 you built a harness for the migration and added
protections to it. Now you'll run the same migration through five
production frameworks: Claude Agent SDK, OpenAI Agents, Google ADK, Deep
Agents and Pydantic AI.

Same task, same model, same turn cap (50 model calls), and every harness
works through **file tools**: read a file, write or edit a file, run the
tests. No shell; that's step 6. So the numbers line up with your h2 and
h3, and the question is simple: what does a production harness do that
yours didn't, and what does it leave to you? Every framework's feature
list mentions memory, tools, context management and guardrails. Running
them side by side shows how they actually differ.

There's no code to write. You'll run two of the five and **watch** them
work, one after the other: the trace shows every turn and every call, the
way Block 3's did. Then you'll design a better tool for the job and run
one. Pydantic AI and ADK behave like the first two; Deep Agents, which
brings its own tools, doesn't, and is optional. All five are in step 5,
and `run_all.py` runs them side by side if you want them yourself.

## The task

The migration from Blocks 2 and 3: move `pyledger` (about 130 files) to
its v2 API following `MIGRATION.md`, until all 35 tests pass, without
touching the tests. Two traps you've seen: `MIGRATION.md` is incomplete,
so some renames only show up in the tests, and `webhook.py` has a `post()`
that is the HTTP verb, not the ledger's `post()`, and must keep its name.

## The five scripts

Arranged as three comparisons:

| Comparison | Scripts |
|---|---|
| A kit vs a composable harness | `google_adk/run.py` · `pydantic_ai/run.py` |
| Two routes to an opinionated harness | `claude_agent_sdk/run.py` · `openai_agents/run.py` |
| A harness built on a runtime | `deepagents/run.py` (LangGraph underneath) |

Each script is 130 to 190 lines, meant to be read as much as run: notice
what you had to write, what came free, and what the harness assumed about
you. Each docstring says what to look for.

Plain `uv sync` installs all five frameworks (setup did this). Two notes,
both part of the lesson. ADK reaches non-Google models through LiteLLM,
and LiteLLM 1.84+ needs version 2 of the `openai` library while OpenAI
Agents needs version 3, so we hold LiteLLM at 1.83.0; ADK's own
`[extensions]` install can't share an environment with OpenAI Agents at
all. And the Claude Agent SDK ships a compiled Claude Code CLI inside its
wheel (~190MB installed).

## Exercise

Run every command from `block4_production_harnesses/`. From the repo root:

```bash
cd block4_production_harnesses
```

### Step 0: Start clean (a few seconds)

```bash
uv run ../scripts/check_fixtures.py
```

Expect `ALL FIXTURES OK`. If not, run `uv run ../scripts/reset.py` (it
also archives your Block 3 score table). Then empty the receipts table so
it ends up yours:

```bash
rm -f runs/receipts.jsonl
```

### Step 1: Watch a harness that uses your tools (2 to 3 minutes)

```bash
uv run openai_agents/run.py
```

The OpenAI Agents SDK gets the four file tools you know from Blocks 2 and
3. Watch:

- **The shape of the run.** A few turns of reading (`read_file × 8`),
  then turns of writing (`write_file × 8`): about 130 files, one call
  each. That's your h2's algorithm, inside someone else's loop.
- **The headers.** The model narrates between steps (`❝ agent says:`):
  where it finds the renames `MIGRATION.md` left out, and whether it
  notices `webhook.py`.
- **How long it reads before it writes.** Usually 6 to 20 turns. Once in
  six runs it was still reading, one or two files a turn, when it hit the
  50-turn cap, and changed nothing: Block 3's budget problem, since
  nothing tells it the turns are running out. If that happens to you,
  keep the result for step 4.

While it runs, open `openai_agents/run.py`: the loop is theirs
(`Runner.run`), and so are the hooks we watch it through (`RunHooks`);
the four tools are yours. Notice what it took to point it at a non-OpenAI
model: an explicit model object, and tracing to OpenAI's platform turned
off by hand.

### Step 2: Watch a second harness with the same tools (3.5 to 7 minutes)

```bash
uv run claude_agent_sdk/run.py
```

The Claude Agent SDK, Claude Code's harness as a library, with its own
tools switched off and our four served to it instead: the same tools as
step 1, so what changes is only the harness. Start it, and think about
step 3 while it runs. Watch:

- **The algorithm.** Is it different from step 1's? (On our runs: about
  15 turns of reading, up to 20 files a turn, then `write_file × 14` a
  turn. Three runs: 29 to 30 turns, 276 to 281 calls, 0.71 to 0.79M
  tokens, all solved. Step 1's range: 25 to 50 turns, 176 to 287 calls.)
- **What the harness adds.** The two warnings at the top are provider
  friction: Claude Code doesn't recognize our model and reads its
  credentials from Anthropic's variable names. It's also the slowest to
  start and to run: it drives the Claude Code program underneath.

While it runs, open `claude_agent_sdk/run.py`: our tools served through
`create_sdk_mcp_server`, and `tools=[]` switching off Claude Code's own.

**Optional, if you have 3 minutes: a harness with its own tools.**
`uv run deepagents/run.py`. Deep Agents ships its own file tools, a
planning tool and subagents (marked `· harness tool`). Watch it hand the
work to a subagent (`task(...)`) that starts from an empty context, edit
one exact string per call (`edit_file`), and usually hit the 50-call cap:
`NOT SOLVED` is the finding, not your setup.

### Step 3: What tool would you design?

Two different harnesses, one algorithm: about 130 reads and 130 writes,
one file per call, for what is really 14 renames. Before reading on:

- **What tool would you give the agent instead?** Write down its name and
  arguments.
- **What should it refuse to do?** Remember the tests, and the webhook's
  `post()`.
- **How would you know it helped?** Which number in the tables would
  move?

Step 4 runs one answer.

### Step 4: Run one answer (about 2 minutes)

**The insight, from the traces you just watched.** By the time the agent
starts writing, it already knows what to do: about 14 rename rules, from
`MIGRATION.md` and the tests. Then it spends some 280 calls applying them,
one file at a time, re-sending each whole file to change a few words. The
model isn't the bottleneck; the tool is. It works one *file* per call,
while the work comes one *rule* at a time. So: a tool whose unit is the
rule.

**What `replace_in_files(old, new, exclude, dry_run)` does:**

| | |
|---|---|
| **One call per rename** | replaces `old` with `new` in every `.py` file, as a whole word (`post`, not the `post` in `posted`), in code, strings and comments (the field names also appear as dict keys) |
| **Never touches a test file** | test files are skipped and counted in the result, whatever the model asks |
| **`exclude`** | files to leave alone, e.g. `webhook.py`, whose `post()` is the HTTP verb. The tool doesn't know that; the agent has to |
| **`dry_run`** | lists the files and counts it *would* change, without changing anything: a search and a preview |
| **Returns** | the files it changed, with counts: proof the model can read |

It sits alongside the four file tools, which are still there for anything
that isn't a rename. It runs no shell commands, so it's as safe on your
laptop as step 1. (About 50 lines, in `openai_agents/run_replace.py`;
design notes in `tool_design/README.md`.)

```bash
uv run openai_agents/run_replace.py
```

Watch for the renames (`replace_in_files × 1` per turn, 14 to 25 in all),
and whether the agent excludes `webhook.py` when it renames `post`. At
the end, the results table shows it as `openai_agents+replace`, right
under step 1's `openai_agents`: compare turns, tool calls and tokens. Over three runs each on GLM-5.3-Flash: 23 to 29 turns and
46 to 54 calls, against 26 to 46 and 278 to 315; tokens 0.25 to 0.39M
against 0.62 to 1.29M. How close is it to the tool you designed?

### Step 5: Compare with all five

Each run printed two tables. **Results** (measured): solved, turns, tool
calls, tokens sent, wall time, with your h2 and h3 from Block 3 as the
last row. **Receipts** (facts about each harness): who owns the loop,
the tools you wrote versus the harness's own, what it took to run on our
provider, and how long the script is.

Here's all five over several runs each on GLM-5.3-Flash, so you can tell
a typical run from an unlucky one:

| Harness | Solved | Turns | Tool calls | Tokens sent |
|---|---|---|---|---|
| Pydantic AI | 3/3 | 20–26 | 186–283 | 0.36–0.66M |
| Google ADK | 3/3 | 24–31 | 276–279 | 0.66–0.82M |
| OpenAI Agents | 5 of 6 | 25–50 | 176–287 | 0.46–1.18M |
| Claude Agent SDK | 3/3 | 29–30 | 276–281 | 0.71–0.79M |
| Deep Agents *(its own tools)* | 0/3 | 50 (the cap) | 146–250 | 0.71–0.86M |
| Claude Agent SDK *(its own file tools, `CLAUDE_TOOLS=own`)* | 4 of 5 | 31–50 | 293–555 | 1.40–3.49M |
| *your h2 / h3* | | *17–34* | *181–299* | *0.37–0.78M* |

The four harnesses on **our** file tools land where your h2 and h3 did:
their loops add nothing you can measure on this task. The runs on a
harness's **own** file tools are the expensive ones. Claude Code's `Edit`
replaces one exact string per call, so it made 200 to 380 edits where our
tools rewrote about 130 files, and sent about twice the tokens. Deep
Agents ran out of budget every time; with two documented settings it
solves it (see `COMPARISON.md`).

One Claude run is left out of the table: with no shell, it wrote a rename
script into the empty `conftest.py`, ran the tests (which runs
`conftest.py`), then emptied the file again. Clever, and against the
rules: a run that changes a test file now fails, even if it changes it
back. And a reminder that "run the tests" means "run code".

Then read `COMPARISON.md`, the full comparison row by row, and argue with
it against what you watched. To run all five yourself, side by side
(4 to 6 minutes): `uv run run_all.py`.

### Step 6: The presenter demo (watch, don't run)

The other answer to step 3: give the agent a shell. The presenter runs
the same harness with a single shell tool, then Claude Code's harness with
its own Bash, for what a product gives you out of the box. Both run
commands on the machine with no sandbox, which is why you watch rather
than run them.

| Tools | Turns | Tool calls | Tokens sent |
|---|---|---|---|
| our four file tools | 26–46 | 278–315 | 0.62–1.29M |
| file tools + `replace_in_files`, a tool designed for renames | 23–29 | 46–54 | 0.25–0.39M |
| one shell tool | 20–25 | 19–24 | 0.16–0.43M |
| Claude Agent SDK with its Bash | 16–23 | 17–23 | 0.41–0.61M |

(GLM-5.3-Flash, three runs each, all solved.)

The designed tool and the shell both get leverage: one call changes every
file. The difference is **where the guardrail can go**:

- **A designed tool checks its own arguments.** `replace_in_files` never
  touches a test file, takes an exclude list (the agent excluded
  `webhook.py` on every rename), and can preview a change first. The
  arguments are structured, so the check is exact.
- **A shell runs whatever program the model writes.** A hook that reads
  each command to decide whether it touches the tests can always be
  written around (`python -c`, a script, `conftest.py`). So the guardrail
  moves down a layer: a sandbox, read-only files, checking the result
  afterwards. Before the test files here were read-only, one shell run's
  global `sed` renamed the webhook's `post()` and rewrote a test file.

Which to reach for: **a shell** for open-ended work you can sandbox; **a
designed tool** for repetitive or consequential work, where you need to
say exactly what it can't do; and no shell at all without a sandbox.
Production harnesses do both: Claude Code ships Bash together with
permission rules, hooks and sandboxing.

The scripts, how `replace_in_files` was designed, and Deep Agents with a
shell to try at home: [`tool_design/README.md`](tool_design/README.md).

## Starting over

Two things accumulate: the receipts table and the task fixtures.

```bash
rm -f runs/receipts.jsonl
```

That clears only the table (or `mv` it to keep the round). For a full
start-over:

```bash
uv run ../scripts/reset.py && uv run ../scripts/check_fixtures.py
```

`reset.py` restores every task, clears run copies and the receipts, and
archives your Block 3 score table. Each run works on its own copy, so the
task normally stays clean; the scripts refuse a task that's already
solved or edited.

## What "sandbox" means here (less than you might think)

Every run works on a **disposable copy** of the task under `runs/`. That
keeps runs repeatable; it isn't security.

| Harness | File tools | What enforces the boundary |
|---|---|---|
| Google ADK, Pydantic AI, OpenAI Agents | ours, from `common.py` | Python code in `_inside()`: paths that climb out (`../`) or start at `/` are refused |
| Deep Agents | its own | its `FilesystemBackend` with `virtual_mode=True`. With `False`, the boundary is gone: we watched an agent edit the original task that way |
| Claude Agent SDK | ours by default (same `_inside()` rule); with `CLAUDE_TOOLS=own`, Claude Code's `Read`, `Write`, `Edit`, `Glob`, `Grep` | with its own tools, **nothing.** They accept absolute paths, and `bypassPermissions` approves every call. The copy is only where it starts |

The tests get one more layer. At the start of every run the test files are
made read-only, and afterwards `verify()` compares them with the
originals: a run that changed, added or deleted one fails, whatever
pytest says. (An agent with a shell can `chmod` its way past the first
layer; not the second.)

And every harness runs `run_tests`, which **executes the code the agent
wrote with your permissions.** Every boundary here is a rule in
application code, not operating-system isolation like a container or VM.
Fine for a workshop task on your laptop; for an agent that runs untrusted
code, the isolation is your job, whichever harness you pick.

## The quick fallback, and the trivial task

If the migration is too slow for your provider or your time:

```bash
BLOCK4_TASK=bug_hunt uv run run_all.py
```

`bug_hunt` is a small order-pricing package with three bugs, two of which
affect the same totals (`../block2_naive_harness/tasks/medium/bug_hunt/TASK.md`).
About a minute for all five, and every harness solves it. And on the
trivial Block 2 task there's nothing to differ over, so the runs collapse
toward the same few turns:

```bash
BLOCK4_TASK=fix_bug uv run pydantic_ai/run.py
```

Differences between harnesses only show on work hard enough to differ
about. `BLOCK4_MAX_TURNS` changes the turn cap for any of these.

## Discussion (10 min, after the presenter demo)

**For the group:**

1. Two vendors' harnesses on the same tools ran the same algorithm, with
   nearly the same numbers. Then one tool, designed for the job, cut the
   calls fivefold. For your agent, where is the effort better spent:
   choosing the harness, or designing its tools?
2. On their own tools, Claude's harness cost 2 to 4 times more and Deep
   Agents ran out of budget, each doing what it was designed to do. Is that
   a flaw or a mismatch with the task, and how would you find out before
   adopting one?
3. **Would this matter for your own agent?** If so, what would you need a
   harness to do, and how would you test that it does? Write it down:
   Block 5's worksheet starts from these notes.

**More to think about:**

- Compare your results table with a neighbor's. Which columns move from
  run to run, and which receipt cells are stable facts about a harness?
- Two harnesses needed a workaround to run on our provider at all (Bearer
  auth for Claude's SDK, an explicit model object for OpenAI's). What does
  that predict about switching providers at work?
- ADK and OpenAI's SDK share an environment only because we hold LiteLLM
  back. What happens the day you need a newer one?
