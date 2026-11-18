# Block 4: After the Workshop

More to run and read, for after the session. Run every command from
`block4_production_harnesses/`. Each run replaces that harness's last one
(`runs/<harness>/` and `runs/logs/<harness>.log`, whatever the task), so
run `compare_reference.py` on the runs you care about first, or `mv`
their folders to keep them.

## The tables each run prints

Each run printed two tables. **Results** (measured): solved, turns, tool
calls, tokens sent, wall time, with our h2 and h3 from Block 3 on the
same endpoint as the last row (on a terminal narrower than 100 columns,
as a line under the table). **Receipts** (facts about each harness): who
owns the loop, the tools you wrote versus the harness's own, what it took
to run on our provider, and how long the script is.

Then read `COMPARISON.md`, the full comparison row by row, and argue with
it against what you watched.

## The other two on our tools

```bash
uv run pydantic_ai/run.py
uv run google_adk/run.py
```

Same four file tools as steps 1 and 2. Both landed where our h2 and h3 did
(see the README's "All five, side by side").

## A harness with its own tools (2 to 4 minutes)

```bash
uv run deepagents/run.py
```

Deep Agents ships its own file tools, a planning tool and subagents
(marked `· harness tool`). It edits one exact string per call
(`edit_file`); watch whether it hands the work to a subagent (`task(...)`)
that starts from an empty context. In our three runs it hit the 50-call
cap every time, so `NOT SOLVED` is a normal result, not your setup. It
can also solve it: its summary line shows how many calls went to
subagents either way. With its subagent turned off and one line of
prompt added, it solved 3 of 3 (each alone solved 1 of 3); see
`COMPARISON.md`.

## Deep Agents' summarization, forced on (4 to 16 minutes a run)

Its context compaction never fires on this task at the defaults.
`deepagents/compaction_experiment.py` makes it fire, and marks every
summary and every re-read it causes. A `TurnCapReached` error line in its
output is the turn cap firing, not a crash. The commands, our results and
what they mean are in `COMPARISON.md`, under "Take-home experiment".

## All five side by side (4 to 6 minutes, traces in `runs/logs/`)

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

## The run left out of the table

One Claude run on its own file tools is left out of the README's
all-five table: with no shell, it wrote a rename script into the empty
`conftest.py`, ran the tests (which runs `conftest.py`), then emptied the
file again. Clever, and against the rules: a run that changes a test file
now fails, even if it changes it back. And a reminder that "run the
tests" means "run code". (The file is empty on purpose: pytest puts its
folder on Python's import path, so a plain `pytest` can import the
package from `tests/`. Tasks whose tests sit next to the code don't have
one.)

## Why LiteLLM is held back

Plain `uv sync` installs all five frameworks. ADK reaches non-Google
models through LiteLLM, and LiteLLM 1.84+ needs version 2 of the `openai`
library while OpenAI Agents needs version 3, so we hold LiteLLM at
1.83.0; ADK's own `[extensions]` install can't share an environment with
OpenAI Agents at all. And the Claude Agent SDK ships a compiled Claude
Code CLI inside its wheel (~190MB installed).

## Shell tools

The scripts from the presenter demo, how `replace_in_files` was
designed, and Deep Agents with a shell:
[`tool_design/README.md`](tool_design/README.md).
