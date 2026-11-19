# Block 3: Measure It

> **In this block (28 min)**
>
> | Part | Time | What happens |
> |---|---|---|
> | Intro | 4 min | The presenter sets up the block and the exercise |
> | Hands-on | 18 min | Steps 0 to 3 under "Exercise" |
> | Discussion | 6 min | The questions under "Discussion" near the end of this page |
>
> **If you're behind:** if any run hasn't finished six minutes after you
> started it, stop it (Ctrl+C) and read the numbers in step 2 instead. If
> you reach step 3 with under four minutes left, skip its runs and read
> its table. The discussion starts on time, whether or not everyone has
> finished.

This block runs Block 2's 149-file migration through two harnesses with
more protections: same model, task and tools, only the harness changes.
It's also how you'd settle a harness argument at work: run your own tasks
through the candidates and check the results yourself, rather than taking
the agent's word for them.

**Your Block 2 numbers are the baseline:** ending, last turn, total sent,
biggest `added`. Block 2 had 20 turns and these get 40, so if yours ran
out, compare turn by turn, not just totals.

## The two harnesses

Each has a short name and a full one. You type the short name (`h2`,
`h3`) when you run it; the output, files and folders use the full name
(`h2_managed`, `h3_full`). Your Block 2 harness is `h1` (`h1_naive`).

**h2** (`h2_managed`): your Block 2 harness plus two protections. In
Block 2, every tool result stayed in the conversation and was re-sent on
every later turn; that's where the cost came from (your biggest `added`).
These two go after it from both ends: the cap keeps one huge result from
getting in, and compaction clears out old results once the conversation
gets big.

1. **A cap on tool output.** Each tool result is cut to 6,000 characters:
   the first 4,000, the last 1,500, and a note saying how much was cut.
   6,000 is a setting we chose: it leaves files whole (only 1 of 149 is
   longer) and cuts searches and tracebacks (see "Why 6,000 and 80,000?").
   Code: `truncate()` in `harnesses/h2_managed.py`, 12 lines.
2. **Compaction.** Past 80,000 characters, the oldest tool results are
   swapped for a short placeholder ("re-run the tool if you need it"); the
   newest messages are never touched. Old results are most of the
   conversation, and the agent has usually already acted on them. 80,000
   is also a setting we chose: we started at 200,000, and compaction never
   fired on this task (see "Why 6,000 and 80,000?"). Code: `compact()`.

h2 also catches a malformed tool call instead of crashing. It's rare on
this task; `AFTER_THE_WORKSHOP.md` shows it.

**h3** (`h3_full`): h2 plus three things production harnesses ship. The
second is off until you flip it in step 3.

1. **Durable notes.** An `update_notes` tool writes to a pinned message
   that compaction never drops, so the agent's plan survives. Code: the
   `[h3]` blocks in `harnesses/h3_full.py`.
2. **A budget signal (off by default).** `BUDGET_SIGNAL=progress` adds
   one line to each turn: the turns left and the last test result. Step 3
   turns it on. Code: `budget_signal()`, tagged `[h3, optional]`.
3. **A write guardrail.** The harness refuses writes to test files, so
   the agent can't make the tests pass by editing them. Code:
   `is_test_file()` and `guarded_write()`.

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

### Step 1: Run h2, then h3 (about 7 minutes)

One at a time, so you can watch each harness work. Each usually takes
about 3 minutes and solves the task. If a model call hangs, the harness
retries after 3 minutes and prints a dim `⟳ model call took over 180s
with no answer; retrying`. That's the provider, not your run: the
behind-rule at the top applies.

#### 1a. h2

Your Block 2 harness plus the cap and compaction. You're watching the
harness manage what the model sees.

```bash
uv run eval/run_eval.py h2 --task refactor_v2
```

Watch for:
- **The cap:** a yellow `✂ … truncated search output: 14,056 → 5,540
  chars`. In Block 2 that whole result was re-sent every turn after it.
  The cap cuts the file listing too (`list_files`, 6,360 characters), and
  what's cut can matter: in one run the agent missed two whole groups of
  files until the tests failed on turn 19, then rewrote them on its last
  turn without reading them.
- **The conversation growing:** `conversation N chars` on the scoreboard.
  Compared turn for turn with your Block 2 run, it should grow more slowly.
- **Compaction:** once `conversation` passes about 80,000, `✂ …
  compaction: dropped N old tool output(s)`, usually every turn after. If
  `re-read` then climbs, it dropped something the agent still needed.
- **The switch from reading to writing**, usually announced in a green
  `agent says` line.
- **When it first runs the tests:** usually late, as in Block 2. None of
  h2's protections change that.
- **Where the time goes:** the end of each scoreboard line, e.g. `21.3s
  (model 21.1s) · 6m 02s in all`. Turns that write many files take longest:
  the model types every file out in full. Time depends on the provider and
  how busy it is, so compare turns within your run, not your times with a
  neighbor's.

#### 1b. h3

h2 plus durable notes and the test guardrail. You're watching whether the
agent uses its notes, and whether more capability changes the cost.

**No reset needed between the two:** each run works on its own copy of
the task.

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
  tried to edit a test. It almost never does here;
  `AFTER_THE_WORKSHOP.md` shows it firing.

### Step 2: Read the results (about 8 minutes)

**Start step 3's two runs first,** then read these while they run. They
take about 3 minutes and don't depend on anything here.

Each run ends with Block 2's turn table and summary, plus a `fired` column:
`✂` a result was cut, `✂✂` old results dropped, `↻` a malformed call
recovered, `⛔` a test write refused. Then the comparison table prints
(`uv run eval/compare.py` re-renders it).

Four things to find:

