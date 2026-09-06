"""h3_full — h2 plus durable memory and a real guardrail (marked [h3]).

  4. Durable working notes — a pinned message the agent updates via a new
     `update_notes` tool. Compaction can drop any tool output, but the
     notes survive: the agent's plan and progress no longer live only in
     the transcript that dies with the context window.
  5. Write-path guardrail — "do not modify the tests" stops being a hope
     expressed in the prompt and becomes a rule the harness enforces.

Read as `diff h2_managed.py h3_full.py`. Note what moved where: in h1/h2
the agent's memory IS the transcript; in h3 the harness gives memory a
home the transcript can't take down.
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

NAME = "h3_full"

MAX_TOOL_RESULT_CHARS = 6_000
TRANSCRIPT_CHAR_BUDGET = 80_000   # ~20k tokens; keeps cumulative cost linear on long tasks
KEEP_RECENT_MESSAGES = 12
DROPPED_MARKER = "[old tool output dropped by the harness to save context — re-run the tool if you need it again]"

# [h3] The notes prompt lives at messages[1], refreshed in place.
NOTES_PREFIX = "YOUR WORKING NOTES (persist even when old tool output is dropped — keep plan and per-file progress here):\n"

# [h3] One more tool: overwrite the durable notes.
NOTES_SCHEMA = {
    "type": "function",
    "function": {
        "name": "update_notes",
        "description": (
            "Overwrite your persistent working notes. They survive context "
            "compaction, so keep your plan, discovered facts, and per-file "
            "progress here rather than only in conversation."
        ),
        "parameters": {
            "type": "object",
            "properties": {"notes": {"type": "string"}},
            "required": ["notes"],
        },
    },
}

# [h3] Paths the agent may not write, no matter what it decides.
PROTECTED_PREFIXES = ("tests/", "conftest.py")


def truncate(text: str) -> str:
    if len(text) <= MAX_TOOL_RESULT_CHARS:
        return text
    head, tail = text[:4_000], text[-1_500:]
    dropped = len(text) - len(head) - len(tail)
    return f"{head}\n... [harness truncated {dropped} chars] ...\n{tail}"


def compact(messages: list) -> int:
    dropped = 0
    for m in messages[:-KEEP_RECENT_MESSAGES]:
        if transcript_chars(messages) <= TRANSCRIPT_CHAR_BUDGET:
            break
        # [h3] Never drop system messages — the durable notes live there.
        if m.get("role") == "tool" and len(m.get("content") or "") > len(DROPPED_MARKER):
            m["content"] = DROPPED_MARKER
            dropped += 1
    return dropped


def run(workspace_dir: str, task: str) -> RunResult:
    client = make_client()
    model = model_name()
    ws = Workspace(workspace_dir)

    # [h3] Guarded write: the harness, not the prompt, enforces test immutability.
    def guarded_write(args):
        path = args["path"]
        if path.startswith(PROTECTED_PREFIXES) or path in PROTECTED_PREFIXES:
            return f"guardrail: writing to {path!r} is not permitted — tests are read-only."
        return ws.write_file(path, args["content"])

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        # [h3] Pinned durable notes, updated in place by update_notes.
        {"role": "system", "content": NOTES_PREFIX + "(empty)"},
        {"role": "user", "content": task},
    ]

    # [h3] update_notes rewrites the pinned message and confirms.
    def update_notes(args):
        messages[1]["content"] = NOTES_PREFIX + args["notes"]
        return "notes updated"

    dispatch = {
        "list_files": lambda args: ws.list_files(),
        "read_file": lambda args: ws.read_file(args["path"]),
        "write_file": guarded_write,
        "search": lambda args: ws.search(args["pattern"]),
        "run_tests": lambda args: ws.run_tests(),
        "update_notes": update_notes,
    }
    tool_schemas = TOOL_SCHEMAS + [NOTES_SCHEMA]

    result = RunResult(harness=NAME, task=workspace_dir)
    start = time.monotonic()
    try:
        for turn in range(1, MAX_TURNS + 1):
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tool_schemas,
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
                    "content": truncate(result_text),
                })

            dropped = compact(messages)
            if dropped:
                result.notes["dropped_tool_outputs"] = result.notes.get("dropped_tool_outputs", 0) + dropped
                print(f"[{NAME} turn {turn}] compaction: dropped {dropped} old tool output(s)")
    except Exception as exc:
        result.status = "crashed"
        result.error = f"{type(exc).__name__}: {exc}"
        print(f"\n[{NAME}] CRASHED: {result.error}")

    result.wall_seconds = round(time.monotonic() - start, 1)
    # [h3] Report the notes content itself, not just its size — what the
    # agent chose to remember is a first-class result of the run.
    final_notes = messages[1]["content"][len(NOTES_PREFIX):]
    result.notes["final_notes_chars"] = len(final_notes)
    result.notes["final_notes_text"] = final_notes
    return result
