"""The migration through the OpenAI Agents SDK, with a shell tool we wrote.

    uv run migration/run_openai_shell.py      (from block4_production_harnesses/)

Identical to run_openai_files.py except for the tools: one `shell` function
tool (ws_shell in common.py, a dozen lines) instead of four file tools. (The SDK's
own shell tools don't work on our model; see run_openai_files.py.) Same
harness, same model, same task. If the agent starts writing scripts the
way Claude Code's harness does, the shell made the difference, not the
harness.

The shell runs in the run's copy of the task, with only PATH and HOME from
our environment (so no API keys), output capped at 30,000 characters. It
is not a sandbox: a command can reach anything you can.
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
from common import SYSTEM_PROMPT, MIGRATION_MAX_TURNS, REFACTOR_SOURCE, REFACTOR_TASK, prepare_workspace, verify, ws_shell  # noqa: E402
from migration_trace import Trace  # noqa: E402

from agents import Agent, OpenAIChatCompletionsModel, RunHooks, Runner, function_tool, set_tracing_disabled  # noqa: E402
from openai import AsyncOpenAI  # noqa: E402

load_dotenv()
NAME = "migration_openai_shell"
workspace: Path


@function_tool
def shell(command: str) -> str:
    """Run a shell command in the workspace and return its output and exit code."""
    return ws_shell(workspace, command)

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
        self.trace.result(tool.name, result)   # the trace reads the exit code


async def main() -> int:
    global workspace
    workspace = prepare_workspace(NAME, source=REFACTOR_SOURCE)
    trace = Trace("openai-shell", workspace)

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
        tools=[shell],
    )

    started = time.monotonic()
    try:
        await Runner.run(agent, REFACTOR_TASK, max_turns=MIGRATION_MAX_TURNS, hooks=Watch(trace))
        trace.flush()
    except Exception as exc:  # running out of turns is an outcome, not a crash
        trace.flush()
        print(f"[openai-shell] run ended without finishing: {exc}")
    solved = verify(NAME, workspace, started) == 0
    trace.finish(script="openai_shell", solved=solved, started=started,
                 tools="ours: one shell tool", tools_we_wrote=1)
    return 0 if solved else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
