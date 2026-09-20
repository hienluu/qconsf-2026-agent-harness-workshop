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
tokens are the numbers that carry the argument. Wall-clock is recorded in
`results/results.jsonl` but deliberately kept out of the table: at this
scale it is mostly provider latency, and we watched one harness go from
23.3s to 10.6s on a rerun with nothing changed. You leave with a table you could put in
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

The exercise below opens on `fix_bug` — to establish what a harness costs
when the workload needs nothing from it — and then uses `refactor_v2` for
the rest, because the long horizon is where the differences appear. Running
both is the point: the same three harnesses give opposite verdicts on the
two tasks, and which task resembles your workload is the actual decision.
Any task works with `--task <name>`.

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

**Before you start:** the exercise is four steps — one cheap batch (three
short runs, ~30 seconds and a few cents together), then h2 and h3 on the
long task at about 3 minutes and $0.60 each, then reading the table. Call
it 8 minutes and $1.25. The h1 baseline on the long task ships as a
reference row so nobody pays to re-measure it, and the two optional steps
at the end add two more long runs if you want them.

**One difference from Block 2 worth knowing up front:** these harnesses
get a 40-turn budget, not Block 2's 20. The budget is held constant and
deliberately generous across all three so the experiment measures the
protections rather than the turn cap. That means h1 may well *finish*
here, where it ran out of room in Block 2 — watch what it costs to do so.

1. **Start cheap: find out what a harness costs when the workload needs
   nothing from it.** `fix_bug` is one file and four tests. No tool result
   comes near the 6k cap, the transcript never approaches the compaction
   budget, and there is nothing worth remembering between turns. Run all
   three harnesses against it:
   ```
   uv run eval/run_eval.py h1 h2 h3 --task fix_bug
   ```
   About 30 seconds and a few cents.

   The table that prints afterwards will also show an `h1_naive` /
   `refactor_v2` row you did not run, marked **not your run**. That is our
   measurement of the long task, shipped with the repo so nobody pays to
   re-measure a baseline. It lives outside `results.jsonl`, so `reset.py`
   never clears it. Every other row is yours.

   **Check the `turns` column before you compare anything.** This task takes
   the agent 5 or 6 turns depending on nothing you control, and a run that
   took one more turn costs roughly 25% more regardless of harness. If you
   compare a 6-turn h3 against a 5-turn h2 you will "measure" a 42% penalty
   that is mostly just the extra turn. That mistake — reading a cost
   difference without checking trajectory length — is the most common error
   in harness benchmarking, and it is why this table puts `turns` next to
   `input tokens`.

   So compare like with like. Our numbers, by turn count:

   | harness | 5 turns | 6 turns |
   |---|---|---|
   | h1_naive | 4,507 (n=3) | 5,256–5,288 (n=6) |
   | h2_managed | 4,507 (n=4) | 5,644–6,157 (n=2) |
   | h3_full | 4,992–5,514 (n=5) | 6,392–6,566 (n=2) |

   Two things to take from that grid. **h1 and h2 are identical to the
   byte** at 5 turns — every protection h2 adds is inert here, so on this
   workload h2 simply *is* h1, and forty lines of harness engineering bought
   exactly nothing. **h3 costs about 11% more at either turn count** for
   capability that never once engages: nothing to truncate, nothing to
   compact, nothing worth remembering. (Which part of h3 charges that 11%
   is a fair question; the optional ablation in step 5 isolates it.)

   If your three runs all landed on different turn counts, you cannot read
   the overhead off them directly — that is a real limitation of n=1, not a
   setup problem. Locate your runs in the grid above instead. Your
   facilitator may also collect the room's numbers, which gives you thirty
   samples of a cell instead of your one.

   **The takeaway, and it is the one Block 5 is built on:** a protection is
   worth whatever the pressure it relieves is worth, and capability you
   don't use is not free — you carry it on every turn. Characterise your
   workload first (how large are tool results, how long are trajectories,
   how does it fail), then choose a harness. Not the other way round.

   Now hold that conclusion loosely. The next step runs the same three
   harnesses against a task that *does* apply the pressure, and the verdict
   reverses.

