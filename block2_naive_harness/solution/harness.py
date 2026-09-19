"""The naive harness, complete. ~60 lines of logic: a loop and a dispatcher.

This is every team's first agent. It works on small tasks and falls apart on
long ones, because it has no context management, no memory, no tool-output
limits, no error recovery, and no plan. Block 3 fixes that — measurably.

Usage: uv run solution/harness.py <workspace_dir> "<task instructions>"
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

# The only guardrail in this harness, and it protects the wallet, not the
# task: 20 turns covers the short tasks; long-task completions need 25+.
MAX_TURNS = 20


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

        # Models often narrate alongside their tool calls ("the tests expect
        # X, so I'll..."), but on many turns content is empty and the intent
        # lives only in the tool calls themselves. Show both: narration when
        # present, plus which tools this turn reaches for. Makes the agent
        # watchable — and lets you see the moment its plan starts to drift.
        tool_names = ", ".join(c.function.name for c in msg.tool_calls)
        narration = msg.content.strip() if msg.content else "(no commentary)"
        print(f"\n[turn {turn}] agent says: {narration}  [tools: {tool_names}]")

        for call in msg.tool_calls:
            name = call.function.name
            args = json.loads(call.function.arguments or "{}")
            print(f"[turn {turn}] {name}({', '.join((f'{k}={v!r}' if k == 'path' else f'{k}={str(v)[:40]!r}') for k, v in args.items())})")
            try:
                result = dispatch[name](args)
            except Exception as exc:  # naive: report and hope the model copes
                result = f"tool error: {exc}"
            messages.append(
                {"role": "tool", "tool_call_id": call.id, "content": result}
            )

    print(f"\ngave up after {MAX_TURNS} turns without finishing")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the naive agent harness on a task.",
        epilog='Example: uv run solution/harness.py tasks/short/01_fix_bug/workspace '
        '"One test fails. Find the bug and fix it."',
    )
    parser.add_argument(
        "workspace",
        help="directory the agent operates on — its tools can only see files under this root",
    )
    parser.add_argument(
        "task",
        help="natural-language instruction for the agent (quote it); becomes the first user message",
    )
    cli = parser.parse_args()
    run(cli.workspace, cli.task)
