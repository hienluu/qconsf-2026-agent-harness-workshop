# Block 3 — Measure It

**Why this block:** at some point your team will pick a harness — adopt
one, extend one, or defend the one you have — and that decision will need
numbers behind it. Vendor benchmarks can't supply them: published scores are measured inside
the vendor's harness and can swing dramatically with it (Block 1 covers
the evidence), so they tell you about the vendor's harness, not yours. The
only numbers you can act on come from running your own tasks through the
candidate harnesses with an external checker. This block is that method,
practiced at a scale where you can see all the moving parts. Block 5's
decision framework assumes you have it.

Block 2 gave you a single data point: one harness, one task, one run.
This block is the controlled experiment: hold the model, the tasks, and
the tools constant; vary only the harness; measure solve rate, turns,
tokens, and wall time. You leave with a score table you could defend to
your team — and, more usefully, a method you can rerun against your own
tasks when a vendor benchmark asks you to take its word for it.

We run the experiment with three harnesses: **`h1_naive`**, the harness you
built in Block 2, unchanged in behavior; **`h2_managed`**, h1 plus three
context/error protections; and **`h3_full`**, h2 plus durable memory and a
guardrail. Each is a small, readable diff on the previous one.

## The three harnesses

| | Adds | Block 2 failure mode addressed |
|---|---|---|
| `h1_naive` | nothing — the harness you built in Block 2, frozen and instrumented (turns, tokens, wall time, outcome) | — the baseline |
| `h2_managed` | tool-output limits · malformed-call recovery · context compaction | one failing `run_tests` dumping 20k+ chars of pytest tracebacks into the transcript · the unhandled JSON crash · the whole growing transcript resent every call (quadratic cost) |
| `h3_full` | durable working notes (survive compaction) · write-path guardrail on `tests/` | plan lost with the transcript · "don't modify tests" enforced by the harness instead of the prompt |

The deltas are deliberately small. Read them as diffs — the diff is the lesson:

```
diff harnesses/h1_naive.py harnesses/h2_managed.py
diff harnesses/h2_managed.py harnesses/h3_full.py
```

## What "vary only the harness" means

| Held constant | Varied (the harness) |
|---|---|
| Model, temperature, provider endpoint | What a tool result looks like by the time the model sees it — the tool's return value is identical everywhere, but h1 forwards it whole (a mid-migration `run_tests` can be ~25k chars of tracebacks, resent every turn thereafter), while h2/h3 forward the first 4k + last 1.5k with a `[harness truncated N chars]` marker, keeping the leading failures and the summary line |
| Tasks: identical pristine workspace copies, identical prompts | What the resent history looks like — h1 resends every message forever; h2/h3 elide old tool outputs once the transcript passes an 80k-char budget |
| Tools: all harnesses import the same `Workspace` + schemas from Block 2 | What happens on a malformed tool call — h1 raises and the run dies; h2/h3 feed the model a recoverable error message and continue |
| Base system prompt, `MAX_TURNS` (both in `harnesses/base.py`; the budget is 40 for every harness here — above Block 2's 20-turn cap, deliberately generous so the experiment measures protections, never the budget) | What the model is offered and refused — h3 only: the `update_notes` tool and pinned notes message are offered; writes to `tests/` are refused |
| The judge: pytest on the workspace, never the agent's self-report | |

Note that h3 does change what the model sees — an extra tool, a pinned
notes message. That isn't contamination; it's the definition. The harness
is the thing that decides what the model observes, what it may do, and
what happens to its output. The model weights never change; its
environment does — and environment changes alone are what move the numbers.

One confound remains: the model isn't deterministic, even at temperature
0.1. The same harness on the same task has crashed at turn 11 on one run
and completed in 31 turns on another. Single runs compare harness+luck
against harness+luck — treat one-run differences as direction, not
magnitude, and collect several runs per cell before quoting numbers.
Every run is preserved in `results/results.jsonl` for exactly this reason.

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

## Exercise flow (all commands from `block3_measure/`)

1. **Baseline the short task** — confirm h1 is the harness you built:
   ```
   uv run eval/run_eval.py h1 --task fix_bug
   ```
2. **Reproduce the Block 2 failure, instrumented this time:**
   ```
   uv run eval/run_eval.py h1 --task refactor_v2
   ```
3. **Read the h2 diff, then run the same task through h2** — identical to
   h1 except tool outputs are capped, malformed tool calls come back as
   recoverable errors, and old tool outputs are elided past a budget.
   Watch the live output for `compaction: elided N old tool output(s)`
   lines — that's the harness managing context mid-run:
   ```
   uv run eval/run_eval.py h2 --task refactor_v2
   ```
4. **Read the h3 diff, then run h3** — h2 plus a durable `update_notes`
   tool (notes survive compaction) and a write guardrail on `tests/`.
   Watch for the agent calling `update_notes` unprompted — the harness
   only offers the tool; whether the model adopts it is part of the
   result:
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
- Before copying, the runner verifies the source workspace is still in its
  unsolved state and refuses to run otherwise. Block 2 exercises modify
  the repo workspaces in place, so if you ran Block 2 first (you did),
  reset before measuring:

  ```
  git checkout -- ../block2_naive_harness/tasks/
  ```

  A benchmark against an already-solved fixture produces small, plausible,
  meaningless numbers — the runner failing loudly here is the same
  eval-hygiene principle as not trusting the agent's self-report.
- Solved means **pytest exits green on the workspace afterward**. The
  agent's self-report is never consulted. Your harness evaluation at work
  should share this property: external checkers on your tasks.
- `results/results.jsonl` accumulates every run; `compare.py` shows the
  latest per cell (with a `when` column so you can tell recent rows from
  old ones). Rerunning a cell needs no reset — each run copies the
  pristine source fresh — and simply appends another sample. One caveat:
  a rerun replaces that cell's run directory, so inspect a failed run's
  workspace under `results/runs/` *before* rerunning it.
- To start the table over — say, to separate warm-up attempts from the
  runs you intend to keep — archive the file; nothing is lost:

  ```
  mv results/results.jsonl results/results.warmup.jsonl
  ```

## Starting over

One command, run from anywhere in the repo:

```
uv run scripts/reset.py
```

It restores the task workspaces to their committed state (including
removing any files an agent created), clears the per-run copies under
`results/runs/`, and archives the score table with a timestamp — then
prints what it did. Then rerun the exercise flow from step 1; the runner's
pre-flight check confirms the workspaces really are unsolved before
spending tokens.

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
