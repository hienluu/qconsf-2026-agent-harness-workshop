# Harness decision worksheet

Every harness in the workshop solved the task. So the question was never
which one *works*. It's which one fits your agent, and what you're
signing up for when you pick it.

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

**Start from your agent, not from the list of harnesses.** A feature only
pays off when your workload actually needs it, and a feature you don't
need still adds tokens to every request. So you describe your agent first,
and every question after that refers back to it.

**Rule options out instead of scoring them.** A weighted score turns a
judgement into one number, and the workshop showed again and again how
misleading single numbers are. Every harness we tested solved the task,
and every feature list reads the same. What actually separates them is
the constraint that rules one out.

**There are two kinds of question.**

- **Part 2: questions that rule harnesses out.** A "yes" makes some of
  them a poor fit.
- **Part 3: what's still your job.** These rule nothing out. They tell you
  what you'll have to build or check whichever harness you pick.

**Then decide (Part 4).** Your Part 2 answers point to one of four
outcomes: adopt, extend, drop down a level, or build.

```
Part 1              Part 2               Part 3                Part 4
describe your  ──►  rule harnesses  ──►  list what's still ──► decide, defend,
agent               out                  your job              and test
```

**About the evidence.** Each question includes what we saw in the
workshop's runs. Two things shaped those results. First, the harness
versions: they're pinned in this repo's `uv.lock`, and newer releases may
behave differently. Second, the setup: we ran one open model through a
third-party provider, not through each vendor's own API. That's why the
vendor-built harnesses needed workarounds. Treat what we saw as a starting
point, and check it against your own versions and your own provider.

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
to reach our provider at all. Pydantic AI, Deep Agents and LangGraph
needed nothing.

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
- Save progress so a run that crashes at step 40 resumes there instead of
  starting over
- Use a cheap model to explore and a stronger one to make the changes
- Pause for a sign-off that might take a day, then continue
- Run three attempts in parallel and keep the best

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

**What we saw:** five of the six harnesses in Block 4 run the loop for you
and offer different places to plug in your own code: OpenAI Agents
through `RunHooks`, LangGraph through callbacks, Pydantic AI through an
event handler. Claude Agent SDK's loop is closed: you can configure it,
but not change it.

**If you can plug in where you need to:** that's *extend* (Part 4).
**If you can't:** you need to write the loop yourself. That's *drop down
a level*.

### Q3. Does it have to fit into an existing codebase?

**What we saw:** Google ADK and OpenAI Agents share an environment in this
repo, but only just. ADK reaches non-Google models through a library called
LiteLLM, which is why this question connects to Q1. LiteLLM 1.84 and later
require version 2 of the `openai` library, while OpenAI Agents requires
version 3. ADK's convenient install option (`google-adk[extensions]`)
requires LiteLLM 1.84 or later, so installed that way the two can't coexist
at all. Installing LiteLLM on its own let us use 1.83.0, the last release
without that limit, and cut ADK's install from 161 packages to 75.

Three things to notice. Neither harness conflicts with the other directly:
they disagree about a library underneath both. *How* you install changes
the answer, not just *what* you install. And the workaround lasts only
until you need a newer LiteLLM. We first wrote this conflict up as
unavoidable. It wasn't, and we only found out by testing the exact
combination.

**Your answer:** ☐ Yes  ☐ No

**If yes:** install your candidate into your actual project, the way you'd
really install it, before you compare anything else. Then check which
library versions you've been held to, and why.

---

## Part 3: What's still your job

These rule nothing out. They're the work you'll do whichever harness you
pick.

### Q4. Will the conversation get big?

The harness sends the whole conversation back to the model on every call,
so what drives cost isn't how long a run takes. It's how big the
conversation gets. Two things make it grow, and you answered both in
Part 1. As a rough guide:

- **Model calls per run.** Under about ten is small. Dozens is large.
- **The biggest thing a tool returns.** A screen or two of text is small.
  Whole files, searches across a codebase and full test logs are large.

**What we saw:**

| Task | Model calls per run | Biggest tool result | Conversation at the end | Did the extra features help? |
|---|---|---|---|---|
| fix_bug | 5–6 | ~1,100 chars (test output) | ~2,500 chars | No, they never fired |
| bug_hunt | 5–6 | ~3,300 chars (test output) | ~7,000 chars | No, they never fired |
| refactor_v2 | 25–36 | ~22,000 chars (a codebase search) | ~77,000 chars | Yes, on every run |

