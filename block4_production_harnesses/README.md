# Block 4: The Production Harnesses

> **In this block (35 min)**
>
> | Part | Time | What happens |
> |---|---|---|
> | Intro | 5 min | The presenter sets up the block and the exercise |
> | Hands-on | 20 min | Steps 0 to 4 under "Exercise": start all five runs, read the scripts while they work, then the tables and `COMPARISON.md` |
> | Discussion | 10 min | The presenter demo (step 5), then the questions under "Discussion" |
>
> **If you're behind:** the runs take 4 to 6 minutes, and nothing else
> needs to wait for them. If your provider is slow or you started late,
> run the quick fallback task instead (`BLOCK4_TASK=bug_hunt`, about a
> minute; see the end of this page). The discussion starts on time,
> whether or not everyone has finished.

In Blocks 2 and 3 you built a harness for the migration and added
protections to it. Now you'll run the same migration through five
production frameworks: Claude Agent SDK, OpenAI Agents, Google ADK, Deep
Agents and Pydantic AI.

Same task, same model, same turn cap (50 model calls), and every harness
works through **file tools**: read a file, write or edit a file, run the
tests. No shell; that's step 5. So the numbers line up with your h2 and
h3, and the question is simple: what does a production harness do that
yours didn't, and what does it leave to you? Every framework's feature
list mentions memory, tools, context management and guardrails. Running
them side by side shows how they actually differ.

There's no code to write. One command starts all five; each adds a row to
two tables.

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

Each script is 110 to 165 lines, meant to be read as much as run: notice
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

### Step 1: Start all five (4 to 6 minutes, while you do step 2)

```bash
uv run run_all.py
```

All five run side by side, each on its own copy of the task. A status line
per harness shows its latest turn; each full trace goes to
`runs/logs/<harness>.log`. To watch one work, in a second terminal:

```bash
tail -f runs/logs/deepagents.log
```

One after another they'd take 12 minutes or more. (Any single script also
runs on its own: `uv run pydantic_ai/run.py`.)

### Step 2: Read the scripts while they run

Three comparisons, one question each:

- **`google_adk/run.py` and `pydantic_ai/run.py`**: a kit and a composable
  harness. Compare how each gets pointed at our provider: a constructor
  argument for Pydantic AI, a LiteLLM setup for ADK.
- **`claude_agent_sdk/run.py` and `openai_agents/run.py`**: two
  opinionated harnesses. Claude's ships its own file tools, so we write
  one tool (`run_tests`, because we withheld Bash); OpenAI's ships none
  that work on our model, so we write four.
- **`deepagents/run.py`**: a harness built on a runtime (LangGraph). Count
  what it ships: its own file tools, a planning tool and subagents it can
  hand work to. We write one tool, `run_tests`.

### Step 3: Read the two tables

When the runs finish, `run_all.py` prints two tables.

**Results** (measured this run): solved, turns, tool calls, tokens sent,
wall time, with your h2 and h3 from Block 3 as the last row. Start here:
which harnesses landed where h2 did, and which didn't?

**Receipts** (facts about each harness): who owns the loop, the tools you
wrote versus the harness's own tools, what it took to run on our provider,
and how long the script is.

Here's what we saw over several runs each on GLM-5.3-Flash, so you can
tell a typical run from an unlucky one:

| Harness | Solved | Turns | Tool calls | Tokens sent |
|---|---|---|---|---|
| Pydantic AI | 3/3 | 20–26 | 186–283 | 0.36–0.66M |
| Google ADK | 3/3 | 24–31 | 276–279 | 0.66–0.82M |
| OpenAI Agents | 3/3 | 25–50 | 176–287 | 0.46–1.18M |
| Claude Agent SDK | 1 of 2 | 39–50 | 392–555 | 1.72–3.49M |
| Deep Agents | 0/3 | 50 (the cap) | 146–250 | 0.71–0.86M |
| *your h2 / h3* | | *17–34* | *181–299* | *0.37–0.78M* |

The three harnesses that use **our** file tools land where your h2 and h3
did: their loops add nothing you can measure on this task. The two that
bring **their own** file tools are the expensive ones:

- **Claude Agent SDK** edits one exact string at a time (`Edit`), so it made
  200 to 380 edits where the others rewrote about 130 files. One of its
  runs is left out of the table: with no shell, it wrote a rename script
  into the empty `conftest.py`, ran the tests (which runs `conftest.py`),
  then emptied the file again. Clever, and against the rules: a run that
  changes a test file now fails, even if it changes it back. And it's a
  reminder that "run the tests" means "run code".
- **Deep Agents usually runs out of budget.** Its defaults hand the work
  to a subagent, which spends calls rediscovering the code, and edit
  occurrence by occurrence. Expect `NOT SOLVED` at 50 calls; that's the
  finding, not a bug in your setup. Its summary line shows how many calls
  went to subagents. (With two documented settings it solves the task; see
  `COMPARISON.md`.)

A batch of five took 4 to 5.5 minutes, set by the slowest harness.

### Step 4: Read `COMPARISON.md`

The full comparison, row by row. Argue with it against your tables.

### Step 5: The presenter demo (watch, don't run)

The same migration, the same harness (OpenAI Agents), run twice: once
with our four file tools, once with a single shell tool. Turns barely
move; tool calls drop about tenfold, because with a shell the agent stops
rewriting files and writes a rename script. Then the other side: one
global `sed` can break forty files at once, tests included, and Block 3's
test guardrail has nothing to check. Details, and the same experiment for
Claude, Deep Agents, Pydantic AI and ADK to try at home, in
[`migration/README.md`](migration/README.md).

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
| Claude Agent SDK | Claude Code's `Read`, `Write`, `Edit`, `Glob`, `Grep` (Bash withheld) | **nothing.** They accept absolute paths, and `bypassPermissions` approves every call. The copy is only where it starts |

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

1. Which harness required the least code, and what did that convenience
   cost in provider coupling?
2. On the same tools, three harnesses matched the one you built in Block
   3. Two cost more or ran out of budget, doing what they're designed to
   do. Is that a flaw in those harnesses or a mismatch with the task, and
   how would you find out before adopting one?
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
