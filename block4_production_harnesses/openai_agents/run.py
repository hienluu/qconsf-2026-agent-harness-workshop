"""fix_bug through the OpenAI Agents SDK.

    uv run --group block4 openai_agents/run.py       (from block4_production_harnesses/)

Where it came from: model-native — a harness co-designed with the vendor's models,
organized around a trusted control plane (loop, handoffs, guardrails,
sessions) over untrusted compute. Notice what's built into the loop here that the
others leave to you (guardrails, handoffs as primitives) and what we must
still write ourselves for this task: the three workspace tools.

Provider note: the SDK defaults to OpenAI's Responses API; pointing it at
an OpenAI-compatible provider means swapping in a chat-completions client —
two lines, officially supported, but the defaults show you who the harness
expects you to be running.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import trace_cost, TASK, TASK_MAX_TURNS, new_turn, prepare_workspace, receipt, trace_key, trace_say, trace_tool, verify, ws_list, ws_read, ws_run_tests, ws_write  # noqa: E402

from agents import (  # noqa: E402
    Agent,
    RunHooks,
    OpenAIChatCompletionsModel,
    Runner,
    function_tool,
    set_tracing_disabled,
)
from openai import AsyncOpenAI  # noqa: E402

load_dotenv()
NAME = "openai_agents"
workspace: Path


@function_tool
def list_files() -> str:
    """List every file in the workspace as relative paths."""
    trace_tool(NAME, "list_files")
    return ws_list(workspace)


@function_tool
def read_file(path: str) -> str:
    """Read one file, path relative to the workspace."""
    trace_tool(NAME, "read_file", f"path={path!r}")
    return ws_read(workspace, path)


@function_tool
def write_file(path: str, content: str) -> str:
    """Overwrite one file, path relative to the workspace."""
    trace_tool(NAME, "write_file", f"path={path!r}, {len(content)} chars")
    return ws_write(workspace, path, content)


@function_tool
def run_tests() -> str:
    """Run pytest in the workspace; done means all tests pass."""
    trace_tool(NAME, "run_tests")
    return ws_run_tests(workspace)


async def main() -> int:
    global workspace
    workspace = prepare_workspace(NAME)
    trace_key(NAME, ["list_files", "read_file", "write_file", "run_tests"], "")

    # Redirect the harness from its home (OpenAI's Responses API) to the
    # workshop provider's OpenAI-compatible chat-completions endpoint. An
    # explicit model object — a bare "org/model" string would be parsed as
    # a provider prefix by the SDK's model router.
    set_tracing_disabled(True)  # tracing ships to OpenAI's platform by default
    model = OpenAIChatCompletionsModel(
        model=os.environ["MODEL"],
        openai_client=AsyncOpenAI(
            base_url=os.environ["PROVIDER_BASE_URL"],
            api_key=os.environ["PROVIDER_API_KEY"],
        ),
    )

    agent = Agent(
        name="bug-fixer",
        model=model,
        instructions=(
            "You fix bugs in a small Python workspace using the provided "
            "tools. The task is complete only when run_tests reports every "
            "test passing."
        ),
        tools=[list_files, read_file, write_file, run_tests],
    )

    # The SDK owns the loop, so a turn number has to come from its hooks.
    # RunHooks fires on_llm_start once per model request — that IS a turn.
    class Watch(RunHooks):
        """RunHooks is the SDK's pluggability seam: on_llm_start marks a
        turn, on_llm_end hands back that request's usage — so the cost
        curve from Block 3 is visible per turn instead of only at the end."""

        total = 0

        async def on_llm_start(self, context, agent, system_prompt, input_items):
            new_turn()

        async def on_llm_end(self, context, agent, response):
            # Mid-run narration: the model's own text for this turn, which a
            # plain Runner.run() only ever hands back as final_output.
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
        result = await Runner.run(agent, TASK, max_turns=TASK_MAX_TURNS,
                                  hooks=Watch())
        trace_say(NAME, str(result.final_output))
    except Exception as exc:  # turn-cap etc. are outcomes, not crashes
        print(f"[{NAME}] run ended without finishing: {exc}")
    solved = verify(NAME, workspace, started) == 0
    receipt(NAME, script=__file__, started=started, solved=solved,
        origin="model-native (guardrails/handoffs as loop primitives)",
        loop_owner="theirs — Runner owns it",
        tools_we_wrote=["list_files", "read_file", "write_file", "run_tests"],
        tools_harness_shipped="none for this task (sandbox tools exist on OpenAI infra)",
        provider_friction="1 workaround: explicit model object (org/model parses as provider prefix); tracing to OpenAI off by hand")
    return 0 if solved else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
