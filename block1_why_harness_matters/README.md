# Block 1: Why the Harness Matters

**Nothing to run in this block.** It's 30 minutes of argument and
vocabulary. This page is the reference card: the rest of the workshop
uses these terms, so keep it open.

## How this workshop works

You won't write a harness from scratch. You'll run harnesses on a real
task, watch what they do, and measure the results. Most of the morning
uses one task, migrating a 140-file library to a new version of its API,
so every number can be compared with the ones before it.

- **Block 2:** a working agent loop with two gaps to fill, about ten
  lines, so you see what sits inside every harness. Then you hand it a
  job bigger than it was built for and watch where it breaks down.
- **Block 3:** the same task through harnesses with protections added.
  You read each run's trace, the turn-by-turn record of what the agent
  did, to see what each protection buys and what it costs.
- **Block 4:** two production harnesses, OpenAI's and Anthropic's, on
  the same task with the same tools. Then you design a better tool for
  the job and run it, and check whether "all tests pass" means the job
  is done.
- **Block 5:** what you measured, turned into a decision for your own
  agent.

Each block's folder has a `README.md` with the steps, the commands, what
to watch for, and the numbers from our runs, so you can tell a normal
result from an unlucky one.

What you take home isn't how to write an agent loop. It's how to run an
experiment on a harness: hold the model and the task fixed, change one
thing, read the trace, and check the result yourself rather than taking
the agent's word for it.

## The claim

> An agent is a model plus a harness, and the harness moves outcomes as
> much as the model does.

The harness is everything around the model that turns it into an agent.
Anthropic: *the loop, tools, context management, and guardrails that
turn raw intelligence into a working agent.* Google Cloud: *all the
deterministic components that wrap the LLM.* Pydantic: *everything
around the model that turns it into an agent.* Three vendors, one
definition.

The working version, which the rest of the workshop tests: **the harness
decides what the model sees, what it may do, and what happens to its
output.** The weights don't change between runs. The environment does.

## Anatomy of a harness

Each component shows up twice more today: as something your harness
lacks in Block 2, and as something a production harness decides for you
in Block 4.

| Component | What it governs |
|---|---|
| **The agentic loop** | Call the model, run what it asks for, feed the results back, repeat, and decide when to stop |
| **Tool dispatch** | What the model can actually cause to happen, and what the results look like by the time it sees them |
| **Context management** | What stays in the conversation as it grows: truncating single results, compacting old ones |
| **Memory / durable state** | What survives when the conversation doesn't |
| **Sandboxing** | Where the agent's actions can and can't reach |
| **Guardrails and permissions** | What the agent is refused, whatever it decides to try |
| **Observability** | What you can see about a run, while it happens and afterwards |

## The spectrum

Vendors ship harness functionality at different levels. Where a product
sits tells you what it will decide for you and what it leaves to you:

```
runtime  →  kit  →  composable  →  opinionated harness  →  packaged product
LangGraph   Google   Pydantic AI    Claude Agent SDK ·      Claude Code,
            ADK                     OpenAI Agents ·         Codex
                                    Deep Agents
```

Further left: more control, and more of the work is yours. Further
right: more decided for you, and less you can change. Neither end is
right in general; Block 5 is about picking your position on purpose.

## The evidence, if you want to check it

The slides go through this in more detail, but the central case is
public and worth reading at the source. ARC Prize, the independent
organisation that runs the ARC-AGI benchmarks, evaluated GPT-6 Astra
under two harnesses and published both results:

| | Standard harness | Provider Adapter harness |
|---|---|---|
| ARC-AGI-3 (Semi-Private) | **62.7%** | **99.9%** |
| Cost | $26,098 | $18,817 |
| Reasoning effort | max | high |

Same model. The Provider Adapter keeps the model's reasoning state
between requests and compacts long conversations, so it can reuse prior
work; the standard harness is a neutral interface built for comparing
providers. The higher score also cost less. On the 167 problems both
harnesses solved, the adapter ran about 3.66× faster on roughly half the
tokens.

Sources: [ARC Prize's write-up](https://arcprize.org/blog/astra) and
their [results page](https://arcprize.org/results/openai-gpt-6-astra).

Two things matter more than the headline gap. ARC Prize will now report
the two harnesses as separately labelled conditions on its leaderboard:
when a benchmark organisation adds a harness column, the question of
whether the harness matters is settled. And this is one benchmark and
one vendor's harness, so treat the size of the gap as an illustration,
not a constant.
