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

import os as _os
import json
import time

from base import (
    BUDGET_SUFFIX,
    MAX_TURNS,
    describe_call,
    print_turn,
    MILESTONE_MARKER,
    BUDGET_MARKER,
    CUT_MARKER,
    RECOVER_MARKER,
    SPEECH_MARKER,
    marker_key,
    SYSTEM_PROMPT,
    TOOL_SCHEMAS,
    RunResult,
    Workspace,
    add_usage,
    corrupt,
    call_model,
    make_client,
    malformed_injection_turn,
    model_name,
    sampling,
    transcript_chars,
)
# base puts block2 on sys.path (for tools); reuse its scoreboard too.
from scoreboard import Scoreboard  # noqa: E402

# [h2, optional] TURN_NOTICE tells the model how much of its turn budget is
# left: TURN_NOTICE=every after every turn, or TURN_NOTICE=10,15,20 after
# just those turns. Off by default. Each schedule is recorded under its own
# name, so it never mixes with plain h2's numbers or another schedule's.
def _notice_schedule(raw: str):
    if not raw:
        return None
    if raw.strip().lower() == "every":
        return "every"
    try:
        turns = sorted({int(x) for x in raw.split(",") if x.strip()})
    except ValueError:
        turns = []
    if not turns or turns[0] < 1 or turns[-1] > MAX_TURNS:
        raise SystemExit(f"TURN_NOTICE must be 'every' or turn numbers from 1 to {MAX_TURNS}, "
                         f"comma-separated (e.g. 10,15,20); got {raw!r}")
    return turns


TURN_NOTICE = _notice_schedule(_os.environ.get("TURN_NOTICE", ""))
if TURN_NOTICE is None:
    NAME = "h2_managed"
elif TURN_NOTICE == "every":
    NAME = "h2_managed+turns"
else:
    NAME = "h2_managed+turns@" + ",".join(map(str, TURN_NOTICE))
NAME += BUDGET_SUFFIX

# [h2] Protection knobs.
MAX_TOOL_RESULT_CHARS = 6_000     # per tool result fed back to the model
# ~20k tokens; keeps cumulative cost linear on long tasks. Overridable so you
# can watch compaction work: on refactor_v2 the transcript peaks just under
# this default (77k of 80k in one measured run), so the protection is real but
# rarely fires. Tighten it and it fires on demand:
#   TRANSCRIPT_CHAR_BUDGET=40000 uv run eval/run_eval.py h2 --task refactor_v2
TRANSCRIPT_CHAR_BUDGET = int(_os.environ.get("TRANSCRIPT_CHAR_BUDGET", 80_000))
KEEP_RECENT_MESSAGES = 12         # never compact the newest N messages
DROPPED_MARKER = "[old tool output dropped by the harness to save context — re-run the tool if you need it again]"


