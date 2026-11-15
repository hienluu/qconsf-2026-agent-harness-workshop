# Block 1 — Why the Harness Matters

**Nothing to run in this block.** It's 30 minutes of argument and vocabulary,
and this page is the reference card: the terms defined here get used for the
rest of the workshop, so keep it open.

## How this workshop works

You won't build a harness from scratch today. Instead, we work from the
outside in: you run harnesses on a real task, watch what they do, and
measure the results. Most of the morning uses one task, updating a
140-file code library to a new version of its API, so you can compare
every number with the ones before it.

- **Block 2:** you get a working agent loop with two small gaps to fill,
  about ten lines in all, so you see what's inside every harness. Then you
  give it a task bigger than it was built for and watch where it
  struggles.
- **Block 3:** you run the same task through harnesses with extra
  protections built in. You read each run's trace, the step-by-step
  record of what the agent did, to see what each protection helps with
  and what it costs.
- **Block 4:** you run two production harnesses, OpenAI's and
  Anthropic's, on the same task with the same tools, and watch them work.
  Then you design a better tool for the job and try it. Finally, you
  check whether "all tests pass" really means "the job is done".
- **Block 5:** you turn what you saw into a decision for your own agent.

Each block has its own `README.md` in its folder. It has the steps, the
commands to copy, what to watch for, and the numbers from our own runs,
so you can tell a normal result from an unlucky one. Keep it open while
you work: it answers most questions before you need to ask them.

The skill you take home isn't writing an agent loop. It's running an
experiment on a harness and reading what it tells you: keep the model and
the task the same, change one thing, read the trace, and check the result
yourself.

## The claim

> An agent is a model plus a harness — and the harness moves outcomes as
> much as the model does.

The harness is everything around the model that turns it into an agent.
Anthropic's phrasing: *the loop, tools, context management, and guardrails
that turn raw intelligence into a working agent.* Google Cloud's: *all the
deterministic components that wrap the LLM.* Pydantic's: *everything around
the model that turns it into an agent.* Three vendors, one idea.

The practical version, and the one the rest of the workshop keeps demonstrating:
**the harness decides what the model sees, what it may do, and what happens
to its output.** The model weights never change. The environment does.

## Anatomy of a harness

Every item below shows up twice more today — as something your own harness
*lacks* in Block 2, and as something a production harness *decides for you*
in Block 4.

| Component | What it governs |
|---|---|
| **The agentic loop** | Call the model, run what it asks for, feed results back, repeat — and decide when to stop |
| **Tool dispatch** | What the model can actually cause to happen, and what the results look like by the time it sees them |
| **Context management** | What stays in the conversation as it grows: truncation of individual results, compaction of old ones |
| **Memory / durable state** | What survives when the conversation doesn't |
| **Sandboxing** | Where the agent's actions can and can't reach |
| **Guardrails and permissions** | What the agent is refused, regardless of what it decides to attempt |
| **Observability** | What you can see about a run — while it happens and afterward |

## The spectrum

Vendors ship harness functionality at different altitudes. Knowing which
altitude a product occupies tells you what it will and won't decide for you:

```
runtime  →  kit  →  composable  →  opinionated harness  →  packaged product
LangGraph   Google   Pydantic AI    Claude Agent SDK ·      Claude Code,
            ADK                     OpenAI Agents ·         Codex
                                    Deep Agents
```

Further left: more control, more of the work is yours. Further right: more
decided for you, less that you can change. Neither end is correct — Block 5
is about choosing your position deliberately.

## The evidence, if you want to check it yourself

The slides work through this in more detail, but the central case is public
and worth reading at the source. ARC Prize — the independent organisation
that runs the ARC-AGI benchmarks — evaluated GPT-6 Astra under two
harnesses and published both results:

| | Standard harness | Provider Adapter harness |
|---|---|---|
| ARC-AGI-3 (Semi-Private) | **62.7%** | **99.9%** |
| Cost | $26,098 | $18,817 |
| Reasoning effort | max | high |

Same model. The Provider Adapter preserves the model's reasoning state
between requests and compacts long conversations, so it can reuse prior
work; the standard harness is a neutral interface built for comparing
providers. The higher score also cost less. On the 167 problems *both*
harnesses solved, the adapter ran about 3.66× faster on roughly half the
tokens.

Sources: [ARC Prize's write-up](https://arcprize.org/blog/astra) and their
[results page](https://arcprize.org/results/openai-gpt-6-astra).

Two things to take from it rather than the headline gap. First, ARC Prize
announced it will report the two harnesses as separately labelled
conditions on its leaderboard. When a benchmark organisation adds a
harness column, the question is settled. Second, this is one benchmark and one vendor's
harness; treat the size of the gap as an illustration, not a constant.
