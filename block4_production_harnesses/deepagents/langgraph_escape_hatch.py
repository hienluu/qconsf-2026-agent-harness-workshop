"""The same task on the raw runtime UNDER Deep Agents — bare LangGraph.

    uv run --group block4 deepagents/langgraph_escape_hatch.py

This is Block 5's build-vs-adopt escape hatch, live: when a pre-built
harness doesn't fit, you drop one layer down to the runtime it's built on.
(The entry point itself just churned — `create_react_agent` moved from
langgraph.prebuilt to `langchain.agents.create_agent` in LangGraph 1.0.
Building at the runtime layer means riding that churn yourself.)
Notice what came back onto our plate the moment we did — every tool must
be defined by hand again, and there are no planning todos, no filesystem
conventions, no subagents unless we build them. The runtime gives control;
the harness was giving opinions.
"""

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import TASK, prepare_workspace, receipt, verify, ws_list, ws_read, ws_run_tests, ws_write  # noqa: E402

from langchain.agents import create_agent  # noqa: E402
from langchain_core.tools import tool  # noqa: E402
from langchain_openai import ChatOpenAI  # noqa: E402

load_dotenv()
NAME = "langgraph_escape_hatch"
workspace: Path


@tool
def list_files() -> str:
    """List every file in the workspace as relative paths."""
    return ws_list(workspace)


@tool
def read_file(path: str) -> str:
    """Read one file, path relative to the workspace."""
    return ws_read(workspace, path)


@tool
def write_file(path: str, content: str) -> str:
    """Overwrite one file, path relative to the workspace."""
    return ws_write(workspace, path, content)


@tool
def run_tests() -> str:
    """Run pytest in the workspace; done means all tests pass."""
    return ws_run_tests(workspace)


def main() -> int:
    global workspace
    workspace = prepare_workspace(NAME)

    agent = create_agent(
        ChatOpenAI(
            model=os.environ["MODEL"],
            base_url=os.environ["PROVIDER_BASE_URL"],
            api_key=os.environ["PROVIDER_API_KEY"],
            max_retries=5,  # the workshop provider throws occasional 500s
        ),
        tools=[list_files, read_file, write_file, run_tests],
        system_prompt=(
            "You fix bugs in a small Python workspace using the provided "
            "tools. The task is complete only when run_tests reports every "
            "test passing. Do not modify the tests."
        ),
    )

    started = time.monotonic()
    result = agent.invoke(
        {"messages": [{"role": "user", "content": TASK}]},
        config={"recursion_limit": 40},
    )
    print(f"[{NAME}] final: {str(result['messages'][-1].content)[:100]}")
    solved = verify(NAME, workspace, started) == 0
    receipt(NAME, script=__file__, started=started, solved=solved,
        pedigree="the runtime itself — one layer below Deep Agents",
        loop_owner="ours to shape (bare create_agent graph)",
        tools_we_wrote=["list_files", "read_file", "write_file", "run_tests"],
        tools_harness_shipped="nothing — dropping a layer put every tool back on our plate",
        provider_friction="none for the model; API churned mid-build (create_react_agent renamed)")
    return 0 if solved else 1


if __name__ == "__main__":
    raise SystemExit(main())
