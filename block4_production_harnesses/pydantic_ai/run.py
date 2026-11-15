"""The Block 4 task through Pydantic AI.

    uv run pydantic_ai/run.py         (from block4_production_harnesses/)

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
from pydantic_ai.messages import FunctionToolCallEvent, FunctionToolResultEvent, PartDeltaEvent, PartStartEvent, RetryPromptPart, TextPart, TextPartDelta  # noqa: E402
from common import end_turn, trace_result, tool_detail, SYSTEM_PROMPT, set_tokens_sent, trace_reject, TASK, TASK_MAX_TURNS, new_turn, prepare_workspace, receipt, trace_key, trace_say, trace_tool, verify, ws_list, ws_read, ws_run_tests, ws_write, sampling  # noqa: E402

from pydantic_ai import Agent, UsageLimits  # noqa: E402
from pydantic_ai.models.openai import OpenAIChatModel  # noqa: E402
from pydantic_ai.providers.openai import OpenAIProvider  # noqa: E402

load_dotenv()
NAME = "pydantic_ai"
workspace: Path

# Provider-portable by construction: any OpenAI-compatible endpoint is a
# constructor argument, not an environment contract.
model = OpenAIChatModel(
    os.environ["LLM_MODEL"],
    provider=OpenAIProvider(
        base_url=os.environ["LLM_BASE_URL"],
        api_key=os.environ["LLM_API_KEY"],
    ),
)

agent = Agent(
    model,
    instructions=SYSTEM_PROMPT,
    model_settings=sampling() or None,   # temperature: see common.temperature_setting
)


@agent.tool_plain
def list_files() -> str:
    """List every file in the workspace as relative paths."""
    trace_tool(NAME, "list_files")
    return ws_list(workspace)


@agent.tool_plain
def read_file(path: str) -> str:
    """Read one file, path relative to the workspace."""
    trace_tool(NAME, "read_file", tool_detail({"path": path}))
    return ws_read(workspace, path)


@agent.tool_plain
def write_file(path: str, content: str) -> str:
    """Overwrite one file, path relative to the workspace."""
    trace_tool(NAME, "write_file", tool_detail({"path": path, "content": content}))
    return ws_write(workspace, path, content)


@agent.tool_plain
def run_tests() -> str:
    """Run pytest in the workspace; done means all tests pass."""
    call = trace_tool(NAME, "run_tests")
    out = ws_run_tests(workspace)
    trace_result(NAME, "run_tests", out, call=call)
    return out


def main() -> int:
    global workspace
    workspace = prepare_workspace(NAME)
    trace_key(NAME, ["list_files", "read_file", "write_file", "run_tests"])
    started = time.monotonic()
    # The SDK owns the loop; event_stream_handler fires once per model
    # request, which is the only hook here that corresponds to a turn.
    async def count_turns(ctx, stream):
        # Fires twice per turn: once for the model's response stream, once
        # for the tool-result phase. Only the first is a model request.
        first = True
        said: list[str] = []
        async for ev in stream:
            if first:
                first = False
                if not isinstance(ev, (FunctionToolCallEvent, FunctionToolResultEvent)):
                    new_turn()
            # Text streams in as a start event plus deltas, so collect the
            # pieces and print the sentence once instead of a letter at a time.
            if isinstance(ev, PartStartEvent) and isinstance(getattr(ev, "part", None), TextPart):
                said.append(ev.part.content or "")
            elif isinstance(ev, PartDeltaEvent) and isinstance(getattr(ev, "delta", None), TextPartDelta):
                said.append(ev.delta.content_delta or "")
            # The typed core's whole pitch: a tool call whose arguments don't
            # validate never reaches the tool. It comes back as a
            # RetryPromptPart instead — the same "feed the error back" move
            # you hand-wrote in h2, here for free and before execution.
            elif isinstance(ev, FunctionToolResultEvent) and isinstance(ev.part, RetryPromptPart):
                trace_reject(NAME, str(getattr(ev.part, "content", ""))[:90])
        if "".join(said).strip():
            trace_say(NAME, "".join(said))

    try:
        result = agent.run_sync(TASK, event_stream_handler=count_turns,
                                usage_limits=UsageLimits(request_limit=TASK_MAX_TURNS))
        trace_say(NAME, str(result.output))
        end_turn()
        print(f"[{NAME}] usage: {result.usage}")
        set_tokens_sent(result.usage.input_tokens, result.usage.output_tokens,
                        result.usage.cache_read_tokens)
    except Exception as exc:  # hitting the request limit is an outcome, not a crash
        end_turn()
        print(f"[{NAME}] run ended without finishing: {type(exc).__name__}: {exc}")
    solved = verify(NAME, workspace, started) == 0
    receipt(NAME, script=__file__, started=started, solved=solved,
        origin="composable (typed core, capabilities you add one at a time)",
        loop_owner="theirs: lean typed loop",
        tools_we_wrote=["list_files", "read_file", "write_file", "run_tests"],
        tools_harness_shipped="none by default (capabilities opt-in); cost accounting free",
        provider_friction="none: the provider is a constructor argument")
    return 0 if solved else 1


if __name__ == "__main__":
    raise SystemExit(main())
