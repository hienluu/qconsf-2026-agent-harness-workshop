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
    corrupt,
    make_client,
    malformed_injection_turn,
    model_name,
    transcript_chars,
)
# base puts block2 on sys.path (for tools); reuse its scoreboard too.
from scoreboard import Scoreboard  # noqa: E402

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
    board = Scoreboard(MAX_TURNS)
    board.legend()
    inject_turn = malformed_injection_turn()
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
            board.record_usage(response)
            msg = response.choices[0].message
            # Keep a handle on the stored copy: if a tool call turns out to be
            # malformed we must repair it here too, not just skip it.
            assistant_msg = msg.model_dump(exclude_none=True)
            messages.append(assistant_msg)

            if not msg.tool_calls:
                result.status = "completed"
                result.final_message = msg.content or ""
                print(f"\n[{NAME} turn {turn}] agent finished")
                break

            for call in msg.tool_calls:
                name = call.function.name
                raw = call.function.arguments or "{}"
                # [chaos] Demo-only fault injection (model-side truncation
                # simulation; off unless INJECT_MALFORMED_TURN is set).
                if inject_turn == turn:
                    inject_turn = None
                    raw = corrupt(raw)
                    for stored in assistant_msg.get("tool_calls", []):
                        if stored.get("id") == call.id:
                            stored["function"]["arguments"] = raw
                    print(f"\033[2m[fault injection] corrupting this {name} call's JSON (INJECT_MALFORMED_TURN={turn})\033[0m")
                # [h2] Guarded parse: a truncated/malformed tool call becomes
                # feedback the model can recover from, not a fatal crash.
                try:
                    args = json.loads(raw)
                except json.JSONDecodeError as exc:
                    # [h2] The malformed arguments are also sitting in the
                    # assistant message we just stored. Feeding that back
                    # gets the ENTIRE next request rejected by the provider
                    # (400: Invalid JSON in tool call arguments), so the run
                    # dies one turn after the "recovery" appeared to work.
                    # Neutralise the stored copy; the tool result below is
                    # what tells the model what went wrong.
                    for stored in assistant_msg.get("tool_calls", []):
                        if stored.get("id") == call.id:
                            stored["function"]["arguments"] = "{}"
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
                    print(f"\033[35m↻  [{NAME} turn {turn}] {name}: malformed tool call — fed back as a recoverable error (h1 crashes here)\033[0m")
                    continue
                board.record_tool(name, turn, args)
                print(f"[{NAME} turn {turn}] {name}({', '.join((f'{k}={v!r}' if k == 'path' else f'{k}={str(v)[:40]!r}') for k, v in args.items())})")
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

            # [h2] End-of-turn compaction pass. Highlighted (yellow, scissors)
            # so the room can see the harness act, not just the agent.
            dropped = compact(messages)
            if dropped:
                result.notes["dropped_tool_outputs"] = result.notes.get("dropped_tool_outputs", 0) + dropped
                print(f"\033[33m✂  [{NAME} turn {turn}] compaction: dropped {dropped} old tool output(s)\033[0m")
            board.report(turn, messages)
    except Exception as exc:
        result.status = "crashed"
        result.error = f"{type(exc).__name__}: {exc}"
        print(f"\n[{NAME}] CRASHED: {result.error}")

    board.summary(finished=result.status == "completed")
    if board.rereads:
        result.notes["rereads"] = board.rereads
    result.wall_seconds = round(time.monotonic() - start, 1)
    return result
