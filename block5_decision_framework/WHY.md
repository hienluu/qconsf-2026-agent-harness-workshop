# Why these questions

The [worksheet](WORKSHEET.md) asks four questions. This page is the
reason for each one: what we saw in Blocks 2 to 4 that makes it matter.
Read it when a question doesn't seem to apply to you, or when someone in
a design review asks "why does that matter?"

**Start from your agent, not from the list of harnesses.** A feature only
pays off when your workload needs it, and one you don't need still adds
tokens to every request.

**Rule options out instead of scoring them.** A weighted score turns a
judgment into one number, and the workshop showed again and again how
misleading single numbers are. Every feature list reads the same. What
actually separates harnesses is a constraint that rules one out, or a
default that doesn't fit your work. Questions 1 and 2 can rule a harness
out; questions 3 and 4 rule nothing out, they list work you'll do
whichever you pick.

**About the evidence.** It comes from the versions pinned in `uv.lock`
and one open model through a third-party provider, not each vendor's own
API (which is why the vendor-built harnesses needed workarounds). Check
it against your own versions and provider.

## 1. Will it work with your model and your code?

### Your model provider

The harnesses built by model vendors were the hardest to point at a
different provider. Claude Agent SDK needed two workarounds and OpenAI
Agents one; Google ADK needed a separate library (LiteLLM) to reach our
provider at all. Pydantic AI and Deep Agents needed nothing. And off its
home model, OpenAI Agents lost its own shell tools: our provider rejected
one and never showed the other to the model.

If you'll switch providers, a vendor-built harness will be expensive to
leave. Work out what moving off it would take, and decide now whether
you'd pay that.

### Your project and its libraries