def truncate(text: str) -> tuple[str, int]:
    """[h2] Cap a tool result, keeping the head and tail (errors live at both
    ends). Returns the capped text and how many characters were removed, so
    the harness can report what it did — this protection fires constantly and
    would otherwise be invisible."""
    if len(text) <= MAX_TOOL_RESULT_CHARS:
        return text, 0
    # Slices are derived from the cap, not hardcoded, so lowering
    # MAX_TOOL_RESULT_CHARS to experiment still shrinks the result.
    keep_head = MAX_TOOL_RESULT_CHARS * 2 // 3
    keep_tail = MAX_TOOL_RESULT_CHARS // 4
    head, tail = text[:keep_head], text[-keep_tail:]
    dropped = len(text) - len(head) - len(tail)
    capped = f"{head}\n... [harness truncated {dropped} chars] ...\n{tail}"
    # Report the NET reduction: the marker itself costs characters, so the
    # figure we count must match the "7,141 -> 5,540" the run prints.
    return capped, len(text) - len(capped)


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
    board.timing = True   # Block 3 shows how long each turn took
    board.drops_context = True   # compaction drops old tool outputs
    board.budget_told = TURN_NOTICE is not None
    board.legend()
    marker_key(SPEECH_MARKER, CUT_MARKER, RECOVER_MARKER, MILESTONE_MARKER,
               *([BUDGET_MARKER] if TURN_NOTICE else []))
    inject_turn = malformed_injection_turn()
    start = time.monotonic()
    try:
        # Chars the harness has removed from the transcript so far. Re-added to
        # a cumulative counter every turn, because the transcript is re-sent on
        # every request — a cut made at turn 5 keeps paying for the rest of the
        # run. That compounding is the real saving, not the one-time cut.
        trimmed_chars = 0
        for turn in range(1, MAX_TURNS + 1):
            result.notes["chars_not_resent"] = (
                result.notes.get("chars_not_resent", 0) + trimmed_chars
            )
            response = call_model(
                client,
                model=model,
                messages=messages,
                tools=TOOL_SCHEMAS,
                **sampling(),
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
                print(f"\033[1;32m❝  [{NAME} turn {turn}] agent finished:\033[0m"
                      f"\n\033[32m{msg.content}\033[0m")
                break

            # Play-by-play, same as the Block 2 harness: models narrate
            # alongside their tool calls ("the tests expect X, so I'll..."),
            # and that narration is where a drifting plan shows up first.
            # The turn number prints once, here; the calls below are indented
            # under it.
            print_turn(NAME, turn, msg.content, [c.function.name for c in msg.tool_calls])

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
                    board.mark("↻")
                    print(f"\033[35m↻  [{NAME} turn {turn}] {name}: malformed tool call — fed back as a recoverable error (h1 crashes here)\033[0m")
                    continue
                board.record_tool(name, turn, args)
                print(f"     {describe_call(name, args)}")
                try:
                    result_text = dispatch[name](args)
                except Exception as exc:
                    result_text = f"tool error: {exc}"
                # [h2] Cap what a single tool result may inject, and say so —
                # this is the protection that fires most and saves most.
                capped, cut = truncate(result_text)
                if cut:
                    result.notes["truncations"] = result.notes.get("truncations", 0) + 1
                    board.mark("✂")
                    result.notes["chars_truncated"] = result.notes.get("chars_truncated", 0) + cut
                    trimmed_chars += cut
                    print(f"\033[33m✂  [{NAME} turn {turn}] truncated {name} output: "
                          f"{len(result_text):,} → {len(capped):,} chars (model sees head + tail)\033[0m")
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": capped,
                })

            # [h2, optional] Budget notice, appended to this turn's last tool
            # result: the end of the conversation, so the start (and the
            # provider's cache) never changes, and every tool call still has
            # exactly one result message.
            # Not after the last turn: no turn follows for the model to read it.
            due = turn < MAX_TURNS and (TURN_NOTICE == "every" or (TURN_NOTICE and turn in TURN_NOTICE))
            if due and messages and messages[-1].get("role") == "tool":
                notice = f"[harness] turn {turn} of {MAX_TURNS} used: {MAX_TURNS - turn} left."
                messages[-1]["content"] += "\n" + notice
                print(f"\033[1;34m⏱  told the model: {notice}\033[0m")

            # [h2] End-of-turn compaction pass. Highlighted (yellow, scissors)
            # so the room can see the harness act, not just the agent.
            size_before = sum(len(str(m.get("content") or "")) for m in messages)
            dropped = compact(messages)
            if dropped:
                freed = size_before - sum(len(str(m.get("content") or "")) for m in messages)
                trimmed_chars += freed
                result.notes["dropped_tool_outputs"] = result.notes.get("dropped_tool_outputs", 0) + dropped
                board.mark("✂✂", dropped)
                result.notes["chars_compacted"] = result.notes.get("chars_compacted", 0) + freed
                print(f"\033[33m✂  [{NAME} turn {turn}] compaction: dropped {dropped} old tool "
                      f"output(s), freeing {freed:,} chars\033[0m")
            board.report(turn, messages)
    except Exception as exc:
        result.status = "crashed"
        result.error = f"{type(exc).__name__}: {exc}"
        print(f"\n[{NAME}] CRASHED: {result.error}")

    board.summary(finished=result.status == "completed", error=result.error)
    if board.rereads:
        result.notes["rereads"] = board.rereads
    result.wall_seconds = round(time.monotonic() - start, 1)
    return result
