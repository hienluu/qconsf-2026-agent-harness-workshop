"""fix_bug through LangChain Deep Agents.

    uv run --group block4 deepagents/run.py          (from block4_production_harnesses/)

Pedigree: a harness built ON a runtime — Deep Agents is LangChain's own
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
from common import TASK, prepare_workspace, receipt, verify, ws_run_tests  # noqa: E402

from deepagents import create_deep_agent  # noqa: E402
from deepagents.backends import FilesystemBackend  # noqa: E402
from langchain_openai import ChatOpenAI  # noqa: E402

load_dotenv()
NAME = "deepagents"
workspace: Path


def run_tests() -> str:
    """Run pytest in the workspace; done means all tests pass."""
    print(f"[{NAME}] tool: run_tests()")
    return ws_run_tests(workspace)


def main() -> int:
    global workspace
    workspace = prepare_workspace(NAME)

    agent = create_deep_agent(
        model=ChatOpenAI(
            model=os.environ["MODEL"],
            base_url=os.environ["PROVIDER_BASE_URL"],
            api_key=os.environ["PROVIDER_API_KEY"],
            max_retries=5,  # the workshop provider throws occasional 500s
        ),
        # The harness's own file tools, aimed at the real workspace.
        backend=FilesystemBackend(root_dir=workspace, virtual_mode=False),
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
        config={"recursion_limit": 40},
    )
    final = result["messages"][-1]
    print(f"[{NAME}] final: {str(final.content)[:100]}")
    print(f"[{NAME}] messages in transcript: {len(result['messages'])}")
    solved = verify(NAME, workspace, started) == 0
    receipt(NAME, script=__file__, started=started, solved=solved,
        pedigree="harness on a runtime (LangGraph underneath)",
        loop_owner="theirs — ReAct + middleware onion",
        tools_we_wrote=["run_tests"],
        tools_harness_shipped="filesystem suite on the real workspace, write_todos, subagents",
        provider_friction="none for the model; retries added for provider 500s")
    return 0 if solved else 1


if __name__ == "__main__":
    raise SystemExit(main())
