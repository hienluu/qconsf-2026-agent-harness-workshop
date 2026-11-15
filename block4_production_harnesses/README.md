# Block 4: The Production Harnesses

> **In this block (35 min)**
>
> | Part | Time | What happens |
> |---|---|---|
> | Intro | 5 min | The presenter sets up the block and the exercise |
> | Hands-on | 20 min | Steps 0 to 4 under "Exercise": watch two harnesses work, design a tool, run one answer |
> | Discussion | 10 min | The presenter demo (step 5), then the questions under "Discussion" |
>
> **If you're behind:** if step 2 hasn't finished when the discussion
> starts, stop it (Ctrl-C); step 2 lists what a full run looks like. The discussion starts on time, whether or
> not everyone has finished.

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

There's no code to write. You'll run two of the five and **watch** them
work, one after the other: the trace shows every turn and every call, the
way Block 3's did. Then you'll design a better tool for the job and run
one. The other three harnesses are under "Optional", with numbers for
all five.

## The task

The migration from Blocks 2 and 3: move `pyledger` (140 files, about 130
of which need changes) to its v2 API following `MIGRATION.md`, until all
35 tests pass, without touching the tests. Two traps you've seen:
`MIGRATION.md` is incomplete, so some renames only show up in the tests,
and `webhook.py` has a `post()` that is the HTTP verb, not the ledger's
`post()`, and must keep its name.

## The scripts

