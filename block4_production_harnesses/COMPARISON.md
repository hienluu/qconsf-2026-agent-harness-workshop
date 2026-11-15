# Five Production Harnesses, Compared the Same Way

Every runner script in this directory runs the same task (the migration
from Blocks 2 and 3; `bug_hunt` and `fix_bug` are the fallbacks) with the
same model, the same provider key, the same 50-call turn cap, and file
tools only. The rows below are the same things
you practiced in Blocks 2–3; each one maps to a failure you watched and
a fix you measured. Where a cell says "you", the harness leaves that
decision to your code.

## The spectrum (from Block 1)

runtime (LangGraph) → **kit** (Google ADK) → **composable** (Pydantic AI) →
**opinionated** (Claude Agent SDK · OpenAI Agents · Deep Agents) → product (Claude Code, Codex)

## What each harness decides for you

| What we compared | Claude Agent SDK | OpenAI Agents | Google ADK | Deep Agents | Pydantic AI |
|---|---|---|---|---|---|
| **Where it came from** | product-extracted (Claude Code as a library) | the model vendor's own SDK, defaulting to its Responses API | construction kit (typed state, sessions, graph runtime) | harness on a runtime (LangGraph underneath) | composable typed core, capabilities à la carte |
| **The loop** | Claude Code's, closed: you configure, not modify | SDK-owned; handoffs + guardrails are loop primitives | Runner + session services; graph workflows in 2.x | LangGraph ReAct + middleware stack | lean typed loop; capabilities hook it |
| **Tools out of the box** | Claude Code's full set (Bash, Read, Edit, search, web); the exercise switches them all off and serves it our four (`CLAUDE_TOOLS=own` keeps its file tools) | none for this task; we wrote all four | none for this task; we wrote all four | filesystem suite + planning todos + subagents; we wrote only run_tests | none for this task; we wrote all four (typed; schema from signatures) |
| **Context management** | automatic compaction, product-tuned | session-managed | you (kit primitives available) | summarization/offload middleware | opt-in capability |
| **Durable memory** | CLAUDE.md conventions | sessions/state | session state; you design it | filesystem + AGENTS.md conventions | opt-in capability (notebooks) |
| **Guardrails/permissions** | permission modes (we ran bypassPermissions on a disposable copy, which is not isolation) | guardrails built into the loop | callbacks/plugins: mechanisms, not policies | filesystem permissions, interrupt_on | opt-in capability (limits, masking) |
| **Provider coupling** | Anthropic env contract (`ANTHROPIC_*`); worked on the compat endpoint but announced `unrecognized_model`, and auth needed Bearer via `AUTH_TOKEN` | OpenAI-shaped; `org/model` strings parse as provider prefixes, so an explicit model object is required | agnostic via LiteLLM (env-var contract) | any LangChain model, as a constructor argument | none: provider is a constructor argument |
| **Cost visibility** | `total_cost_usd` on every result (an estimate; on a model it doesn't recognize, not to be trusted) | you | you | you | an estimate (`RunUsage.cost`) for models its pricing data knows; empty through our provider |
| **Install weight** | pip pkg bundles a compiled Claude Code CLI per platform (~90MB wheel, ~190MB installed) | light | 75 packages with LiteLLM (OpenTelemetry, tokenizers, Hugging Face Hub); its `[extensions]` bundle would be 161 and **can't share an environment with openai-agents** | LangChain ecosystem | light |

Wall times are deliberately NOT a matrix row: single-run wall clock on
short tasks is provider-latency noise (see below). Your receipts table
carries per-run times with their task labels; treat them as direction,
never magnitude. What the harnesses did on the migration is in the next section.

## What the migration showed

Three or more runs each, GLM-5.3-Flash through the hosted endpoint in
`.env.example`, same prompt, file tools only, 50-call cap:

| Harness | Solved | Turns | Tool calls | Tokens sent |
|---|---|---|---|---|
| Pydantic AI | 3/3 | 20–26 | 186–283 | 0.36–0.66M |
| Google ADK | 3/3 | 24–31 | 276–279 | 0.66–0.82M |
| OpenAI Agents | 5 of 6 | 25–50 | 176–287 | 0.46–1.18M |
| Claude Agent SDK, our tools | 3/3 | 29–30 | 276–281 | 0.71–0.79M |
| Claude Agent SDK, its own file tools | 4 of 5 | 31–50 | 293–555 | 1.40–3.49M |
| Deep Agents, its own tools | 0/3 | 50 | 146–250 | 0.71–0.86M |
| *our h2 / h3 (Block 3, same endpoint)* | | *19–34* | *181–299* | *0.39–0.78M* |

**Same tools, same results.** Pydantic AI, ADK, OpenAI Agents and the
Claude Agent SDK, given the file tools from `common.py` (the same ones as
your h2), all run the same algorithm (read everything, then rewrite each
file once) and land in h2's range. On this task their loops make no
measurable difference.

**Their own tools, their own costs.** Claude Code and Deep Agents bring
file tools built for surgical edits: replace one exact string, keep the
rest of the file. Most coding work wants that. A rename across 130 files
doesn't. The same Claude harness on its own `Edit` made 200 to 380 edits
where it had rewritten each file once with ours, and sent 2 to 4 times
the tokens: the tools changed, the harness didn't.

**Deep Agents ran out of budget, and it's not misconfigured.** Each run
handed the rename to a subagent, which started with an empty context and
spent 20 to 35 of the 50 calls finding its way around before editing. A
documented setting that turns its subagent off, plus one line of prompt,
changes that (neither alone does):

```python
from deepagents import GeneralPurposeSubagentProfile, HarnessProfile, register_harness_profile

# no built-in subagent and no `task` tool, for models from this provider
register_harness_profile("openai", HarnessProfile(
    excluded_tools=frozenset({"task"}),
    general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False)))

# plus, appended to the system prompt:
# "For a rename across many files, use edit_file with replace_all=true,
#  and do the work yourself instead of delegating to a subagent."
```

| Deep Agents variant | Solved | Model calls |
|---|---|---|
| defaults | 0/3 | 50 |
| hint only | 1/3 | 38–50 |
| no subagent only | 1/3 | 31–50 |
| both | 3/3 | 32–48 |

What separated wins from losses was the edit strategy: every run that
rewrote files whole solved it, and most runs that edited occurrence by
occurrence hit the cap. The workshop runs Deep Agents with its defaults,
like every other harness; the tuning is yours to try. That's Block 5's
"extend" decision in miniature: the harness fits once you configure it
for the job, and finding out what to configure is your work.

**Claude found a shell anyway.** With Bash withheld, one run wrote a
rename script into the empty `conftest.py`, called `run_tests` (pytest
runs `conftest.py`), and emptied the file again: 21 turns, 42 calls, the
cheapest run of all. It's left out of the table above. `run_tests` now
refuses to run on modified test files, and a run that modified one fails
even if it put it back. The gap that can't be closed: the tests import
the source code, so code hidden there runs too. Taking away the shell
doesn't take away code execution while the agent can run tests.

## What the "context management" row actually means

That row is one phrase per harness, which undersells the most consequential
difference in the table. Block 3 gave you the vocabulary for it: your h2
protected context by **discarding**: capping each tool result at 6k chars,
keeping head and tail, dropping the middle with a marker. It works, and it
is lossy by construction.

Production harnesses mostly do something else. Claude Code's `Read` tool
takes `offset` and `limit`, and when a whole-file read exceeds the token
limit it returns the first page with a `PARTIAL view` notice telling the
model how much it got and how to ask for more. Same pressure, different
answer: h2 throws the middle away and hopes; pagination bounds the payload
while keeping every byte reachable. Neither is magic: a paginated read
that still blows the limit errors out and sends the model to Grep instead.
The difference is that one of them leaves the agent somewhere to go.

You can run this. With `CLAUDE_TOOLS=own`, the Claude Agent SDK script
defines only `run_tests`, so its `Read` is Claude Code's, the paginating
one. That's not only convenience: you inherit someone else's answer to a
problem you solved by hand in Block 3, and you don't get to see it
happen.

That is the general shape of this block. Every cell in the matrix above is
a decision someone made for you. Convenient when you agree with it, and
invisible until you don't.

Source for the `Read` behaviour: [Claude Code tools
reference](https://code.claude.com/docs/en/tools-reference) (checked
Sep 2026).

## Take-home experiment: does Deep Agents' summarization help?

Optional, for your own time. Block 3's h2 compacts by dropping old tool
outputs a little every turn. Deep Agents ships something more
sophisticated: past a token threshold, its summarization middleware
replaces older history with a summary the model writes, and saves the
originals to a file the agent can read back. Does that do better?

**First, it probably never fires.** For a model LangChain has no profile
for (ours), the threshold is 170,000 tokens. Our migration runs peaked at
23k to 38k per call, so with the defaults the feature is on and does
nothing. Its other two mechanisms (clipping old `write_file`/`edit_file`
arguments, saving one huge tool result to a file) didn't fire either.

**So force it.** `deepagents/compaction_experiment.py` is the same agent
with switches, and it marks under each turn (`✂`) what compaction did: each
summary, the summary's own model call (billed, but not a turn), and every
re-read of a file a summary had dropped. Run from
`block4_production_harnesses/`, one run at a time:

```bash
# no compaction at all
DEEPAGENTS_SUBAGENTS=off DEEPAGENTS_COMPACTION=off BLOCK4_MAX_TURNS=40 \
  uv run deepagents/compaction_experiment.py

# summarize at 12,000 tokens
DEEPAGENTS_SUBAGENTS=off DEEPAGENTS_COMPACTION=early DEEPAGENTS_SUMMARY_AT=12000 \
  BLOCK4_MAX_TURNS=40 uv run deepagents/compaction_experiment.py
```

`DEEPAGENTS_SUBAGENTS=off` matters: with subagents on, the agent hands the
work to subagents that start with a fresh context, the main conversation
stays small, and compaction has nothing to do. Each run takes 4 to 16
minutes and sends 0.4 to 1.3M tokens.

**What we got** (GLM-5.3-Flash, three runs each):

| | No compaction | Summarize at 12k |
|---|---|---|
| Solved | 3/3 | 0/3 (all hit the 40-call cap) |
| Summaries | 0 | 9, 14, 17 |
| Re-reads of a file a summary had dropped | 0 | 32, 19, 129 |
| Tokens sent | 0.96–1.29M | 0.40–0.54M |
| Cached | 93–95% | 33–52% |
| Uncached input | 54k–74k | 191k–361k |
| Wall time | 4.5–7 min | 10–16 min |

After each summary the agent no longer had the exact file contents, so it
read them again, which refilled the context and triggered the next
summary. One run said "Now reading the 64 integration files not yet read
this session" and re-read 54 files in one turn. It sent fewer tokens, but
almost none came from the cache: 3 to 5 times the uncached input, and
twice the wall time.

12k is deliberately aggressive, about a third to half of the observed
peaks. The result is about summarizing below what the task needs in view
at once, not about summarization in general.

**Why it fails here, and where it would fit.** Three questions decide
whether summarizing old context suits a task:

1. **Does the task need the gist, or the exact text?** A summary keeps
   decisions and intent and loses verbatim detail. A migration needs to
   know which file has `amt` on which line.
2. **Can the lost information be fetched again?** If it lives in a file
   or a database, dropping the raw output and letting the agent re-read
   it (h2's way) is cheaper and exact. If it lives only in the
   conversation (something a user said once, a decision made in
   discussion), dropping it loses it, and that's where a summary earns
   its place.
3. **Does it fire at a phase boundary or at a token count?** A token
   count fires mid-step; ours fired halfway through rewriting a family of
   14 files. At a phase boundary (exploration done, subtask finished) the
   past really is history.

By that reasoning, summarization suits support, planning and long-running
assistant conversations better than code. Only the code half is
measured here; the rest is for you to test.

**Things to try:**

- A middle threshold (`DEEPAGENTS_SUMMARY_AT=25000` or `50000`): is there
  a setting where summarizing pays on this task?
- The library's defaults with subagents on (no switches at all) and
  `DEEPAGENTS_COMPACTION=off` side by side: does turning compaction off
  change anything when it never fires?
- Your own task. Where does the information your agent needs live, and
  what would summarizing it lose?

## On the wall-clock column: mostly noise, and that's the lesson

Do not rank harnesses by the `wall s` column. On a short task (the
extra-credit `fix_bug` especially),
provider latency swamps harness overhead: the same deepagents script
measured 23.3s in one dry run and 10.6s on the immediate rerun. (The
workshop author briefly enshrined "heavy harnesses are slow on trivial tasks"
from that single 23.3s sample, and the next run falsified it. Single runs
are harness+luck; Block 3's rule applies to Block 4 too.)

What the receipts DO establish is structural, and stable across every
run: who owns the loop, tools we wrote vs the harness's own, provider friction,
dependency weight, code size. Those columns don't vary with the
provider's mood.

The horizon question survives in a weaker, honest form: a rich harness's
machinery is overhead a short task can't fully use. On the migration it
didn't pay off either; the harnesses with the most machinery were the
most expensive (see "What the migration showed"). Where a harness's
built-in tools do pay off is when they include a shell: see
`tool_design/README.md`, where every harness given one scripted the rename
in 14 to 30 calls, and a tool designed for renames did nearly as well
while keeping its guardrails.

## What the scripts show, one line each

- **Claude Agent SDK**: the "define nothing" experience, and the price is
  an environment contract that assumes Anthropic (the auth dance and the
  `unrecognized_model` warning are lock-in made visible).
- **OpenAI Agents**: clean primitives, but the defaults (Responses API,
  tracing to OpenAI's platform) show who it expects you to be.
- **Google ADK**: the most ceremony for the smallest agent: structure you
  will want at enterprise scale and pay for at prototype scale.
- **Deep Agents**: LangChain's own verdict that batteries matter: file
  tools, planning and subagents on top of LangGraph.
- **Pydantic AI**: the only one with no home vendor; typed tools and
  built-in cost accounting for free.

## Dependency note (a finding, not a footnote)

All five harnesses share one environment in this repo, but only because
we hold one library back. ADK reaches non-Google models through LiteLLM.
LiteLLM 1.84 and later require version 2 of the `openai` library;
`openai-agents` requires version 3. So we install LiteLLM directly, and the
resolver settles on 1.83.0, the last release without that limit. ADK's
convenient `[extensions]` bundle requires LiteLLM 1.84 or later, so
installed that way, ADK and OpenAI Agents can't share an environment at
all. (Tested with google-adk 2.8.0, openai-agents 0.22.0, and LiteLLM
1.83 through 1.100.)

This repo originally used the bundle and documented the conflict as
unavoidable. It wasn't. Three things worth taking from that:

- **Neither harness conflicts with the other directly.** They disagree
  about a library underneath both.
- **How you install matters, not just what.** The bundle breaks it; the
  bare library doesn't. The bundle is also twice the size: 161 packages
  against 75.
- **The workaround has a shelf life.** The day you need a newer LiteLLM,
  the conflict comes back.

If you adopt two of these in one codebase, you may be choosing a container
boundary, not just an import.
