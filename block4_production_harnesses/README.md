# Block 4 — The Production Harnesses

**Why this block:** You wrote the loop, watched it die, and measured what
five protections were worth. These five frameworks made every one of those
decisions for you already — Claude Agent SDK, OpenAI Agents, Google ADK,
Deep Agents, Pydantic AI.

**All five solve the task**, on the same model. That's the design: hold the
outcome constant, and what's left to compare is what each one decided on
your behalf — who owns the loop, which tools you still had to write, what
you had to work around to use your own provider, and how much code it took.

Feature lists can't tell you any of that. Every one of them says memory,
tools, context management, guardrails. They only start to differ once
you've built those yourself, which you now have.

**What you leave with:** the ability to look at any agent framework and say
what it decides for you — plus a comparison you ran yourself instead of one
a vendor published. Block 5 turns that into a choice.

No code to write here. Six scripts, well under a minute each, and a table
that fills in as you go.

## The five harnesses (and one escape hatch)

Same task, same model, same provider key. The task is `bug_hunt`: a small
order-pricing package (8 modules, 18 tests, 5 failing) with three bugs that
interact. Real diagnosis rather than a typo hunt, and big enough that
differences in how each harness explores, plans and batches have room to
show.

You may have run this task once already — it's what Block 3's compaction
demo uses — but you were watching the harness then, not the bugs. Here they
are, so you can follow what the agents are doing. The agents get no such
help:

1. **One wrong line, wrong answers in two modules.**
   `discounts.percent_off` is `cents * pct // 100`. Integer division
   throws away the remainder, so 5% of a $1.50 item is 7.5¢ and the
   function returns **7¢ instead of 8¢**. `tax.py` calls that same helper
   to compute tax, so a single rounding mistake produces wrong numbers in
   two places that look unrelated from the test output.
2. **A bug that disappears whenever there's no discount.**
   `pricing.price_cart` computes `tax_cents(subtotal)` where it should be
   `tax_cents(taxable)` — customers get taxed on money the discount took
   off. On a cart with no coupon, `subtotal` and `taxable` are the same
   number, so that test passes. The passing test is a clue, not luck.
3. **A crash that has nothing to do with the other two.**
   `receipt.format_receipt` divides the subtotal by the item count to
   print an average, and nothing handles an empty cart. The resulting
   `ZeroDivisionError` lands at the top of the pytest output, so it's the
   first thing the agent sees and the least useful.

(The exact diffs live in `scripts/derive_bug_hunt.py`, which injects them
into the green reference; task details in
`../block2_naive_harness/tasks/medium/bug_hunt/TASK.md`.)

One runner script per harness, organized as three side-by-side comparisons:

| Comparison | Scripts |
|---|---|
| Kit vs composable | `google_adk/` · `pydantic_ai/` |
| Two roads to opinionated | `claude_agent_sdk/` · `openai_agents/` |
| Harness on a runtime | `deepagents/` · its escape hatch, `deepagents/langgraph_escape_hatch.py` |

Each `run.py` is ~100 lines, meant to be read as much as run — notice what
you had to write, what came free, and what the harness assumed about who
you are.

Setup: the usual `.env` plus `uv sync --group block4`, which installs all
five harnesses into one environment. Two notes baked into that sync, both
part of the lesson. First, getting ADK to share that environment took care.
ADK reaches non-Google models through LiteLLM, and LiteLLM 1.84 and later
require version 2 of the `openai` library, while OpenAI Agents requires
version 3. So we install LiteLLM directly and stay on 1.83.0, the last
release without that limit. ADK's own `[extensions]` bundle requires a newer
LiteLLM and couldn't share the environment at all. Second, the Claude Agent
SDK wheel bundles a compiled Claude Code CLI (~90MB download, ~190MB
installed), one more reason the sync happens at home, not on venue WiFi.

## Exercise flow

**Run every command in this section from the
`block4_production_harnesses/` directory** — the paths below are relative
to it, and they will fail from anywhere else:

```
cd block4_production_harnesses   # from the repo root
pwd                              # .../agent-harness-workshop/block4_production_harnesses
```

Every command on this page, including the reset script, runs from here —
nothing requires switching directories mid-exercise.

Every run prints a **harness receipt** — the things named above, measured
for that run, plus what the harness shipped that you didn't have to write.
Receipts accumulate, so after the sixth run the table on your screen is the
whole comparison, built from your runs rather than anyone's docs.

All six runs together cost well under $1. Between runs, spend sixty
seconds in the script you just ran on ONE question its receipt raised —
each docstring says what to look for.

0. **Start clean** (a few seconds, no API calls). You arrive here carrying
   state from Blocks 2 and 3, and two bits of it matter: the task fixtures
   must still be unsolved, and the receipts table should be empty so it
   ends up being *yours*.
   ```
   uv run ../scripts/check_fixtures.py   # expect: ALL FIXTURES OK
   rm -f runs/receipts.jsonl             # start the table empty
   ```
   `check_fixtures.py` only reads — it never changes anything. If it
   complains, run `uv run ../scripts/reset.py` and try again. Note that a
   full reset also archives your Block 3 score table (timestamped, not
   deleted), so run it only if you need it — Block 4 doesn't require it.

   This matters most for the extra credit at the bottom of this page:
   `fix_bug` is the one workspace Block 2 edits in place, so if you fixed
   it there it is already solved. The scripts refuse to run against a
   finished task rather than quietly reporting that every harness
   succeeded in one turn.

