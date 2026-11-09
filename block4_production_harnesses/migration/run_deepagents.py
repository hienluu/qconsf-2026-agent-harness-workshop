"""The migration through LangChain Deep Agents, with its own tools.

    uv run migration/run_deepagents.py      (from block4_production_harnesses/)

We define no tools. Deep Agents ships them: file tools (ls, read_file,
write_file, edit_file, glob, grep), planning todos, subagents, and with
LocalShellBackend an `execute` tool that runs shell commands. Its own docs
say that shell runs "directly on the host system without any sandboxing";
virtual_mode=True keeps only the file tools inside the run's copy. The
shell gets PATH and HOME from our environment, nothing else (no API keys).

The trace comes from LangChain callbacks: each model call is a turn, its
tool calls arrive with the response, each result arrives on tool end.
"""

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import SYSTEM_PROMPT, MIGRATION_MAX_TURNS, TurnCapReached, REFACTOR_SOURCE, REFACTOR_TASK, prepare_workspace, verify  # noqa: E402
from migration_trace import Trace  # noqa: E402

from deepagents import create_deep_agent  # noqa: E402
from deepagents.backends import LocalShellBackend  # noqa: E402
from langchain_core.callbacks import BaseCallbackHandler  # noqa: E402
from langchain_openai import ChatOpenAI  # noqa: E402

load_dotenv()
NAME = "migration_deepagents"


class Watch(BaseCallbackHandler):
    def __init__(self, trace: Trace):
        self.trace, self.names = trace, {}

    raise_error = True   # let TurnCapReached stop the graph instead of being logged

    def on_chat_model_start(self, serialized, messages, **kwargs) -> None:
        # Our counter is the cap, subagents included: recursion_limit counts
        # graph steps, and each subagent gets its own.
        if self.trace.turn >= MIGRATION_MAX_TURNS:
            raise TurnCapReached(f"turn cap reached: {MIGRATION_MAX_TURNS} model calls")
        self.trace.new_turn()

    def on_llm_end(self, response, **kwargs) -> None:
        for batch in getattr(response, "generations", None) or []:
            for gen in batch:
                msg = getattr(gen, "message", None)
                for call in getattr(msg, "tool_calls", None) or []:
                    self.trace.call(call.get("name", "tool"), call.get("args") or {})
                u = getattr(msg, "usage_metadata", None) or {}
                if u:
                    self.trace.usage(u.get("input_tokens"), (u.get("input_token_details") or {}).get("cache_read"),
                                     u.get("output_tokens"))
                content = getattr(msg, "content", "") if msg is not None else getattr(gen, "text", "")
                if isinstance(content, str):
                    self.trace.text(content)

    def on_tool_start(self, serialized, input_str, *, run_id=None, **kwargs) -> None:
        self.names[run_id] = (serialized or {}).get("name") or kwargs.get("name") or "tool"

    def on_tool_end(self, output, *, run_id=None, **kwargs) -> None:
        name = self.names.pop(run_id, "tool")
        text = getattr(output, "content", output)
        self.trace.result(name, text)

    def on_tool_error(self, error, *, run_id=None, **kwargs) -> None:
        self.names.pop(run_id, None)
        self.trace.failure(error)


def main() -> int:
    workspace = prepare_workspace(NAME, source=REFACTOR_SOURCE)
    trace = Trace("deepagents", workspace, virtual_paths=True)

    agent = create_deep_agent(
        model=ChatOpenAI(
            model=os.environ["MODEL"],
            base_url=os.environ["PROVIDER_BASE_URL"],
            api_key=os.environ["PROVIDER_API_KEY"],
            max_retries=5,
        ),
        backend=LocalShellBackend(
            root_dir=workspace, virtual_mode=True, timeout=120,
            env={"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", "")},
        ),
        system_prompt=SYSTEM_PROMPT,
    )

    started = time.monotonic()
    try:
        agent.invoke(
            {"messages": [{"role": "user", "content": REFACTOR_TASK}]},
            # Set well above the turn cap so our counter is what stops it.
            config={"recursion_limit": MIGRATION_MAX_TURNS * 10, "callbacks": [Watch(trace)]},
        )
        trace.flush()
    except Exception as exc:  # running out of steps is an outcome, not a crash
        trace.flush()
        print(f"[deepagents] run ended without finishing: {type(exc).__name__}: {exc}")
    solved = verify(NAME, workspace, started) == 0
    trace.finish(script="deepagents", solved=solved, started=started,
                 tools="Deep Agents' own, incl. execute (shell)", tools_we_wrote=0)
    return 0 if solved else 1


if __name__ == "__main__":
    raise SystemExit(main())
