"""h2_managed — h1 plus exactly three protections, ~40 changed lines.

Each addition answers a death we watched h1 die in live runs (marked [h2]):

  1. Tool-output limits   — full pytest tracebacks and 149-file search
                            results no longer flood the context whole.
  2. Malformed-call retry — a tool call truncated at the model's output
                            ceiling becomes an error the model can react
                            to, instead of an unhandled crash.
  3. Context compaction   — old tool outputs are dropped once the
                            transcript exceeds a budget, so cost stops
                            growing quadratically and the window never
                            fills with stale file dumps.

Read this file as `diff h1_naive.py h2_managed.py` — the diff IS the lesson.
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
    transcript_chars,
)

NAME = "h2_managed"

# [h2] Protection knobs.
MAX_TOOL_RESULT_CHARS = 6_000     # per tool result fed back to the model
TRANSCRIPT_CHAR_BUDGET = 80_000   # ~20k tokens; keeps cumulative cost linear on long tasks
KEEP_RECENT_MESSAGES = 12         # never compact the newest N messages
DROPPED_MARKER = "[old tool output dropped by the harness to save context — re-run the tool if you need it again]"


def truncate(text: str) -> str:
    """[h2] Cap a tool result, keeping the head and tail (errors live at both ends)."""
    if len(text) <= MAX_TOOL_RESULT_CHARS:
        return text
    head, tail = text[:4_000], text[-1_500:]
    dropped = len(text) - len(head) - len(tail)
    return f"{head}\n... [harness truncated {dropped} chars] ...\n{tail}"


def compact(messages: list) -> int:
    """[h2] Drop the oldest large tool outputs until under budget.

    System and user messages are never touched; the newest messages are
    never touched. Deterministic and cheap — no extra model calls.
    """
    dropped = 0
    for m in messages[:-KEEP_RECENT_MESSAGES]:
        if transcript_chars(messages) <= TRANSCRIPT_CHAR_BUDGET:
            break
        if m.get("role") == "tool" and len(m.get("content") or "") > len(DROPPED_MARKER):
            m["content"] = DROPPED_MARKER
            dropped += 1
    return dropped


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
                # [h2] Guarded parse: a truncated/malformed tool call becomes
                # feedback the model can recover from, not a fatal crash.
                try:
                    args = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError as exc:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": (
                            f"harness error: tool call arguments were not valid JSON "
                            f"({exc}). Your output was probably truncated — retry with "
                            f"smaller file content or fewer tool calls per turn."
                        ),
                    })
                    result.notes["malformed_calls"] = result.notes.get("malformed_calls", 0) + 1
                    print(f"[{NAME} turn {turn}] {name}(<malformed — recovered>)")
                    continue
                print(f"[{NAME} turn {turn}] {name}({', '.join(f'{k}={str(v)[:40]!r}' for k, v in args.items())})")
                try:
                    result_text = dispatch[name](args)
                except Exception as exc:
                    result_text = f"tool error: {exc}"
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    # [h2] Cap what a single tool result may inject.
                    "content": truncate(result_text),
                })

            # [h2] End-of-turn compaction pass.
            dropped = compact(messages)
            if dropped:
                result.notes["dropped_tool_outputs"] = result.notes.get("dropped_tool_outputs", 0) + dropped
                print(f"[{NAME} turn {turn}] compaction: dropped {dropped} old tool output(s)")
    except Exception as exc:
        result.status = "crashed"
        result.error = f"{type(exc).__name__}: {exc}"
        print(f"\n[{NAME}] CRASHED: {result.error}")

    result.wall_seconds = round(time.monotonic() - start, 1)
    return result