2. **Measure what h2's protections buy.** Skim the three `[h2]`-marked
   blocks in `harnesses/h2_managed.py` first — tool results capped at 6k
   chars before the model sees them, malformed calls returned as
   recoverable errors, old tool outputs dropped past a budget. Everything
   unmarked is identical to h1. Then run it:
   ```
   uv run eval/run_eval.py h2 --task refactor_v2
   ```

   **What to expect, so you're not watching it blind:** 25–36 turns
   (typically around 26) and **2.5–4 minutes**. All nine of our h2 runs
   solved it. The scoreboard counts against a 40-turn budget, so a line
   reading `turn 26/40` is a comfortable finish rather than a near-miss —
   unlike Block 2, this harness is not expected to run out of room.

   Watch for the yellow `truncated <tool> output: N → M chars` lines — the
   cap doing its job on a big `search` result. Expect a handful.

   **Compaction is a coin flip here, and it is all-or-nothing.** Across ten
   h2 runs it fired in exactly one — and in that run it fired *fourteen
   times*. That shape is worth understanding: compaction triggers on a
   threshold (an 80,000-char transcript), and once a run crosses it, it
   keeps crossing on every subsequent turn. So you do not get "a little
   compaction" — you get none, or you get a lot. Our h3 runs show the same
   bimodality: six at zero, then 1, 17 and 49.

   Most of you will see zero, because h2 typically peaks just under budget
   (77,243 of 80,000 in one measured run). That is data, not a broken setup.
   If you'd rather see the mechanism than wait for luck, force it — the
   budget is an env override, and the short task is enough:

   ```
   TRANSCRIPT_CHAR_BUDGET=4000 uv run eval/run_eval.py h2 --task bug_hunt
   ```

   Six turns, about a cent. Watch the `✂ compaction: dropped N old tool
   output(s), freeing N chars` lines, then the scoreboard's transcript
   column on the very next line — in our run it fell from 6,898 to 3,414
   chars. That number going *down* mid-run is the harness reclaiming
   context, and it is the only place in the whole block where you see the
   conversation get *smaller*.

   The table already carries an `h1_naive` row marked **not your run**: our
   measurement of the harness you built, on this same task. Compare against
   it — and treat the comparison carefully, because across eight of our h2
   runs the gap to that reference ranged from **47% cheaper to 1% cheaper**.
   Median 38%. The cheapest run took 25 turns; the dearest took 36 and
   essentially erased the advantage.

   Turn count is most of that. But not all of it: three of our runs finished
   in exactly 25 turns and still cost 493k, 550k and 571k tokens — a 16%
   spread at identical length, driven by how many files the agent opened and
   how large they were.

   So **your run may land anywhere in that range, including no better than
   the reference, and that is a real result rather than a broken one.** The
   `not re-sent` column is the part genuinely attributable to the harness:
   10–22% of what the run would otherwise have sent across our h2 runs, 28%
   in the one instrumented h3 run. Everything beyond that is trajectory.
   "What it was actually worth" below has the numbers, and one more caveat
   worth holding onto: the reference row is a single h1 run, so this is a
   distribution being compared to a point.

