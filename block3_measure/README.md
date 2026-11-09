# Block 3: Measure It

> **In this block (30 min)**
>
> | Part | Time | What happens |
> |---|---|---|
> | Intro | 5 min | The presenter sets up the block and the exercise |
> | Hands-on | 15 min | Steps 0 to 3 under "Exercise" |
> | Discussion | 10 min | The questions under "Discussion" near the end of this page |
>
> **If you're behind:** if h3 hasn't finished ten minutes into the
> hands-on, stop it (Ctrl+C) and read your h2 results plus the h3 numbers
> in step 2. If you reach step 3 with under four minutes left, skip its
> runs and read its table. Steps 4 and 5 are optional, for after the
> workshop. The discussion starts on time, whether or not everyone has
> finished.

Block 2 ended with the naive harness on the 149-file migration. This block
runs the **same task** through two better harnesses and measures what each
change was worth: same model, same task, same tools, only the harness
changes. That's also how to settle a harness argument at work: run your
own tasks through the candidates, and judge with something other than the
agent's own report.

**Bring your Block 2 numbers:** how it ended, the last turn, the total
sent, and your biggest `added`. That run is your baseline. One difference:
Block 2's harness had 20 turns and these get 40, so if your Block 2 run ran
out, its total is what it spent before it was cut off. Compare turn by turn,
not just totals.

## The two harnesses

Each has a short name and a full one. You type the short name (`h2`,
`h3`) when you run it; the output, files and folders use the full name
(`h2_managed`, `h3_full`). Your Block 2 harness is `h1` (`h1_naive`).

**h2** (`h2_managed`): your Block 2 harness plus three protections.

1. **A cap on tool output.** Each tool result is cut to 6,000 characters:
   the first 4,000, the last 1,500, and a note saying how much was cut. It
   targets single huge results, such as a search across all 149 files
   (13,000 to 22,000 characters). Code: `truncate()` in
   `harnesses/h2_managed.py`, 12 lines.
2. **Recovery from a malformed tool call.** If the model sends a tool call
   that isn't valid JSON, the harness tells it what went wrong and carries
   on. In Block 2, that crashed the run. Code: the `[h2] Guarded parse`
   block in `run()`.
3. **Compaction.** Past 80,000 characters, the oldest tool results are
   swapped for a short placeholder ("re-run the tool if you need it"); the
   newest messages are never touched. Why: old tool results are most of
   the conversation, the agent has usually already acted on them, and every
   turn pays to re-send them. Code: `compact()`.

**h3** (`h3_full`): h2 plus two things production harnesses ship.

1. **Durable notes.** An `update_notes` tool writes to a pinned message
   that compaction never drops, so the agent's plan survives. Code: the
   `[h3]` blocks in `harnesses/h3_full.py`.
2. **A write guardrail.** Writes to test files (under `tests/`, any
   `test_*.py`, `conftest.py`) are refused by the harness, not just
   forbidden by the prompt. Why: success means "the tests pass," and an
   agent that can edit the tests can get there without fixing anything.
   Code: `is_test_file()` and `guarded_write()`.

Every addition is tagged in the source; everything untagged is identical
to the harness before it:

```bash
grep -n "\[h2\]" harnesses/h2_managed.py
```

```bash
grep -n "\[h3\]" harnesses/h3_full.py
```

## Exercise

Run every command from `block3_measure/`. From the repo root:

```bash
cd block3_measure
```

### Step 0: Start clean (a few seconds)

Block 2 edited the migration task in place, so put it back:

```bash
uv run ../scripts/reset.py && uv run ../scripts/check_fixtures.py
```

Expect `ALL FIXTURES OK`. The runner also refuses a task an agent has
already touched.

### Step 1: Run h2, then h3 (about 6 minutes)

One at a time, so you can watch each harness work. Each takes 2 to 3
minutes and usually solves the task in 17 to 34 turns.

#### 1a. h2

