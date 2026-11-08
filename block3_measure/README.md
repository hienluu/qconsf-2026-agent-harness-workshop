# Block 3: Measure It

> **In this block (30 min)**
>
> | Part | Time | What happens |
> |---|---|---|
> | Intro | 5 min | The presenter sets up the block and the exercise |
> | Hands-on | 15 min | Steps 0 to 2 under "Exercise" |
> | Discussion | 10 min | The questions under "Discussion" near the end of this page |
>
> **If you're behind:** the two long runs are the slow part, so start them
> side by side (step 1). If h3 hasn't finished twelve minutes into the
> hands-on, read your h2 results and the h3 numbers in step 2. Steps 3 to
> 7 are optional, for after the workshop. The discussion starts on time,
> whether or not everyone has finished.

At the end of Block 2 you ran the naive harness on the 149-file migration.
This block runs the **same task** through two better harnesses and
measures what each change was worth. Same model, same task, same tools;
only the harness changes.

That's also how your team should settle a harness argument. A published
benchmark score is measured inside someone else's harness, on someone
else's tasks. The numbers you can act on come from running your own tasks
through the candidates and checking the result with something other than
the agent's own report.

**Bring your Block 2 numbers:** how it ended, the last turn, the total
sent, and your biggest `added`. That run is your baseline. One caveat:
Block 2 stopped at 20 turns, and these harnesses get 40, so a Block 2 run
that "ran out" may simply have needed more turns.

## The two harnesses

- **`h2_managed`**: your Block 2 harness plus three protections, each
  aimed at something you saw there:
  1. **A cap on tool output.** Each tool result is cut to 6,000 characters
     (the first 4,000 and the last 1,500, with a note saying how much was
     cut). It targets single huge results: one search across all 149 files
     returns 13,000 to 22,000 characters, and a failing test run can return
     pages of tracebacks. It's per result, so a turn of many medium results
     mostly passes under it; that's compaction's job.
  2. **Recovery from a malformed tool call.** If the model sends a tool call
     that isn't valid JSON, the harness tells the model what went wrong and
     carries on instead of crashing. Block 2: one cut-off tool call killed
     the whole run.
  3. **Compaction.** Once the conversation passes 80,000 characters of
     messages and tool results, the harness replaces tool results with a
     placeholder, oldest first, until it's back under. The placeholder tells
     the model to re-run the tool if it needs the result again, and the most
     recent messages are never touched. Block 2: everything stayed forever
     and was re-sent every turn.
- **`h3_full`**: h2 plus two things production harnesses ship:
  1. **Durable notes.** An `update_notes` tool, and a pinned message near
     the top of the conversation holding whatever the agent writes there.
     Compaction never drops it, so the agent's plan survives even when old
     tool results are gone.
  2. **A write guardrail.** Writes under `tests/` are refused by the harness
     itself, instead of relying on the prompt's "don't modify the tests."

Every addition is tagged `[h2]` or `[h3]` in the source; everything
untagged is identical to the harness before it:

```bash
grep -n "\[h2\]" harnesses/h2_managed.py
```

```bash
grep -n "\[h3\]" harnesses/h3_full.py
```

`h1_naive` is your Block 2 harness, rerun under Block 3's rules (40 turns).
It's optional here (step 6): your own Block 2 run is the baseline.

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

Expect `ALL FIXTURES OK`. The runner also refuses to start on a task an
agent has already touched, so nothing measures a head start by accident.

### Step 1: Run h2 and h3 side by side (about 4 minutes)

**First, write down a prediction:** will h3, the more capable harness,
send more tokens than h2, or fewer?