3. **Then measure h3 — more capability, same task.** h3 adds two things to
   h2: durable working notes the agent maintains through an `update_notes`
   tool, and a guardrail making `tests/` read-only. Skim the `[h3]`-marked
   blocks, then run it:
   ```
   uv run eval/run_eval.py h3 --task refactor_v2
   ```

   **What to expect:** 22–38 turns (typically around 27) and **2–4
   minutes**; all nine of our h3 runs solved it. Note that range against
   h2's — h3 is the wider of the two, and that is the finding rather than
   noise in your run.

   Watch for the cyan `✎ update_notes` lines — the agent deciding what is
   worth remembering. The harness only *offers* that tool; whether and when
   the model uses it is part of the result.

   **Before the run finishes, write down your prediction:** will the more
   capable harness cost more or less than h2 did? Step 4 is where you find
   out, and the answer is not the one a feature comparison would give you.

   Afterward, read what the agent chose to remember:
   ```
   cat results/runs/h3_full__refactor_v2__*/agent_notes.md   # newest run's notes
   ```

   **What a good one looks like.** The notes are worth reading properly,
   because a strong run produces something you'd be happy to find in a
   colleague's scratch file. Things to look for in yours:

   - **Knowledge it had to derive.** `MIGRATION.md` documents 8 renames and
     says outright that it's incomplete. Good notes carry roughly 14 — the
     extra ones (`entries_by_account → entries_for`, `Entry.side →
     Entry.kind`, `balanced → is_balanced` and the dict key that follows
     from it, the CSV column order) were worked out from the test suite.
     That's the expensive knowledge on this task.
   - **Rules rather than logs.** The best line we've seen is *"8 families ×
     14 accounts, all follow exact templates verified by reading samples"* —
     112 of the workspace's files compressed into one rule plus how it was
     checked. A weaker run lists 112 checkboxes.
   - **Negative results.** `webhook.py: NO CHANGE`; these five modules have
     no v1 names. Knowing what you've ruled out is what stops you
     re-checking it.
   - **A work queue, not a summary** — checkboxes and a `Next:` line, written
     during the work rather than at the end.

   If yours is thinner than that, it isn't a broken run. Across ten of our
   h3 runs the notes ranged from **247 to 2,138 characters** — same harness,
   same task, same model. The harness offers the tool; how well the model
   uses it varies run to run, which is worth knowing if you were planning to
   depend on it.

   **What it costs.** Those notes are re-sent on every request. A 2,138-char
   set (~534 tokens) carried across 27 turns is about **14,400 tokens, 2.1%
   of that run**. Cheap — but it is charged on every turn whether or not the
   notes are ever needed.

   **And here is the tension worth sitting with.** That artifact looks
   obviously valuable. The measurements say it didn't pay: the ablation
   found ~2% with overlapping ranges. The reason is visible in your own
   run's `protections fired` column — if compaction never fired, nothing was
   ever dropped from the transcript, so the notes' stated purpose ("persist
   even when old tool output is dropped") never activated. Stronger still,
   our `h3_no_notes` runs that *did* compact hard — 16, 12 and 9 times —
   recorded **zero re-reads anyway**. This task never sends the agent back
   for something it already had, so memory had nothing to preserve.

   A capability can be well designed, well used, produce a genuinely good
   artifact, and still not earn its place on your workload. You cannot tell
   from the artifact. Only from the counterfactual — which is what step 5
   runs, if you want it.

4. **Read the table — this is the payoff, and it costs nothing more.** It
   prints after every run, so you've watched it grow. Re-render any time:
   ```
   uv run eval/compare.py
   ```
   You now have three `refactor_v2` rows and haven't run anything extra to
   get them: `h1_naive` (ours, marked *not your run*), `h2_managed` from step 2,
   `h3_full` from step 3. Two comparisons are sitting in them, and they
   behave very differently.

   **h2 vs h1 — the robust one.** Eight of our nine h2 runs came in below
   h1's *best* run, medians 33% apart. Expect your h2 row to be cheaper.
   Individual gaps in our runs ranged from 47% cheaper to 1% cheaper, so
   trust the direction and not the number.

   **h2 vs h3_full — the one that isn't robust, and the point of the
   block.** Note which way yours went. We ran this comparison twice:

   | | h2_managed | h3_full | conclusion |
   |---|---|---|---|
   | first pair | 540,541 (28 turns) | 961,713 (34 turns) | h3 costs **78% more** |
   | second pair | 633,845 (29 turns) | 608,488 (25 turns) | h3 costs **4% less** |
   | third pair | 696,526 (29 turns) | 691,073 (27 turns) | h3 costs **0.8% less** — a tie |

   Same harnesses, same task, same model, nothing changed between them.
   Whichever way your single run landed, someone else in the room got the
   opposite, and both of you have exactly the evidence a one-run benchmark
   provides.

   The third pair adds something the first two didn't. Those two runs
   finished within 0.8% of each other — yet the work their harnesses did was
   nothing alike. h2 truncated 8 times, compacted 14 times, and kept 1,091k
   characters off the wire (28% of what it would otherwise have sent). h3
   truncated 6 times, never compacted once, and kept 563k off (17%). One
   harness did nearly twice the context management of the other and they
   cost the same. **Protection activity and final cost are only loosely
   coupled** — which is exactly why the `not re-sent` column exists
   separately from `input tokens`, and why you should never infer one from
   the other. Across nine runs each, h3's spread is 3.23× against h2's 1.87×
   — so the more capable harness was also the less predictable one, which
   is often the property that decides an adoption argument.

   Now check your prediction from step 3. If you guessed that the harness
   with more capability would cost less, you had a 50/50 shot — which is
   the honest state of the evidence, and worth more than a tidy result.

   The method, not the numbers, is what you take to work: fix the model,
   fix the tasks, vary one thing, judge with an external checker, and run
   it enough times to know whether you're looking at a result or at noise.

