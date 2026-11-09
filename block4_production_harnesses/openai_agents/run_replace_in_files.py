"""Step 4: the OpenAI Agents SDK with a tool designed for the job.

    uv run openai_agents/run_replace_in_files.py       (from block4_production_harnesses/)

Identical to step 1 (openai_agents/run.py) except for one extra tool:
replace_in_files, a whole-word rename across the source in one call.

Why this tool: in step 1's trace, the agent knows the ~14 rename rules
early, then spends ~280 calls applying them one file at a time, re-sending
whole files to change a few words. The work comes one rule at a time, so
this tool's unit is the rule. Its guardrails live inside it, because its
arguments are structured: it never touches a test file, takes an exclude
list (the webhook's `post` must keep its name), and can preview a change
before making it. Design notes and trade-offs: tool_design/README.md.

The question: does a designed tool get a shell's leverage while keeping
the file tools' guardrails? (The shell is the presenter demo, in
tool_design/.)
"""

import asyncio
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import end_turn, spotlight, is_test_path, tool_detail, SYSTEM_PROMPT, trace_cost, TASK, TASK_MAX_TURNS, new_turn, prepare_workspace, receipt, trace_key, trace_result, trace_say, trace_tool, verify, ws_list, ws_read, ws_run_tests, ws_write  # noqa: E402

from agents import Agent, OpenAIChatCompletionsModel, RunHooks, Runner, function_tool, set_tracing_disabled  # noqa: E402
from openai import AsyncOpenAI  # noqa: E402

load_dotenv()
NAME = "openai_agents+replace_in_files"
workspace: Path


@function_tool
def list_files() -> str:
    """List every file in the workspace as relative paths."""
    trace_tool(NAME, "list_files")
    return ws_list(workspace)


@function_tool
def read_file(path: str) -> str:
    """Read one file, path relative to the workspace."""
    trace_tool(NAME, "read_file", tool_detail({"path": path}))
    return ws_read(workspace, path)


@function_tool
def write_file(path: str, content: str) -> str:
    """Overwrite one file, path relative to the workspace."""
    trace_tool(NAME, "write_file", tool_detail({"path": path, "content": content}))
    return ws_write(workspace, path, content)


@function_tool
def run_tests() -> str:
    """Run pytest in the workspace; done means all tests pass."""
    trace_tool(NAME, "run_tests")
    out = ws_run_tests(workspace)
    trace_result(NAME, "run_tests", out)
    return out


@function_tool
def replace_in_files(old: str, new: str, exclude: list[str] | None = None, dry_run: bool = False) -> str:
    """Rename an identifier across every .py file in the workspace: replaces
    `old` with `new` wherever it appears as a whole word (in code, strings
    and comments). Test files are never changed. `exclude` lists files to
    leave alone (paths relative to the workspace). With dry_run=true, only
    reports where it would change, without changing anything."""
    args = f"old={old!r}, new={new!r}" + (f", exclude={exclude}" if exclude else "") + (", dry_run=True" if dry_run else "")
    trace_tool(NAME, "replace_in_files", args)
    out = rename_everywhere(workspace, old, new, exclude, dry_run)
    trace_result(NAME, "replace_in_files", out)
    return out


def rename_everywhere(workspace: Path, old: str, new: str, exclude=None, dry_run: bool = False) -> str:
    """The tool's logic, as a plain function so it can be tested alone."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", old or "") or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", new or ""):
        return "error: old and new must each be a single identifier, like make_ledger"
    skip = {str(Path(e)).lstrip("./") for e in (exclude or [])}
    word = re.compile(rf"\b{re.escape(old)}\b")
    changed, skipped_tests, total = [], 0, 0
    for f in sorted(workspace.rglob("*.py")):
        rel = f.relative_to(workspace)
        if "__pycache__" in rel.parts or str(rel) in skip:
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


async def main() -> int:
    global workspace
    workspace = prepare_workspace(NAME)
    spotlight("replace_in_files")   # the tool this step is about: easy to spot as it scrolls
    trace_key(NAME, ["list_files", "read_file", "write_file", "run_tests", "replace_in_files"])

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

    class Watch(RunHooks):
        """Same hooks as step 1: one model request is one turn."""

        total = 0

        async def on_llm_start(self, context, agent, system_prompt, input_items):
            new_turn()

        async def on_llm_end(self, context, agent, response):
            for item in (getattr(response, "output", None) or []):
                for c in (getattr(item, "content", None) or []):
                    said = getattr(c, "text", None)
                    if said and said.strip():
                        trace_say(NAME, said)
            u = getattr(response, "usage", None)
            if u:
                Watch.total += u.input_tokens
                trace_cost(NAME, u.input_tokens, u.output_tokens, Watch.total)

    started = time.monotonic()
    try:
        result = await Runner.run(agent, TASK, max_turns=TASK_MAX_TURNS, hooks=Watch())
        trace_say(NAME, str(result.final_output))
    except Exception as exc:  # turn-cap etc. are outcomes, not crashes
        end_turn()
        print(f"[{NAME}] run ended without finishing: {exc}")
    solved = verify(NAME, workspace, started) == 0
    receipt(NAME, script=__file__, started=started, solved=solved,
        origin="model-native (guardrails/handoffs as loop primitives)",
        loop_owner="theirs: Runner owns it",
        tools_we_wrote=["list_files", "read_file", "write_file", "run_tests", "replace_in_files"],
        tools_harness_shipped="none for this task",
        provider_friction="same as openai_agents")
    return 0 if solved else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
