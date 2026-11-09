"""The migration through the OpenAI Agents SDK, with a tool designed for it.

    uv run openai_agents/run_replace.py      (from block4_production_harnesses/)

The third of the OpenAI trio, identical to run_openai_files.py except for
one extra tool: replace_in_files, a whole-word rename across the source.

- run_openai_files.py: four file tools. Safe, slow: one write per file.
- run_openai_shell.py: one shell tool. Fast, and nothing in the tool can
  stop a command from touching what it shouldn't.
- this script: the file tools plus a tool we designed for renames. Its
  guardrails live inside it, because its arguments are structured: it
  never touches a test file, takes an exclude list (the webhook's `post`
  must keep its name), and can preview a change before making it.

Why this tool: in the file-tools trace, the agent knows the ~14 rename
rules early, then spends ~280 calls applying them one file at a time. The
work comes one rule at a time, so this tool's unit is the rule. Design
notes and trade-offs: tool_design/README.md.

The question for the room: does a designed tool get the shell's leverage
while keeping the file tools' guardrails?
"""

import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tool_design"))  # the shared trace
from common import SYSTEM_PROMPT, MIGRATION_MAX_TURNS, REFACTOR_SOURCE, REFACTOR_TASK, is_test_path, prepare_workspace, receipt, verify, ws_list, ws_read, ws_run_tests, ws_write  # noqa: E402
from migration_trace import Trace  # noqa: E402

from agents import Agent, OpenAIChatCompletionsModel, RunHooks, Runner, function_tool, set_tracing_disabled  # noqa: E402
from openai import AsyncOpenAI  # noqa: E402

load_dotenv()
NAME = "migration_openai_replace"
workspace: Path


@function_tool
def list_files() -> str:
    """List every file in the workspace as relative paths."""
    return ws_list(workspace)


@function_tool
def read_file(path: str) -> str:
    """Read one file, path relative to the workspace."""
    return ws_read(workspace, path)


@function_tool
def write_file(path: str, content: str) -> str:
    """Overwrite one file, path relative to the workspace."""
    return ws_write(workspace, path, content)


@function_tool
def run_tests() -> str:
    """Run pytest in the workspace; done means all tests pass."""
    return ws_run_tests(workspace)


@function_tool
def replace_in_files(old: str, new: str, exclude: list[str] | None = None, dry_run: bool = False) -> str:
    """Rename an identifier across every .py file in the workspace: replaces
    `old` with `new` wherever it appears as a whole word (in code, strings
    and comments). Test files are never changed. `exclude` lists files to
    leave alone (paths relative to the workspace). With dry_run=true, only
    reports where it would change, without changing anything."""
    return rename_everywhere(workspace, old, new, exclude, dry_run)


def rename_everywhere(workspace: Path, old: str, new: str, exclude=None, dry_run: bool = False) -> str:
    """The tool's logic, as a plain function so it can be tested alone."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", old or "") or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", new or ""):
        return "error: old and new must each be a single identifier, like make_ledger"
    skip = {str(Path(e)).lstrip("./") for e in (exclude or [])}
    word = re.compile(rf"\b{re.escape(old)}\b")
    changed, skipped_tests, total = [], 0, 0
    for f in sorted(workspace.rglob("*.py")):
        rel = f.relative_to(workspace)
        if "__pycache__" in rel.parts:
            continue
        if str(rel) in skip:
            continue
        text = f.read_text()
        n = len(word.findall(text))
        if not n:
            continue
        if is_test_path(rel):              # the guardrail: structured, so exact
            skipped_tests += 1
            continue
        total += n
        changed.append(f"{rel} ({n})")
        if not dry_run:
            f.write_text(word.sub(new, text))
    lines = changed[:40] + ([f"... and {len(changed) - 40} more files"] if len(changed) > 40 else [])
    if skipped_tests:
        lines.append(f"(left {skipped_tests} test file(s) alone: tests are never changed)")
    verb = "would replace" if dry_run else "replaced"
    lines.append(f"{verb} {total} occurrence(s) of {old!r} with {new!r} in {len(changed)} file(s)")
    return "\n".join(lines)


class Watch(RunHooks):
    """Same hooks as run_openai_files.py: one model response is one turn."""

    def __init__(self, trace: Trace):
        self.trace = trace

    async def on_llm_start(self, context, agent, system_prompt, input_items):
        self.trace.new_turn()

    async def on_llm_end(self, context, agent, response):
        for item in getattr(response, "output", None) or []:
            if getattr(item, "type", "") == "function_call":
                try:
                    args = json.loads(item.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                self.trace.call(item.name, args)
            for c in getattr(item, "content", None) or []:
                self.trace.text(getattr(c, "text", "") or "")
        u = getattr(response, "usage", None)
        if u:
            details = getattr(u, "input_tokens_details", None)
            self.trace.usage(u.input_tokens, getattr(details, "cached_tokens", 0), u.output_tokens)

    async def on_tool_end(self, context, agent, tool, result):
        self.trace.result(tool.name, result)


async def main() -> int:
    global workspace
    workspace = prepare_workspace(NAME, source=REFACTOR_SOURCE)
    trace = Trace("openai-replace", workspace)

    set_tracing_disabled(True)  # tracing ships to OpenAI's platform by default
    model = OpenAIChatCompletionsModel(
        model=os.environ["MODEL"],
        openai_client=AsyncOpenAI(base_url=os.environ["PROVIDER_BASE_URL"],
                                  api_key=os.environ["PROVIDER_API_KEY"]),
    )
    agent = Agent(
        name="migrator",
        model=model,
        instructions=SYSTEM_PROMPT,
        tools=[list_files, read_file, write_file, run_tests, replace_in_files],
    )

    started = time.monotonic()
    try:
        await Runner.run(agent, REFACTOR_TASK, max_turns=MIGRATION_MAX_TURNS, hooks=Watch(trace))
        trace.flush()
    except Exception as exc:  # running out of turns is an outcome, not a crash
        trace.flush()
        print(f"[openai-replace] run ended without finishing: {exc}")
    solved = verify(NAME, workspace, started) == 0
    trace.finish(script="openai_replace", solved=solved, started=started,
                 tools="ours: file tools + replace_in_files", tools_we_wrote=5)
    # It's step 4 of Block 4's exercise, so it also goes in the exercise's
    # results table, right next to step 1 (openai_agents/run.py).
    receipt("openai_agents+replace", script=__file__, started=started, solved=solved,
        origin="model-native (guardrails/handoffs as loop primitives)",
        loop_owner="theirs: Runner owns it",
        tools_we_wrote=["list_files", "read_file", "write_file", "run_tests", "replace_in_files"],
        tools_harness_shipped="none for this task",
        provider_friction="same as openai_agents",
        measured={"turns": trace.turn, "tool_calls": sum(trace.counts.values()),
                  "tokens_sent": sum(s for s, _, _ in trace.tokens.values())})
    return 0 if solved else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
