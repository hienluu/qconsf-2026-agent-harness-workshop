"""Take-home: LangChain Deep Agents with its own tools, a shell included.

    uv run tool_design/run_deepagents.py      (from block4_production_harnesses/)

In the exercise (deepagents/run.py), Deep Agents gets its own file tools
and usually runs out of budget: it hands the work to a subagent and edits
one string per call. Here its backend is LocalShellBackend, which adds an
`execute` tool that runs shell commands. Same harness, same model, same
budget: with a shell, it greps and scripts the rename, and solves it.
The tools decided, not the harness.

We define no tools. Its own docs say the shell runs "directly on the host
system without any sandboxing"; virtual_mode=True keeps only the file
tools inside the run's copy. The shell gets PATH and HOME from our
environment, nothing else (no API keys), and git can't see the workshop
repo around the copy (shell_env in common.py).
"""

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from langchain_core.callbacks import BaseCallbackHandler  # noqa: E402
from common import TurnCapReached, end_turn, tool_detail, SYSTEM_PROMPT, trace_cost, TASK, TASK_MAX_TURNS, new_turn, prepare_workspace, receipt, shell_env, trace_key, trace_result, trace_say, trace_tool, verify, sampling  # noqa: E402

from deepagents import create_deep_agent  # noqa: E402
from deepagents.backends import LocalShellBackend  # noqa: E402
from langchain_openai import ChatOpenAI  # noqa: E402

load_dotenv()
NAME = "deepagents+shell"


class Watch(BaseCallbackHandler):
    """Same callbacks as deepagents/run.py, plus each call's result."""

    main_calls = sub_calls = sent = 0
    raise_error = True   # let TurnCapReached stop the graph instead of being logged
    names: dict = {}

    def on_chat_model_start(self, serialized, messages, **kwargs) -> None:
        if Watch.main_calls + Watch.sub_calls >= TASK_MAX_TURNS:
            raise TurnCapReached(f"turn cap reached: {TASK_MAX_TURNS} model calls")
        new_turn()
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
                    cached = (u.get("input_token_details") or {}).get("cache_read") or 0
                    trace_cost(NAME, u["input_tokens"], u.get("output_tokens") or 0, Watch.sent,
                               cached=cached)
                said = getattr(gen, "text", None)
                if said and said.strip():
                    trace_say(NAME, said)

    def on_tool_start(self, serialized, input_str, *, run_id=None, **kwargs) -> None:
        name = (serialized or {}).get("name") or kwargs.get("name") or "tool"
        Watch.names[run_id] = name
        args = kwargs.get("inputs")
        detail = tool_detail(args, virtual=True) if isinstance(args, dict) else str(input_str)[:70]
        trace_tool(NAME, name, detail, harness_tool=True, call_id=run_id)

    def on_tool_end(self, output, *, run_id=None, **kwargs) -> None:
        name = Watch.names.pop(run_id, "tool")
        if name in ("execute", "grep", "glob", "edit_file", "write_file", "task"):
            trace_result(NAME, name, getattr(output, "content", output), call_id=run_id)

    def on_tool_error(self, error, *, run_id=None, **kwargs) -> None:
        trace_result(NAME, Watch.names.pop(run_id, "tool"), error, failed=True, call_id=run_id)


def main() -> int:
    workspace = prepare_workspace(NAME)
    trace_key(NAME, [], "ls, read_file, write_file, edit_file, glob, grep, execute (shell), write_todos, task (subagents)")

    agent = create_deep_agent(
        model=ChatOpenAI(
            model=os.environ["LLM_MODEL"],
            base_url=os.environ["LLM_BASE_URL"],
            api_key=os.environ["LLM_API_KEY"],
            max_retries=5,  # the workshop provider throws occasional 500s
            **sampling(),   # temperature: see common.temperature_setting
        ),
        backend=LocalShellBackend(
            root_dir=workspace, virtual_mode=True, timeout=120,
            env=shell_env(workspace),
        ),
        system_prompt=SYSTEM_PROMPT,
    )

    started = time.monotonic()
    try:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": TASK}]},
            # recursion_limit counts graph steps; set well above the cap so
            # our counter is the one that stops it.
            config={"recursion_limit": TASK_MAX_TURNS * 10, "callbacks": [Watch()]},
        )
        trace_say(NAME, str(result["messages"][-1].content))
    except Exception as exc:  # hitting the turn cap is an outcome, not a crash
        end_turn()
        print(f"[{NAME}] run ended without finishing: {type(exc).__name__}: {str(exc)[:120]}")
    end_turn()
    print(f"[{NAME}] model calls: {Watch.main_calls + Watch.sub_calls} "
          f"({Watch.main_calls} by the main agent, {Watch.sub_calls} by subagents)")
    solved = verify(NAME, workspace, started) == 0
    receipt(NAME, script=__file__, started=started, solved=solved,
        origin="harness on a runtime (LangGraph underneath)",
        loop_owner="theirs: ReAct + middleware onion",
        tools_we_wrote=[],
        tools_harness_shipped="file tools, execute (an unsandboxed shell), write_todos, subagents",
        provider_friction="none for the model; retries added for provider 500s")
    return 0 if solved else 1


if __name__ == "__main__":
    raise SystemExit(main())
