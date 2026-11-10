# Harness decision worksheet

Pick an agent you're working on, or one you'll build soon. Answer four
questions about it, then decide. About 15 minutes. Short answers are
fine. Why each question matters, with what we saw this morning:
[WHY.md](WHY.md).

## Your agent

- **What does it do?** ________________________________________________
- **Model calls per run:** ☐ under ten  ☐ dozens  ☐ a hundred or more
- **Biggest thing a tool returns:** ☐ a screen of text  ☐ whole files or logs
- **Model it uses today, and who serves it:** __________________________
  *For example: Claude from Anthropic, GPT from Azure, an open model from Fireworks.*

## Questions 1 and 2 can rule a harness out

**1. Will it work with your model and your code?**

- Will you need to switch model providers? ☐ yes ☐ no ☐ not sure
  *Vendor-built harnesses were the hardest to move off their own models.*
- Will it go into an existing project, next to the libraries already there? ☐ yes ☐ no
  *If yes, install it into your real project before you compare anything.*

**2. What will you need to add or change?**

- Steps the agent must take whatever the model decides (an approval, a
  spending limit, "done means the tests pass"). For each, point to where
  it goes in your Block 2 loop, then check the harness lets you plug in
  there.

  | Step | Can I plug in there? |
  |---|---|
  | | |
  | | |

- Do the harness's own tools fit your unit of work (one file? one record?
  one rule?) ☐ yes ☐ I'd replace or tune them ☐ not sure
  *The wrong tools cost 2 to 4 times the tokens on the same task.*

## Now rule them out

What we saw this morning, for each harness. Use your answers to 1 and 2:
cross out any harness that fails one, and tick the ones still standing.

| Harness | Off its own model (question 1) | Its own tools (question 2) | Where you plug in (question 2) | Still standing? |
|---|---|---|---|---|
| Claude Agent SDK | 2 workarounds; built for Anthropic's API | Claude Code's whole kit, Bash included (you can switch them off) | hooks (`PreToolUse`, `PostToolUse`, `Stop`, …), `can_use_tool` | ☐ |
| OpenAI Agents | 1 workaround; its own shell tools don't work off OpenAI | none that work off OpenAI: you write them | `RunHooks`, guardrails, `needs_approval` | ☐ |
| Google ADK | needs LiteLLM to reach other providers, which clashes with OpenAI Agents' libraries | none for this kind of task: you write them | `before_tool_callback` (and the other callbacks), plugins | ☐ |
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

- The conversation will be:
  - ☐ small (a lighter harness costs less)
  - ☐ large (find out how it keeps the conversation from growing)
- In the trace, I'll need:
  - ☐ what the model is actually sent
  - ☐ every tool call with its arguments
  - ☐ when it ran the tests
  - ☐ cost per step

## Decide

Questions 1 and 2 decide which of these you land on. Use 3 and 4 to
choose between harnesses that pass 1 and 2: the lighter one if the
conversation is small, and the one that already shows what you need to
watch.

- ☐ **Adopt:** it passes 1 and 2 and does what I need as it is
- ☐ **Extend:** it passes, and I'll add what's missing (steps, tools, settings)
- ☐ **Drop down a level:** I need a step no harness lets me plug in
- ☐ **Build my own:** rarely right

**The harness I'd adopt or extend:** ______________________ (from the
harnesses still standing)

**What's still my job (from 3 and 4):** ________________________________

**In a design review, I'd say (with a number):**

*For example: "We'll extend OpenAI Agents with our own rename tool,
because on our migration it cut the tool calls from about 280 to about
50 per run. We'd look again if another harness matched that on the same
test."*

______________________________________________________________________

**I'd test it by:** running a real task of mine through my top two
choices, several times each, with the same prompt and budget, and
checking the results myself, not just that the tests pass:

______________________________________________________________________
