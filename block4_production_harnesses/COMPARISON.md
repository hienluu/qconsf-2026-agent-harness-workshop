# Five Production Harnesses, Compared the Same Way

Every runner script in this directory solves the same task (`bug_hunt` — three
interacting bugs in a small pricing package; `fix_bug` is the extra-credit
variant) with the same model and the same provider key. The rows below are the same things
you practiced in Blocks 2–3 — each one maps to a failure you watched and
a fix you measured. Where a cell says "you", the harness leaves that
decision to your code.

## The spectrum (from Block 1)

runtime (LangGraph) → **kit** (Google ADK) → **composable** (Pydantic AI) →
**opinionated** (Claude Agent SDK · OpenAI Agents · Deep Agents) → product (Claude Code, Codex)

## What each harness decides for you

| What we compared | Claude Agent SDK | OpenAI Agents | Google ADK | Deep Agents | Pydantic AI |
|---|---|---|---|---|---|
| **Where it came from** | product-extracted (Claude Code as a library) | model-native (co-designed with vendor models) | construction kit (typed state, sessions, graph runtime) | harness on a runtime (LangGraph underneath) | composable typed core, capabilities à la carte |
| **The loop** | Claude Code's, closed — you configure, not modify | SDK-owned; handoffs + guardrails are loop primitives | Runner + session services; graph workflows in 2.x | LangGraph ReAct + middleware stack | lean typed loop; capabilities hook it |
| **Tools out of the box** | full Claude Code set (Bash, Read, Edit, search, web) — our script defined zero tools | none for this task — we wrote all four | none for this task — we wrote all four | filesystem suite + planning todos + subagents; we wrote only run_tests | none for this task — we wrote all four (typed; schema from signatures) |
| **Context management** | automatic compaction, product-tuned | session-managed | you (kit primitives available) | summarization/offload middleware | opt-in capability |
| **Durable memory** | CLAUDE.md conventions | sessions/state | session state; you design it | filesystem + AGENTS.md conventions | opt-in capability (notebooks) |
| **Guardrails/permissions** | permission modes (we ran bypassPermissions in a sandbox copy) | guardrails built into the loop | callbacks/plugins — mechanisms, not policies | filesystem permissions, interrupt_on | opt-in capability (limits, masking) |
| **Provider coupling** | Anthropic env contract (`ANTHROPIC_*`); worked on the compat endpoint but announced `unrecognized_model`, and auth needed Bearer via `AUTH_TOKEN` | OpenAI-shaped; `org/model` strings parse as provider prefixes — explicit model object required | agnostic via LiteLLM (env-var contract) | any LangChain model — constructor argument | none — provider is a constructor argument |
| **Cost visibility** | `total_cost_usd` on every result | you | you | you | built-in (`RunUsage.cost`) |
| **Install weight** | pip pkg bundles a compiled Claude Code CLI per platform (~90MB wheel, ~190MB installed) | light | heavy — 86 packages (k8s, botocore, llama-index); **cannot co-resolve with openai-agents** (own uv group) | LangChain ecosystem | light |

Wall times are deliberately NOT a matrix row: single-run wall clock on
short tasks is provider-latency noise (see below). Your receipts table
carries per-run times with their task labels; treat them as direction,
never magnitude. Every harness solved both tasks in every observed run.

## What the "context management" row actually means

That row is one phrase per harness, which undersells the most consequential
difference in the table. Block 3 gave you the vocabulary for it: your h2
protected context by **discarding** — capping each tool result at 6k chars,
keeping head and tail, dropping the middle with a marker. It works, and it
is lossy by construction.

Production harnesses mostly do something else. Claude Code's `Read` tool
takes `offset` and `limit`, and when a whole-file read exceeds the token
limit it returns the first page with a `PARTIAL view` notice telling the
model how much it got and how to ask for more. Same pressure, different
answer: h2 throws the middle away and hopes; pagination bounds the payload
while keeping every byte reachable. Neither is magic — a paginated read
that still blows the limit errors out and sends the model to Grep instead.
The difference is that one of them leaves the agent somewhere to go.

You already ran this. The Claude Agent SDK script defines **zero tools**,
so the `Read` in that run was Claude Code's — the paginating one. The
"tools we wrote: 0" cell on your receipt is not only about convenience; it
means you also inherited someone else's answer to a problem you solved by
hand in Block 3, and you did not get to see it happen.

That is the general shape of this block. Every cell in the matrix above is
a decision someone made for you. Convenient when you agree with it, and
invisible until you don't.

Source for the `Read` behaviour: [Claude Code tools
reference](https://code.claude.com/docs/en/tools-reference) (checked
Sep 2026).

## On the wall-clock column: mostly noise — and that's the lesson

Do not rank harnesses by the `wall s` column. On a short task (the
extra-credit `fix_bug` especially),
provider latency swamps harness overhead: the same deepagents script
measured 23.3s in one dry run and 10.6s on the immediate rerun. (The
workshop author briefly enshrined "heavy harnesses are slow on trivial tasks"
from that single 23.3s sample — falsified by the next run. Single runs
are harness+luck; Block 3's rule applies to Block 4 too.)

What the receipts DO establish is structural, and stable across every
run: who owns the loop, tools written vs shipped, provider friction,
dependency weight, code size. Those columns don't vary with the
provider's mood.

The horizon question survives in weaker, honest form: a rich harness's
machinery (middleware, planning, subagents) is overhead a short task
can't fully use — its measured payoff so far is on the long task, where the
heavy Claude harness needed about 1.5× fewer turns than our h3 (presenter
demo median 18 turns over 2 runs, against h3's median 27 over 10, by
scripting the migration through Bash). An earlier draft said "2–3×" here;
that figure came from dividing wall-clock times — the column this very
section calls unreliable — and does not survive being recomputed on turns. Whether harness
weight has a measurable toy-task latency cost needs October's multi-run
sampling before anyone quotes it.

## What the scripts show, one line each

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
