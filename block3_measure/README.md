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

At a glance — same loop, same five workspace tools, same 40-turn budget;
each ✓ is a capability the harness adds:

| Capability | h1_naive | h2_managed | h3_full |
|---|:-:|:-:|:-:|
| Tool-output truncation (per-result 6k-char cap, head+tail) | – | ✓ | ✓ |
| Malformed-tool-call recovery (error message instead of crash) | – | ✓ | ✓ |
| Context compaction (drop old tool outputs past 80k chars) | – | ✓ | ✓ |
| Durable working notes (`update_notes` tool + pinned message) | – | – | ✓ |
| Write guardrail (`tests/` read-only at the dispatcher) | – | – | ✓ |

In one line each: **h1** is the loop and nothing else — its only memory is
the transcript and its only rule is the prompt. **h2** manages what the
model *sees* (tool results capped, history compacted, bad calls survivable).
**h3** additionally changes what the model *can do* — one action granted
(persist notes that outlive compaction), one revoked (writing to tests).

In more detail:

| | Adds | Block 2 failure mode addressed |
|---|---|---|
| `h1_naive` | nothing — the harness you built in Block 2, frozen and instrumented (turns, tokens, wall time, outcome) | — the baseline |
| `h2_managed` | tool-output limits · malformed-call recovery · context compaction | one failing `run_tests` dumping 20k+ chars of pytest tracebacks into the transcript · the unhandled JSON crash · the whole growing transcript resent every call (quadratic cost) |
| `h3_full` | durable working notes (survive compaction) · write-path guardrail on `tests/` | plan lost with the transcript · "don't modify tests" enforced by the harness instead of the prompt |

The deltas are deliberately small, and you don't need to diff anything to
see them: every addition is tagged with a `[h2]` or `[h3]` comment marker
in the source. Open the file, jump between markers, and everything
unmarked is identical to the previous harness:

```
grep -n "\[h2\]" harnesses/h2_managed.py    # every h2-added block
grep -n "\[h3\]" harnesses/h3_full.py       # every h3-added block
```

(If you do prefer a diff, `diff harnesses/h1_naive.py harnesses/h2_managed.py`
works — the files are kept structurally parallel for exactly that reason.)

### How h3's durable notes work, and why they exist

**Motivation:** h2's compaction creates a tension. It controls cost by
dropping old tool outputs — but the transcript is the agent's only memory,
so the cost fix deletes things the agent may still need (the dropped-output
marker admits as much: "re-run the tool if you need it again"). On a
30-turn task, re-running tools to recover dropped information costs turns
and re-injects large outputs. h3 resolves the tension by giving memory a
home compaction is not allowed to touch.

**Core logic (three pieces, all in the `[h3]` blocks):**
1. A second system message is pinned near the top of the conversation:
   `"YOUR WORKING NOTES (persist even when old tool output is dropped...)"`.
2. One extra tool, `update_notes`, overwrites that message's content —
   the agent curates its own memory.
3. Compaction only ever drops `tool` messages, so the notes are resent to
   the model on every turn, intact, no matter how much history is trimmed.

**What to expect:** whether and *when* the agent uses this is part of the
result, not a given — the harness offers the capability; adoption is the
model's choice. After a run, the final notes are saved to
`results/runs/<cell>/agent_notes.md`, and the cyan ✎ lines in the console
show when each update happened. Runs that bank their notes early tend to
re-read far less than runs that treat notes as an end-of-run summary —
check your own trace against that claim.

## What "vary only the harness" means