Then start both, each in its own terminal (they work on separate copies,
so they don't interfere):

```bash
uv run eval/run_eval.py h2 --task refactor_v2
```

```bash
uv run eval/run_eval.py h3 --task refactor_v2
```

**While they run**, watch for the harness acting:
- `✂ truncated <tool> output: N → M chars`: the cap cutting a big result.
- `✂ compaction: dropped N old tool output(s)`: compaction, once the
  conversation passes its budget.
- `✎ update_notes` (h3 only): the agent writing its notes. The harness
  only offers the tool; whether and when the model uses it is part of the
  result.

**What to expect:** both usually solve it, in roughly 17 to 34 turns.
Unlike Block 2, running out of turns is unlikely at 40.

### Step 2: Read the results (about 5 minutes)

Each run ends with Block 2's turn-by-turn table and run summary, plus a
`fired` column marking the turns where a protection acted (`✂` a result
was cut, `✂✂` old results were dropped, `↻` a malformed call was
recovered). Then the comparison table prints; re-render it any time:

```bash
uv run eval/compare.py
```

Four things to find:

1. **Against your Block 2 run.** Find your biggest `added` in h2's table
   and compare it with Block 2's. In one of our pairs, Block 2's biggest
   turn was 12 searches adding 19,747 tokens, re-sent on the 14 turns after
   it (about 276,000 tokens); h2's was 8 searches adding 9,391 (about
   113,000). h2 sent 390,294 tokens in total against Block 2's 646,417, in
   about the same number of turns. Is the turn with a `✂` where yours
   differed?
2. **What h2 kept off the wire.** The comparison table's `not re-sent`
   column counts what h2's protections removed, once for every turn it
   would otherwise have been re-sent. In our h2 runs it came to roughly a
   quarter to a third of what would have been sent. That part is the
   harness; the rest of any gap is how the run went.
