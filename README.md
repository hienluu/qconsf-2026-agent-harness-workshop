# Agent Harness Workshop

Hands-on repository for **"Building AI Agents: A Practical Framework for
Choosing the Right Agent Harness"** — QCon San Francisco, November 19, 2026.

An agent is a model plus a harness: the loop, tools, context management,
memory, sandboxing, and guardrails around it. In this repo you build a
minimal harness, see what it costs and where it falls short, measure what
each added component buys, and then run five production harnesses on the
same task to see what each one decides for you.

## Setup (do this at home — venue WiFi will not support it)

No virtualenv to create or activate — `uv run` manages the environment
itself.

**1. Install [uv](https://docs.astral.sh/uv/)** (one time per laptop).
If `uv --version` already works, skip to step 2.

- macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`

Open a new terminal afterwards so `uv` is on your PATH.

**2. Clone and sync** (on real WiFi, before the workshop):

```
git clone https://github.com/hienluu/qconsf-2026-agent-harness-workshop.git
cd qconsf-2026-agent-harness-workshop
uv sync
```

`uv sync` downloads the dependencies, and installs Python 3.11+ for you
if you don't have it.

**3. Configure the provider.**

- Copy the template: `cp .env.example .env` (Windows: `copy .env.example .env`)
- Create an account and an API key at https://app.gomomento.ai/
- In `.env`, find the Momento section and edit the `LLM_API_KEY` line:
  remove the leading `#`, then replace `<api_key>` with your key:

  ```
  LLM_API_KEY="your-key-here"
  ```

- Leave `LLM_BASE_URL` and `LLM_MODEL` in that section as they are, and
  leave the other provider sections (Fireworks, Anthropic, Baseten)
  commented out.

**4. Verify.**

```
uv run setup/check_setup.py
```

The check makes two small API calls, so it needs network and a working
key. The last line should read `ALL GREEN — see you at the workshop.` If
it doesn't, follow the hints it prints, or bring the output to the help
desk before 9am.

**On Windows:** the commands in the block READMEs are written for bash
or zsh. A line ending in `\` continues on the next line, `A && B` runs
two commands in a row, and `NAME=value uv run ...` sets a variable for
that one command. The easiest route is to run them in Git Bash (it comes
with Git for Windows). In PowerShell instead: put a continued command on
one line, write `A; B` for `A && B`, and set the variable first with
`$env:NAME="value"; uv run ...`. In PowerShell the variable stays set
until you close the window or run `Remove-Item Env:NAME`.

The numbers in this repo come from GLM-5.3-Flash. Any OpenAI-compatible
model runs the harnesses, but some won't finish Block 3's migration task:
in our runs, Gemini Flash models mostly made one tool call per turn and
ran out of turns every time. If yours reads one file a turn and never
starts editing, switch to GLM-5.3-Flash for Blocks 3 and 4.

## Schedule (9:00 to noon)

| Time | Block | Minutes |
|---|---|---|
| 9:00 | 1. Why the Harness Matters (slides) | 30 |
| 9:30 | Lab setup: `uv run setup/check_setup.py`, help for anything not green | 10 |
| 9:40 | 2. Build the Naive Harness | 32 |
| 10:12 | 3. Measure It | 28 |
| 10:40 | Break | 10 |
| 10:50 | 4. The Production Harnesses | 40 |
| 11:30 | 5. The Decision Framework | 20 |
| 11:50 | Conclusion and feedback | 10 |

Each block's README opens with its own breakdown: intro, hands-on and
discussion.

## Layout

| Path | Workshop block |
|---|---|
| [`block1_why_harness_matters/`](./block1_why_harness_matters/README.md) | Reference card: what a harness is, its components, the vendor spectrum (no code: Block 1 is slides) |
| [`block2_naive_harness/`](./block2_naive_harness/README.md) | Build a minimal harness (loop + tool dispatch), run it on a short task, then give it a long one that needs about all of its 20 turns |
| [`block3_measure/`](./block3_measure/README.md) | Same model + tasks through three harness configs; compare cost, turns and traces |
| [`block4_production_harnesses/`](./block4_production_harnesses/README.md) | Claude Agent SDK, OpenAI Agents, Google ADK, Deep Agents and Pydantic AI, all on the same task |
| [`block5_decision_framework/`](./block5_decision_framework/README.md) | A worksheet that takes your own agent to a harness decision, with two worked examples |
| `scripts/` | `preflight.py` (one-command readiness check: runs `check_fixtures.py` and `test_llm.py`), `reset.py` (start any block over), `check_fixtures.py` (verify the task workspaces are still unsolved), `test_llm.py` (test the LLM provider connection in `.env`), plus the generators that rebuild workspaces from their green references |

Start at [`block1_why_harness_matters/README.md`](./block1_why_harness_matters/README.md) for the vocabulary, then
`block2_naive_harness/README.md` for the first hands-on block.

## License

MIT. See [LICENSE](./LICENSE).
