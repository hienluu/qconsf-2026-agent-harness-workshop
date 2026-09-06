"""fix_bug through Google ADK.

    uv run --group block4-adk google_adk/run.py      (from block4_production_harnesses/)

Pedigree: harness construction kit — maximum structure (typed state,
sessions, services, a graph runtime in 2.x), with the opinions left to
you. Notice the ceremony this smallest-possible agent still requires:
a Runner, a session service, a session, typed Content parts. And notice
the import weight — ADK could not share a dependency resolution with the
other four harnesses (that's why it runs from its own uv group).

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
from common import TASK, prepare_workspace, receipt, verify, ws_list, ws_read, ws_run_tests, ws_write  # noqa: E402

load_dotenv()
# LiteLLM's OpenAI adapter reads these; set before ADK imports settle.
os.environ["OPENAI_API_KEY"] = os.environ["PROVIDER_API_KEY"]
os.environ["OPENAI_API_BASE"] = os.environ["PROVIDER_BASE_URL"]

from google.adk import Agent  # noqa: E402
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

    agent = Agent(
        name="bug_fixer",
        model=LiteLlm(model=f"openai/{os.environ['MODEL']}", num_retries=3),
        instruction=(
            "You fix bugs in a small Python workspace using the provided "
            "tools. The task is complete only when run_tests reports every "
            "test passing. Do not modify the tests."
        ),
        tools=[list_files, read_file, write_file, run_tests],
    )

    runner = InMemoryRunner(agent=agent, app_name="block4")
    session = await runner.session_service.create_session(
        app_name="block4", user_id="attendee"
    )

    started = time.monotonic()
    message = types.Content(role="user", parts=[types.Part(text=TASK)])
    async for event in runner.run_async(
        user_id="attendee", session_id=session.id, new_message=message
    ):
        for part in (event.content.parts if event.content else []):
            if getattr(part, "function_call", None):
                print(f"[{NAME}] tool: {part.function_call.name}")
            elif getattr(part, "text", None) and part.text.strip():
                print(f"[{NAME}] says: {part.text.strip()[:100]}")

    solved = verify(NAME, workspace, started) == 0
    receipt(NAME, script=__file__, started=started, solved=solved,
        pedigree="construction kit (typed state, sessions, graph runtime)",
        loop_owner="theirs — Runner + session services (most ceremony)",
        tools_we_wrote=["list_files", "read_file", "write_file", "run_tests"],
        tools_harness_shipped="none for this task (rich ecosystem exists: executors, computer-use)",
        provider_friction="LiteLLM env contract; own uv group (conflicts with openai-agents); 86 extra pkgs; transient 500s -> num_retries")
    return 0 if solved else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
