"""Optional: the migration through Pydantic AI, with a shell tool we wrote.

    uv run tool_design/run_pydantic_shell.py      (from block4_production_harnesses/)

Take-home or extra credit, for completeness. Pydantic AI ships no file or
shell tools (its bundled tools are web search, web fetch and image
generation), so like the OpenAI Agents SDK it gets the same shell tool
(ws_shell in common.py). If it also drops from ~190 tool calls to ~25,
that's a second harness showing the tools set the strategy, not the loop.

What to look for that's Pydantic AI's own: tool arguments are validated
against the function's type hints before the tool runs. A malformed call
comes back to the model as a retry prompt (printed as ✗), the recovery
you wrote by hand in h2.

The trace walks the run node by node with agent.iter(): a CallToolsNode
holds one model response (a turn), the next ModelRequestNode holds the
tool results.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import SYSTEM_PROMPT, MIGRATION_MAX_TURNS, REFACTOR_SOURCE, REFACTOR_TASK, prepare_workspace, verify, ws_shell  # noqa: E402
from migration_trace import Trace  # noqa: E402

from pydantic_ai import Agent, UsageLimits  # noqa: E402
from pydantic_ai.messages import RetryPromptPart, TextPart, ToolCallPart, ToolReturnPart  # noqa: E402
from pydantic_ai.models.openai import OpenAIChatModel  # noqa: E402
from pydantic_ai.providers.openai import OpenAIProvider  # noqa: E402

load_dotenv()
NAME = "migration_pydantic_shell"
workspace: Path

agent = Agent(
    OpenAIChatModel(os.environ["MODEL"], provider=OpenAIProvider(
        base_url=os.environ["PROVIDER_BASE_URL"], api_key=os.environ["PROVIDER_API_KEY"])),
    instructions=SYSTEM_PROMPT,
)


@agent.tool_plain
def shell(command: str) -> str:
    """Run a shell command in the workspace and return its output and exit code."""
    return ws_shell(workspace, command)


async def main() -> int:
    global workspace
    workspace = prepare_workspace(NAME, source=REFACTOR_SOURCE)
    trace = Trace("pydantic", workspace)

    started = time.monotonic()
    try:
        async with agent.iter(REFACTOR_TASK, usage_limits=UsageLimits(request_limit=MIGRATION_MAX_TURNS)) as run:
            async for node in run:
                if Agent.is_call_tools_node(node):
                    trace.new_turn()
                    response = node.model_response
                    for part in response.parts:
                        if isinstance(part, ToolCallPart):
                            trace.call(part.tool_name, part.args_as_dict())
                        elif isinstance(part, TextPart):
                            trace.text(part.content)
                    u = response.usage
                    trace.usage(u.input_tokens, u.cache_read_tokens, u.output_tokens)
                elif Agent.is_model_request_node(node):
                    for part in node.request.parts:
                        if isinstance(part, ToolReturnPart):
                            trace.result(part.tool_name, part.content)
                        elif isinstance(part, RetryPromptPart):
                            trace.failure(f"rejected before running: {part.model_response()}")
        trace.flush()
    except Exception as exc:  # hitting the request limit is an outcome, not a crash
        trace.flush()
        print(f"[pydantic] run ended without finishing: {type(exc).__name__}: {exc}")
    solved = verify(NAME, workspace, started) == 0
    trace.finish(script="pydantic_shell", solved=solved, started=started,
                 tools="ours: one shell tool", tools_we_wrote=1)
    return 0 if solved else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
