# Block 1 — Why the Harness Matters

**Nothing to run in this block.** It's 30 minutes of argument and vocabulary,
and this page is the reference card: the terms defined here get used for the
rest of the day, so keep it open.

## The claim

> An agent is a model plus a harness — and the harness moves outcomes as
> much as the model does.

The harness is everything around the model that turns it into an agent.
Anthropic's phrasing: *the loop, tools, context management, and guardrails
that turn raw intelligence into a working agent.* Google Cloud's: *all the
deterministic components that wrap the LLM.* Pydantic's: *everything around
the model that turns it into an agent.* Three vendors, one idea.

The practical version, and the one the rest of the day keeps demonstrating:
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

## What you'll do with this

- **Block 2** — build a harness with none of the components above, then hand
  it a task sized past its limits and watch precisely how it fails.
- **Block 3** — add the missing components one configuration at a time and
  measure what each is worth. A controlled experiment, not a vibe.
- **Block 4** — read five production harnesses through the same lens and see
  what each one decided for you.
- **Block 5** — the rubric: how to choose, extend, or defend a harness, with
  numbers behind the decision.

The benchmark evidence for the claim at the top is on the slides. By the end
of Block 3 you won't need it — you'll have measured your own.