| Held constant | Varied (the harness) |
|---|---|
| Model, temperature, provider endpoint | What a tool result looks like by the time the model sees it — the tool's return value is identical everywhere, but h1 forwards it whole (a mid-migration `run_tests` can be ~25k chars of tracebacks, resent every turn thereafter), while h2/h3 forward the first 4k + last 1.5k with a `[harness truncated N chars]` marker, keeping the leading failures and the summary line |
| Tasks: identical pristine workspace copies, identical prompts | What the resent history looks like — h1 resends every message forever; h2/h3 drop old tool outputs once the transcript passes an 80k-char budget |
| Tools: all harnesses import the same `Workspace` + schemas from Block 2 | What happens on a malformed tool call — h1 raises and the run dies; h2/h3 feed the model a recoverable error message and continue |
| Base system prompt, `MAX_TURNS` (both in `harnesses/base.py`; the budget is 40 for every harness here — above Block 2's 20-turn cap, deliberately generous so the experiment measures protections, never the budget) | What the model is offered and refused — h3 only: the `update_notes` tool and pinned notes message are offered; writes to `tests/` are refused |
| The judge: pytest on the workspace, never the agent's self-report | |

Note that h3 does change what the model sees — an extra tool, a pinned
notes message. That isn't contamination; it's the definition. The harness
is the thing that decides what the model observes, what it may do, and
what happens to its output. The model weights never change; its
environment does — and environment changes alone are what move the numbers.

One variable we can't control remains: the model isn't deterministic, even at temperature
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

## Exercise flow

**Run every command in this section from the `block3_measure/`
directory** — the paths below are relative to it, and they will fail from
anywhere else:

```
cd block3_measure   # from the repo root
pwd                 # .../agent-harness-workshop/block3_measure
```

Every command on this page, including the reset script, runs from here —
nothing requires switching directories mid-exercise.

**Before you start:** you'll run the long task three times, once per
harness. Budget about 3–5 minutes and $0.50–1.50 each, so ~10 minutes and
~$3 in total. Run each one once — the point is the comparison, not
repetition.

**One difference from Block 2 worth knowing up front:** these harnesses
get a 40-turn budget, not Block 2's 20. The budget is held constant and
deliberately generous across all three so the experiment measures the
protections rather than the turn cap. That means h1 may well *finish*
here, where it ran out of room in Block 2 — watch what it costs to do so.

1. **Run the same naive harness you built, now instrumented.** No need to
   re-verify it on the short tasks; this is the long one. You'll see the
   same per-turn scoreboard as Block 2 — watch the transcript column climb
   and never come back down, since h1 has no way to shrink it:
   ```
   uv run eval/run_eval.py h1 --task refactor_v2
   ```
   Expect several minutes of scrolling tool calls, then a one-line verdict
   and the comparison table with its first row.
2. **Skim the three `[h2]`-marked blocks in `harnesses/h2_managed.py`**
   (the capability matrix above tells you what you'll find: tool results
   capped at 6k chars before the model sees them, recoverable bad calls,
   compaction — everything unmarked is identical to h1), then run the same
   task through h2. Watch two things in the live output: yellow
   `compaction: dropped N old tool output(s)` lines, and the scoreboard's
   transcript column immediately after one — that number going *down* is
   the harness reclaiming context mid-run, which never happened in h1:
   ```
   uv run eval/run_eval.py h2 --task refactor_v2
   ```
3. **Skim the `[h3]`-marked blocks in `harnesses/h3_full.py`** (durable
   notes + the write guardrail), then run h3. Watch for the agent calling
   `update_notes` unprompted — the harness only offers the tool; whether
   the model adopts it is part of the result:
   ```
   uv run eval/run_eval.py h3 --task refactor_v2
   ```
   Afterward, read what the agent chose to remember — the final state of
   its durable notes is saved as a run artifact:
   ```
   cat results/runs/h3_full__refactor_v2/agent_notes.md
   ```
   Compare it against the task: did the agent record the rename map? The
   undocumented renames it discovered? Per-file progress? Its notes are a
   window into what the model considered worth keeping when it knew the
   transcript wouldn't last.
4. **Review the comparison table.** It prints automatically after every
   run, so by now you've watched it grow row by row. To re-render it at
   any time without running anything:
   ```
   uv run eval/compare.py
   ```

## Seeing the protection that doesn't fire

One of h2's three protections — malformed-call recovery — is tail-risk
insurance, not something you'll usually watch happen (it triggered in
roughly 1 of 4 naive long runs during tuning). Two ways to see it anyway.

Replay the real triggering event offline. No API calls, no cost:

```
uv run eval/demo_recovery.py
```

The same truncated tool call goes into both harnesses: h1's path dies with
an unhandled traceback, h2's turns it into feedback the model can act on.

Or trigger it inside a real run. Fault injection corrupts one tool call's
JSON at a turn you choose, simulating the model hitting its output ceiling
— the harness code itself is untouched, so what follows is live model
behavior. Cheap, because it uses the short task:

```
INJECT_MALFORMED_TURN=3 uv run eval/run_eval.py h2 --task fix_bug   # recovers, still solves
INJECT_MALFORMED_TURN=3 uv run eval/run_eval.py h1 --task fix_bug   # crashes on the spot
```

## How scoring works (worth internalizing)

- Every run copies the pristine workspace to `results/runs/<harness>__<task>/`
  — runs never touch the repo or each other, and a failed run's workspace
  is kept for you to inspect.
- Before copying, the runner verifies the source workspace is still in its
  unsolved state and refuses to run otherwise. Block 2's exercises edit
  those workspaces in place, so if you came from Block 2 (you did), reset
  before measuring — see "Starting over" below. A benchmark against an
  already-solved fixture produces small, plausible, meaningless numbers;
  the runner failing loudly here is the same principle as not trusting the
  agent's self-report.
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

The tasks are fixtures: a codebase that must still be on the old API, a
bug that must still be there. Agents edit them, so after a run they're no
longer in their starting state. Two scripts keep that straight, and both
run from this directory:

```
uv run ../scripts/reset.py          # restore the fixtures
uv run ../scripts/check_fixtures.py # confirm: ALL FIXTURES OK
```

**`reset.py`** restores every task workspace to its committed state
(including deleting files an agent created), clears the per-run copies
under `results/runs/`, and archives your score table with a timestamp
rather than deleting it. It prints what it changed.

**`check_fixtures.py`** asserts each workspace's tests still *fail* — a
fixture that passes is a solved task, and measuring against it is
meaningless — confirms the reference copies still pass, and re-derives the
long task into a temp directory to check the committed one hasn't drifted.

Then rerun the exercise flow from step 1.

## Debrief questions

1. What did ~40 lines of harness (h1→h2) buy, in solve rate, tokens, and
   dollars?
2. Which h2 protection did the heavy lifting on `refactor_v2`? (Check
   `notes` in the table: `malformed_calls` recovered, `dropped_tool_outputs`.)
3. What does h3's guardrail change about how much you must trust the
   *prompt*? (Try h1 on a task and count how many times "do not modify the
   tests" was load-bearing.)
4. These five protections are a tiny subset of what production harnesses
   ship. Block 4: what the pros decided for you.