**Steps 1–4 are the exercise.** Everything below is optional — worth doing
if you have time or want to push on a specific claim, and safe to skip
entirely. Both optional steps add a long run each; neither changes the
conclusions above, and both of their findings are written up further down
this page.

5. **Optional — the ablation: do the notes actually earn their place?**
   Steps 1 and 3 told you what h3 costs — about 11% more than h2 on the
   short task, and either more or less on the long one — but not which part
   of h3 is responsible. The ablation isolates one capability by running the
   same harness twice, once with the notes and once with them removed,
   everything else identical:
   ```
   uv run eval/ablation.py --runs 1 --task refactor_v2
   ```
   Two more long runs, and a summary comparing turns, input tokens and
   re-reads. **We ran three per arm and found no measurable difference**
   (~2% on the median, ranges overlapping). Predict the direction before
   you look, then read "What the ablation found" below for why it turned
   out that way — and for what it implies about adopting a harness feature
   on the strength of its description.

6. **Optional — run h1 on the long task yourself.** The reference row saves
   you ~$0.60 and three minutes, but if you'd rather measure your own
   baseline:
   ```
   uv run eval/run_eval.py h1 --task refactor_v2
   ```
   Note it gets 40 turns here rather than Block 2's 20, so it will probably
   *finish* this time. Watch what finishing costs.


## Watching the protections fire

h2 and h3 print a line every time one of their protections acts, so you can
watch the harness work instead of inferring it from a total at the end.
Two of the three show up on their own during `refactor_v2`:

```
✂  [h2_managed turn 6] truncated search output: 14,056 → 5,540 chars (model sees head + tail)
✂  [h3_full turn 14] compaction: dropped 5 old tool output(s), freeing 4,825 chars
```

**Tool-output limits (`✂ truncated`)** fire on this task and essentially
never on the short ones — a `search` across 149 files returns 13–22k
characters, while every tool result in `fix_bug` fits under the 6k cap.
That is worth sitting with: on a small task h2 and h1 are the same harness.
Protections are not free-floating virtues, they are responses to a
specific pressure, and if your workload never applies the pressure you are
paying complexity for nothing.

### "But what about a file bigger than 6k — doesn't truncating it hurt?"

The right question, and worth being precise about. What the model actually
receives is the first 4,000 characters, the last 1,500, and a marker
between them: `... [harness truncated 1,641 chars] ...`. It is *told* that
material was removed, so it can search or re-read for the rest. Silent
truncation would be the dangerous design — an agent reasoning confidently
about a file it only partly saw.

On this task the impact is measurably nil, for a reason worth checking
rather than assuming:

- **One of the 149 files exceeds 6k.** The median file is 470 characters.
  What actually gets truncated here is `search` output (13–22k) and
  `list_files` (6,360) — not file contents.
- That one file, `pyledger/integrations/registry.py` at 7,141 chars,
  contains **none of the fourteen v1 identifiers** — not in the visible
  head and tail, and not in the 1,641 hidden characters either. There was
  nothing in it for the agent to do.