Your Block 2 harness plus the cap, recovery and compaction. You're
watching the harness manage what the model sees.

```bash
uv run eval/run_eval.py h2 --task refactor_v2
```

Watch for:
- **The cap:** a yellow `✂ … truncated search output: 14,056 → 5,540
  chars`. In Block 2 that whole result was re-sent every turn after it.
- **The conversation growing:** `conversation N chars` on the scoreboard.
  Compared turn for turn with your Block 2 run, it should grow more slowly.
- **Compaction:** once `conversation` passes about 80,000, `✂ …
  compaction: dropped N old tool output(s)`, usually every turn after. If
  `re-read` then climbs, it dropped something the agent still needed.
- **The switch from reading to writing**, usually announced in a green
  `agent says` line.
- **When it first runs the tests:** usually late, as in Block 2. None of
  h2's protections change that.

#### 1b. h3

h2 plus durable notes and the test guardrail. You're watching whether the
agent uses its notes, and whether more capability changes the cost.

**Note: no reset needed between the two.** Each run works on its own copy
of the task.

**Write down a prediction first:** will h3 send more tokens than h2, or
fewer?

```bash
uv run eval/run_eval.py h3 --task refactor_v2
```

Watch for everything above, plus:
- **Notes:** a cyan `✎ … update_notes('## Plan ...')`. Early, as a plan,
  or late, as a summary? Some runs never use it; the harness only offers
  the tool.
- **The guardrail:** a red `⛔ guardrail refused a write …` would mean it
  tried to edit a test. It almost never does here; step 4 shows it firing.

### Step 2: Read the results (about 5 minutes)

Each run ends with Block 2's turn table and summary, plus a `fired` column:
`✂` a result was cut, `✂✂` old results dropped, `↻` a malformed call
recovered, `⛔` a test write refused. Then the comparison table prints
(`uv run eval/compare.py` re-renders it).

Six things to find:

1. **Against your Block 2 run.** Find the biggest `added` in each. In one
   of our pairs, Block 2's was 12 searches adding 19,747 tokens, re-sent on
   14 later turns (~276,000 tokens); h2's was 8 searches adding 9,391
   (~113,000). In total, h2 sent 390,294 to Block 2's 646,417, in about the
   same number of turns.
2. **What h2 kept off the wire.** `not re-sent` counts what the
   protections removed, once for every turn it would otherwise have been
   re-sent: roughly a quarter to a third in our runs. That part is the
   harness; the rest of any gap is how the run went.
3. **Re-reads after compaction.** `re-read` climbing right after `✂✂`
   turns means compaction dropped something still needed. In one of our
   runs that cost about ten extra turns (see "Compaction" below).
4. **h3's notes, and your prediction.**

   ```bash
   cat results/runs/h3_full__refactor_v2__*/agent_notes.md
   ```

   If the agent never called `update_notes`, the file says so. That's a
   result, not an error: it happened in two of our five runs. Then compare
   totals. h3's only systematic extra cost is its notes overhead, about 115
   to 240 tokens a turn, under 1% of a run this size. So if your h3 cost
   40% more or less than h2, that's the run, not the harness. Ours: h3
   365k to 702k, h2 390k to 778k.
5. **When the agent ran the tests.** The line after the verdict:
   `what the trace shows: tests run 2 times, first at turn 24 of 28 · 0
   files rewritten without being read first`. Note when your h2 and h3
   first tested: step 3 asks whether telling the agent its budget changes
   that. You'll see the same line in Block 4, for every harness.
6. **Against the reference.** On `refactor_v2`, the last line compares the
   final code with a careful hand migration: `against the reference
   migration: matches`, or how many files differ. Tests passing and this
   line disagreeing is a finding, not a bug in the checker.

Every run's full trace is saved, as plain text, to
`results/runs/<harness>__<task>__<time>/console.log`, one file per run,
so you can search it after it scrolls past:

```bash
grep -n "run_tests" results/runs/h2_managed__refactor_v2__*/console.log
```

