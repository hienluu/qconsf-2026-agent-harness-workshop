# The migration with a shell: presenter demo and take-home

In Block 4's exercise, every harness gets file tools: read a file, write a
file, run the tests. This folder asks what happens when you hand the agent
a **shell** instead. Same task (Blocks 2 and 3's migration), same model,
same turn cap.

**These scripts run shell commands on your machine with no sandbox.** Each
one works on a fresh copy of the task under `runs/`, gets only `PATH` and
`HOME` from your environment (no API keys), and the test files are made
read-only. None of that is isolation: a command can reach anything you
can. That's why they're a presenter demo and a take-home, not the
exercise. Read a script before you run it.

Run every command from `block4_production_harnesses/`.

## The presenter demo: one harness, two tool sets

The OpenAI Agents SDK, twice. The only difference is the tools.

```bash
uv run migration/run_openai_files.py
```

```bash
uv run migration/run_openai_shell.py
```

| Script | Tools | Turns | Tool calls | Tokens sent |
|---|---|---|---|---|
| `run_openai_files.py` | our four file tools | 20–27 | 187–275 | 0.62M |
| `run_openai_shell.py` | one shell tool | 20–26 | 19–25 | 0.25–0.50M |

(GLM-5.3-Flash, three to four runs each; tokens from one to three.)

With file tools, the agent rewrites the ~130 affected files one
`write_file` at a time, as your h2 and h3 did. With a shell, it greps for
the old names and writes a rename script. **Tool calls drop about tenfold;
turns don't move.** Cost follows turns more than calls, so tokens fall far
less than calls do.

The shell cuts both ways. In one run, before the test files were
read-only, the agent ran one global `sed` renaming `post` to `record`. That
also renamed `webhook.py`'s HTTP `post()`, which the file says is not part
of the ledger API, and it rewrote a test file. It never recovered and hit
the turn cap. One command, forty files, tests included: the same leverage
that saves 250 calls. Block 3's test guardrail worked by checking each
`write_file`; a shell has no such choke point.

Why not OpenAI's own shell tools? `ShellTool`, `LocalShellTool` and
`ApplyPatchTool` are built for OpenAI's Responses API. On GLM through our
provider they don't work: over chat completions the SDK refuses them, and
over the Responses API the gateway rejects `ShellTool` and accepts
`LocalShellTool` without ever showing it to the model. So the shell here
is a dozen lines we wrote (`ws_shell` in `common.py`).

## Take-home: the rest

| Script | Harness and tools | What to look for |
|---|---|---|
| `run_claude.py` | Claude Agent SDK, Claude Code's full kit including Bash | the harness that ships a shell: it scripts the rename unprompted |
| `run_deepagents.py` | Deep Agents, its own file tools plus `execute` (its shell) | same, from a different vendor |
| `run_pydantic_shell.py` | Pydantic AI, our shell tool | malformed calls rejected before they run (`✗`) |
| `run_adk_shell.py` | Google ADK, our shell tool | the event stream; the cap is `max_llm_calls` |

Every one of them, given a shell, scripted the migration: 12 to 42 tool
calls where file tools take 187 to 299. The harness didn't decide the
strategy; the tools did.

Each run prints a Block 3-style trace (one header per turn, its calls, a
short result under each, `✗` for a failed command) and adds a row to
`runs/migration.jsonl`. The table at the end shows the latest run of each
script next to h2 and h3. Delete that file to start the table over.

## Every run is graded the same way

Against the **original** tests: a run that changed, added or deleted a
test file fails, whatever pytest says, and its originals are restored
before the final pytest so the summary shows where the code really stands.
The cap is `BLOCK4_MAX_TURNS` (default 50 model calls, subagents
included).