On the two small tasks our fuller harness (h3) cost 11–13% more than the
simpler one (h2) and got nothing for it. How a harness handles a big
conversation matters too: our h2 keeps the start and end of a large file
and drops the middle, while Claude Code reads a large file page by page,
so every part of it stays reachable.

**How to find out:** if your agent already runs, log two numbers over a
few runs: how many model calls it made, and the size of its largest tool
result. Your provider's usage page also shows input tokens per run. If
that's many times the size of a single request, the conversation is being
resent and growing. If you haven't built it yet, estimate: how many steps
would a person take, and how much would they need to read at once?

**Your answer:** ☐ Small  ☐ Large  ☐ It varies

**If small:** the features for managing a big conversation won't fire, and
a lighter harness costs less on every call.
**If large:** find out *how* your candidate keeps the conversation in
check, not just whether it does.

### Q5. Can it write files outside the folder you gave it?

**What we saw:** two of the five harnesses did. Both times, the setting
that allowed it was one we had changed so the agent could run unattended.

- **Deep Agents** edited the original task files instead of its own copy.
  By default it keeps file access inside the folder you give it. We had
  turned that off by setting `virtual_mode=False`. The name makes that an
  easy mistake: "virtual" sounds like the agent works on pretend files. It
  doesn't. The default mode still writes real files; it just stops paths
  from leaving the folder.
- **Claude Agent SDK** created a new folder outside its workspace when the
  model got one character of a file path wrong. We had turned off its
  permission prompts (`bypassPermissions`) so it could run without a person
  approving each step, so nothing stopped the write.

You'll make the same kind of change in production, because an agent that
waits for approval on every step isn't much use unattended. That's exactly
when these protections go away.

**Before it goes near production:**

☐ I know which settings I changed from the defaults, and why
☐ I know where its file tools can write with those settings
☐ I know what its shell access can reach, if it has any
☐ I've asked it to write outside its folder and watched that get blocked

### Q6. When something goes wrong in production, what will you need to see?

You debug an agent from its trace. Each harness makes different things easy
or hard to see, and none of that shows up on a feature list. Here's what
we had to work for in Block 4:

- **Every tool call, with its arguments.** Which file it read, which
  command it ran. Deep Agents' own file tools didn't appear at all until we
  hooked into its callbacks. In one run, the plain trace showed 2 tool
  calls; the agent had actually made 15. A short trace can mean the work is
  invisible, not that there was less of it.
- **Which step it's on.** Getting a step number took one line in Claude's
  SDK and close to twenty in Pydantic AI's.
- **What the model said between steps.** That's where a plan going wrong
  shows up first. Claude's SDK and ADK hand you the model's text as it
  happens. In the other three, the simple way of running the agent returns
  only the final answer, and seeing anything along the way took a hook.
  Pydantic AI then streamed the text a fragment at a time, so we had to
  reassemble it.
- **Cost per step.** OpenAI Agents and ADK reported tokens for each model
  call. On our provider, Claude's SDK reported only the total; the
  per-step numbers came back empty.
- **What the harness did on its own.** Cutting a long result, dropping old
  history, refusing a malformed tool call. These change what the model
  sees, so they belong in the trace. ADK's events include a field for when
  it compacts history; Pydantic AI has an event for a tool call it rejected
  before running it.

**Check your candidate:**

| I need to see | Can my candidate show it? | How much code did it take? |
|---|---|---|
| Every tool call, with arguments | | |
| Which step it's on | | |
| What the model said between steps | | |
| Cost per step | | |
| What the harness did on its own | | |

**Then:** build this trace while you're still evaluating. If one of these
takes real work to get, you want to know before you choose, not in the
middle of your first incident.

---

## Part 4: Decide

Use your Part 2 answers to pick one:

1. **Adopt:** a harness survives Q1–Q3 and does what you need as it is.
2. **Extend:** it survives, but you need steps it doesn't have, and Q2
   showed you can plug them in. Add them there.
3. **Drop down a level:** you need to write the loop yourself, because you
   can't plug in where you need to. Use a lower-level framework such as
   LangGraph. When we did that, the number of tools we had to write went
   from 1 to 4.
4. **Build your own:** rarely the right call. Blocks 2 and 3 showed what
   it costs.

**Where I landed:** ☐ Adopt  ☐ Extend  ☐ Drop down a level  ☐ Build

**What's still my job (from Part 3):** _______________________________

**What I'd say in a design review, in one sentence:**

______________________________________________________________________

**How to test it:** run one real task from your own codebase through your
top two candidates, using the same model in each, and compare what each
one decided for you. The scripts in Block 3 and Block 4 are a starting
point.
