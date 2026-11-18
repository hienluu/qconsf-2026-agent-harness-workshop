# Block 5: The Decision Framework

> **In this block (20 min)**
>
> | Part | Time | What happens |
> |---|---|---|
> | Intro | 3 min | The presenter recaps what Blocks 2 to 4 showed |
> | Worksheet | 12 min | Your agent, questions 1 and 2 of [`WORKSHEET.md`](WORKSHEET.md), then decide |
> | Pairs | 5 min | Swap worksheets and challenge each other's answers |
>
> **If you finish early:** questions 3 and 4. They rule nothing out, but
> they list what stays your job whichever harness you pick. The pair
> discussion starts on time. "Discussion" and the take-home come in the
> workshop's conclusion, right after this block.

You've built a harness, measured what its protections buy, and run
production harnesses on the same task. This block turns that into a
decision for an agent you actually own. The worksheet doesn't rank
harnesses. It rules them out against your constraints, then lists what
stays your job whichever you pick. Every question traces back to
something you measured in Blocks 2 to 4. No code.

## What the last three blocks showed

The worksheet rests on these, and on nothing a feature list says:

- **On the same tools, the loop barely matters.** OpenAI Agents and the
  Claude Agent SDK, on our four file tools, ran the same algorithm as
  your h2, in the same turn and token ranges (Block 4).
- **The tools set the strategy and the cost.** A tool designed for the
  job cut calls three to eight times; a shell, more than ten. A harness's
  own tools carry its style of work: Claude Code's `Edit` cost 2 to 4
  times the tokens on a bulk rename, and Deep Agents' defaults ran out of
  budget every time (Block 4).
- **Cost follows turns; latency follows output.** Every turn re-sends the
  conversation, so tokens sent track turns. Wall time tracks tokens
  written, which is why re-typing whole files is slow (Blocks 2 to 4).
- **Agents test at the end unless something pulls testing earlier.** A
  budget signal that showed the test status did (Block 3).
- **Passing the tests isn't doing the job.** Two Block 4 runs changed a
  message the CLI prints and the tests didn't notice. A Block 3 run
  aliased the old names, left 70 files on the old API, and was the
  cheapest 20-turn run we had (Blocks 3 and 4).
- **The settings that let an agent run unattended also let it reach
  further.** Permission prompts off, virtual paths off, a shell on: each
  was our choice, and each widened what it could touch (Blocks 3 and 4).

## Exercise

### Step 1: Your agent, through the worksheet (12 minutes)

Open [`WORKSHEET.md`](WORKSHEET.md) and pick an agent you're working on
or expect to build. Keep your notes from Blocks 2 to 4 next to it.

| Part | Time |
|---|---|
| Your agent: what it does, which model it uses | 2 min |
| Questions 1 and 2, which can rule a harness out | 4 min |
| Decide: adopt, extend, drop down a level, or build. One sentence you'd defend in a design review, with a number you have or will measure, and how you'd test it | 6 min |
| Questions 3 and 4, your job whichever you pick | if you finish early |

Stuck? The worked examples below answer every question for two very
different agents, and [`WHY.md`](WHY.md) gives the reasoning behind each
question.

### Step 2: Pairs (5 minutes)

Swap worksheets with your neighbor and push on their answers in this
order. Five minutes covers the first two:

1. **The test.** Would it catch a run that passed every check and still
   did the wrong job, like the alias shortcut? This is the question that
   changes worksheets.
2. **The design-review sentence.** What number would change their mind?
   If they don't have one yet, what will they measure, and what value
   would make them look again?
3. **The eliminations.** If they crossed a harness out, is the
   constraint real or a preference?

## Two worked examples

Same worksheet, two agents, two different answers.

### A: a code-migration agent

*Moves a service from a deprecated internal API to its replacement,
across a few hundred files, until the tests pass. Close to the
workshop's task.*

Dozens of model calls per run, with big tool results (whole files,
searches, test logs). One provider now, maybe a cheaper model later.
Fails today by running out of budget mid-job, and by finishing green
with the wrong result.

