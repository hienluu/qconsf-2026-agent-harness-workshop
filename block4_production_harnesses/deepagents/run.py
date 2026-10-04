"""fix_bug through LangChain Deep Agents.

    uv run --group block4 deepagents/run.py          (from block4_production_harnesses/)

Where it came from: a harness built ON a runtime — Deep Agents is LangChain's own
conclusion that teams need batteries included, assembled on top of the
LangGraph runtime. Notice how little we define: the harness SHIPS its own
filesystem tools (pointed at the real workspace via a backend), planning
todos, and subagent machinery. Our only custom tool is run_tests — the
task's definition of done.
"""

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from langchain_core.callbacks import BaseCallbackHandler  # noqa: E402
from common import TASK, TASK_MAX_TURNS, new_turn, prepare_workspace, receipt, trace_key, trace_say, trace_tool, verify, ws_run_tests  # noqa: E402

from deepagents import create_deep_agent  # noqa: E402
from deepagents.backends import FilesystemBackend  # noqa: E402
from langchain_openai import ChatOpenAI  # noqa: E402

load_dotenv()
NAME = "deepagents"
workspace: Path


def run_tests() -> str:
    """Run pytest in the workspace; done means all tests pass."""
    trace_tool(NAME, "run_tests")
    return ws_run_tests(workspace)


class Watch(BaseCallbackHandler):
    """LangGraph accepts LangChain callbacks, which buys us two things a
    plain .invoke() hides: turn boundaries, and the harness's OWN tool
    calls. Without on_tool_start this trace showed 2 calls where other
    harnesses showed 12 — because Deep Agents does its file work through
    tools it shipped, and we never see them."""

    def on_chat_model_start(self, serialized, messages, **kwargs) -> None:
        new_turn()

    def on_llm_end(self, response, **kwargs) -> None:
        for batch in (getattr(response, "generations", None) or []):
            for gen in batch:
                said = getattr(gen, "text", None)
                if said and said.strip():
                    trace_say(NAME, said)

    def on_tool_start(self, serialized, input_str, **kwargs) -> None:
        name = (serialized or {}).get("name") or kwargs.get("name") or "tool"
        if name == "run_tests":
            return                       # already traced by the tool itself
        trace_tool(NAME, name, str(input_str)[:70], shipped=True)


def main() -> int:
    global workspace
    workspace = prepare_workspace(NAME)
    trace_key(NAME, ["run_tests"], "filesystem suite (ls, read_file, write_file), write_todos, subagents")

    agent = create_deep_agent(
        model=ChatOpenAI(
            model=os.environ["MODEL"],
            base_url=os.environ["PROVIDER_BASE_URL"],
            api_key=os.environ["PROVIDER_API_KEY"],
            max_retries=5,  # the workshop provider throws occasional 500s
        ),
        # The harness's own file tools, aimed at the run's private copy.
        # virtual_mode=True is the SANDBOXED mode: paths are confined to
        # root_dir. With virtual_mode=False the library documents that
        # "absolute paths are allowed as-is" — root_dir becomes a default
        # for relative paths, not a boundary — and we watched an agent walk
        # out of its copy and edit the source fixture in place.
        backend=FilesystemBackend(root_dir=workspace, virtual_mode=True),
        tools=[run_tests],
        system_prompt=(
            "You fix bugs in the Python workspace you have filesystem access "
            "to. The task is complete only when run_tests reports every test "
            "passing. Do not modify the tests."
        ),
    )

    started = time.monotonic()
    result = agent.invoke(
        {"messages": [{"role": "user", "content": TASK}]},
        # LangGraph counts super-steps (node executions), not agent turns, and
        # a ReAct loop burns at least two per turn — more through deepagents'
        # middleware. Deriving the limit from the same TASK_MAX_TURNS the other
        # harnesses use keeps the budget comparable instead of quietly tighter.
        config={"recursion_limit": TASK_MAX_TURNS * 3,
                "callbacks": [Watch()]},
    )
    final = result["messages"][-1]
    trace_say(NAME, str(final.content))
    print(f"[{NAME}] messages in transcript: {len(result['messages'])}")
    solved = verify(NAME, workspace, started) == 0
    receipt(NAME, script=__file__, started=started, solved=solved,
        origin="harness on a runtime (LangGraph underneath)",
        loop_owner="theirs — ReAct + middleware onion",
        tools_we_wrote=["run_tests"],
        tools_harness_shipped="filesystem suite on the real workspace, write_todos, subagents",
        provider_friction="none for the model; retries added for provider 500s")
    return 0 if solved else 1


if __name__ == "__main__":
    raise SystemExit(main())
