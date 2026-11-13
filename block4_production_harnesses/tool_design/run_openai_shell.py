"""Presenter demo: the OpenAI Agents SDK with a shell tool we wrote.

    uv run tool_design/run_openai_shell.py      (from block4_production_harnesses/)

Identical to step 1 (openai_agents/run.py) except for the tools: one
`shell` function tool (ws_shell in common.py, a dozen lines) instead of
four file tools. Same harness, same model, same task: if the agent starts
writing scripts, the shell made the difference, not the harness.

Why not OpenAI's own shell tools? ShellTool, LocalShellTool and
ApplyPatchTool are built for OpenAI's Responses API. On GLM through our
provider they don't work: over chat completions the SDK refuses them, and
over the Responses API the gateway rejects ShellTool and accepts
LocalShellTool's `local_shell` type without ever showing it to the model.

The shell runs in the run's copy of the task, with only PATH and HOME from
our environment (so no API keys), output capped at 30,000 characters. It
is not a sandbox: a command can reach anything you can.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import end_turn, SYSTEM_PROMPT, trace_cost, TASK, TASK_MAX_TURNS, new_turn, prepare_workspace, receipt, trace_key, trace_result, trace_say, trace_tool, verify, ws_shell  # noqa: E402

from agents import Agent, OpenAIChatCompletionsModel, RunHooks, Runner, function_tool, set_tracing_disabled  # noqa: E402
from openai import AsyncOpenAI  # noqa: E402

load_dotenv()
NAME = "openai_agents+shell"
workspace: Path


@function_tool
def shell(command: str) -> str:
    """Run a shell command in the workspace and return its output and exit code."""
    call = trace_tool(NAME, "shell", command)
    out = ws_shell(workspace, command)
    trace_result(NAME, "shell", out, call=call)
    return out


async def main() -> int:
    global workspace
    workspace = prepare_workspace(NAME)
    trace_key(NAME, ["shell"])

    set_tracing_disabled(True)  # tracing ships to OpenAI's platform by default
    model = OpenAIChatCompletionsModel(
        model=os.environ["LLM_MODEL"],
        openai_client=AsyncOpenAI(base_url=os.environ["LLM_BASE_URL"],
                                  api_key=os.environ["LLM_API_KEY"]),
    )
    agent = Agent(name="migrator", model=model, instructions=SYSTEM_PROMPT, tools=[shell])

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
        tools_we_wrote=["shell"],
        tools_harness_shipped="none that work on our model (ShellTool, LocalShellTool are Responses-API only)",
        provider_friction="same as openai_agents")
    return 0 if solved else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
