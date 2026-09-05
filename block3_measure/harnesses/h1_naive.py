"""h1_naive — the Block 2 harness, frozen and instrumented.

This is the loop attendees built: same prompt, same tools, same absence of
protections. Two deliberate differences from Block 2: the observer (it
counts turns and tokens, times the run, and reports how it ended, instead
of just printing) and the turn budget (40 here, like every Block 3 harness,
vs Block 2's 20 — see base.py). Do not "improve" this file; it is the
experimental baseline that h2/h3 are diffed and measured against.

Frozen from block2_naive_harness/solution/harness.py on 2026-09-05.
"""

import json
import time

from base import (
    MAX_TURNS,
    SYSTEM_PROMPT,
    TOOL_SCHEMAS,
    RunResult,
    Workspace,
    add_usage,
    make_client,
    model_name,
)

NAME = "h1_naive"


def run(workspace_dir: str, task: str) -> RunResult:
    client = make_client()
    model = model_name()
    ws = Workspace(workspace_dir)
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

    result = RunResult(harness=NAME, task=workspace_dir)
    start = time.monotonic()
    try:
        for turn in range(1, MAX_TURNS + 1):
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOL_SCHEMAS,
                temperature=0.1,
            )
            result.turns = turn
            add_usage(result, response)
            msg = response.choices[0].message
            messages.append(msg.model_dump(exclude_none=True))

            if not msg.tool_calls:
                result.status = "completed"
                result.final_message = msg.content or ""
                print(f"\n[{NAME} turn {turn}] agent finished")
                break

            for call in msg.tool_calls:
                name = call.function.name
                # Naive: unguarded parse — a truncated tool call kills the run.
                args = json.loads(call.function.arguments or "{}")
                print(f"[{NAME} turn {turn}] {name}({', '.join(f'{k}={str(v)[:40]!r}' for k, v in args.items())})")
                try:
                    result_text = dispatch[name](args)
                except Exception as exc:
                    result_text = f"tool error: {exc}"
                messages.append(
                    {"role": "tool", "tool_call_id": call.id, "content": result_text}
                )
    except Exception as exc:
        result.status = "crashed"
        result.error = f"{type(exc).__name__}: {exc}"
        print(f"\n[{NAME}] CRASHED: {result.error}")

    result.wall_seconds = round(time.monotonic() - start, 1)
    return result
