"""The naive harness, complete. ~60 lines of logic: a loop and a dispatcher.

This is every team's first agent. It works on small tasks and falls apart on
long ones, because it has no context management, no memory, no tool-output
limits, no error recovery, and no plan. Block 3 fixes that — measurably.

Usage: python solution/harness.py <workspace_dir> "<task instructions>"
"""

import json
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools import TOOL_SCHEMAS, Workspace  # noqa: E402

SYSTEM_PROMPT = """You are a coding agent operating on a local workspace via tools.
Work step by step: inspect files, make edits, and run the tests to check yourself.
The task is complete only when run_tests reports that every test passed.
When the tests are green, reply with a short summary instead of calling tools."""

# The only guardrail in this harness, and it protects the wallet, not the task.
MAX_TURNS = 40


def run(workspace_dir: str, task: str) -> None:
    """Drive one agent session: give the model a task and a set of tools,
    then loop — model call, tool execution, results fed back — until the
    model stops calling tools (its way of saying "done") or MAX_TURNS runs
    out.

    `workspace_dir` is the directory the tools operate in; `task` is the
    natural-language instruction that becomes the first user message. The
    conversation transcript (`messages`) is the agent's entire memory: every
    file read, tool result, and edit accumulates there, and the full list is
    resent to the model on every turn.
    """
    client = OpenAI(
        base_url=os.environ["PROVIDER_BASE_URL"],
        api_key=os.environ["PROVIDER_API_KEY"],
    )
    model = os.environ["MODEL"]
    ws = Workspace(workspace_dir)

    # The tool dispatcher: the bridge between what the model SAYS and what
    # actually HAPPENS. The model only ever emits a tool name plus JSON
    # arguments — it cannot touch the filesystem itself. This dict maps each
    # name from TOOL_SCHEMAS to the code that really runs. Every key here is
    # a capability you've granted the agent; anything not in this dict, the
    # agent simply cannot do. (In production harnesses this same idea grows
    # into permissions, sandboxing, and guardrails.)
    dispatch = {
        "list_files": lambda args: ws.list_files(),
        "read_file": lambda args: ws.read_file(args["path"]),
        "write_file": lambda args: ws.write_file(args["path"], args["content"]),
        "search": lambda args: ws.search(args["pattern"]),
        "run_tests": lambda args: ws.run_tests(),
    }

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]

    for turn in range(1, MAX_TURNS + 1):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_SCHEMAS,
            temperature=0.1,
        )
        msg = response.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))

        if not msg.tool_calls:
            print(f"\n[turn {turn}] agent finished:\n{msg.content}")
            return

        for call in msg.tool_calls:
            name = call.function.name
            args = json.loads(call.function.arguments or "{}")
            print(f"[turn {turn}] {name}({', '.join(f'{k}={str(v)[:40]!r}' for k, v in args.items())})")
            try:
                result = dispatch[name](args)
            except Exception as exc:  # naive: report and hope the model copes
                result = f"tool error: {exc}"
            messages.append(
                {"role": "tool", "tool_call_id": call.id, "content": result}
            )

    print(f"\ngave up after {MAX_TURNS} turns without finishing")


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2])