1. **What h2 saved.** Find the biggest `added` in your Block 2 run and in
   h2, and multiply each by the turns after it. In one of our pairs,
   Block 2's biggest was re-sent for ~276,000 tokens, h2's for ~113,000;
   in total, h2 sent 390,294 to Block 2's 646,417 in about the same
   number of turns. Then read `not re-sent` (characters; divide by 4 for
   tokens): kept off ÷ (sent + kept off) was a quarter to a third in our
   runs. That part is the harness; the rest of any gap is how the run
   went. If your h2 ran past 20 turns, compare its `sent so far` at turn
   20 with your Block 2 total.
2. **h3's notes, and your prediction.**

   ```bash
   cat results/runs/h3_full__refactor_v2__*/agent_notes.md
   ```

   If it says the agent never called `update_notes`, that's a result, not
   an error (most of our runs took notes; on one provider most didn't).
   Then check your prediction: notes add about 1% to a run, so a big h2/h3
   gap is the run, not the harness. Ours on Fireworks: h2 0.62M to 1.19M
   over seven runs, h3 0.73M to 1.18M over eight. Don't compare across
   providers. In our ablation (h3 with and without notes,
   three runs each), the notes bought nothing measurable: no run re-read a
   file, so there was nothing to preserve.
3. **When the agent ran the tests.** The line under the verdict:
   `what the trace shows: tests run 2 times, first at turn 24 of 28 · 0
   files rewritten without being read first`. Note when your h2 and h3
   first tested: step 3 asks whether telling the agent its budget changes
   that. Block 4 shows the same line for every harness. Check it against
   the run's full trace:

   ```bash
   grep -n "run_tests" results/runs/h2_managed__refactor_v2__*/console.log
   ```
4. **Against the reference.** On `refactor_v2`, the last line compares the
   final code with a careful hand migration: `against the reference
   migration: matches`, or how many files differ. Tests passing and this
   line disagreeing is a finding, not a bug in the checker.

### Step 3: Tell the agent its budget (runs started in step 2; 2 minutes to compare)

No harness so far tells the model how many turns it has left or whether
its work passes. `BUDGET_SIGNAL=progress` makes h3 add one line to each
turn, e.g. `Turn 12 of 20 used: 8 left. Last test run (turn 9): 23 failed,
12 passed.` A signal only matters when the budget is tight, so both runs
get 20 turns. Start them side by side, each in its own terminal:

```bash
MAX_TURNS=20 uv run eval/run_eval.py h3 --task refactor_v2
```

```bash
MAX_TURNS=20 BUDGET_SIGNAL=progress uv run eval/run_eval.py h3 --task refactor_v2
```

In the second, watch the dim `⏱ told the model: …` lines and when it
first runs the tests. Our Fireworks runs, five of each, at about the same
cost (0.33M to 0.48M tokens):

| h3 with 20 turns | Tests pass | Said it was done |
|---|---|---|
| No signal | 0 of 5 | 0 of 5 |
| `BUDGET_SIGNAL=progress` | 4 of 5 | 3 of 5 |

The difference was the agent testing its work, and it never mentioned the
signal: you only see the effect by measuring. A turn count alone did
little; the test status is what mattered. The signal doesn't stop an agent
leaving testing to its last turn, though: one of ours found a missed file
that way, with no turn left to fix it.

**Read the last line, too.** One no-signal run finished in 14 turns at
half the cost of any other, all 35 tests passing, but `120 files differ`
from the reference: it had aliased the old names (`make_ledger =
new_ledger`) and left 70 files on v1. The cheapest run didn't do the job.

**The method is what you take to work:** fix the model and the task, vary
one thing, judge with an external checker, and run enough times to tell
a result from noise. Then check the checker: an agent under pressure will
find what your tests don't cover.

## Starting over

```bash
uv run ../scripts/reset.py && uv run ../scripts/check_fixtures.py
```

`reset.py` restores every task, clears run copies, and archives (doesn't
delete) your score table. `check_fixtures.py` only checks.

## Discussion (6 min)

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

Block 4: what production harnesses decide for you, and what they leave
to you.

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
  Block 4 shows both. h3's version guards one thing, the tests, at the one
  place every tool call passes through.

That these patterns are common is documented. That they help *your*
workload is something to measure.

## After the workshop

Want to see the rare protections fire, or test whether h3's notes earn
their place? See [`AFTER_THE_WORKSHOP.md`](AFTER_THE_WORKSHOP.md).

## Reference

### Compaction

It triggers on a threshold, and once crossed, keeps firing every later
turn: none, or a lot. It fired in three of our five long h2 runs on the
hosted endpoint (9, 13 and 40 results dropped), and in every h2 and h3
run on Fireworks, where runs went longer.

It can also cost turns. In one run it started on turn 14, while the agent
was still reading. The agent re-read 18 dropped files, made its first edit
on turn 20, and finished on 34. Our other runs re-read nothing. Compaction
saves tokens per turn, but when it drops something still needed, the run
gets longer; that's the problem h3's notes target.

### "Why 6,000 and 80,000?"

Knobs, not derived values. **6,000** was a starting value that happens to
fit this task: only 1 of the 149 files is longer, so files are rarely cut,
while searches and tracebacks are. The file listing (6,360 characters) is
cut too, and in one run the cut hid two file families, which the agent
then rewrote from guesses. **80,000** was tuned down from 200,000, at
which compaction never fired here. (It counts messages and tool results,
not files the agent writes.)

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
- h2 changes several things at once (the cap, compaction and recovery),
  so it can't say which one earned a difference. The ablation in
  `AFTER_THE_WORKSHOP.md` shows how to isolate one.
