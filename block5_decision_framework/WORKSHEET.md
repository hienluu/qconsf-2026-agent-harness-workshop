# Harness decision worksheet

On the same task, model and tools, three of Block 4's harnesses matched
the one you built. The other two cost more or ran out of budget, doing
exactly what they were designed to do. So the question isn't which one
*works*. It's which one fits your agent, and what you're signing up for
when you pick it.

## The goal

Pick an agent you're working on, or one you expect to build soon. By the
end of this worksheet, you'll have:

1. **A shortlist:** the harnesses that survive your real constraints.
2. **A decision:** adopt one as it is, extend one, drop down to a
   lower-level framework, or build your own.
3. **What's still your job:** the work no harness will do for you, like
   checking where it's allowed to write files.
4. **One sentence you could say in a design review** to defend your choice.
5. **A way to test your choice** on one real task, before your team builds
   on it.

It takes about ten minutes.

## How it works

**Start from your notes.** At the end of Blocks 2, 3 and 4 you wrote down
what would matter for your own agent, and how you'd test for it. Keep
those notes in front of you: Part 1 starts from them.

**Start from your agent, not from the list of harnesses.** A feature only
pays off when your workload needs it, and one you don't need still adds
tokens to every request.

**Rule options out instead of scoring them.** A weighted score turns a
judgement into one number, and the workshop showed again and again how
misleading single numbers are. Every feature list reads the same. What
actually separates harnesses is a constraint that rules one out, or a
default that doesn't fit your work.

**There are two kinds of question.**

- **Part 2: questions that rule harnesses out.** A "yes" (or a "no") makes
  some of them a poor fit.
- **Part 3: what's still your job.** These rule nothing out. They tell you
  what you'll have to build or check whichever harness you pick.

**Then decide (Part 4).** Your Part 2 answers point to one of four
outcomes: adopt, extend, drop down a level, or build.

```
Part 1              Part 2               Part 3                Part 4
describe your  ──►  rule harnesses  ──►  list what's still ──► decide, defend,
agent               out                  your job              and test
```

**About the evidence.** Each question includes what we saw, with the
versions pinned in `uv.lock` and one open model through a third-party
provider, not each vendor's own API (which is why the vendor-built
harnesses needed workarounds). Check it against your own versions and
provider.

---

## Part 1: Describe your agent

- **What does it do?** ______________________________________________
- **How many model calls does a typical run make?** Under ten, or dozens?
  ______________________________________________
- **What's the biggest thing its tools return?** A screen or two of text,
  or whole files, codebase searches and full logs?
  ______________________________________________
- **How does it fail today?** Or how do you expect it to?
  ______________________________________________
- **Which model provider(s)?** Now, and possibly next year.
  ______________________________________________

---

## Part 2: Questions that rule harnesses out

### Q1. Will you need to switch model providers?

**What we saw:** the harnesses built by model vendors were the hardest to
point at a different provider. Claude Agent SDK needed two workarounds and
OpenAI Agents needed one; Google ADK needed a separate library (LiteLLM)
to reach our provider at all. Pydantic AI and Deep Agents needed
nothing. And off its home model, OpenAI Agents lost its own shell tools:
our provider rejected one and never showed the other to the model.

**Your answer:** ☐ Yes  ☐ No  ☐ Not sure yet

**If yes:** a vendor-built harness will be expensive to leave. Work out
what moving off it would take, and decide now whether you'd pay that.

### Q2. Do you need to add your own steps to how the agent runs?

These are rules your system enforces regardless of what the model decides.
Some examples, grouped by when they happen:

**Before a tool runs**
- A person must approve anything irreversible, such as a deploy, a
  refund over $500, or an email to a customer
- Block any tool call that touches production or customer PII
- Stop the run once it has spent more than $5

**After a tool runs**
- Strip secrets or PII out of a tool's result before the model sees it
- Run the linter after every file write, whether or not the model asks
- Retry a flaky API three times with backoff, but never retry a payment

