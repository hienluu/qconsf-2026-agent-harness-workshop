# Block 4 — The Production Harnesses

**Why this block:** you now know, from your own hands, what a harness must
decide — you built the loop, watched it fail, and measured five specific
protections. The production harnesses decide those same things for you,
differently, and their feature lists all read alike until you can map each
feature to a failure you've seen. This block is that mapping: five
harnesses, one controlled task, read side by side.

## The five harnesses (and one escape hatch)

Same task, same model, same provider key. The task is `bug_hunt`: a small
order-pricing package (8 modules, 18 tests, 5 failing) with three seeded
bugs that interact — real diagnosis, sized so each harness's character
(exploration, planning, batching) has room to show. Details and spoilers:
`../block2_naive_harness/tasks/medium/bug_hunt/TASK.md`.

One specimen script per harness, organized in three teaching beats:

| Beat | Specimens |
|---|---|
| Kit vs composable | `google_adk/` · `pydantic_ai/` |
| Two roads to opinionated | `claude_agent_sdk/` · `openai_agents/` |
| Harness on a runtime | `deepagents/` · its escape hatch, `deepagents/langgraph_escape_hatch.py` |

Each `run.py` is ~100 lines, meant to be read as much as run — notice what
you had to write, what came free, and what the harness assumed about who
you are.

Setup: the usual `.env` plus `uv sync --group block4`. Two notes baked
into that sync, both part of the lesson: ADK lives in a separate
dependency group because it cannot co-resolve with openai-agents, and the
Claude Agent SDK wheel bundles a compiled Claude Code CLI (~90MB download,
~190MB installed — one more reason the sync happens at home, not on venue
WiFi).

## Exercise flow (from `block4_production_harnesses/`)

Fair warning about what you'll see: **all six runs succeed.** That's the
experimental design — outcome is the controlled variable. The information
is in *how* each harness got there and what each run didn't require of
you, and that's what the **harness receipt** printed
after every run captures: who owns the loop, what tools you wrote versus
what the harness shipped, what provider friction you paid, how many lines
the same job took. Receipts accumulate — after your sixth run, the table
on your screen IS the five-harness comparison, built from your own runs.

All six runs together cost well under $1. Between runs, spend sixty
seconds in the specimen you just ran on ONE question its receipt raised —
each docstring says what to look for.

1. **Beat 1 — kit vs composable.** Run both, and compare their friction
   cells: "none — a constructor argument" vs a paragraph plus its own
   dependency group:
   ```
   uv run --group block4-adk google_adk/run.py
   uv run --group block4 pydantic_ai/run.py
   ```
2. **Beat 2 — two roads to opinionated.** Claude's receipt will say
   "tools we wrote: 0" — go find the line that made that possible (there
   isn't one; that's the point). Then notice it also has the most
   provider friction: convenience and coupling, same row:
   ```
   uv run --group block4 claude_agent_sdk/run.py
   uv run --group block4 openai_agents/run.py
   ```
3. **Beat 3 — a harness on a runtime, then the layer below it.** Watch
   "tools we wrote" jump from 1 to 4 when you drop from Deep Agents to
   bare LangGraph — the price of the escape hatch, as a number:
   ```
   uv run --group block4 deepagents/run.py
   uv run --group block4 deepagents/langgraph_escape_hatch.py
   ```
4. **Read `COMPARISON.md`** — the full dimension matrix — and argue with
   it against your receipts.
5. Presenter demo (watch, don't run — ~$1): `refactor_v2`, the task that
   killed the naive harness, through Claude Code's harness:
   ```
   uv run --group block4 presenter_demo/run.py
   ```
   The closing question: **did the professionals' harness beat our
   200-line h3?** Whatever the answer, it teaches — a big win shows what
   production harness engineering buys; anything else is the harness-model
   fit lesson from Block 1, live.

   For calibration, two live runs (Sep 2026, GLM-5.3) agree: SOLVED in
   17–19 turns, ~16–18 tool calls, 65–97s wall — versus 117–208s for our
   h3 — with a Bash-dominated tool profile and a single Edit for a
   ~130-file migration. Both runs chose the same algorithm: reconnoiter
   via grep/cat, detect that MIGRATION.md is incomplete from the tests,
   then *write a word-boundary-regex rename script* and run it — followed
   by collateral-damage checks on display strings. Given a shell, the
   model stopped rewriting files and started scripting; the decisive
   advantage wasn't the loop or compaction but tool design changing which
   algorithm the model chose. (The same Bash tool is why production
   harnesses need sandboxing and permissions — we ran `bypassPermissions`
   on a disposable copy, deliberately.)

## Clearing the receipts table

Receipts accumulate in `runs/receipts.jsonl`; the table shows the latest
run per (specimen, task). To start it over (from `block4_production_harnesses/`):

```
rm runs/receipts.jsonl
```

To keep a finished round for reference instead of deleting it:

```
mv runs/receipts.jsonl runs/receipts.round1.jsonl
```

`uv run scripts/reset.py` (from the repo root) also clears it, along with
all run workspaces and the Block 3 state — the full start-over.

## Extra credit: the trivial task

Rerun any specimens against `fix_bug` — the one-line Block 2 bug you know
by heart:

```
BLOCK4_TASK=fix_bug uv run --group block4 pydantic_ai/run.py
```

Watch what happens to the receipts table: on a task with nothing to
differentiate on, the specimens collapse toward the same few turns and
seconds. Harness character needs work worth differing over — which is the
weight-vs-horizon question from Q1, run in the other direction.

## Debrief questions

1. Compare your wall-clock column with a neighbor's — the same specimen
   has measured 23.3s and 10.6s on back-to-back runs. Which receipt
   columns are noise on a 10-second task, and which are stable structural
   facts? (Then: the heavy Claude harness *did* dominate the long-horizon
   presenter demo. What experiment would you run to establish how harness
   weight relates to task horizon — and what would Block 3 say about
   sample size?)
2. Which specimen required the least code — and what did that convenience
   cost in provider coupling?
3. Two harnesses needed an explicit workaround to run on our provider at
   all (Bearer auth for Claude's SDK, an explicit model object for
   OpenAI's). What does that predict about switching costs at your job?
4. ADK couldn't even share a dependency resolution with OpenAI's SDK.
   What does your platform team do with that fact?
5. Every one of these solved the task. On what basis, then, would you
   actually choose? (That's Block 5.)
