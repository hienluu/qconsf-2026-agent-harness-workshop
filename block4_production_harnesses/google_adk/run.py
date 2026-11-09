"""fix_bug through Google ADK.

    uv run google_adk/run.py      (from block4_production_harnesses/)

Where it came from: harness construction kit — maximum structure (typed state,
sessions, services, a graph runtime in 2.x), with the opinions left to
you. Notice the ceremony this smallest-possible agent still requires:
a Runner, a session service, a session, typed Content parts. And notice
the import weight. To reach a non-Google model ADK needs LiteLLM, and
LiteLLM 1.84 and later require version 2 of the `openai` library, which
OpenAI Agents can't accept. This repo installs LiteLLM directly and stays on
1.83.0, so ADK can share an environment with the other harnesses. ADK's own
`[extensions]` bundle requires a newer LiteLLM and would break that.

Provider note: ADK is model-agnostic via LiteLLM, which reads the
OpenAI-compatible endpoint from environment variables we set below.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import end_turn, tool_detail, SYSTEM_PROMPT, trace_cost, trace_note, trace_state, TASK, TASK_MAX_TURNS, new_turn, prepare_workspace, receipt, trace_key, trace_say, trace_tool, verify, ws_list, ws_read, ws_run_tests, ws_write  # noqa: E402

load_dotenv()
# LiteLLM's OpenAI adapter reads these; set before ADK imports settle.
os.environ["OPENAI_API_KEY"] = os.environ["PROVIDER_API_KEY"]
os.environ["OPENAI_API_BASE"] = os.environ["PROVIDER_BASE_URL"]

from google.adk import Agent  # noqa: E402
from google.adk.agents.run_config import RunConfig  # noqa: E402
from google.adk.models.lite_llm import LiteLlm  # noqa: E402
from google.adk.runners import InMemoryRunner  # noqa: E402
from google.genai import types  # noqa: E402

NAME = "google_adk"
workspace: Path


def list_files() -> str:
    """List every file in the workspace as relative paths."""
    return ws_list(workspace)


def read_file(path: str) -> str:
    """Read one file, path relative to the workspace."""
    return ws_read(workspace, path)


def write_file(path: str, content: str) -> str:
    """Overwrite one file, path relative to the workspace."""
    return ws_write(workspace, path, content)


def run_tests() -> str:
    """Run pytest in the workspace; done means all tests pass."""
    return ws_run_tests(workspace)


async def main() -> int:
    global workspace
    workspace = prepare_workspace(NAME)
    trace_key(NAME, ["list_files", "read_file", "write_file", "run_tests"])

    agent = Agent(
        name="bug_fixer",
        model=LiteLlm(model=f"openai/{os.environ['MODEL']}", num_retries=3),
        instruction=SYSTEM_PROMPT,
        tools=[list_files, read_file, write_file, run_tests],
    )

    runner = InMemoryRunner(agent=agent, app_name="block4")
    session = await runner.session_service.create_session(
        app_name="block4", user_id="attendee"
    )

    started = time.monotonic()
    message = types.Content(role="user", parts=[types.Part(text=TASK)])
    try:
        async for event in runner.run_async(
            user_id="attendee", session_id=session.id, new_message=message,
            run_config=RunConfig(max_llm_calls=TASK_MAX_TURNS),
        ):
            parts = event.content.parts if event.content else []
            # ADK emits a second event carrying each tool's RESULT; only the
            # model-authored ones (a call or text) count as a turn.
            if any(getattr(p, "function_call", None) or getattr(p, "text", None) for p in parts):
                new_turn()
            for part in parts:
                if getattr(part, "function_call", None):
                    args = getattr(part.function_call, "args", None) or {}
                    detail = tool_detail(dict(args))
                    trace_tool(NAME, part.function_call.name, detail)
                elif getattr(part, "text", None) and part.text.strip():
                    trace_say(NAME, part.text)

            # ADK's events carry more than content — session state deltas and its
            # own compaction are the structure the "kit" is really selling. Printed
            # after the turn's tool calls, the way Block 3's scoreboard line is.
            acts = getattr(event, "actions", None)
            if acts is not None:
                if getattr(acts, "state_delta", None):
                    trace_state(NAME, acts.state_delta)
                if getattr(acts, "compaction", None):
                    trace_note(NAME, "the harness compacted its own session history")
            um = getattr(event, "usage_metadata", None)
            if um and getattr(um, "prompt_token_count", None):
                trace_cost(NAME, um.prompt_token_count,
                           getattr(um, "candidates_token_count", 0) or 0)
    except Exception as exc:  # hitting max_llm_calls is an outcome, not a crash
        end_turn()
        print(f"[{NAME}] run ended without finishing: {type(exc).__name__}: {exc}")

    solved = verify(NAME, workspace, started) == 0
    receipt(NAME, script=__file__, started=started, solved=solved,
        origin="construction kit (typed state, sessions, graph runtime)",
        loop_owner="theirs — Runner + session services (most ceremony)",
        tools_we_wrote=["list_files", "read_file", "write_file", "run_tests"],
        tools_harness_shipped="none for this task (rich ecosystem exists: executors, computer-use)",
        provider_friction="LiteLLM env contract; LiteLLM held at 1.83.0 to share an env with openai-agents; transient 500s -> num_retries")
    return 0 if solved else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
