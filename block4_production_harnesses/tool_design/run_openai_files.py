"""The migration through the OpenAI Agents SDK, with file tools.

    uv run tool_design/run_openai_files.py      (from block4_production_harnesses/)

The SDK's own shell tools (ShellTool, LocalShellTool, ApplyPatchTool) are
built for OpenAI's Responses API. On GLM through our provider they don't
work. Over chat completions the SDK refuses them outright. Over the
Responses API, the gateway rejects ShellTool, and it accepts
LocalShellTool's `local_shell` type but never presents it to the model:
in three raw requests the model said it had no tools, or made up the
command's output. The same request with an ordinary function tool got a
proper call three times out of three. So on this model, a shell is
something you write. Here: the same four file tools
as Block 2 (list, read, write, run the tests).

Its twin, run_openai_shell.py, is identical except that it gets one shell
tool instead. Same harness, different tools: if the behavior changes, the
tools changed it.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import SYSTEM_PROMPT, MIGRATION_MAX_TURNS, REFACTOR_SOURCE, REFACTOR_TASK, prepare_workspace, verify, ws_list, ws_read, ws_run_tests, ws_write  # noqa: E402
from migration_trace import Trace  # noqa: E402

from agents import Agent, OpenAIChatCompletionsModel, RunHooks, Runner, function_tool, set_tracing_disabled  # noqa: E402
from openai import AsyncOpenAI  # noqa: E402

load_dotenv()
NAME = "migration_openai_files"
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


class Watch(RunHooks):
    """The SDK owns the loop; its hooks are where we see inside it. One
    model response is one turn: its text and tool calls arrive together in
    on_llm_end, before any tool runs; each result arrives in on_tool_end."""

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
    trace = Trace("openai-files", workspace)

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
        tools=[list_files, read_file, write_file, run_tests],
    )

    started = time.monotonic()
    try:
        result = await Runner.run(agent, REFACTOR_TASK, max_turns=MIGRATION_MAX_TURNS, hooks=Watch(trace))
        trace.flush()
    except Exception as exc:  # running out of turns is an outcome, not a crash
        trace.flush()
        print(f"[openai-files] run ended without finishing: {exc}")
    solved = verify(NAME, workspace, started) == 0
    trace.finish(script="openai_files", solved=solved, started=started,
                 tools="ours: list/read/write files, run_tests", tools_we_wrote=4)
    return 0 if solved else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