- Every h2 and h3 run solved the task, with re-reads of 0 or 1.

So the honest claim is narrow: truncation didn't hurt *because this
workload never put anything important behind it*. Head-and-tail truncation
does lose information, and it would bite on a codebase of large files where
the change you need sits mid-file and the agent doesn't think to search.
Three things make it survivable in general — the marker, the fact that an
agent with `search` rarely needs whole files, and head/tail being chosen
because signal clusters at the ends. None of them is a guarantee.

**The part worth carrying into Block 4:** our 6k cap is deliberately the
naive answer. Production harnesses don't truncate file reads at all — they
*paginate* them. Claude Code's `Read` tool takes `offset` and `limit` and
returns a bounded number of lines per call, so a large file arrives in
chunks the agent asks for explicitly. Nothing is lost; the agent decides
how much to pull and can walk the file. Same pressure, better answer, more
engineering. h2 protects context by **discarding**; a production harness
protects it by **giving the agent control over what it pulls**. That
difference is most of what Block 4 is about.

**Compaction (`✂ compaction`)** only starts once the transcript passes its
80,000-char budget, so it is late-run or absent. How absent depends on the
harness, which surprised us when we counted:

| harness | runs on `refactor_v2` | runs where compaction fired |
|---|---|---|
| h2_managed | 9 | 1 |
| h3_full | 9 | 4 (17, 12, 1, 49 times) |
| h3_no_notes | 3 | 3 (9, 12, 16 times) |

h2 finishes with its transcript just under the budget — 77,243 of 80,000 in
one measured run, a 3.4% margin. h3 carries a pinned notes message and tends
to run longer, so it crosses. Two things follow. First, **a protection can
be correctly implemented and still never fire on your workload** — worth
knowing before you pay for one. Second, a threshold this close to the ceiling
is a coin flip, and a run that shows no compaction is data rather than a
broken setup.

If you'd rather see it work than take our word for it, `TRANSCRIPT_CHAR_BUDGET`
is an env override on both harnesses — the exercise flow above shows how to
make it fire for about a cent.

The `not re-sent` column in the comparison table is what these add up to.
It counts characters the harness kept off the wire, once for **every turn
they would otherwise have been re-sent** — a cut at turn 6 of a 28-turn run
is spared 22 times, because the entire transcript goes over the wire on
every single request. That compounding, not the one-time cut, is the whole
argument for context management.

### What it was actually worth — read this before you trust the totals

We ran the h2-vs-h3 comparison twice on `refactor_v2`. It gave opposite
answers:

| | h2_managed | h3_full | conclusion you'd draw |
|---|---|---|---|
| **first pair** | 540,541 (28 turns) | 961,713 (34 turns) | h3 costs **78% more** |
| **second pair** | 633,845 (29 turns) | 608,488 (25 turns) | h3 costs **4% less** |

Same harnesses, same task, same model, nothing changed between them. If you
run this comparison once — as you are about to — you will get a confident
answer, and it may be either of these. That is the single most useful thing
in this block.

Why it swings: cost is dominated by how many turns the agent takes, and
turn count is not a harness property. Cost also grows *faster* than turn
count, because each extra turn re-sends a transcript that the extra turns
themselves made longer. In the first pair 1.21× the turns produced 1.78×
the tokens.

Across nine runs of each on this task:

| harness | n | turns | input tokens | spread | attributable saving |
|---|---|---|---|---|---|
| h1_naive | 2 | 30–31 | 850,627–932,248 | 1.10× | — |
| h2_managed | 9 | 25–36 | 493,339–924,737 (med 593,102) | 1.87× | 10–22% (med 12%) |
| h3_full | 9 | 22–38 | 336,041–1,086,714 (med 642,091) | **3.23×** | 23–28% (med 26%) |

Three things fall out of that table, and none of them is "the better
harness won."