**Across the whole run**
- "Done" means the tests pass, not that the model says it's finished
- Tell the model how much budget it has left (Block 3's budget signal)
- Save progress so a run that crashes at step 40 resumes there instead of
  starting over
- Use a cheap model to explore and a stronger one to make the changes
- Pause for a sign-off that might take a day, then continue

**The test.** You wrote an agent loop in Block 2. For each step you need,
ask two questions:

> **Can you point to the line in your Block 2 loop where this would go?**
> If you can, you genuinely need it.
>
> **Does the harness you're considering let you plug code in at that point?**

| Step I need | Where it goes in my Block 2 loop | Can I plug in there? |
|---|---|---|
| | | |
| | | |
| | | |

**What we saw:** all five harnesses in Block 4 run the loop for you, and
all five let you plug in somewhere: OpenAI Agents through `RunHooks`,
Deep Agents through LangChain callbacks, Pydantic AI through an event
handler, Google ADK through callbacks and plugins, and Claude Agent SDK
through hooks at the events it defines: before and after each tool call,
before it compacts, when it's about to stop. What differs is how far in
you can reach: with Claude you get its events, and a step it has no event
for can't be added.

**If you can plug in where you need to:** that's *extend* (Part 4).
**If you can't:** you need to write the loop yourself. That's *drop down
a level*.

### Q3. Does it have to fit into an existing codebase?

**What we saw:** Google ADK and OpenAI Agents share an environment in this
repo, but only because we hold one library back: they need incompatible
versions of a library underneath both, and ADK's convenient install
option can't coexist with OpenAI Agents at all. We first wrote that up as
unavoidable. It wasn't, and we only found out by testing the exact
combination. (The details are in Block 4's `COMPARISON.md`.)

**Your answer:** ☐ Yes  ☐ No

**If yes:** install your candidate into your actual project, the way you'd
really install it, before you compare anything else. Then check which
library versions you've been held to, and why.

### Q4. Do the harness's own tools fit your work?

Some harnesses bring their own tools: file editing, a shell, subagents to
hand work to. Those tools encode a style of work, and on the wrong task
you pay for it.

**What we saw on the migration** (same model, prompt and turn cap):

- The four harnesses on **our** file tools, Claude's included, ran the
  same algorithm and landed in your h2's range.
- **The same Claude harness on its own tools** used Claude Code's `Edit`,
  which replaces one exact string at a time: right for most coding, wrong
  for a rename across 130 files. It made 200 to 380 edits and sent 2 to 4
  times the tokens.
- **Deep Agents** handed the work to a subagent that started from an empty
  context, and ran out of budget in all three runs. Not broken, just
  untuned: see Part 4.
- **Given a shell,** every harness stopped editing files and wrote a
  rename script: tool calls fell tenfold. A tool designed for renames cut
  them fivefold, and unlike the shell could still refuse to touch the
  tests.

**Your answer:** ☐ Its tools fit  ☐ I'd replace or tune them  ☐ Not sure yet

**How to find out:** run one representative task with its tools, and with
yours if you can swap them in. Compare tool calls and tokens, not just
whether it finished. If you'd replace its tools anyway, much of what you'd
adopt it for is gone.

---

## Part 3: What's still your job

These rule nothing out. They're the work you'll do whichever harness you
pick.

### Q5. Will the conversation get big?

The harness sends the whole conversation back to the model on every call,
so cost grows with the number of model calls and with how big the
conversation gets. You answered both in Part 1. As a rough guide: under
about ten calls is small, dozens is large; a screen of text per tool
result is small, whole files and full logs are large.

**What we saw:** on the small tasks (5 or 6 calls) the features for
managing a big conversation never fired, and our fuller harness cost
11–13% more for nothing. On the migration (25 to 36 calls, tool results
up to 22,000 characters) they fired every run. And it's model calls, not
tool calls, that drive cost: the shell cut tool calls tenfold but tokens
only 2 to 4 times, tracking the drop in model calls (20–25 against 26–46).

**How to find out:** log model calls and the largest tool result over a
few runs, or, before you've built it, estimate how many steps a person
would take and how much they'd read at once.

**Your answer:** ☐ Small  ☐ Large  ☐ It varies

**If small:** the features for managing a big conversation won't fire, and
a lighter harness costs less on every call.
**If large:** find out *how* your candidate keeps the conversation in
check, not just whether it does.

### Q6. What can it write, and what can it run?

**What we saw:**

- **Deep Agents** edited the original task files instead of its own copy,
  after we'd set `virtual_mode=False` (the default keeps paths inside the
  folder; "virtual" doesn't mean pretend files).
- **Claude Agent SDK** created a folder outside its workspace from a
  one-character path typo. With `bypassPermissions` on, nothing stopped it.
- **Running the tests means running code.** With its shell taken away,
  Claude wrote a rename script into an empty `conftest.py` and ran the
  tests to execute it. Any tool that runs code the agent can edit is a
  shell.
- **A shell gets past per-call guardrails.** One global `sed` renamed a
  function everywhere, a test file included. Block 3's guardrail checked
  each `write_file`; a shell command has no such checkpoint.

You'll change settings like these in production too, so the agent can
run unattended.

**Before it goes near production:**

☐ I know which settings I changed from the defaults, and why
☐ I know where its file tools can write with those settings
☐ I know which of its tools execute code, the test runner included
☐ I've asked it to write outside its folder and watched that get blocked

### Q7. When something goes wrong in production, what will you need to see?

You debug an agent from its trace, and each harness makes different
things easy or hard to see. Here's what we had to work for in Block 4:

- **What the model is actually sent.** Claude Agent SDK sent an *empty*
  system prompt until we set one: not ours, not Claude Code's. Check the
  prompt and tool descriptions that really go out.
- **Every tool call, with its arguments.** Deep Agents' own file tools
  didn't appear at all until we hooked into its callbacks: the plain trace
  showed 2 calls where the agent had made 15. And cutting arguments to 70
  characters hid the one field that explained a failure.
- **Which step it's on.** Every SDK counts "turns" its own way. Claude's
  streams one model response as several messages, so the obvious count
  said 500 for a run of 45, and its own `max_turns` didn't stop that run.
  Deep Agents' limit counts graph steps, and each subagent gets its own.
  To cap runs fairly we counted model calls ourselves.
- **What the model said between steps,** where a plan going wrong shows
  up first. In three of the five, the simple way to run it returns only
  the final answer.
- **Cost per step.** OpenAI Agents and ADK reported tokens for each model
  call. On our provider, Claude's SDK reported only the total.
- **What the harness did on its own.** Cutting a long result, dropping old
  history, refusing a malformed tool call, handing work to a subagent.
  These change what the model sees, so they belong in the trace.

**Check your candidate:**

| I need to see | Can my candidate show it? | How much code did it take? |
|---|---|---|
| What the model is actually sent | | |
| Every tool call, with arguments | | |
| Which step it's on | | |
| What the model said between steps | | |
| Cost per step | | |
| What the harness did on its own | | |

**Then:** build this trace while you're still evaluating, so you find
out what's hard to get before you choose, not during your first incident.

---

## Part 4: Decide

Use your Part 2 answers to pick one:

1. **Adopt:** a harness survives Q1–Q4 and does what you need as it is.
2. **Extend:** it survives, but you need steps it doesn't have (Q2) or its
   defaults don't fit your work (Q4), and you can change that. Deep
   Agents on the migration is the example: 0 of 3 with its defaults, 3 of
   3 after two documented settings, no subagent and one line of prompt:

   ```python
   register_harness_profile("openai", HarnessProfile(
       excluded_tools=frozenset({"task"}),
       general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False)))
   ```

   Finding out *what* to change was the work: it took reading the trace.
3. **Drop down a level:** you need to write the loop yourself, because you
   can't plug in where you need to. Use a lower-level framework such as
   LangGraph, under Deep Agents. Everything the harness shipped, from
   file tools to subagents, becomes yours to write.
4. **Build your own:** rarely the right call. Blocks 2 and 3 showed what
   it costs.

**Where I landed:** ☐ Adopt  ☐ Extend  ☐ Drop down a level  ☐ Build

**What's still my job (from Part 3):** _______________________________

**What I'd say in a design review, in one sentence:**

______________________________________________________________________

**How to test it:** run one real task from your own codebase through your
top two candidates, the way Block 4 did:

- the same model, the same prompt and the same budget for each;
- several runs, not one (one harness's turns ranged from 25 to 50 on
  the same task);
- judge by your own check, like the tests, never the agent's word;
- and read the traces, not just the verdicts: every finding above came
  from a trace.

Block 4's `run_all.py` and `common.py` are a starting point.
