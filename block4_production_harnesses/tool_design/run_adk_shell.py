"""Optional: the migration through Google ADK, with a shell tool we wrote.

    uv run tool_design/run_adk_shell.py      (from block4_production_harnesses/)

Take-home or extra credit, for completeness. ADK's built-in code executor
runs only on Gemini, so on GLM it gets the same shell tool as the OpenAI
and Pydantic AI scripts (ws_shell in common.py). Same question: does the
shell, not the harness, set the strategy?

What to look for that's ADK's own: everything arrives as an event (a model
response, a tool result, a state change), and the turn limit is a
RunConfig setting (max_llm_calls) rather than a loop counter.
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

load_dotenv()
# LiteLLM's OpenAI adapter reads these; set before ADK imports settle.
os.environ["OPENAI_API_KEY"] = os.environ["PROVIDER_API_KEY"]
os.environ["OPENAI_API_BASE"] = os.environ["PROVIDER_BASE_URL"]

from google.adk import Agent  # noqa: E402
from google.adk.agents.run_config import RunConfig  # noqa: E402
from google.adk.models.lite_llm import LiteLlm  # noqa: E402
from google.adk.runners import InMemoryRunner  # noqa: E402
from google.genai import types  # noqa: E402

NAME = "migration_adk_shell"
workspace: Path


def shell(command: str) -> str:
    """Run a shell command in the workspace and return its output and exit code."""
    return ws_shell(workspace, command)


async def main() -> int:
    global workspace
    workspace = prepare_workspace(NAME, source=REFACTOR_SOURCE)
    trace = Trace("adk", workspace)

    agent = Agent(
        name="migrator",
        model=LiteLlm(model=f"openai/{os.environ['MODEL']}", num_retries=3),
        instruction=SYSTEM_PROMPT,
        tools=[shell],
    )
    runner = InMemoryRunner(agent=agent, app_name="block4")
    session = await runner.session_service.create_session(app_name="block4", user_id="attendee")

    started = time.monotonic()
    message = types.Content(role="user", parts=[types.Part(text=REFACTOR_TASK)])
    try:
        async for event in runner.run_async(user_id="attendee", session_id=session.id,
                                            new_message=message,
                                            run_config=RunConfig(max_llm_calls=MIGRATION_MAX_TURNS)):
            parts = event.content.parts if event.content else []
            # A model response carries calls or text; ADK sends each tool's
            # result as a separate event, which is not a turn.
            if any(getattr(p, "function_call", None) or getattr(p, "text", None) for p in parts):
                trace.new_turn()
                um = getattr(event, "usage_metadata", None)
                if um:
                    trace.usage(um.prompt_token_count, getattr(um, "cached_content_token_count", 0),
                                getattr(um, "candidates_token_count", 0))
            for part in parts:
                if getattr(part, "function_call", None):
                    trace.call(part.function_call.name, dict(part.function_call.args or {}))
                elif getattr(part, "function_response", None):
                    r = part.function_response.response or {}
                    trace.result(part.function_response.name, r.get("result", r))
                elif getattr(part, "text", None):
                    trace.text(part.text)
        trace.flush()
    except Exception as exc:  # hitting max_llm_calls is an outcome, not a crash
        trace.flush()
        print(f"[adk] run ended without finishing: {type(exc).__name__}: {exc}")
    solved = verify(NAME, workspace, started) == 0
    trace.finish(script="adk_shell", solved=solved, started=started,
                 tools="ours: one shell tool", tools_we_wrote=1)
    return 0 if solved else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
