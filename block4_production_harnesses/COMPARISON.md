# Five Production Harnesses, One Lens

Every specimen in this directory solves the same task (`fix_bug`) with the
same model and the same provider key. The rows below are the dimensions
you practiced in Blocks 2–3 — each one maps to a failure you watched and
a fix you measured. Where a cell says "you", the harness leaves that
decision to your code.

## The spectrum (from Block 1)

runtime (LangGraph) → **kit** (Google ADK) → **composable** (Pydantic AI) →
**opinionated** (Claude Agent SDK · OpenAI Agents · Deep Agents) → product (Claude Code, Codex)

## Dimension matrix

| Dimension | Claude Agent SDK | OpenAI Agents | Google ADK | Deep Agents | Pydantic AI |
|---|---|---|---|---|---|
| **Pedigree** | product-extracted (Claude Code as a library) | model-native (co-designed with vendor models) | construction kit (typed state, sessions, graph runtime) | harness on a runtime (LangGraph underneath) | composable typed core, capabilities à la carte |
| **The loop** | Claude Code's, closed — you configure, not modify | SDK-owned; handoffs + guardrails are loop primitives | Runner + session services; graph workflows in 2.x | LangGraph ReAct + middleware stack | lean typed loop; capabilities hook it |
| **Tools out of the box** | full Claude Code set (Bash, Read, Edit, search, web) — our specimen defined zero tools | none for this task — we wrote all three | none for this task — we wrote all three | filesystem suite + planning todos + subagents; we wrote only run_tests | none for this task — we wrote all three (typed; schema from signatures) |
| **Context management** | automatic compaction, product-tuned | session-managed | you (kit primitives available) | summarization/offload middleware | opt-in capability |
| **Durable memory** | CLAUDE.md conventions | sessions/state | session state; you design it | filesystem + AGENTS.md conventions | opt-in capability (notebooks) |
| **Guardrails/permissions** | permission modes (we ran bypassPermissions in a sandbox copy) | first-class guardrail primitives | callbacks/plugins — mechanisms, not policies | filesystem permissions, interrupt_on | opt-in capability (limits, masking) |
| **Provider coupling** | Anthropic env contract (`ANTHROPIC_*`); worked on the compat endpoint but announced `unrecognized_model`, and auth needed Bearer via `AUTH_TOKEN` | OpenAI-shaped; `org/model` strings parse as provider prefixes — explicit model object required | agnostic via LiteLLM (env-var contract) | any LangChain model — constructor argument | none — provider is a constructor argument |
| **Cost visibility** | `total_cost_usd` on every result | you | you | you | built-in (`RunUsage.cost`) |
| **Install weight** | pip pkg + requires Claude Code CLI | light | heavy — 86 packages (k8s, botocore, llama-index); **cannot co-resolve with openai-agents** (own uv group) | LangChain ecosystem | light |
| **Specimen wall time (1 run each)** | 9.1s | 7.7s | 8.3s | 8.8s | 6.6s |

Single runs — character evidence, not a benchmark. Every harness solved it.

## The wall-clock finding: harness weight is a fixed cost; harness value scales with horizon

On this 5-turn toy task, the two most batteries-included harnesses were
the *slowest* (observed receipts: deepagents ~23s with its middleware
onion wrapping every model call, claude_agent_sdk ~18s, vs ~9–10s for the
lean ones — and the bare-runtime escape hatch at ~9.5s). Yet on the
long-horizon migration, the same heavy Claude harness beat every
hand-built harness by 2–3× (presenter demo: 19 turns, 65s). Short tasks
punish rich harnesses; long tasks reward them. When you evaluate a
harness, your task-horizon profile is a first-order input — which is
exactly where Block 5's rubric picks up.

## What the specimens teach, one line each

- **Claude Agent SDK**: the "define nothing" experience — and the price is
  an environment contract that assumes Anthropic (the auth dance and the
  `unrecognized_model` warning are lock-in made visible).
- **OpenAI Agents**: clean primitives, but the defaults (Responses API,
  tracing to OpenAI's platform) show who it expects you to be.
- **Google ADK**: the most ceremony for the smallest agent — structure you
  will want at enterprise scale and pay for at prototype scale.
- **Deep Agents**: LangChain's own verdict that batteries matter; the
  escape hatch script shows exactly what dropping to the runtime costs.
- **Pydantic AI**: the only one with no home vendor; typed tools and
  built-in cost accounting for free.

## Dependency note (a finding, not a footnote)

The five harnesses could not share one dependency resolution:
`google-adk[extensions]` conflicts with `openai-agents`, so ADK lives in
its own uv group. If you adopt two of these in one codebase, you may be
choosing a container boundary, not just an import.