| Question | Answer | What it means |
|---|---|---|
| 1. Model and code | provider: maybe; a standalone tool | nothing ruled out, though vendor-built harnesses needed workarounds off their home models |
| 2. What to add | test after each batch, review the diff after green, never write to `tests/`. Built-in tools **don't fit** | all five can plug those steps in. Design a tool around the unit of work (one rename rule), as in Block 4's step 4, and check whether the harness runs a turn's calls at once: if so, a tool that writes files needs a lock |
| 3. Reach | the code it runs (the tests) | sandbox the test runner; with a shell, the guardrail moves to the sandbox |
| 4. Watch | a large conversation; test timing, files rewritten unread, every tool call | learn how your choice keeps the conversation from growing; build the "what the trace shows" line in from day one |

**Decision: extend.** A harness with plug-in points (OpenAI Agents or
Pydantic AI), your own designed tools, a test-after-each-batch rule and
a review step after green.

*Design review:* "OpenAI Agents with our own rename tool, which takes a
lock because the SDK runs a turn's calls at once, plus a review step
after the tests pass, because passing tests once let a wrong migration
through. On our migration the tool cut calls from 278–315 to 35–88 per
run. We'd revisit if another harness matched that on the same test."

*Test it:* five runs of a real past migration, same prompt and budget,
each compared with the migration a person actually did.

### B: a refund support agent

*Reads a customer's request, looks up the order, checks the refund
policy, issues the refund and emails the customer.*

Under ten model calls per run, with small tool results (an order record,
a policy paragraph). A cheap model now, and the team expects to switch
providers as prices move. Fails by refunding the wrong amount, or by
issuing one that needed a person's sign-off.

| Question | Answer | What it means |
|---|---|---|
| 1. Model and code | provider: **will switch**; goes into an existing Python service | vendor-built harnesses drop to second choice: off their home models, Claude's SDK needed Bearer auth, OpenAI's an explicit model object, ADK needed LiteLLM. Pydantic AI and Deep Agents needed nothing. Install the candidate into the service first |
| 2. What to add | a person approves refunds over $500, never retry a payment, strip card numbers from results. Built-in tools **irrelevant** | every harness has an approval hook: OpenAI Agents `needs_approval`, Pydantic AI `requires_approval`, Deep Agents `interrupt_on`, Claude Agent SDK `can_use_tool`, ADK `before_tool_callback`; if approval can wait a day, check how the run is saved. You write the order and refund tools anyway, so built-in file tools and a shell are cost, not value |
| 3. Reach | money and customers; no files, no shell | put the guardrail inside the refund tool (a cap, an idempotency key), where Block 4 showed it's exact |
| 4. Watch | a small conversation; every tool call with its arguments, cost per step | compaction will never fire, so a lighter harness costs less on every call. Pydantic AI can cap a run on estimated cost, but the estimate was empty through our provider: check yours |

**Decision: adopt.** A light, provider-neutral harness (Pydantic AI) used
as is. The approval is a built-in flag on the refund tool; the no-retry
rule and card-number stripping live in the tools you write anyway.

*Design review:* "Pydantic AI, because our provider will change and it
takes the provider as a constructor argument, and approval is a flag on
the refund tool. Runs are under ten calls, so a heavier harness would
cost more for nothing. We'd revisit if runs grew past a few dozen
calls."

*Test it:* replay 50 past tickets and compare each refund with what the
support team actually did.

**Same worksheet, different answers.** For A the tools are the job, so
you extend the harness and design them. For B the tools are yours either
way and the conversation is small, so the lightest harness that won't
tie you to a provider wins. Neither came down to a feature list: all
five harnesses tick every box.

## Discussion (in the conclusion, after this block)

1. **Did you end up adopting or extending,** and what tipped it?
2. **What's still your job no matter which harness you pick,** and who on
   your team owns it today?
3. **What would you measure first** on your own agent, now that you've
   seen what a run's trace can show?

## After the workshop

To test your choice on your own task, using this repo as the testbed:
see [`AFTER_THE_WORKSHOP.md`](AFTER_THE_WORKSHOP.md).
