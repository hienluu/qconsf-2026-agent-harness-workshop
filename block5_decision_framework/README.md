# Block 5: The Decision Framework

> **In this block (35 min)**
>
> | Part | Time | What happens |
> |---|---|---|
> | Intro | 5 min | The presenter recaps what Blocks 2 to 4 showed |
> | Worksheet | 15 min | You work through [`WORKSHEET.md`](WORKSHEET.md) for your own agent |
> | Pairs | 10 min | Swap worksheets and challenge each other's answers |
> | Wrap-up | 5 min | The take-home, and the questions under "Discussion" |
>
> **If you're behind:** do Parts 1, 2 and 4 of the worksheet and skip
> Part 3; it's the part that rules nothing out. The pair discussion starts
> on time.

You've built a harness, measured what its protections buy, and run five
production harnesses on the same task. Now the question the workshop is
named for: **which one should you choose for your agent?**

Not "which is best". The worksheet doesn't score harnesses; it rules them
out against your constraints, then lists what stays your job whichever
you pick. Every question in it comes from something you saw in Blocks 2
to 4. There's no code in this block.

## What the last three blocks showed

The worksheet stands on these. Each is something you measured, not
something a feature list says.

- **On the same tools, the loop barely matters.** OpenAI Agents and the
  Claude Agent SDK, given the same four file tools, ran the same
  algorithm with nearly the same numbers, in the range of the h2 you
  built (Blocks 3 and 4).
- **The tools decide the strategy and the cost.** One tool designed for
  the job cut the calls three to eight times. A shell cut them tenfold.
  A harness's own tools encode a style of work: Claude Code's `Edit`
  cost 2 to 4 times the tokens on a bulk rename, and Deep Agents' defaults
  ran out of budget every time until two settings fixed them (Block 4).
- **Cost follows turns; latency follows what the model writes.** Every
  turn re-sends the conversation, so tokens sent track turns. Wall time
  tracks tokens written, which is why re-typing whole files is slow
  (Blocks 2 to 4).
- **Agents test at the end unless something pulls testing earlier.**
  Most runs ran the tests once or twice, near the end. Cheap actions, a
  budget signal or a shell changed that (Blocks 3 and 4).
- **Passing the tests isn't doing the job.** Two Block 4 runs changed a
  message the CLI prints, and the tests couldn't tell. A Block 3 run
  "solved" the migration by adding aliases for the old names and left
  120 files unmigrated: the cheapest run on the board (Blocks 3 and 4).
- **The settings that let an agent run unattended are the ones that let
  it reach further.** Permission prompts off, virtual paths off, a shell
  on: each was ours to change, and each widened what it could touch
  (Blocks 3 and 4).

## Exercise

### Step 1: Your agent, through the worksheet (15 minutes)

Open [`WORKSHEET.md`](WORKSHEET.md) and pick an agent you're working on
or expect to build. Keep your notes from Blocks 2 to 4 in front of you.

| Part | What it does | Time |
|---|---|---|
| 1. Describe your agent | five short answers everything else refers back to | 3 min |
| 2. Questions that rule harnesses out (Q1 to Q4) | provider switching, your own steps, an existing codebase, whether its tools fit | 6 min |
| 3. What's still your job (Q5 to Q7) | conversation size, what it can write and run, what you'll need to see | 3 min |
| 4. Decide | adopt, extend, drop down a level, or build; one sentence for a design review; how you'd test it | 3 min |

Stuck on a question? The worked examples below answer every question for
two very different agents.

### Step 2: Pairs (10 minutes)

Swap worksheets with your neighbor. For each other's answer, push on
three things:

1. **The eliminations.** Which question ruled out a harness? Is that
   constraint real, or a preference?
2. **The design-review sentence.** What number would change your mind?
   ("Choose, extend or defend, with numbers": the promise from Block 1.)
3. **The test.** Would their test catch a run that passed every check and
   still did the wrong job, like the alias shortcut?

## Two worked examples

The same worksheet, two agents, two different answers.

### A: a code-migration agent

*Moves a service from a deprecated internal API to its replacement,
across a few hundred files, until the tests pass. Much like the
workshop's task.*

**Part 1.** Dozens of model calls per run. Big tool results: whole files,
codebase searches, test logs. Fails today by running out of budget mid-job,
and by finishing with green tests and a wrong result. One provider now,
possibly a cheaper model later.