| Script | Harness and tools | Used in |
|---|---|---|
| `openai_agents/run.py` | OpenAI Agents, our four file tools | step 1 |
| `claude_agent_sdk/run.py` | Claude Agent SDK, our four file tools (`CLAUDE_TOOLS=own` for Claude Code's) | step 2 |
| `deepagents/run.py` | Deep Agents (LangGraph underneath), its own tools | optional |
| `openai_agents/run_replace_in_files.py` | step 1, plus a tool designed for the job | step 4 |
| `pydantic_ai/run.py` | Pydantic AI, our four file tools | optional |
| `google_adk/run.py` | Google ADK, our four file tools | optional |

Each is 130 to 190 lines, meant to be read as much as run: what you had to
write, what came free, and what the harness assumed about you. Each
docstring says what to look for.

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

Expect `ALL FIXTURES OK`. If not, run `uv run ../scripts/reset.py`. It
restores the tasks, clears Block 3's and Block 4's run copies and this
block's receipts table, and keeps your Block 3 score table by renaming it
to `block3_measure/results/results.<date-time>.jsonl`.

If you've run Block 4 before and didn't reset, empty its receipts table so
the one you end up with is yours:

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
- **When it runs the tests, and whether it reads before it writes.** The
  line after the verdict tells you: `what the trace shows: tests run 2
  times, first at turn 31 of 35 · 0 files rewritten without being read
  first`. Most runs test only at the end. Some rewrite dozens of files they
  never read, reconstructing them from the pattern of the others, and
  still pass. Keep your numbers for the discussion.
- **Where the time goes.** The dim `┈` line under each turn ends with how
  long that turn took (its tools, then the model's reply) and the time so
  far. The writing turns are the slow ones: the model types out every file
  it writes.

The whole trace is also saved to `runs/logs/openai_agents.log` (each
script saves to `runs/logs/<harness>.log`), so you can search it after it
scrolls past: `grep -n "run_tests" runs/logs/openai_agents.log`.

While it runs, open `openai_agents/run.py`: the loop is theirs
(`Runner.run`), and so are the hooks we watch it through (`RunHooks`);
the four tools are yours. Notice what it took to point it at a non-OpenAI
model: an explicit model object, and tracing to OpenAI's platform turned
off by hand.

### Step 2: Watch a second harness with the same tools (3 to 7 minutes)

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
- **What the harness adds.** Provider friction, at the top of the run:
  `[claude-code:unrecognized_model]` means Claude Code doesn't recognize
  our model, and it reads its credentials from Anthropic's variable
  names. (If you're logged into Claude Code with a claude.ai account,
  you'll also see a line saying its claude.ai connectors are disabled.
  That's about your login, not this run.) Underneath, the SDK starts the
  Claude Code program as a separate process and drives it.

While it runs, open `claude_agent_sdk/run.py`: our tools served through
`create_sdk_mcp_server`, and `tools=[]` switching off Claude Code's own.

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

<details>
<summary><b>The answer we ran.</b> Open it once you've written yours down (step 3).</summary>

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
| **`exclude`** | files to leave alone, e.g. `pyledger/integrations/webhook.py`, whose `post()` is the HTTP verb. The tool doesn't know that; the agent has to. A path that matches no file is an error, so a typo can't quietly let the rename through |
| **`dry_run`** | lists the files and counts it *would* change, without changing anything: a search and a preview |
| **Returns** | the files it changed, with counts: proof the model can read |

It sits alongside the four file tools, which are still there for anything
that isn't a rename. It runs no shell commands, so it's as safe on your
laptop as step 1. One thing it has to handle that `write_file` didn't: the
model can ask for several renames in one turn, and the SDK runs a turn's
calls at the same time, each in its own thread. Two renames of the same
file would each read the old text, and the second write would undo the
first, so the tool takes a lock and runs one rename at a time. (About 50
lines, in `openai_agents/run_replace_in_files.py`; design notes in
`tool_design/README.md`.)

</details>

```bash
uv run openai_agents/run_replace_in_files.py
```

Watch for the renames, in bold cyan: `replace_in_files`, 14 to 27 calls
in all on our runs, often one a turn but sometimes several at once (what
the lock is for). And watch whether the agent excludes `webhook.py` when
it renames `post`. At the
end, the results table shows it as `openai_agents+replace_in_files`, right under
step 1's `openai_agents`. Compare the two:

| Over several runs each | Turns | Tool calls | Tokens sent | Tokens written |
|---|---|---|---|---|
| step 1, file tools | 26–46 | 278–315 | 0.62–1.29M | ~22–28k |
| step 4, plus `replace_in_files` | 23–35 | 35–88 | 0.22–0.69M | ~3k |

(The step 1 row here is three runs made back to back with step 4's, so it
isn't the same as step 1's six-run range in step 2 and under "Optional".)

Tool calls always drop, three to eight times. Tokens sent usually drop
too, but not always: they follow **turns**, since every turn re-sends the
conversation, and one run took 35 turns (more than its step 1) and sent
0.69M. What reliably drops is **tokens written**: with `write_file` the
model re-types every file it changes, and output is generated a token at
a time, which is why step 4 finishes in about half the time even when it
sends as much. The results table shows both columns.

How close is it to the tool you designed?

### Step 5: The presenter demo

The other answer to step 3: give the agent a shell. The presenter runs
the same harness with a single shell tool, then Claude Code's harness with
its own Bash, for what a product gives you out of the box.

OpenAI Agents with one shell tool:

```bash
uv run tool_design/run_openai_shell.py
```

The Claude Agent SDK with Claude Code's whole kit, Bash included:

```bash
uv run tool_design/run_claude.py
```

**Watch first. If you run them yourself, it's at your own risk:** both
run shell commands the model writes, on your machine, with no sandbox.
They work on a copy of the task, their commands get no API keys, and git
stops at the copy instead of finding the workshop repo around it. But a
command can reach anything you can. Read the script before you run it.

| Tools | Turns | Tool calls | Tokens sent |
|---|---|---|---|
| our four file tools (your step 1) | 26–46 | 278–315 | 0.62–1.29M |
| plus `replace_in_files` (your step 4) | 23–35 | 35–88 | 0.22–0.69M |
| one shell tool | 20–25 | 19–24 | 0.16–0.43M |
| Claude Agent SDK with its Bash | 16–23 | 17–23 | 0.41–0.61M |

(GLM-5.3-Flash, three to six runs each, all solved. The step 1 row is the
same back-to-back set as in step 4's table.)

On a Mac, expect the shell runs to take a few extra turns sometimes: BSD
`sed` has no `\b`, so a `sed` rename changes nothing until the agent
notices and switches to `perl` or Python.

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

## Optional: more to run and read

None of this is part of the hands-on. Try it if you finish early, or at
home. Each run replaces that harness's last one (`runs/<harness>/` and
`runs/logs/<harness>.log`, whatever the task), so run `compare_reference.py`
on the runs you care about first, or `mv` their folders to keep them.

**Compare with all five.** Each run printed two tables. **Results**
(measured): solved, turns, tool calls, tokens sent, wall time, with our
h2 and h3 from Block 3 on the same endpoint as the last row (on a terminal narrower than 100
columns, as a line under the table). **Receipts** (facts about each
harness): who owns the loop, the tools you wrote versus the harness's
own, what it took to run on our provider, and how long the script is.

Here's all five over several runs each on GLM-5.3-Flash through the
hosted endpoint in `.env.example`, so you can tell a typical run from an
unlucky one:

| Harness | Solved | Turns | Tool calls | Tokens sent |
|---|---|---|---|---|
| Pydantic AI | 3/3 | 20–26 | 186–283 | 0.36–0.66M |
| Google ADK | 3/3 | 24–31 | 276–279 | 0.66–0.82M |
| OpenAI Agents | 5 of 6 | 25–50 | 176–287 | 0.46–1.18M |
| Claude Agent SDK | 3/3 | 29–30 | 276–281 | 0.71–0.79M |
| Deep Agents *(its own tools)* | 0/3 | 50 (the cap) | 146–250 | 0.71–0.86M |
| Claude Agent SDK *(its own file tools, `CLAUDE_TOOLS=own`)* | 4 of 5 | 31–50 | 293–555 | 1.40–3.49M |
| *our h2 / h3 (Block 3, same endpoint)* | | *19–34* | *181–299* | *0.39–0.78M* |

The four harnesses on **our** file tools land where our h2 and h3 did on
the same endpoint: their loops add nothing you can measure on this task.
Compare on one provider: on Fireworks, the same model took h2 and h3 26
to 39 turns and 0.84M to 1.19M tokens (Block 3's numbers), so a Block 3
run there sits above this table. The runs on a
harness's **own** file tools are the expensive ones. Claude Code's `Edit`
replaces one exact string per call, so it made 200 to 380 edits where our
tools rewrote about 130 files, and sent 2 to 4 times the tokens. Deep
Agents ran out of budget in all three of these runs; with its subagent
turned off and one line of prompt added it solves it (neither alone
did; see `COMPARISON.md`).

One Claude run on its own file tools is left out of the table: with no
shell, it wrote a rename script into the empty `conftest.py`, ran the
tests (which runs `conftest.py`), then emptied the file again. Clever,
and against the rules: a run that changes a test file now fails, even if
it changes it back. And a reminder that "run the tests" means "run code".
(The file is empty on purpose: pytest puts its folder on Python's import
path, so a plain `pytest` can import the package from `tests/`. Tasks
whose tests sit next to the code don't have one.)

Then read `COMPARISON.md`, the full comparison row by row, and argue with
it against what you watched.

**A harness with its own tools** (2 to 4 minutes):

```bash
uv run deepagents/run.py
```

Deep Agents ships its own file tools, a planning tool and subagents
(marked `· harness tool`). It edits one exact string per call
(`edit_file`); watch whether it hands the work to a subagent (`task(...)`)
that starts from an empty context. In our three runs above it hit the
50-call cap every time, so `NOT SOLVED` is a normal result, not your
setup. It can also solve it: its summary line shows how many calls went to
subagents either way. With its subagent turned off and one line of
prompt added, it solved 3 of 3 (each alone solved 1 of 3); see
`COMPARISON.md`.

**Take-home: Deep Agents' summarization, forced on** (4 to 16 minutes a
run). Its context compaction never fires on this task at the defaults.
`deepagents/compaction_experiment.py` makes it fire, and marks every
summary and every re-read it causes. A `TurnCapReached` error line in its
output is the turn cap firing, not a crash. The commands, our results and
what they mean are in `COMPARISON.md`, under "Take-home experiment".

**All five side by side** (4 to 6 minutes, traces in `runs/logs/`):

```bash
uv run run_all.py
```

Google ADK's run starts with a `UserWarning: [EXPERIMENTAL] ...
JSON_SCHEMA_FOR_FUNC_DECL` line from ADK itself. It's harmless.

**A quicker task**, if the migration is too slow for your provider or
your time:

```bash
BLOCK4_TASK=bug_hunt uv run run_all.py
```

`bug_hunt` is a small order-pricing package with three bugs, two of which
affect the same totals (`../block2_naive_harness/tasks/medium/bug_hunt/TASK.md`).
About a minute for all five. On the trivial Block 2 task there's nothing
to differ over, so the runs collapse toward the same few turns:

```bash
BLOCK4_TASK=fix_bug uv run pydantic_ai/run.py
```

Differences between harnesses only show on work hard enough to differ
about. `BLOCK4_MAX_TURNS` changes the turn cap for any of these.

## Starting over

Two things accumulate: the receipts table and the task fixtures. (Run
copies and logs don't: each run replaces its harness's last one.)

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

The tests get more. At the start of every run the test files are made
read-only; `run_tests` refuses to run if any of them changed; and
afterwards `verify()` compares them with the originals: a run that
changed, added or deleted one fails, whatever pytest says. (An agent with
a shell can `chmod` its way past the first; not the last.)

And every harness runs `run_tests`, which **executes the code the agent
wrote with your permissions.** Every boundary here is a rule in
application code, not operating-system isolation like a container or VM.
Fine for a workshop task on your laptop; for an agent that runs untrusted
code, the isolation is your job, whichever harness you pick.

## Discussion (10 min, after the presenter demo)

**For the group:**

1. **Of your runs that passed all 35 tests, which would you merge?** Decide
   first, then check each one against the reference solution (a careful
   hand migration):

   ```bash
   uv run compare_reference.py
   ```

   Most of what it prints is docstrings and blank lines; skip those and
   look for strings the program prints or checks. In our runs, two of five that passed every test still changed something
   they shouldn't have, and the tests couldn't tell. What would have caught
   it: a stronger test, a review step, or a tool that couldn't make that
   change?

2. Two vendors' harnesses on the same tools ran the same algorithm, with
   ranges that overlap our h2's. Then one tool, designed for the job, cut the
   calls three to eight times. For your agent, where is the effort better spent:
   choosing the harness, or designing its tools?
3. On their own tools, Claude's harness cost 2 to 4 times more and Deep
   Agents ran out of budget, each doing what it was designed to do. Is that
   a flaw or a mismatch with the task, and how would you find out before
   adopting one?
4. **Would this matter for your own agent?** If so, what would you need a
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
