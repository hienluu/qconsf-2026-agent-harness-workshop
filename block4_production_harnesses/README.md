# Block 4 — The Production Harnesses

**Why this block:** you now know, from your own hands, what a harness must
decide — you built the loop, watched it fail, and measured five specific
protections. The production harnesses decide those same things for you,
differently, and their feature lists all read alike until you can map each
feature to a failure you've seen. This block is that mapping: five
harnesses, one task you know by heart, read side by side.

## The specimens

Same task (`fix_bug`), same model, same provider key. Each `run.py` is
meant to be read as much as run — notice what you had to write, what came
free, and what the harness assumed about who you are.

| Beat | Specimen | Run with |
|---|---|---|
| Kit vs composable | `google_adk/` | `uv run --group block4-adk google_adk/run.py` |
| | `pydantic_ai/` | `uv run --group block4 pydantic_ai/run.py` |
| Two roads to opinionated | `claude_agent_sdk/` | `uv run --group block4 claude_agent_sdk/run.py` |
| | `openai_agents/` | `uv run --group block4 openai_agents/run.py` |
| Harness on a runtime | `deepagents/` | `uv run --group block4 deepagents/run.py` |
| — its escape hatch | `deepagents/langgraph_escape_hatch.py` | `uv run --group block4 deepagents/langgraph_escape_hatch.py` |

(ADK runs from its own dependency group — it cannot co-resolve with
openai-agents. That fact is part of the lesson; see COMPARISON.md.)

Prerequisites beyond the usual `.env`: the Claude Agent SDK specimen
requires the Claude Code CLI to be installed (`npm install -g
@anthropic-ai/claude-code` — in the pre-conference setup email).

## Exercise flow (from `block4_production_harnesses/`)

1. Pick any specimen. **Read its `run.py` first** — each is ~80 lines and
   its docstring says what to notice. Then run it and watch the same
   5-turn arc you know from Blocks 2–3, driven by someone else's harness.
2. Repeat for the others, in any order. Total cost for all six: well
   under $1.
3. As you go, keep score against three questions:
   - What did I have to write? (tools? loop? nothing?)
   - What did the harness assume about my provider, my model, my trust?
   - Which Block 2 failure does each built-in feature answer?
4. Read `COMPARISON.md` — the dimension matrix — and argue with it.
5. Presenter demo (watch, don't run — ~$1): `refactor_v2`, the task that
   killed the naive harness, through Claude Code's harness:
   ```
   uv run --group block4 presenter_demo/run.py
   ```
   The closing question: **did the professionals' harness beat our
   200-line h3?** Whatever the answer, it teaches — a big win shows what
   production harness engineering buys; anything else is the harness-model
   fit lesson from Block 1, live.

   For calibration, the first live run (Sep 2026, GLM-5.3): SOLVED in 19
   turns and 65 seconds — versus 117–208s for our h3 — with a tool profile
   of 16× Bash, 1× Read, 1× Edit. One Edit, for a ~130-file migration:
   given a shell, the model scripted the renames instead of rewriting
   files one by one. The decisive advantage wasn't the loop or compaction;
   it was tool design changing which algorithm the model chose. (The same
   Bash tool is why production harnesses need sandboxing and permissions —
   we ran `bypassPermissions` on a disposable copy, deliberately.)

## Debrief questions

1. Which specimen required the least code — and what did that convenience
   cost in provider coupling?
2. Two harnesses needed an explicit workaround to run on our provider at
   all (Bearer auth for Claude's SDK, an explicit model object for
   OpenAI's). What does that predict about switching costs at your job?
3. ADK couldn't even share a dependency resolution with OpenAI's SDK.
   What does your platform team do with that fact?
4. Every one of these solved fix_bug. On what basis, then, would you
   actually choose? (That's Block 5.)