3. **Re-reads after compaction.** If `re-read` climbs right after `✂✂`
   turns, compaction dropped something the agent still needed. In one of
   our runs that cost about ten extra turns (see "When compaction costs
   turns" below).
4. **h3's notes, and your prediction.** Read what the agent chose to
   remember:

   ```bash
   cat results/runs/h3_full__refactor_v2__*/agent_notes.md
   ```

   Then compare h3's total with h2's. In our runs, h3 sent 365k to
   702k tokens and h2 390k to 778k: no clear winner either way. Whichever
   way yours went, someone near you probably got the opposite, and both of
   you hold exactly the evidence one run provides. The notes themselves
   varied as much: about 500 characters in two of our runs, nothing at all
   in the third. The harness offers the tool; how well the model uses it
   varies from run to run.

**The method is what you take to work:** fix the model and the task, vary
one thing, judge with an external checker (here, the tests), and run it
enough times to know whether you're looking at a result or at noise.

## Optional steps

Each one is safe to skip; none changes the conclusions above.

**3. The same harnesses on a short task.** Does h2 help when the work is
small?

```bash
uv run eval/run_eval.py h1 h2 h3 --task fix_bug
```

About 30 seconds. On a one-file bug fix nothing comes near the cap or the
compaction budget, so h2's protections never fire and it behaves exactly
like h1. h3 still carries its notes instructions on every turn, so it
costs a little more for nothing. Compare runs with the same turn count:
one extra turn costs more than any harness difference here. The lesson: a
protection is only worth as much as the problem it solves on *your*
workload, and a capability you don't use isn't free. Block 5's worksheet
starts from exactly this: describe your agent before choosing a harness.

**4. Make the two rare protections fire.** Malformed tool calls are rare,
and compaction may not fire on every long run, so force each on a short
task. These are demos, not measurements: the runner doesn't record them.

```bash
INJECT_MALFORMED_TURN=3 uv run eval/run_eval.py h1 --task fix_bug
```

```bash
INJECT_MALFORMED_TURN=3 uv run eval/run_eval.py h2 --task fix_bug
```

The first corrupts the model's tool call on turn 3, the way a call cut off
at the model's output limit looks: h1 crashes (`the harness crashed
(JSONDecodeError ...)`), h2 prints `↻ ... malformed tool call`, carries
on and solves it.

```bash
TRANSCRIPT_CHAR_BUDGET=4000 uv run eval/run_eval.py h2 --task bug_hunt
```

This lowers the compaction budget to 4,000 characters. In our run, the
`fired` column showed `✂✂` on turns 6 to 11, `added` went negative on
turns 7, 8 and 11 (the conversation got smaller), and `cached` fell from
64% to 10% on turn 7: compaction changes the start of the conversation,
so the provider's cache no longer matches it.

**5. Do h3's notes earn their place?** Runs h3 with and without the notes,
everything else identical:

```bash
uv run eval/ablation.py --runs 1 --task refactor_v2
```

Two more long runs. Two more long runs. We ran three of each, and
the notes made no measurable difference (see "What the ablation found"
below). Predict the direction before you look.

**6. Run h1 on the long task.** Your Block 2 harness with 40 turns
instead of 20:

```bash
uv run eval/run_eval.py h1 --task refactor_v2
```

It will probably finish this time. Watch what finishing costs.

**7. Does telling the agent its budget help?** Block 2's scoreboard said
"4 turns left, and nothing is tracking how much work remains", and no
harness here tells the model its budget either. `TURN_NOTICE` makes h2 add
one line to the end of a turn's last tool result, e.g. `[harness] turn 12
of 40 used: 28 left.`, which the model reads on its next call. It's
appended at the end, so the start of the conversation, and the provider's
cache, never changes.
- `TURN_NOTICE=every`: after every turn. Recorded as `h2_managed+turns`.
- `TURN_NOTICE=20,30,36`: only after those turns (here 50%, 75% and 90% of
  the budget). Recorded as `h2_managed+turns@20,30,36`.

```bash
TURN_NOTICE=every uv run eval/run_eval.py h2 --task refactor_v2
```

Our first try, 3 runs each, all solved:

| | Plain h2 | With the notice |
|---|---|---|
| Turns | 23, 25, 34 (median 25) | 20, 21, 28 (median 21) |
| Tokens sent | 500k, 590k, 778k (median 590k) | 398k, 445k, 667k (median 445k) |
| First file written | turn 11, 12, 20 | turn 7, 8, 10 |

The medians point the right way, but the ranges overlap: the worst notice
run did worse than two plain ones. The steadiest signal is that it starts
writing sooner. The agent never once mentioned the budget, so if the
notice changes its behavior, it does so silently: only measuring tells
you. Late warnings like `20,30,36` would rarely fire on a 40-turn budget;
they matter more on a tight one, where they might turn "ran out" into
"finished", or make the agent rush and skip its tests.

## How the protections behave

### When compaction fires

Compaction triggers on a threshold, and once a run crosses it, it keeps
crossing on every later turn: you get none, or a lot. In our runs it fired
in most long h2 runs (dropping 9, 13 and 40 old results in three of them)
and not at all in one that finished early. If yours shows none, that's
data, not a broken setup; step 4 shows it working.

### When compaction costs turns

In one of our h2 runs, compaction started on turn 14 while the agent was
still reading (about 144 reads in, nothing written yet). It kept dropping
files the agent had just read, the placeholder told it to re-run the tool
if it needed them, and it re-read 18 of them. Its first edit came on turn
20, and it finished on 34. Our other h2 runs re-read nothing; when
compaction fired late, it cost no extra turns. So compaction saves tokens
per turn, but when it drops something the agent still needs, the run gets
longer. Keeping state that survives compaction is what h3's notes are for.

### "Why 6,000 and 80,000? Why not more, or less?"

Neither number is derived from first principles; both are knobs.

- **6,000 characters per tool result** was a starting value, and it lands
  in a sensible place for this task: only 1 of the 149 files is longer
  (the median is 470), so reading files is essentially never cut, while
  the bulk outputs (searches across the codebase, long tracebacks) are.
- **80,000 characters for compaction** was tuned. It started at 200,000,
  and at that size compaction never fired on this task, because the
  conversation never got that big. It was lowered so it would. (It counts
  messages and tool results, not the files the agent writes, so the real
  conversation is somewhat bigger when it fires.)

| Knob | Lower | Higher |
|---|---|---|
| Tool-output cap | Saves more, but cuts things the agent needed, so it re-runs tools to get them back | Cuts less, saves less |
| Compaction budget | Compacts sooner, but drops results it may need again, and every compaction breaks the provider's cache | May never fire |

The right values depend on your tools' output sizes and how long your
tasks run: a harness's defaults were tuned for someone's workload.
Production harnesses usually tie compaction to the model's context window
rather than a fixed character count. `TRANSCRIPT_CHAR_BUDGET` lets you try
a different budget (step 4).

### "Doesn't truncating a big file hurt?"

What the model receives is the first 4,000 characters, the last 1,500,
and a marker between them: `... [harness truncated 1,641 chars] ...`. It
is *told* material was removed, so it can search or re-read for the rest.
Silent truncation would be the dangerous design.

On this task it doesn't matter, and it's worth checking why rather than
assuming: only one of the 149 files exceeds 6,000 characters
(`pyledger/integrations/registry.py`, 7,141), and it contains none of the
fourteen v1 names. What actually gets cut is `search` output. On a
codebase of large files, where the change sits mid-file and the agent
doesn't think to search, head-and-tail truncation would bite.

Production harnesses tend to **paginate** instead. Claude Code's `Read`
tool takes `offset` and `limit`; per its documentation, a read past the
token limit "returns the first page with a `PARTIAL view` notice that
tells Claude how much of the file it received and how to read more with
`offset` and `limit`." Both h2 and Claude Code tell the model it's seeing
part of the result; the difference is the way back. h2 says *the middle is
gone, re-run the tool*; pagination says *here's page one, ask for page
two*. ([Claude Code tools reference](https://code.claude.com/docs/en/tools-reference),
checked Sep 2026; re-check before quoting.)

### Recovery has two halves

Catching the parse error is the obvious half. The other: the malformed
arguments are also in the assistant message the harness already added to
the conversation. Leave them there and the next request sends invalid JSON
back to the provider, which rejects the whole request (`400 Invalid JSON
in tool call arguments`), one turn *after* recovery seemed to work. h2 and
h3 clean the stored copy too. This was a real bug in this repo, found by
an attendee's run: our fault injection had corrupted only a local copy of
the arguments, so it simulated a failure that couldn't happen. **A test
that can't reproduce the real failure will still pass, convincingly.**

`uv run eval/demo_recovery.py` replays the same cut-off call through both
code paths offline, with no API calls.

## How scoring works

- Every run copies the task to `results/runs/<harness>__<task>__<time>/`,
  so runs never touch the repo or each other.
- Before copying, the runner checks that the task is untouched: its tests
  still fail, and no file differs from git. A run on a task an agent
  already worked on would measure a head start.
- Solved means **pytest passes on the workspace afterwards**. The agent's
  own report is never consulted.
- Green tests are this exercise's definition of done, not proof the code
  is correct. At work, a passing checker tells you the agent met *your*
  bar, so how good that bar is matters as much as which harness you pick.
- `results/results.jsonl` keeps every run, with its model and provider;
  `compare.py` shows the latest per harness and task, and warns if the rows
  came from different setups.
- One run proves little. The same harness on the same task varies a lot
  from run to run (our h2 runs ranged from 19 to 34 turns), so treat a
  single difference as a direction, not a size.
- h2 changes three things at once, so h2 against Block 2 compares two
  configurations; it can't say which protection earned the difference.
  The ablation (step 5) is how you'd isolate one.

## Starting over

```bash
uv run ../scripts/reset.py && uv run ../scripts/check_fixtures.py
```

`reset.py` restores every task to its committed state, clears the run
copies, and archives (doesn't delete) your score table.
`check_fixtures.py` changes nothing: it confirms every task is untouched
and every reference copy passes.

## Discussion (10 min)

**For the group:**

1. Compare your Block 2 run with h2 on the same task. Where did the
   difference come from? Find the turn that made it, and say how much of
   it you'd credit to the harness and how much to how the run went.
2. h3 adds durable notes, a capability production harnesses
   ship. On this task they made no measurable difference. How would you
   have found that out without running it? And if the answer is "you
   wouldn't," what does that say about choosing a harness from a feature
   list?
3. **Would this matter for your own agent?** If so, what would you need a
   harness to do about it, and how would you test that it does? Write your
   answer down: Block 5's worksheet starts from these notes.

**More to think about, on your own or afterwards:**

- Which of h2's three protections did the work in your run? Read the
  `fired` column and `not re-sent` before answering.
- What would have to be true of a workload for h3's notes to pay off?
  Describe a task at your job that has that shape.
- h3's write guardrail never fired: the model never tried to edit the
  tests. Is it therefore worthless? (Consider what you could claim about
  the runs nobody inspected.)

These five protections are a small subset of what production harnesses
ship. Block 4: what the professionals decided for you.

## What the ablation found

Three runs each on `refactor_v2`, everything identical except the notes:

| | Solved | Turns | Tokens sent | Compaction | Re-reads |
|---|---|---|---|---|---|
| `h3_full` (notes) | 3 of 3 | 17, 21, 30 | 365k, 459k, 702k (median 459k) | in 2 of 3 runs | 0 |
| `h3_no_notes` | 3 of 3 | 16, 18, 26 | 187k, 357k, 492k (median 357k) | never | 0 |

**On this task, the notes bought nothing measurable.** The runs without
them were, if anything, cheaper, but the ranges overlap, so three runs each
can't say more than "no benefit."

The re-read column explains it. Notes are meant to spare the agent from
re-fetching what compaction dropped, and no run in either arm re-read a
single file. This migration is read once, transform, done: nothing sends
the agent back for something it already had, so the notes had nothing to
preserve. (Compare the h2 run in "When compaction costs turns", which did
go back, 18 times.)

Two things to take from that:

- **A capability's value is a property of your workload, not of the
  feature list.** Durable memory is a good feature, and production
  harnesses ship it. It did nothing here because this workload doesn't
  produce the failure it prevents.
- **We only know that because we measured it.** A plausible mechanism that
  every vendor ships is not a result.

Raw rows: `ablation_results.jsonl`. Reproduce with
`uv run eval/ablation.py --runs 3 --task refactor_v2` (six long runs).

## Where these ideas come from

Each protection here is a scaled-down version of something production
harnesses ship.

**Durable working notes (h3).** Agent-maintained notes that live outside
the conversation and survive compaction are widespread:

- Claude Code and the Claude Agent SDK load `CLAUDE.md` and `.claude/`
  memory automatically each session
  ([Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview)).
- Deep Agents ships a `write_todos` planning tool plus persistent
  `AGENTS.md` memory
  ([docs](https://docs.langchain.com/oss/python/deepagents/overview)).
- Pydantic AI's Harness package includes persistent notebooks with search
  ([docs](https://pydantic.dev/docs/ai/harness/)).

One difference: production systems almost always keep these notes in
**files**. h3 pins them as a message instead, because a file has to be
read to be useful and the model may not think to read it, while a pinned
message is in front of it every turn. That trade is right at a few hundred
characters of notes and wrong at 50,000, a good question to carry into
Block 4, where the file-based harnesses make the opposite call.

**Context compaction and tool-output limits (h2).** Every production
harness manages context somehow: Claude Code compacts automatically, Deep
Agents uses summarization middleware, Pydantic AI offers compaction as an
opt-in capability. h2 uses the simplest version, dropping the oldest tool
results, so the mechanism fits in a dozen readable lines. Its lossiness is
deliberate, and it's the gap h3's notes fill.

That these patterns are common is well documented. That they *help on
your workload* is not something to take on faith, including from us:
measure it on your own tasks.
