# Harness decision worksheet

Pick an agent you're working on, or one you'll build soon. Answer four
questions about it, then decide. About 15 minutes. Short answers are
fine. Why each question matters, with what we saw this morning:
[WHY.md](WHY.md).

## Your agent

- **What does it do?** ________________________________________________
- **Model it uses today, and who serves it:** __________________________
  - *For example: Claude from Anthropic, GPT from Azure, an open model from Fireworks.*

## Questions 1 and 2 can rule a harness out

**1. Will it work with your model and your code?**

- Will you need to switch model providers? ☐ yes ☐ no ☐ not sure
- Will it go into an existing project, next to the libraries already there? ☐ yes ☐ no
  - *If yes, install it into your real project before you compare anything.*

**2. What will you need to add or change?**

- Steps it must take whatever the model decides (an approval, a spending
  limit, "done means the tests pass"):
  1. ____________________________________________
  2. ____________________________________________
- Its unit of work (one file? one record? one rule?): ____________________
  - *On the migration, tools that didn't match the unit of work cost 2 to 4 times the tokens.*

## Now rule them out

What we saw this morning, for each harness. Apply your answers to 1 and 2:

- **Switching providers?** Cross out the ones that needed workarounds off
  their own model, unless you'd pay to leave them later.
- **A step you need has nowhere to plug in?** Cross it out.
- **Its own tools don't match your unit of work?** Keep it, but you'll be
  extending it.

| Harness | Off its own model (question 1) | Its own tools (question 2) | Where you plug in (question 2) | Still standing? |
|---|---|---|---|---|
| Claude Agent SDK | Bearer auth through `ANTHROPIC_AUTH_TOKEN`, plus an unrecognized-model warning; built for Anthropic's API | Claude Code's whole kit, Bash included (you can switch them off) | hooks (`PreToolUse`, `PostToolUse`, `Stop`, …), `can_use_tool` | ☐ |
| OpenAI Agents | an explicit model object, and tracing to OpenAI turned off; its own shell tools don't work off OpenAI | none that work off OpenAI: you write them | `RunHooks`, guardrails, `needs_approval` | ☐ |
| Google ADK | needs LiteLLM to reach other providers; shares an environment with OpenAI Agents only with LiteLLM held at 1.83 | none for this kind of task: you write them | `before_tool_callback` (and the other callbacks), plugins | ☐ |
| Deep Agents | none: any LangChain model | its own file tools, subagents, and a shell if you add one | LangChain callbacks, `interrupt_on`, `HarnessProfile` | ☐ |
| Pydantic AI | none: the provider is a setting | none for this kind of task: you write them | `event_stream_handler`, `requires_approval` | ☐ |

## Questions 3 and 4 are your job, whichever harness you pick

**3. What can your agent reach or affect?** Tick all that apply.

- ☐ files outside its own folder
- ☐ code it runs (the test runner counts)
- ☐ a shell
- ☐ money, customers or production

*Each tick is something to sandbox, limit, or guard inside a tool.*

**4. What will you need to watch?**

- **Cost.** Every call re-sends the whole conversation, so its size sets
  the cost.
  - Model calls per run: ☐ under ten ☐ dozens ☐ a hundred or more
  - Biggest thing a tool returns: ☐ a screen of text ☐ whole files or logs
  - *Ticked dozens or more, or whole files? Find out how the harness keeps
    the conversation from growing. Otherwise a lighter harness costs less.*
- **The trace.** In it, I'll need:
  - ☐ what the model is actually sent
  - ☐ every tool call with its arguments
  - ☐ when it ran the tests
  - ☐ cost per step

## Decide

- ☐ **Adopt:** a harness still standing, with nothing to add or change
- ☐ **Extend:** a harness still standing, plus the steps or tools from question 2
- ☐ **Drop down a level or build:** every harness is crossed out (rarely
  right; Blocks 2 and 3 showed what building costs)

If more than one is still standing, use 3 and 4 to choose: the lighter
one for a small conversation, the one that already shows what you need
to watch.

**The harness I'd adopt or extend:** ________________________________

**What's still my job (from 3 and 4):** ________________________________

**In a design review, I'd say (with a number):**

*For example: "We'll extend OpenAI Agents with our own rename tool,
because on our migration it cut the tool calls from 278–315 to 35–88
per run. We'd look again if another harness matched that on the same
test."*

______________________________________________________________________

- **I'd test it by:** ____________________________________________________
  - *Several runs, the same prompt and budget, and check the results yourself.*