1. **Kit vs composable.** Run both, and compare their friction cells.
   Pydantic AI's says the provider is just a constructor argument; ADK's
   lists the LiteLLM setup it needed:
   ```
   uv run --group block4 google_adk/run.py
   ```

   ```
   uv run --group block4 pydantic_ai/run.py
   ```
2. **Two roads to an opinionated harness.** Claude's receipt will say
   "tools we wrote: 0" — go find the line that made that possible (there
   isn't one; that's the point). Then notice it also has the most
   provider friction: convenience and coupling, same row:
   ```
   uv run --group block4 claude_agent_sdk/run.py
   ```

   ```
   uv run --group block4 openai_agents/run.py
   ```
3. **A harness on a runtime, then the layer below it.** Watch
   "tools we wrote" jump from 1 to 4 when you drop from Deep Agents to
   bare LangGraph — the price of the escape hatch, as a number:
   ```
   uv run --group block4 deepagents/run.py
   ```

   ```
   uv run --group block4 deepagents/langgraph_escape_hatch.py
   ```
4. **Read `COMPARISON.md`** — the full comparison table — and argue with
   it against your receipts.
5. Presenter demo (watch, don't run — ~$1): `refactor_v2`, the task that
   killed the naive harness, through Claude Code's harness:
   ```
   uv run --group block4 presenter_demo/run.py
   ```
   The closing question: **did the professionals' harness beat our
   285-line h3?** Whatever the answer, it teaches — a big win shows what
   production harness engineering buys; anything else is the harness-model
   fit lesson from Block 1, live.

   For calibration, two live runs (Sep 2026, GLM-5.3) agree: SOLVED in
   17–19 turns with ~16–18 tool calls, against 22–38 turns (median 27) for
   our h3 across ten runs — roughly **1.5× fewer turns**. Wall-clock ran
   65–97s versus h3's 117–222s, but read that second: it is the column
   this page and Block 3 both tell you not to rank on, and quoting the
   wall-clock ratio instead of the turn ratio is how the "2–3× faster"
   claim that used to sit here got inflated. The tool profile is the real
   story: Bash-dominated, with a single Edit for a ~130-file migration. Both runs chose the same approach: survey the
   code via grep/cat, detect that MIGRATION.md is incomplete from the tests,
   then *write a word-boundary-regex rename script* and run it — followed
   by collateral-damage checks on display strings. Given a shell, the
   model stopped rewriting files and started scripting; the decisive
   advantage wasn't the loop or compaction but tool design changing which
   algorithm the model chose. (The same Bash tool is why production
   harnesses need sandboxing and permissions — we ran `bypassPermissions`
   on a disposable copy, deliberately.)

## Starting over

Two different things accumulate here, and you usually only want to clear
one of them.

**The receipts table.** Every run appends to `runs/receipts.jsonl`, and the
table shows the latest run per (harness, task). To start the table fresh
without touching anything else:

```
rm runs/receipts.jsonl                          # discard it
mv runs/receipts.jsonl runs/receipts.round1.jsonl   # or keep the round
```

**The task fixtures.** The tasks are fixtures: a bug that must still be
there. Each run works on its own copy under `runs/`, so the originals
normally stay clean — but Block 2 edits the `fix_bug` workspace *in place*,
so if you did Block 2 and then come here for the extra credit, that fixture
is already fixed. The scripts now refuse to run in that state rather than
quietly measuring a finished task. Both scripts run from this directory:

```
uv run ../scripts/reset.py          # restore the fixtures
uv run ../scripts/check_fixtures.py # confirm: ALL FIXTURES OK
```

**`reset.py`** restores every task workspace to its committed state
(including deleting files an agent created), clears the per-run copies
under `runs/`, and archives the Block 3 score table with a timestamp. It
also removes `runs/receipts.jsonl`, so it is the full start-over — use the
`rm`/`mv` above if you only want the table gone.

**`check_fixtures.py`** asserts each workspace's tests still *fail* — a
fixture that passes is a solved task, and measuring against it is
meaningless — and confirms the reference copies still pass.

Then rerun the exercise flow from step 1.

## Extra credit: the trivial task

Rerun any of the scripts against `fix_bug` — the one-line Block 2 bug you know
by heart:

```
BLOCK4_TASK=fix_bug uv run --group block4 pydantic_ai/run.py
```

Watch what happens to the receipts table: on a task with nothing to
differentiate on, the runs collapse toward the same few turns and
seconds. Differences between harnesses only show on work hard enough to
differ over — which is the
weight-vs-horizon question from Q1, run in the other direction.

## Debrief questions

1. Compare your wall-clock column with a neighbor's — the same script
   has measured 23.3s and 10.6s on back-to-back runs. Which receipt
   columns are noise on a 10-second task, and which are stable structural
   facts? (Then: the heavy Claude harness *did* dominate the long-horizon
   presenter demo. What experiment would you run to establish how harness
   weight relates to task horizon — and what would Block 3 say about
   sample size?)
2. Which harness required the least code — and what did that convenience
   cost in provider coupling?
3. Two harnesses needed an explicit workaround to run on our provider at
   all (Bearer auth for Claude's SDK, an explicit model object for
   OpenAI's). What does that predict about switching costs at your job?
4. ADK and OpenAI's SDK share an environment here only because we hold
   LiteLLM at an older release; ADK's convenient `[extensions]` install
   can't coexist with OpenAI Agents at all. How would your team have caught
   that before adopting both, and what happens the day you need a newer
   LiteLLM?
5. Every one of these solved the task. On what basis, then, would you
   actually choose? (That's Block 5.)
