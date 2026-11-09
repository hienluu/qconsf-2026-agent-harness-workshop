# Tool design: the presenter demo and take-home

In Block 4's exercise, every harness gets file tools: read a file, write a
file, run the tests. They spend most of their calls changing one file at
a time. Step 3 asks what tool you'd design instead. Step 4 runs one answer,
a tool **designed** for the job (`openai_agents/run_replace.py`). This
folder holds the other answer, a **shell**, plus the baseline to compare
against. Same task (Blocks 2 and 3's migration), same model, prompt and
turn cap.

**The shell scripts run commands on your machine with no sandbox.** Each
works on a fresh copy of the task under `runs/`, gets only `PATH` and
`HOME` from your environment (no API keys), and the test files are made
read-only. None of that is isolation: a command can reach anything you
can. That's why these are a presenter demo and a take-home, not the
exercise. Read a script before you run it.

Run every command from `block4_production_harnesses/`.

## One harness, three tool sets

The OpenAI Agents SDK, three times. The only difference is the tools. In
the workshop you've run the first two already: step 1 is the same harness
and tools as `run_openai_files.py` (which prints this folder's trace and
table), and step 4 is `openai_agents/run_replace.py`. The presenter runs
the shell ones.

```bash
uv run tool_design/run_openai_files.py
```

```bash
uv run openai_agents/run_replace.py
```

```bash
uv run tool_design/run_openai_shell.py
```

Then Claude Code's harness with its own Bash, for what a product gives
you out of the box:

```bash
uv run tool_design/run_claude.py
```

| Script | Tools | Turns | Tool calls | Tokens sent |
|---|---|---|---|---|
| `run_openai_files.py` | our four file tools | 26–46 | 278–315 | 0.62–1.29M |
| `openai_agents/run_replace.py` | file tools + `replace_in_files` | 23–29 | 46–54 | 0.25–0.39M |
| `run_openai_shell.py` | one shell tool | 20–25 | 19–24 | 0.16–0.43M |
| `run_claude.py` | Claude Code's kit, Bash included | 16–23 | 17–23 | 0.41–0.61M |

(GLM-5.3-Flash, three runs each, all solved.)

**File tools:** the agent rewrites ~130 files one `write_file` at a time,
as your h2 and h3 did.

**A designed tool:** `replace_in_files` cut the calls from about 280 to
about 50 (14 to 25 of them renames). How it was designed is below.

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

## Take-home: the shell in the other harnesses

| Script | Harness and tools | Turns | Tool calls | Tokens sent |
|---|---|---|---|---|
| `run_deepagents.py` | Deep Agents, its own tools plus `execute` (its shell) | 20–26 | 26–30 | 0.31–0.45M |
| `run_pydantic_shell.py` | Pydantic AI, our shell tool | 18–20 | 17–19 | 0.29–0.38M |
| `run_adk_shell.py` | Google ADK, our shell tool | 15–20 | 14–19 | 0.21–0.38M |

Every harness given a shell scripted the rename, in 14 to 30 calls. That
includes Deep Agents, which ran out of budget in the exercise with only
its file tools. The harness didn't decide the strategy; the tools did.

Ideas to try:

- Add `replace_in_files` to another harness, or to Deep Agents alongside
  its own tools. Does it reach for it?
- Give `replace_in_files` a mistake to make: drop the exclude list and see
  whether the agent still protects `webhook.py`.
- Put a `PreToolUse` hook on Claude's Bash that blocks commands mentioning
  `tests/`, then look for a command that gets past it.

Each run prints a Block 3-style trace (one header per turn, its calls, a
short result under each, `✗` for a failed command) and adds a row to
`runs/migration.jsonl`. The table at the end shows the latest run of each
script next to h2 and h3. Delete that file to start the table over.

## Every run is graded the same way

Against the **original** tests: a run that changed, added or deleted a
test file fails, whatever pytest says, and so does one that ran the tests
on modified ones. The originals are restored before the final pytest, so
the summary shows where the code really stands. The cap is
`BLOCK4_MAX_TURNS` (default 50 model calls, subagents included).