**The h2-over-h1 result is real; the percentage is not.** Eight of nine h2
runs came in below h1's *best* run, and the medians sit 33% apart. But
individual gaps ranged from 47% cheaper to 1% cheaper. Quote the direction,
not the number.

**Adding capability made the harness less predictable.** h3 has both the
best run on record (336k) and the worst (1,087k) — a 3.23× spread against
h2's 1.87×. If you are budgeting for a fleet, variance may matter more to
you than the median, and more capability did not buy less of it.

**Doing more work is not the same as costing less.** h3's context
management provably removed about twice as much from the wire as h2's
(26% vs 12% of what it would otherwise have sent), and h3's median run
still cost 8% *more* than h2's. Judge a mechanism by what it removed;
judge a harness by many runs.

The honest conclusion, and the one to carry into Block 5: **context
management measurably works, and on any single run it can be completely
buried by how long the agent wandered.** If you compare harnesses on total
tokens from one run each, you are mostly measuring trajectory luck. Judge
the mechanism by what it demonstrably removed, judge the harness on many
runs, and be suspicious of anyone — including this workshop — quoting a
percentage from a sample of one.

### The protection that doesn't fire on its own

The third one, malformed-call recovery, is tail-risk insurance rather than
something you'll usually watch happen (it triggered in roughly 1 of 4 naive
long runs during tuning). Two ways to see it anyway.

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

**Recovery has two halves, and the second one is easy to miss.** Catching
the parse error is the obvious half. The other half: the malformed
arguments are also sitting in the assistant message the harness already
appended to the transcript. Skip the bad call but leave that message
untouched and the next request ships invalid JSON back to the provider,
which rejects the *whole* request:

```
BadRequestError: Error code: 400 - {'message': 'Invalid JSON in tool call arguments'}
```

The run then dies one turn *after* the recovery appeared to work, which is
a genuinely confusing way to fail. h2 and h3 neutralise the stored copy
before continuing. This was a real bug in this repo, found by an attendee
run rather than by our own fault injection — the injection had been
corrupting only the local copy of the arguments, so it simulated a failure
that could not actually occur. Worth remembering when you write your own
fault injection: **a test that can't reproduce the real failure will still
pass, convincingly.**

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

1. On `fix_bug`, h1 and h2 produced **identical** token counts. On
   `refactor_v2`, h2 came in under h1 in eight of our nine runs. Same two
   harnesses, opposite verdicts. What changed — and how would you tell, in
   advance, which of those two situations your own workload is in?
2. What did ~40 lines of harness (h1→h2) buy on the long task, in tokens
   and dollars — and which of h2's three protections did the work? Read the
   `protections fired` and `not re-sent` columns before answering, and note
   that `not re-sent` is the only part of the gap you can actually
   attribute to the harness.
3. h3's durable notes bought nothing on this task, and the re-read counter
   says why. **What would have to be true of a workload for them to pay
   off?** Describe a task at your job that has that shape.
4. You just watched a capability that every major vendor ships fail to
   earn its place on one specific workload. How would you have found that
   out without running it — and if the answer is "you wouldn't," what does
   that imply about choosing a harness from a feature comparison?
5. h3's write guardrail never fired either: the model never tried to edit
   the tests. Is the guardrail therefore worthless? (Consider what you'd
   be able to claim about the runs nobody inspected.)
6. These five protections are a tiny subset of what production harnesses
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

Worse than nothing, in fact, once you look at the tasks where h3's extra
capabilities never engage at all. Comparing h2 and h3 at identical turn
counts on the small tasks:

| task | h2 median | h3 median | h3's overhead |
|---|---|---|---|
| `fix_bug` | 4,507 | 4,992 | **+10.8%** |
| `bug_hunt` | 11,900 | 13,490 | **+13.4%** |

Nothing fires: no truncation, no compaction, no notes worth keeping. The
difference is h3's notes instructions and pinned notes message riding along
in the transcript, re-sent every turn, earning nothing. **A capability you
don't use is not free — you pay for it on every request.** Which is the
real argument for sizing a harness to a workload rather than adopting the
most capable one available.

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
