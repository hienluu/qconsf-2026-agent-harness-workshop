# Block 3 — Measure It

**Why this block:** sooner or later your team picks a harness — adopts
one, extends one, or defends the one it already has — and that argument
needs numbers. Published benchmark scores can't supply them: a score is
measured inside the vendor's harness and moves when that harness changes.
Block 1's page has a case where the same model scored 62.7% and 99.9% on
one benchmark with nothing different but the harness running it. Those
numbers describe the vendor's setup, not yours. The ones you can act on
come from running your own tasks through the candidate harnesses and
checking the result with something other than the agent's own report.
That's this block, at a size where every moving part is visible.

Block 2 gave you one data point: one harness, one task, one run. This is
the controlled version — hold the model, the tasks and the tools fixed,
change only the harness, and record what each run costs. Turns and input
tokens are the numbers that carry the argument; wall-clock is in the table
too, but at this scale it's mostly provider latency, so don't rank on it
(there's a section below on why). You leave with a table you could put in
front of your team, and a method you can point at your own tasks.

Three harnesses, each a small readable diff on the one before it:

- **`h1_naive`** — the harness you built in Block 2. Same code path, with
  one deliberate difference: a 40-turn budget instead of 20, so the
  comparison is decided by the protections rather than by the turn cap.
- **`h2_managed`** — h1 plus three context and error protections.
- **`h3_full`** — h2 plus two things every production harness ships:
  durable notes the agent maintains itself, and a guardrail making
  `tests/` read-only.

**h3 is a question, not an upgrade.** h2's protections are mechanical, so
its savings are near-guaranteed. h3's notes are only *offered* — the model
decides whether to use them, and when. We ran the ablation (three runs
with notes, three with the capability removed, nothing else changed) and
measured a ~2% median difference with overlapping ranges: no benefit on
this task. The guardrail never fired either — the model never tried to
edit the tests. "What the ablation found" below has the numbers and the
reason. If your h3 run lands worse than h2, that's the finding, not a
mistake.

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

Five tasks are available here. Each is a small codebase with a test suite,
and "solved" always means the same thing: **pytest exits green afterward**
(the agent is never asked whether it succeeded).

| task | the agent must... | horizon | where you've seen it |
|---|---|---|---|
| `fix_bug` | find and fix an off-by-one in a stats module (1 file, 4 tests) | short — a few turns | Block 2, step 3 |
| `add_function` | implement a missing `slugify` from its 5 tests | short | Block 2, optional |
| `small_rename` | rename two legacy functions across 2 files | short | Block 2, optional |
| `bug_hunt` | diagnose three interacting bugs in an 8-module pricing package (18 tests, 5 failing) | medium | new here; it's Block 4's task |
| `refactor_v2` | migrate a ~150-file bookkeeping library to its v2 API using an *incomplete* changelog, 35 tests | long — sized past a naive harness's design limits | Block 2, step 4 |

The exercise below uses `refactor_v2` throughout, because the long horizon
is where harness differences show. Any task works with `--task <name>` if
you want to see how the three harnesses behave on a smaller job.

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

**Before you start:** the required runs are h2 once and the h3 ablation
pair — three long runs, about 3–5 minutes and $0.50–1.50 each. The h1
baseline ships as a reference row in the table, so you only run it if you
want your own number.

**One difference from Block 2 worth knowing up front:** these harnesses
get a 40-turn budget, not Block 2's 20. The budget is held constant and
deliberately generous across all three so the experiment measures the
protections rather than the turn cap. That means h1 may well *finish*
here, where it ran out of room in Block 2 — watch what it costs to do so.

1. **Measure what h2's protections buy.** Skim the three `[h2]`-marked
   blocks in `harnesses/h2_managed.py` first — tool results capped at 6k
   chars before the model sees them, malformed calls returned as
   recoverable errors, old tool outputs dropped past a budget. Everything
   unmarked is identical to h1. Then run it:
   ```
   uv run eval/run_eval.py h2 --task refactor_v2
   ```
   Watch two things in the live output: the yellow
   `compaction: dropped N old tool output(s)` lines, and the scoreboard's
   transcript column immediately after one — that number going *down* is
   the harness reclaiming context mid-run.

   The table already carries an `h1_naive` row marked **reference**: our
   measurement of the harness you built, on this same task. Compare
   against it. Across four of our runs h2 came in about 35% cheaper in
   input tokens, and your number should land in the same neighbourhood.

2. **Then test a capability that might not be worth anything.** h3 adds
   two things to h2: durable working notes the agent can write via an
   `update_notes` tool, and a guardrail making `tests/` read-only. Skim
   the `[h3]`-marked blocks, then run the ablation — the same harness
   twice, once with the notes capability and once with it removed:
   ```
   uv run eval/ablation.py --runs 1 --task refactor_v2
   ```
   That's two runs and a summary comparing turns, input tokens, and
   re-reads. **We ran three per arm and found no measurable difference**
   (~2% on the median, ranges overlapping). Before you look at your own
   numbers, predict which way it will go — then see "What the ablation
   found" below for why it turned out that way, and what it means for
   deciding whether a harness feature is worth adopting.

   Afterward, read what the agent chose to remember:
   ```
   cat results/runs/h3_full__refactor_v2__*/agent_notes.md   # newest run's notes
   ```

3. **Optional — run h1 yourself.** The reference row saves you the ~$1 and
   four minutes, but if you'd rather measure your own baseline:
   ```
   uv run eval/run_eval.py h1 --task refactor_v2
   ```
   Note it gets 40 turns here rather than Block 2's 20, so it will
   probably *finish* this time. Watch what finishing costs.

4. **Review the comparison table.** It prints automatically after every
   run, so by now you've watched it grow. To re-render it any time:
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

1. What did ~40 lines of harness (h1→h2) buy, in tokens and dollars — and
   which of h2's three protections did the work here? Check the
   `dropped_tool_outputs` and `malformed_calls` values before answering.
2. h3's durable notes bought nothing on this task, and the re-read counter
   says why. **What would have to be true of a workload for them to pay
   off?** Describe a task at your job that has that shape.
3. You just watched a capability that every major vendor ships fail to
   earn its place on one specific workload. How would you have found that
   out without running it — and if the answer is "you wouldn't," what does
   that imply about choosing a harness from a feature comparison?
4. h3's write guardrail never fired either: the model never tried to edit
   the tests. Is the guardrail therefore worthless? (Consider what you'd
   be able to claim about the runs nobody inspected.)
5. These five protections are a tiny subset of what production harnesses
   ship. Block 4: what the pros decided for you.

## What the ablation found

We ran it three times per arm on `refactor_v2`, everything identical
except the notes capability:

| arm | solved | turns (median) | input tokens (median) | re-reads |
|---|---|---|---|---|
| `h3_full` (notes) | 3/3 | 25–28 (25) | 539k–642k (**611k**) | **0** |
| `h3_no_notes` | 3/3 | 26–30 (26) | 607k–713k (**621k**) | **0** |

About 2% apart on the median, with ranges that overlap. **On this task,
durable notes bought nothing measurable.**

The diagnostic column explains it: **re-reads were zero in every run, in
both arms.** The claim notes are supposed to satisfy is that they spare
the agent from re-fetching what compaction dropped. That never happened,
because this task never asks the agent to go back. `refactor_v2` is a
read-once, write-once migration — survey the files, transform them, done.
Nothing sends it looking for something it already had, so memory had
nothing to preserve.

Two things worth taking from that, and they matter more than the number:

- **A capability's value is a property of your workload, not of the
  feature list.** Every production harness ships durable memory (see the
  citations below). It is a good feature. It did nothing here, because
  this workload doesn't produce the failure it prevents.
- **We only know that because we measured it.** The mechanism was
  plausible, the vendors all ship it, and our own earlier runs seemed to
  show a pattern — four uncontrolled runs suggested that *when* the agent
  wrote notes predicted cost. Six controlled runs said that spread was
  path variance. Plausible mechanism plus suggestive data is not a result.

This is the block's method applied to the block's own content, and it's
the reason Block 5's rubric starts from your tasks rather than a vendor's
capability matrix.

Raw rows: `ablation_results.jsonl`. Reproduce with
`uv run eval/ablation.py --runs 3 --task refactor_v2` (six runs, ~$6).

## Where these ideas come from

The three protections in h2 and the two in h3 aren't inventions for this
workshop — each is a scaled-down version of something production harnesses
ship. If you want to check the lineage yourself:

**Durable working notes (h3).** The general pattern — agent-maintained
notes that live outside the conversation and survive compaction — is
widespread:

- Claude Code and the Claude Agent SDK load `CLAUDE.md` and `.claude/`
  memory automatically each session
  ([Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview)).
- Deep Agents ships a `write_todos` planning tool plus persistent
  `AGENTS.md` memory
  ([docs](https://docs.langchain.com/oss/python/deepagents/overview)).
- Pydantic AI's Harness package includes persistent notebooks with search
  ([docs](https://pydantic.dev/docs/ai/harness/)).
- Community writeups converge on the same reasoning — markdown notes are
  durable, greppable, and survive a compaction:
  [structured scratchpads for coding agents](https://nikiforovall.blog/ai/2026/06/08/scratch.html),
  [agent-maintained durable notes](https://github.com/stubbedev/harness/issues/7),
  [AgentMemory](https://github.com/jayzeng/agentmemory).

One honest difference: production systems almost always keep these notes
in **files**. h3 pins them as an in-context message instead, because a
file has to be read to be useful and the model may not think to read it,
while a pinned message is in front of it on every turn. That trade is
right at ~900 characters of notes and wrong at 50,000 — which is a good
question to carry into Block 4, where the file-based harnesses make the
opposite call.

**Context compaction and tool-output limits (h2).** Every production
harness manages context somehow; the approaches differ. Claude Code
compacts automatically; Deep Agents uses summarization middleware;
Pydantic AI offers compaction as an opt-in capability. h2 uses the
simplest possible version — drop the oldest large tool outputs — so the
mechanism is readable in a dozen lines. The lossiness is deliberate, and
it's exactly the gap h3's notes then fill.

**A caveat worth keeping.** That these patterns are common is well
documented. That they *help on your workload* is not something to take on
faith — including from us. Across four runs of h3 during development, cost
ranged from 336k to 1,087k input tokens for the same task: when the agent
wrote its notes early it re-read far less, and when it treated them as an
end-of-run summary it didn't. That's the whole argument for measuring on
your own tasks rather than adopting a feature list.
