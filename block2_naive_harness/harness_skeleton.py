"""Build the naive harness: YOU write the agent loop and the tool dispatcher.

Everything else — client setup, tool implementations, tool schemas — is
provided. The two TODO blocks below are the beating heart of every agent
harness ever shipped. They total ~30-40 lines.

Usage: python harness_skeleton.py <workspace_dir> "<task instructions>"

Check yourself against solution/harness.py if you get stuck.
"""

import json
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tools import TOOL_SCHEMAS, Workspace  # noqa: E402

SYSTEM_PROMPT = """You are a coding agent operating on a local workspace via tools.
Work step by step: inspect files, make edits, and run the tests to check yourself.
The task is complete only when run_tests reports that every test passed.
When the tests are green, reply with a short summary instead of calling tools."""

MAX_TURNS = 40


def run(workspace_dir: str, task: str) -> None:
    client = OpenAI(
        base_url=os.environ["PROVIDER_BASE_URL"],
        api_key=os.environ["PROVIDER_API_KEY"],
    )
    model = os.environ["MODEL"]
    ws = Workspace(workspace_dir)

    # ------------------------------------------------------------------
    # TODO 1 — the tool dispatcher (~10 lines)
    #
    # Build `dispatch`: a dict mapping each tool name from TOOL_SCHEMAS to
    # a callable that takes the parsed arguments dict and invokes the right
    # Workspace method:
    #   list_files -> ws.list_files()
    #   read_file  -> ws.read_file(args["path"])
    #   write_file -> ws.write_file(args["path"], args["content"])
    #   search     -> ws.search(args["pattern"])
    #   run_tests  -> ws.run_tests()
    # ------------------------------------------------------------------
    dispatch = {}  # <-- your code here

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]

    # ------------------------------------------------------------------
    # TODO 2 — the agent loop (~25 lines)
    #
    # For up to MAX_TURNS iterations:
    #   1. Call client.chat.completions.create(model=model, messages=messages,
    #      tools=TOOL_SCHEMAS, temperature=0.1)
    #   2. Take response.choices[0].message; append it to `messages`
    #      (msg.model_dump(exclude_none=True) converts it to a plain dict).
    #   3. If the message has NO tool_calls, the agent is done: print
    #      msg.content and return.
    #   4. Otherwise, for each tool call:
    #        - parse call.function.arguments with json.loads
    #        - look up call.function.name in `dispatch` and invoke it
    #        - if the tool raises, use f"tool error: {exc}" as the result
    #        - append {"role": "tool", "tool_call_id": call.id,
    #                  "content": result} to `messages`
    #      Printing each tool name as it runs makes the agent watchable.
    #
    # That's it. No compaction, no truncation, no recovery, no memory —
    # notice what you did NOT have to build, then watch what that costs.
    # ------------------------------------------------------------------
    raise NotImplementedError("write the agent loop")


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2])
