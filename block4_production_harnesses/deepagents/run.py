"""fix_bug through LangChain Deep Agents.

    uv run deepagents/run.py          (from block4_production_harnesses/)

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
from common import end_turn, trace_result, tool_detail, SYSTEM_PROMPT, trace_cost, TASK, TASK_MAX_TURNS, TurnCapReached, new_turn, prepare_workspace, receipt, trace_key, trace_say, trace_tool, verify, ws_run_tests  # noqa: E402

from deepagents import create_deep_agent  # noqa: E402
from deepagents.backends import FilesystemBackend  # noqa: E402
from langchain_openai import ChatOpenAI  # noqa: E402

load_dotenv()
NAME = "deepagents"
workspace: Path


def run_tests() -> str:
    """Run pytest in the workspace; done means all tests pass."""
    call = trace_tool(NAME, "run_tests")
    out = ws_run_tests(workspace)
    trace_result(NAME, "run_tests", out, call=call)
    return out


class Watch(BaseCallbackHandler):
    """LangGraph accepts LangChain callbacks, which buys us two things a
    plain .invoke() hides: turn boundaries, and the harness's OWN tool
    calls. Without on_tool_start this trace showed 2 calls where other
    harnesses showed 12 — because Deep Agents does its file work through
    tools it brought, and we never see them."""

    main_calls = sub_calls = sent = 0
    raise_error = True   # let TurnCapReached stop the graph instead of being logged

    def on_chat_model_start(self, serialized, messages, **kwargs) -> None:
        # The turn cap, enforced here: recursion_limit counts graph steps,
        # and each subagent gets its own, so neither caps model calls.
        if Watch.main_calls + Watch.sub_calls >= TASK_MAX_TURNS:
            raise TurnCapReached(f"turn cap reached: {TASK_MAX_TURNS} model calls")
        new_turn()
        # Deep Agents tags a subagent's runs: ls_agent_type "subagent", and
        # lc_agent_name set to the subagent's name ("general-purpose" for the
        # built-in one).
        meta = kwargs.get("metadata") or {}
        if meta.get("ls_agent_type") == "subagent" or meta.get("lc_agent_name") == "general-purpose":
            Watch.sub_calls += 1
        else:
            Watch.main_calls += 1

    def on_llm_end(self, response, **kwargs) -> None:
        for batch in (getattr(response, "generations", None) or []):
            for gen in batch:
                u = getattr(getattr(gen, "message", None), "usage_metadata", None) or {}
                if u.get("input_tokens"):
                    Watch.sent += u["input_tokens"]
                    trace_cost(NAME, u["input_tokens"], u.get("output_tokens") or 0, Watch.sent)
                said = getattr(gen, "text", None)
                if said and said.strip():
                    trace_say(NAME, said)

    def on_tool_start(self, serialized, input_str, **kwargs) -> None:
        name = (serialized or {}).get("name") or kwargs.get("name") or "tool"
        if name == "run_tests":
            return                       # already traced by the tool itself
        # The arguments, summarized (relative paths, sizes not contents,
        # replace_all when set): cutting the raw string at a fixed length
        # hid the fields that matter.
        args = kwargs.get("inputs")
        detail = tool_detail(args, virtual=True) if isinstance(args, dict) else str(input_str)[:70]
        trace_tool(NAME, name, detail, harness_tool=True)


def main() -> int:
    global workspace
    workspace = prepare_workspace(NAME)
    trace_key(NAME, ["run_tests"], "ls, read_file, write_file, edit_file, glob, grep, write_todos, task (subagents)")

    agent = create_deep_agent(
        model=ChatOpenAI(
            model=os.environ["MODEL"],
            base_url=os.environ["PROVIDER_BASE_URL"],
            api_key=os.environ["PROVIDER_API_KEY"],
            max_retries=5,  # the workshop provider throws occasional 500s
        ),
        # The harness's own file tools, aimed at the run's private copy.
        # virtual_mode=True is the confined mode: paths are kept inside
        # root_dir. With virtual_mode=False the library documents that
        # "absolute paths are allowed as-is" — root_dir becomes a default
        # for relative paths, not a boundary — and we watched an agent walk
        # out of its copy and edit the source fixture in place.
        backend=FilesystemBackend(root_dir=workspace, virtual_mode=True),
        tools=[run_tests],
        system_prompt=SYSTEM_PROMPT,
    )

    started = time.monotonic()
    try:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": TASK}]},
            # recursion_limit counts graph steps (a turn takes two or more);
            # set well above the cap so our counter is the one that stops it.
            config={"recursion_limit": TASK_MAX_TURNS * 10,
                    "callbacks": [Watch()]},
        )
        trace_say(NAME, str(result["messages"][-1].content))
        end_turn()
        print(f"[{NAME}] messages in transcript: {len(result['messages'])}")
    except Exception as exc:  # hitting the recursion limit is an outcome, not a crash
        end_turn()
        print(f"[{NAME}] run ended without finishing: {type(exc).__name__}: {str(exc)[:120]}")
    end_turn()
    print(f"[{NAME}] model calls: {Watch.main_calls + Watch.sub_calls} "
          f"({Watch.main_calls} by the main agent, {Watch.sub_calls} by subagents); "
          f"tokens sent: {Watch.sent:,}")
    solved = verify(NAME, workspace, started) == 0
    receipt(NAME, script=__file__, started=started, solved=solved,
        origin="harness on a runtime (LangGraph underneath)",
        loop_owner="theirs: ReAct + middleware onion",
        tools_we_wrote=["run_tests"],
        tools_harness_shipped="filesystem suite on the real workspace, write_todos, subagents",
        provider_friction="none for the model; retries added for provider 500s")
    return 0 if solved else 1


if __name__ == "__main__":
    raise SystemExit(main())
