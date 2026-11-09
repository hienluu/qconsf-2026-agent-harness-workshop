# Tool design: the presenter demo and take-home

In Block 4's exercise, the harnesses spend most of their calls changing
one file at a time. Step 3 asks what tool you'd design instead; step 4
runs one answer, a tool **designed** for the job
(`openai_agents/run_replace.py`). This folder holds the other answer, a
**shell**: two scripts for the presenter demo (step 5) and one for
take-home. Same task, model, prompt and turn cap as the exercise, the same
trace, and every run adds a row to the same results table.

**These scripts run shell commands on your machine with no sandbox.**
Each works on a fresh copy of the task under `runs/`, the shells get only
`PATH` and `HOME` from your environment (no API keys), and the test files
are read-only. None of that is isolation: a command can reach anything you
can. That's why they're a demo and a take-home, not the exercise. Read a
script before you run it.

Run every command from `block4_production_harnesses/`.

| Script | Harness and tools | Used for |
|---|---|---|
| `run_openai_shell.py` | OpenAI Agents, one shell tool we wrote | demo: step 1's harness, given a shell |
| `run_claude.py` | Claude Agent SDK, Claude Code's whole kit, Bash included | demo: what a product gives you out of the box |
| `run_deepagents.py` | Deep Agents, its own tools plus `execute` (its shell) | take-home |

## The demo: the same task, four tool sets

```bash
uv run tool_design/run_openai_shell.py
```

```bash
uv run tool_design/run_claude.py
```

With steps 1 and 4 from the exercise, that's one task through four tool
sets:

| Run | Tools | Turns | Tool calls | Tokens sent |
|---|---|---|---|---|
| step 1, `openai_agents/run.py` | our four file tools | 26–46 | 278–315 | 0.62–1.29M |
| step 4, `openai_agents/run_replace.py` | file tools + `replace_in_files` | 23–35 | 35–88 | 0.22–0.69M |
| `run_openai_shell.py` | one shell tool | 20–25 | 19–24 | 0.16–0.43M |
| `run_claude.py` | Claude Code's kit, Bash included | 16–23 | 17–23 | 0.41–0.61M |

(GLM-5.3-Flash, three to six runs each, all solved. Step 1's numbers come from
the same harness and tools run three times in a row.)

**File tools:** the agent rewrites ~130 files one `write_file` at a time,
as your h2 and h3 did.

**A designed tool:** `replace_in_files` cut the calls from about 280 to
35 to 88 (14 to 27 of them renames). Tokens sent fell less reliably,
because they follow turns; tokens written fell from ~25k to ~3k. How it
was designed is below.

**A shell:** the agent greps for the old names and writes a rename
script. As fast, and it works on tasks nobody anticipated. But nothing
in a shell tool can tell which commands are safe: a hook that reads each
command can always be written around (`python -c`, a script file, even
`conftest.py`, which the tests run). Before the test files were
read-only, one run's global `sed` renamed `post` to `record` everywhere,
including the webhook and a test file, and never recovered.

**Where each fits:** a shell for open-ended work you can sandbox; a
designed tool for repetitive or consequential work, where you need to say
exactly what it can't do; no shell without a sandbox. Claude Code ships
Bash with permission rules, hooks and sandboxing for the same reason.

**Why not OpenAI's own shell tools?** `ShellTool`, `LocalShellTool` and
`ApplyPatchTool` are built for OpenAI's Responses API. On GLM through our
provider they don't work: over chat completions the SDK refuses them, and
over the Responses API the gateway rejects `ShellTool` and accepts
`LocalShellTool` without ever showing it to the model. So the shell here
is a dozen lines we wrote (`ws_shell` in `common.py`).

## How `replace_in_files` was designed

**The insight came from the trace.** Watching the file-tools run, the
agent reads `MIGRATION.md` and the tests, and from then on it knows the
job: about 14 rename rules (8 documented, the rest found in the tests).
Then it spends some 280 calls applying them, one `write_file` per file,
re-sending a whole file to change a few words. Most of its output tokens
go to copying code it isn't changing. The model's understanding isn't the
bottleneck; the tool's granularity is. The work comes one *rule* at a
time; the tool works one *file* at a time. So the tool's unit became the
rule.

**The choices, and what each trades:**

- **Whole words, in code, strings and comments.** A regex word boundary,
  so renaming `post` leaves `posted` alone. It deliberately reaches into
  strings, because the v1 field names also appear as dict keys. A
  code-aware rename (through the syntax tree) would be more precise and
  miss those keys.
- **Test files are never touched.** The same rule `verify()` uses (anything
  under `tests/`, `test_*.py`, `conftest.py`). Skipped files are counted in
  the result, so the model sees the tool held the line. Because the
  arguments are structured, this check is exact. A shell can't offer that.
- **Task knowledge stays outside the tool.** It doesn't know `webhook.py`
  is special; it takes an `exclude` list, and spotting the trap is the
  agent's job. (It excluded `webhook.py` on every rename in our runs.)
  A tool that hardcoded it would only work for this task.
- **A dry run before a real run.** `dry_run=true` lists the files and
  counts it would change. It doubles as a search: where does this name
  still appear?
- **Narrow inputs.** `old` and `new` must each be a single identifier, so
  no regex surprises and no multi-word replacements.
- **A small result.** The files changed with their counts, at most 40
  listed: Block 3's lesson that tool output is context you pay for on
  every later turn.
- **The file tools stay.** Anything that isn't a rename still goes through
  `read_file` and `write_file`.

**What it can't do:** change a signature, move code between files, or
rename something that isn't a whole identifier. It also can't tell two
different things that share a name apart: the reason `exclude` and
`dry_run` exist.

## Take-home: Deep Agents with a shell

```bash
uv run tool_design/run_deepagents.py
```

In the exercise, Deep Agents gets only its own file tools and usually runs
out of budget. Here its backend adds `execute`, a shell. Same harness,
same budget: 20 to 26 turns, 26 to 30 calls, 0.31 to 0.45M tokens, solved
every time. We also gave Pydantic AI and ADK the same shell tool as
OpenAI: 14 to 19 calls. Every harness given a shell scripted the rename.
The harness didn't decide the strategy; the tools did.

Ideas to try:

- Add `replace_in_files` to another harness, or to Deep Agents alongside
  its own tools. Does it reach for it?
- Give `replace_in_files` a mistake to make: drop the exclude list and see
  whether the agent still protects `webhook.py`.
- Put a `PreToolUse` hook on Claude's Bash that blocks commands mentioning
  `tests/`, then look for a command that gets past it.

## Every run is graded the same way

Against the **original** tests: a run that changed, added or deleted a
test file fails, whatever pytest says, and so does one that ran the tests
on modified ones. The originals are restored before the final pytest, so
the summary shows where the code really stands. The cap is
`BLOCK4_MAX_TURNS` (default 50 model calls, subagents included).
