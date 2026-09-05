# Block 3 — Measure It

Block 2 gave you a single data point: one harness, one task, one run. None
of us would accept that in a design review, so let's not accept it here.
This block is the controlled experiment: hold the model, the tasks, and
the tools constant; vary only the harness; measure solve rate, turns,
tokens, and wall time. You leave with a score table you could defend to
your team — and, more usefully, a method you can rerun against your own
tasks when a vendor benchmark asks you to take its word for it.

## The task suite

The same four tasks you ran in Block 2 — each is a small codebase with a
test suite, and "solved" always means the same thing: **pytest exits green
afterward** (the agent is never asked whether it succeeded).

| task | the agent must... | horizon |
|---|---|---|
| `fix_bug` | find and fix an off-by-one in a stats module (1 file, 4 tests) | short — a few turns |
| `add_function` | implement a missing `slugify` from its 5 tests | short |
| `small_rename` | rename two legacy functions across 2 files | short |
| `refactor_v2` | migrate a ~150-file bookkeeping library to its v2 API using an *incomplete* changelog, 35 tests | long — sized past a naive harness's design limits |

Workspaces live under `../block2_naive_harness/tasks/` (each has a TASK.md
with details); the prompts sent to the agent are in `eval/tasks.py`.

## The three harnesses

| | Adds | Answers which Block 2 death |
|---|---|---|
| `h1_naive` | nothing — the Block 2 harness, frozen and instrumented (turns, tokens, wall time, outcome) | — the baseline |
| `h2_managed` | tool-output limits · malformed-call recovery · context compaction | tracebacks flooding context · the JSON crash · quadratic cost |
| `h3_full` | durable working notes (survive compaction) · write-path guardrail on `tests/` | plan lost with the transcript · "don't modify tests" as hope |

The deltas are deliberately small. Read them as diffs — the diff is the lesson:

```
diff harnesses/h1_naive.py harnesses/h2_managed.py
diff harnesses/h2_managed.py harnesses/h3_full.py
```

## Exercise flow (all commands from `block3_measure/`)

1. **Baseline the short task** — confirm h1 is the harness you built:
   ```
   uv run eval/run_eval.py h1 --task fix_bug
   ```
2. **Reproduce the Block 2 failure, instrumented this time:**
   ```
   uv run eval/run_eval.py h1 --task refactor_v2
   ```
3. **Read the h2 diff, then run the same task through it:**
   ```
   uv run eval/run_eval.py h2 --task refactor_v2
   ```
4. **And h3:**
   ```
   uv run eval/run_eval.py h3 --task refactor_v2
   ```
5. **The comparison table:**
   ```
   uv run eval/compare.py
   ```

Cost note: each `refactor_v2` run is roughly $0.50–1.50; the short tasks
are pennies. Run the long task once per harness.

## How scoring works (worth internalizing)

- Every run copies the pristine workspace to `results/runs/<harness>__<task>/`
  — runs never touch the repo or each other, and failed runs leave wreckage
  you can inspect.
- Solved means **pytest exits green on the workspace afterward**. The
  agent's self-report is never consulted. Your harness evaluation at work
  should share this property: external checkers on your tasks.
- `results/results.jsonl` accumulates every run; `compare.py` shows the
  latest per cell. Rerun a flaky cell and the table updates.

## Debrief questions

1. What did ~40 lines of harness (h1→h2) buy, in solve rate, tokens, and
   dollars?
2. Which h2 protection did the heavy lifting on `refactor_v2`? (Check
   `notes` in the table: `malformed_calls` recovered, `elided_messages`.)
3. What does h3's guardrail change about how much you must trust the
   *prompt*? (Try h1 on a task and count how many times "do not modify the
   tests" was load-bearing.)
4. These five protections are a tiny subset of what production harnesses
   ship. Block 4: what the pros decided for you.