### Step 3: Tell the agent its budget (about 4 minutes)

No harness so far tells the model how many turns it has left, or whether
its work passes. Research says it should: a 2025 paper's "Budget Tracker"
showed the agent its remaining tool calls after every step and matched a
standard agent's accuracy at 31% lower cost
([arXiv 2511.17006](https://arxiv.org/abs/2511.17006)), and Anthropic's
[context awareness](https://platform.claude.com/docs/en/build-with-claude/context-windows)
and [task budgets](https://platform.claude.com/docs/en/build-with-claude/task-budgets)
show the model its remaining tokens as it works.

`BUDGET_SIGNAL=progress` makes h3 add one line to the end of each turn's
last tool result: turns left plus the last test result, e.g. `Turn 12 of
20 used: 8 left. Last test run (turn 9): 23 failed, 12 passed.`, or `Tests
not run yet.` A signal only matters when the budget is tight, so both runs
get 20 turns (`MAX_TURNS=20`, recorded separately from the 40-turn runs).
Start them side by side, each in its own terminal:

```bash
MAX_TURNS=20 uv run eval/run_eval.py h3 --task refactor_v2
```

```bash
MAX_TURNS=20 BUDGET_SIGNAL=progress uv run eval/run_eval.py h3 --task refactor_v2
```

In the second, watch the dim `⏱ told the model: …` lines, and when it
first runs the tests. Then compare how each ended. Our runs, six of each
(plus five of a third signal, `pacing`, which tells it to start editing at half
the budget and to test and finish with 5 turns left):

| h3 with 20 turns | Tests pass | Said it was done | Never ran the tests | Tokens (median) |
|---|---|---|---|---|
| No signal | 2 of 6 | 0 of 6 | 5 of 6 | 384k |
| `BUDGET_SIGNAL=progress` | 6 of 6 | 6 of 6 | 0 of 6 | 336k |
| `BUDGET_SIGNAL=pacing` | 4 of 5 | 2 of 5 | 1 of 5 | 348k |

What made the difference was the agent checking its work. Without a
signal, five of six runs never ran the tests, so none could say it was
done. With `progress`, every run tested (three on turn 3, to see the
starting state) and finished inside the budget. The agent never once
mentioned the signal: you only see the effect by measuring.

Two more findings, at the normal 40 turns, where the budget never got
tight. The signals changed behavior but not cost: with
`BUDGET_SIGNAL=compaction` ("save what you need to your notes" near the
compaction budget), the agent saved its notes as the warnings began in
all three runs, yet no signal ran cheaper than plain h3. And a turn count
alone did little: h2's `TURN_NOTICE=every` adds just "turn 12 of 40 used:
28 left", and its costs overlapped plain h2's. What `progress` adds is the
test status.

**Read the last line, too.** One of our 20-turn runs without the signal
finished in 14 turns at half the cost of any other, and the scoreboard
called it solved. The line under it said `against the reference
migration: 120 files differ`. The agent had renamed the core functions,
then added aliases (`make_ledger = new_ledger`) so the old names kept
working, and left 70 files still calling v1 functions. All 35 tests
passed: they exercise only the v2 API. Under a tight budget, the
cheapest run was the one that didn't do the job.

**The method is what you take to work:** fix the model and the task, vary
one thing, judge with an external checker, and run enough times to tell a
result from noise. Then check the checker: a test suite measures what it
tests, and an agent under pressure will find what it doesn't.

## Optional steps

**4. Make the rare protections fire.** Each on a short task. The first two
are demos and aren't recorded.

```bash
INJECT_MALFORMED_TURN=3 uv run eval/run_eval.py h1 --task fix_bug
```

```bash
INJECT_MALFORMED_TURN=3 uv run eval/run_eval.py h2 --task fix_bug
```

A corrupted tool call on turn 3: h1 (your Block 2 harness, run here) crashes (`the harness crashed
(JSONDecodeError ...)`); h2 prints `↻`, carries on and solves it.

```bash
TRANSCRIPT_CHAR_BUDGET=4000 uv run eval/run_eval.py h2 --task bug_hunt
```

A 4,000-character budget. In our run, `✂✂` fired on turns 6 to 11, `added`
went negative, and `cached` fell from 64% to 10%: compaction changes the
start of the conversation, so the provider's cache stops matching.

```bash
uv run eval/run_eval.py h2 --task touch_tests
```

```bash
uv run eval/run_eval.py h3 --task touch_tests
```

This task asks the agent to fix the bug *and* add a test. h2 adds it (5
pass). h3 refuses (`⛔`), still fixes the bug, and carries on, because the
refusal is an ordinary tool result. Ours said so in its summary: it tried
to add the test "but the workspace blocks writes to test files."

**5. Do h3's notes earn their place?** h3 with and without notes, nothing
else changed:

```bash
uv run eval/ablation.py --runs 1 --task refactor_v2
```

Two more long runs. Predict the direction first. We ran three of each:
with notes 365k to 702k tokens, without 187k to 492k, ranges overlapping,
and no run in either arm re-read a single file. **The notes bought
nothing measurable**, because this migration never sends the agent back
for something it already had, so there was nothing for the notes to
preserve. Durable memory is a good feature; it did nothing here because
this workload doesn't produce the failure it prevents. Raw rows:
`ablation_results.jsonl`.

## Reference

### Compaction

It triggers on a threshold, and once crossed, keeps firing every later
turn: none, or a lot. It fired in three of our five long h2 runs (9, 13
and 40 results dropped).

It can also cost turns. In one run it started on turn 14, while the agent
was still reading. The agent re-read 18 dropped files, made its first edit
on turn 20, and finished on 34. Our other runs re-read nothing. Compaction
saves tokens per turn, but when it drops something still needed, the run
gets longer; that's the problem h3's notes target.

### "Why 6,000 and 80,000?"

Knobs, not derived values. **6,000** was a starting value that happens to
fit this task: only 1 of the 149 files is longer, so files are rarely cut,
while searches and tracebacks are. **80,000** was tuned down from 200,000,
at which compaction never fired here. (It counts messages and tool
results, not files the agent writes.)

| Knob | Lower | Higher |
|---|---|---|
| Tool-output cap | Saves more, but cuts things the agent needed | Saves less |
| Compaction budget | Compacts sooner, but drops results it may need, and breaks the cache | May never fire |

Defaults are tuned to someone's workload. Production harnesses usually
tie compaction to the model's context window instead.

### "Doesn't truncating a big file hurt?"

It can. The model is told what was cut (`... [harness truncated N chars]
...`), so it can search or re-read for the rest. On this task it doesn't
matter: the one file over the cap contains none of the renames. Production
harnesses tend to **paginate** instead: Claude Code's `Read` returns "the
first page with a `PARTIAL view` notice" and lets the model ask for more
with `offset` and `limit`
([tools reference](https://code.claude.com/docs/en/tools-reference),
checked Sep 2026). h2 discards the middle; pagination keeps it reachable.

### Recovery has two halves

Catching the parse error is one. The other: the bad arguments are also in
the stored assistant message, and if left there, the next request is
rejected (`400 Invalid JSON in tool call arguments`), one turn *after*
recovery seemed to work. h2 cleans both. An attendee's run found that bug;
our own fault injection had missed it because it corrupted only a local
copy. **A test that can't reproduce the real failure still passes.**
`uv run eval/demo_recovery.py` replays the case offline.

### How scoring works

- Each run works on a copy of the task under `results/runs/`, so runs
  never touch the repo or each other, and its trace is saved next to that
  copy (`console.log`). The runner refuses a task whose tests already
  pass or whose files differ from git.
- Solved means **pytest passes** afterwards; the agent's report is never
  consulted. Green tests are this exercise's definition of done, not proof
  of correctness: your checker is only as good as your bar. On
  `refactor_v2`, a second line compares the code with the reference
  migration (`../scripts/reference_check.py`); the score table still
  counts only the tests.
- `results/results.jsonl` keeps every run with its model and provider;
  `compare.py` shows the latest per harness and task.
- h2 changes three things at once, so it can't say which protection earned
  a difference. The ablation (step 5) shows how to isolate one.

### Starting over

```bash
uv run ../scripts/reset.py && uv run ../scripts/check_fixtures.py
```

`reset.py` restores every task, clears run copies, and archives (doesn't
delete) your score table. `check_fixtures.py` only checks.

## Discussion (10 min)

**For the group:**

1. Compare your Block 2 run with h2. Where did the difference come from?
   Find the turn, and say how much you'd credit to the harness and how much
   to how the run went.
2. One line of harness text changed whether the agent finished, and the
   agent never mentioned it. How would you have found that out without
   measuring? What does that say about choosing a harness from a feature
   list?
3. **Would this matter for your own agent?** If so, what would you need a
   harness to do, and how would you test that it does? Write it down:
   Block 5's worksheet starts from these notes.

**More to think about:**

- Which of h2's protections did the work in your run?
- h3's notes, a capability production harnesses ship, made no measurable
  difference here. How would you have found that out without running it?
- What kind of workload would make h3's notes pay off?
- The guardrail never fired on the migration. Is it worthless? (What could
  you claim about the runs nobody inspected?)

Block 4: what five production harnesses decide for you, and what they leave to you.

## Where these ideas come from

Each protection is a scaled-down version of something production
harnesses ship:

- **Durable notes:** Claude Code and the Agent SDK load `CLAUDE.md`
  memory each session ([docs](https://code.claude.com/docs/en/agent-sdk/overview));
  Deep Agents has `write_todos` and `AGENTS.md`
  ([docs](https://docs.langchain.com/oss/python/deepagents/overview));
  Pydantic AI's Harness has persistent notebooks
  ([docs](https://pydantic.dev/docs/ai/harness/)). They keep notes in
  files; h3 pins them as a message, always in view but re-sent every turn.
  Right at a few hundred characters, wrong at 50,000.
- **Budget signals (step 3):** Anthropic's API tells newer Claude models
  their remaining token budget after every tool call
  ([context awareness](https://platform.claude.com/docs/en/build-with-claude/context-windows))
  and offers an advisory countdown for a whole agentic loop
  ([task budgets](https://platform.claude.com/docs/en/build-with-claude/task-budgets));
  a 2025 paper's "Budget Tracker" does the same for tool calls
  ([arXiv 2511.17006](https://arxiv.org/abs/2511.17006)). Ours adds the
  last test result, which is what made the difference here.
- **Compaction and output limits:** Claude Code compacts automatically,
  Deep Agents uses summarization, Pydantic AI offers compaction as an
  option. h2 uses the simplest version so it fits in a dozen lines.
- **Malformed-call recovery:** Pydantic AI sends argument validation
  errors back to the model and lets it retry
  ([docs](https://pydantic.dev/docs/ai/core-concepts/retries/)); OpenAI's
  Agents SDK turns a tool call that crashes into an error message for the
  model (`failure_error_function`,
  [docs](https://openai.github.io/openai-agents-python/tools/#handling-errors-in-function-tools)).
  h2's version is the same idea in a few lines.
- **The test guardrail:** permission systems that decide what a tool may
  touch, whatever the model asks for: Claude Code's permission rules and
  modes ([docs](https://code.claude.com/docs/en/permissions)), Deep
  Agents' file access confined to a folder with `virtual_mode=True`
  ([docs](https://docs.langchain.com/oss/python/deepagents/backends)).
  Block 4 shows both. h3's
  version guards one thing, the tests, at the one place every tool call
  passes through.

That these patterns are common is documented. That they help *your*
workload is something to measure.
