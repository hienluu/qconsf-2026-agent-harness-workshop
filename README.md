# Agent Harness Workshop

Hands-on repository for **"Building AI Agents: A Practical Framework for
Choosing the Right Agent Harness"** — QCon San Francisco, November 19, 2026.

An agent is a model plus a harness: the loop, tools, context management,
memory, sandboxing, and guardrails around it. In this repo you build a
minimal harness, characterize where and why it fails, measure what each
added component buys, and then evaluate the production harnesses through
the same lens.

## Setup (do this at home — venue WiFi will not support it)

Requires [uv](https://docs.astral.sh/uv/) (`brew install uv`, or
`curl -LsSf https://astral.sh/uv/install.sh | sh`). No virtualenv to
create or activate — `uv run` manages the environment itself.

```
git clone <repo-url> && cd agent-harness-workshop
uv sync                        # downloads dependencies — do this on real WiFi
cp .env.example .env           # fill in your provider API key + model
uv run setup/check_setup.py    # expect: ALL GREEN
```

## Layout

| Path | Workshop block |
|---|---|
| `block2_naive_harness/` | Build a minimal harness (loop + tool dispatch), run it on short tasks, break it on a long-horizon one |
| `block3_measure/` | *(coming)* Same model + tasks through three harness configs; compare scores and traces |
| `block4_production_harnesses/` | *(coming)* Claude Agent SDK, OpenAI Agents, Google ADK, Deep Agents, Pydantic AI — one task each |
| `block5_framework/` | *(coming)* The harness decision rubric |
| `scripts/derive_workspace.py` | Regenerates the long-horizon task workspace from its reference solution |

Start at `block2_naive_harness/README.md`.