Google ADK and OpenAI Agents share an environment in this repo, but only
because we hold one library back: they need incompatible versions of a
library underneath both, and ADK's convenient install option can't
coexist with OpenAI Agents at all. We first wrote that up as
unavoidable. It wasn't, and we only found out by testing the exact
combination. (The details are in Block 4's `COMPARISON.md`.)

If it's going into an existing project, install your candidate into
that project, the way you'd really install it, before you compare
anything else. Then check which library versions you've been held to,
and why.

## 2. What will you need to add or change?

### Your own steps

These are rules your system enforces whatever the model decides. Some
examples, grouped by when they happen:

- **Before a tool runs:** a person approves anything irreversible (a
  deploy, a refund over $500, an email to a customer); block any call
  that touches production or customer data; stop once a run has spent $5.
- **After a tool runs:** strip secrets out of a result before the model
  sees it; run the linter after every file write; retry a flaky API with
  backoff, but never retry a payment.
- **Across the whole run:** "done" means the tests pass, not that the
  model says so; tell the model how much budget it has left (Block 3's
  budget signal); save progress so a crash at step 40 resumes there; use
  a cheap model to explore and a stronger one to make the changes; pause
  for a sign-off that might take a day.

**The test:** can you point to the line in your Block 2 loop where the
step would go? If you can, you need it. Then: does the harness let you
plug code in at that point?

All five harnesses run the loop for you, and all five let you plug in
somewhere: OpenAI Agents through `RunHooks`, Deep Agents through LangChain
callbacks, Pydantic AI through an event handler, Google ADK through
callbacks and plugins, and Claude Agent SDK through hooks at the events
it defines (before and after each tool call, before it compacts, when
it's about to stop). What differs is how far in you can reach: with
Claude you get its events, and a step it has no event for can't be
added. If you can plug in where you need to, that's **extend**. If you
can't, you'll write the loop yourself: **drop down a level**.

### Better tools

Some harnesses bring their own tools: file editing, a shell, subagents to
hand work to. Those tools encode a style of work, and on the wrong task
you pay for it. On the migration (same model, prompt and turn cap):

- The four harnesses on **our** file tools, Claude's included, ran the
  same algorithm and landed in your h2's range.
- **The same Claude harness on its own tools** used Claude Code's `Edit`,
  which replaces one exact string at a time: right for most coding, wrong
  for a rename across 130 files. It made 200 to 380 edits and sent 2 to 4
  times the tokens.
- **Deep Agents** handed the work to a subagent that started from an
  empty context, and ran out of budget in all three runs. Not broken,
  just untuned: two documented settings fixed it (see "Deciding" below).
- **Given a shell,** every harness stopped editing files and wrote a
  rename script: tool calls fell tenfold. A tool designed for renames cut
  them three to eight times, and unlike the shell could still refuse to
  touch the tests.

To find out: run one representative task with the harness's tools, and
with yours if you can swap them in. Compare tool calls and tokens, not
just whether it finished. If you'd replace its tools anyway, much of what
you'd adopt it for is gone.

## 3. What can your agent reach or affect?

- **Deep Agents** edited the original task files instead of its own copy,
  after we'd set `virtual_mode=False` (the default keeps paths inside the
  folder; "virtual" doesn't mean pretend files).
- **Claude Agent SDK** created a folder outside its workspace from a
  one-character path typo. With `bypassPermissions` on, nothing stopped
  it.
- **Running the tests means running code.** With its shell taken away,
  Claude wrote a rename script into an empty `conftest.py` and ran the
  tests to execute it. Any tool that runs code the agent can edit is a
  shell.
- **A shell gets past per-call guardrails.** One global `sed` renamed a
  function everywhere, a test file included. Block 3's guardrail checked
  each `write_file`; a shell command has no such checkpoint.

You'll change settings like these in production too, so the agent can run
unattended. Before it goes near production, know which settings you
changed and why, where its file tools can write, which of its tools run
code (the test runner included), and watch an attempt to write outside
its folder get blocked.

## 4. What will you need to watch?

### How big the conversation gets

The harness sends the whole conversation back to the model on every call,
so cost grows with the number of model calls and with how big the
conversation gets. As a rough guide: under about ten calls is small,
dozens is large; a screen of text per tool result is small, whole files
and full logs are large.

A hundred calls or more goes past anything we measured this morning
(our longest runs were about 50), and it changes what you need. Cost
grows faster than the number of calls, because every call re-sends a
longer conversation. Compaction, and notes that survive it (Block 3's h2
and h3), stop being optional. And a crash at call 150 is expensive, so
saving progress and resuming from it becomes one of your own steps
(question 2).

On the small tasks (5 or 6 calls) the features for managing a big
conversation never fired, and our fuller harness cost 11–13% more for
nothing. On the migration (25 to 36 calls, tool results up to 22,000
characters) they fired every run. And it's model calls, not tool calls,
that drive cost: the shell cut tool calls tenfold but tokens only 2 to 4
times, tracking the drop in model calls. If the conversation is small, a
lighter harness costs less on every call. If it's large, find out *how*
your candidate keeps it in check, not just whether it does.

### The trace

You debug an agent from its trace, and each harness makes different
things easy or hard to see. What we had to work for in Block 4:

- **What the model is actually sent.** Claude Agent SDK sent an *empty*
  system prompt until we set one: not ours, not Claude Code's.
- **Every tool call, with its arguments.** Deep Agents' own file tools
  didn't appear until we hooked into its callbacks: the plain trace
  showed 2 calls where the agent had made 15. And cutting arguments to 70
  characters hid the one field that explained a failure.
- **Which step it's on.** Every SDK counts "turns" its own way. Claude's
  streams one model response as several messages, so the obvious count
  said 500 for a run of 45. To cap runs fairly we counted model calls
  ourselves.
- **What the model said between steps,** where a plan going wrong shows
  up first. In three of the five, the simple way to run it returns only
  the final answer.
- **When it ran the tests.** Most runs tested once or twice, near the
  end. You only see that if the trace shows it.
- **Cost per step.** OpenAI Agents and ADK reported tokens for each model
  call. On our provider, Claude's SDK reported only the total.
- **What the harness did on its own:** cutting a long result, dropping old
  history, refusing a malformed call, handing work to a subagent. These
  change what the model sees.

Build this trace while you're still evaluating, so you find out what's
hard to get before you choose, not during your first incident.

## Deciding

1. **Adopt:** a harness passes questions 1 and 2 and does what you need
   as it is.
2. **Extend:** it passes, but you need steps it doesn't have, or its
   defaults don't fit your work, and you can change that. Deep Agents on
   the migration is the example: 0 of 3 with its defaults, 3 of 3 after
   two documented settings, no subagent and one line of prompt:

   ```python
   register_harness_profile("openai", HarnessProfile(
       excluded_tools=frozenset({"task"}),
       general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False)))
   ```

   Finding out *what* to change was the work: it took reading the trace.
3. **Drop down a level:** you need to write the loop yourself, because
   you can't plug in where you need to. Use a lower-level framework such
   as LangGraph, under Deep Agents. Everything the harness shipped, from
   file tools to subagents, becomes yours to write.
4. **Build your own:** rarely the right call. Blocks 2 and 3 showed what
   it costs.

Questions 3 and 4 don't pick one of these, but they shape the choice in
three ways:

- **They break ties.** If two harnesses pass questions 1 and 2, a small
  conversation favors the lighter one, which costs less on every call; a
  large one favors the one that best keeps the conversation from growing.
- **They can turn adopt into extend.** If you need to see something your
  candidate doesn't show, or need a guard it doesn't have, you'll add it
  through its hooks or inside a tool. That's extending it.
- **They raise the stakes on a harness's own shell.** If your agent can
  reach money, customers or production, a harness that ships a shell
  (Claude Code's Bash, Deep Agents' `execute`) needs a sandbox you trust,
  or that shell switched off.

Whatever you pick, your answers to 3 and 4 are a to-do list: what to
sandbox or guard, and what to build into the trace before the first real
run.

### Testing your choice

Run one real task from your own codebase through your top two
candidates, the way Block 4 did:

- the same model, the same prompt and the same budget for each;
- several runs, not one (one harness's turns ranged from 25 to 50 on the
  same task);
- judge by your own check, never the agent's word, and check the checker:
  in our runs, passing tests let through a changed CLI message and a
  migration that left 120 files undone;
- read the traces, not just the verdicts: every finding on this page came
  from a trace.