| Question | Answer | What it means |
|---|---|---|
| Q1. Will you need to switch model providers? | maybe | not a hard rule-out; note that vendor-built harnesses needed workarounds off their home models |
| Q2. Do you need to add your own steps to how the agent runs? | yes: run the tests after each batch; review the diff after green; never write to `tests/` | all five can plug in; check each lands where you need it. Claude's hooks cover tool calls and stopping, which covers these three |
| Q3. Does it have to fit into an existing codebase? | no, a standalone tool | nothing ruled out |
| Q4. Do the harness's own tools fit your work? | **no** | file-at-a-time editing was the bottleneck; you'll design a tool around the unit of work (one rename rule), as in Block 4's step 4. A harness whose value is its built-in tools loses most of its value here |
| Q5. Will the conversation get big? | large | you need truncation and compaction; find out how your choice does them |
| Q6. What can it write, and what can it run? | it writes code and runs the tests, so it runs code | sandbox the test runner; with a shell, the guardrail moves to the sandbox |
| Q7. When something goes wrong, what will you need to see? | test timing, files rewritten unread, every tool call | the "what the trace shows" line, built in from day one |

**Decision: extend.** A harness with plug-in points (here, OpenAI Agents
or Pydantic AI), your own designed tools, a test-after-each-batch rule
and a review step after green.

*Design review:* "We use OpenAI Agents with our own rename tool and a
review step after the tests pass, because on our migration the tools,
not the loop, set the cost, and the review step is what catches green
runs that are wrong."

*Test it:* five runs of a real past migration, same prompt and budget,
each compared with the migration a person actually did.

### B: a refund support agent

*Reads a customer's request, looks up the order, checks the refund
policy, issues the refund and emails the customer.*

**Part 1.** Under ten model calls per run. Small tool results: an order
record, a policy paragraph. Fails by refunding the wrong amount, or a
refund that needed a person's sign-off. A cheap model now; the team
expects to switch providers as prices move.

| Question | Answer | What it means |
|---|---|---|
| Q1. Will you need to switch model providers? | **yes** | rules out the vendor-built harnesses as a first choice: Claude Agent SDK needed two workarounds off its home model, OpenAI Agents one. Pydantic AI and Deep Agents needed none |
| Q2. Do you need to add your own steps to how the agent runs? | yes: a person approves any refund over $500; never retry a payment; strip card numbers from tool results | approval rules nobody out: OpenAI Agents (`needs_approval`), Pydantic AI (`requires_approval`), Deep Agents (`interrupt_on`), Claude Agent SDK (`can_use_tool`), ADK (`before_tool_callback`). If an approval can wait a day, check how the run is saved meanwhile (Deep Agents takes a LangGraph checkpointer; Pydantic AI returns the pending calls as deferred requests) |
| Q3. Does it have to fit into an existing codebase? | yes, a Python service | install the candidate into the service first, the way you really would |
| Q4. Do the harness's own tools fit your work? | **irrelevant** | you write the order, policy and refund tools whatever you pick; a harness's file tools and shell are cost, not value. Claude Code's whole kit re-sent about 15,000 tokens of tool definitions on every call |
| Q5. Will the conversation get big? | small | compaction will never fire; a lighter harness costs less on every call |
| Q6. What can it write, and what can it run? | no files, no shell, but it moves money | put the guardrail inside the refund tool (a cap, an idempotency key), where Block 4 showed it's exact |
| Q7. When something goes wrong, what will you need to see? | every tool call with its arguments, cost per step | Pydantic AI reports cost per run (`RunUsage.cost`) |

**Decision: adopt.** A light, provider-neutral harness, here Pydantic AI,
used as it is, with the approval on the refund tool.

*Design review:* "We use Pydantic AI because our provider will change and
it takes the provider as a constructor argument; approval is a flag on
the refund tool, and the conversation is too small for anything heavier
to pay off."

*Test it:* replay 50 past tickets and compare each refund with what the
support team actually did.

**Same worksheet, different answers.** For A, the tools are the job, so
you extend and design them. For B, the tools are yours either way and
the conversation is small, so the lightest harness that won't lock you
to a provider wins. Neither came down to a feature list: all five
harnesses would have ticked every box.

## Take-home: test your choice on your own task

The worksheet ends with "how to test it". The repo is a testbed for that:

- **Your task in Block 3's runner.** Add your task under
  `block2_naive_harness/tasks/` (a workspace whose tests fail, committed
  to git, so the runner can tell it's clean) and an entry in
  `block3_measure/eval/tasks.py`, then run it through h2 and h3 the way
  you did in Block 3.
- **Your task through a production harness.** Block 4's scripts are each
  about 150 lines; copy the one closest to your candidate and point it at
  your task.
- **Read the traces, not the verdict.** The line after each verdict says
  when the agent ran the tests and whether it rewrote files it never
  read. If your task has one right answer, keep it, and compare against
  it the way `scripts/reference_check.py` does: passing tests is where
  checking starts.

## Discussion (5 min, in the wrap-up)

1. **Which question ruled out the most for you,** and was it the one you
   expected before the workshop?
2. **What's still your job no matter which harness you pick,** and who on
   your team owns it today?
3. **What would you measure first** on your own agent, now that you've
   seen what a run's trace can show?
