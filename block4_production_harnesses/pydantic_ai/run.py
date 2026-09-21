"""fix_bug through Pydantic AI.

    uv run --group block4 pydantic_ai/run.py         (from block4_production_harnesses/)

Where it came from: composable — a lean typed core, with harness behavior
assembled from capabilities you opt into rather than a bundle you accept.
Notice the provider portability: this is the only Block 4 harness with no
home vendor at all — the model is just a parameter. And notice the typed
tools: signatures + docstrings become the schema; a wrong type is a
retryable validation error, not a runtime surprise.
"""

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pydantic_ai.messages import FunctionToolCallEvent, FunctionToolResultEvent  # noqa: E402
from common import TASK, new_turn, prepare_workspace, receipt, trace_key, trace_say, trace_tool, verify, ws_list, ws_read, ws_run_tests, ws_write  # noqa: E402

from pydantic_ai import Agent  # noqa: E402
from pydantic_ai.models.openai import OpenAIChatModel  # noqa: E402
from pydantic_ai.providers.openai import OpenAIProvider  # noqa: E402

load_dotenv()
NAME = "pydantic_ai"
workspace: Path

# Provider-portable by construction: any OpenAI-compatible endpoint is a
# constructor argument, not an environment contract.
model = OpenAIChatModel(
    os.environ["MODEL"],
    provider=OpenAIProvider(
        base_url=os.environ["PROVIDER_BASE_URL"],
        api_key=os.environ["PROVIDER_API_KEY"],
    ),
)

agent = Agent(
    model,
    instructions=(
        "You fix bugs in a small Python workspace using the provided tools. "
        "The task is complete only when run_tests reports every test passing."
    ),
)


@agent.tool_plain
def list_files() -> str:
    """List every file in the workspace as relative paths."""
    trace_tool(NAME, "list_files")
    return ws_list(workspace)


@agent.tool_plain
def read_file(path: str) -> str:
    """Read one file, path relative to the workspace."""
    trace_tool(NAME, "read_file", f"path={path!r}")
    return ws_read(workspace, path)


@agent.tool_plain
def write_file(path: str, content: str) -> str:
    """Overwrite one file, path relative to the workspace."""
    trace_tool(NAME, "write_file", f"path={path!r}, {len(content)} chars")
    return ws_write(workspace, path, content)


@agent.tool_plain
def run_tests() -> str:
    """Run pytest in the workspace; done means all tests pass."""
    trace_tool(NAME, "run_tests")
    return ws_run_tests(workspace)


def main() -> int:
    global workspace
    workspace = prepare_workspace(NAME)
    trace_key(NAME, ["list_files", "read_file", "write_file", "run_tests"], "")
    started = time.monotonic()
    # The SDK owns the loop; event_stream_handler fires once per model
    # request, which is the only hook here that corresponds to a turn.
    async def count_turns(ctx, stream):
        # Fires twice per turn: once for the model's response stream, once
        # for the tool-result phase. Only the first is a model request.
        first = True
        async for ev in stream:
            if first:
                first = False
                if not isinstance(ev, (FunctionToolCallEvent, FunctionToolResultEvent)):
                    new_turn()

    result = agent.run_sync(TASK, event_stream_handler=count_turns)
    trace_say(NAME, str(result.output))
    print(f"[{NAME}] usage: {result.usage}")
    solved = verify(NAME, workspace, started) == 0
    receipt(NAME, script=__file__, started=started, solved=solved,
        origin="composable (typed core, capabilities you add one at a time)",
        loop_owner="theirs — lean typed loop",
        tools_we_wrote=["list_files", "read_file", "write_file", "run_tests"],
        tools_harness_shipped="none by default (capabilities opt-in); cost accounting free",
        provider_friction="none — provider is a constructor argument")
    return 0 if solved else 1


if __name__ == "__main__":
    raise SystemExit(main())
