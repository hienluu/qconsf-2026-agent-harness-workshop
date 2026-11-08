# Agent Harness Workshop

Hands-on repository for **"Building AI Agents: A Practical Framework for
Choosing the Right Agent Harness"** — QCon San Francisco, November 19, 2026.

An agent is a model plus a harness: the loop, tools, context management,
memory, sandboxing, and guardrails around it. In this repo you build a
minimal harness, see what it costs and where it falls short, measure what
each added component buys, and then run five production harnesses on the
same task to see what each one decides for you.

## Setup (do this at home — venue WiFi will not support it)

Requires [uv](https://docs.astral.sh/uv/) (`brew install uv`, or
`curl -LsSf https://astral.sh/uv/install.sh | sh`). No virtualenv to
create or activate — `uv run` manages the environment itself.

```
git clone https://github.com/hienluu/qconsf-2026-agent-harness-workshop.git
cd qconsf-2026-agent-harness-workshop
uv sync                        # downloads dependencies — do this on real WiFi
cp .env.example .env           # fill in your provider API key + model
uv run setup/check_setup.py    # expect: ALL GREEN
```

## Layout

| Path | Workshop block |
|---|---|
| [`block1_why_harness_matters/`](./block1_why_harness_matters/README.md) | Reference card: what a harness is, its components, the vendor spectrum (no code: Block 1 is slides) |
| [`block2_naive_harness/`](./block2_naive_harness/README.md) | Build a minimal harness (loop + tool dispatch), run it on a short task, then push it through a long one until it hits its turn limit |
| [`block3_measure/`](./block3_measure/README.md) | Same model + tasks through three harness configs; compare cost, turns and traces |
| [`block4_production_harnesses/`](./block4_production_harnesses/README.md) | Claude Agent SDK, OpenAI Agents, Google ADK, Deep Agents and Pydantic AI, all on the same task |
| [`block5_decision_framework/`](./block5_decision_framework/WORKSHEET.md) | A worksheet that takes your own agent to a harness decision |
| `scripts/` | `preflight.py` (one-command readiness check: runs `check_fixtures.py` and `test_llm.py`), `reset.py` (start any block over), `check_fixtures.py` (verify the task workspaces are still unsolved), `test_llm.py` (test the LLM provider connection in `.env`), plus the generators that rebuild workspaces from their green references |

Start at [`block1_why_harness_matters/README.md`](./block1_why_harness_matters/README.md) for the vocabulary, then
`block2_naive_harness/README.md` for the first hands-on block.

## License

MIT. See [LICENSE](./LICENSE).
