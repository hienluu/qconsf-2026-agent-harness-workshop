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
import posixpath
from pathlib import PurePosixPath
import time

from base import (
    BUDGET_SUFFIX,
    MAX_TURNS,
    describe_call,
    forget_write,
    print_turn,
    MILESTONE_MARKER,
    BUDGET_MARKER,
    CUT_MARKER,
    NOTES_MARKER,
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

# Ablation switch for measuring what the notes are actually worth:
# H3_NO_NOTES=1 removes the update_notes tool and the pinned notes message,
# leaving everything else in h3 identical. Runs report as a separate
# harness so both appear in the comparison table.
import os as _os

NOTES_ENABLED = _os.environ.get("H3_NO_NOTES") != "1"
NAME = "h3_full" if NOTES_ENABLED else "h3_no_notes"

# [h3, optional] BUDGET_SIGNAL tells the model about its budget, one line
# appended to the turn's last tool result (the end of the conversation, so
# the provider's cache is unaffected). Off by default; each mode is recorded
# as its own harness so it never mixes with plain h3's numbers.
#   compaction  near the compaction budget: warn, and point at the notes
#   progress    every turn: turns left plus the last test result
#   pacing      at half the turns and with 5 left: what to do now
BUDGET_SIGNAL = _os.environ.get("BUDGET_SIGNAL", "").strip().lower()
if BUDGET_SIGNAL and BUDGET_SIGNAL not in ("compaction", "progress", "pacing"):
    raise SystemExit(f"BUDGET_SIGNAL must be compaction, progress or pacing; got {BUDGET_SIGNAL!r}")
if BUDGET_SIGNAL:
    NAME += "+" + BUDGET_SIGNAL
NAME += BUDGET_SUFFIX

MAX_TOOL_RESULT_CHARS = 6_000
# ~20k tokens; keeps cumulative cost linear on long tasks. Overridable so you
# can watch compaction work: on refactor_v2 the transcript peaks just under
# this default (77k of 80k in one measured run), so the protection is real but
# rarely fires. Tighten it and it fires on demand:
#   TRANSCRIPT_CHAR_BUDGET=40000 uv run eval/run_eval.py h2 --task refactor_v2
TRANSCRIPT_CHAR_BUDGET = int(_os.environ.get("TRANSCRIPT_CHAR_BUDGET", 80_000))
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

# [h3] Files the agent may not write, no matter what it decides: anything
# under a tests/ folder, any test_*.py or *_test.py, and conftest.py. The
# path is normalized first, so "./tests/x.py" or "src/../tests/x.py" can't
# slip past a plain prefix check.
def is_test_file(path: str) -> bool:
    p = PurePosixPath(posixpath.normpath(path.replace("\\", "/")))
    name = p.name
    return ("tests" in p.parts or name == "conftest.py"
            or (name.startswith("test_") and name.endswith(".py"))
            or name.endswith("_test.py"))


def truncate(text: str) -> tuple[str, int]:
    """Cap a tool result, keeping head and tail. Returns the capped text and
    how many characters were removed, so the harness can report it."""
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
    dropped = 0
    for m in messages[:-KEEP_RECENT_MESSAGES]:
        if transcript_chars(messages) <= TRANSCRIPT_CHAR_BUDGET:
            break
        # [h3] This role filter is unchanged from h2, but here it is
        # load-bearing: the durable notes live in a system message, so
        # widening compaction beyond tool messages would silently break
        # the memory guarantee.
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
        if is_test_file(path):
            result.notes["guardrail_refusals"] = result.notes.get("guardrail_refusals", 0) + 1
            board.mark("⛔")
            print(f"\033[31m⛔ [{NAME}] guardrail refused a write to {path!r}\033[0m")
            forget_write(str(path))
            return f"guardrail: writing to {path!r} is not permitted — tests are read-only."
        return ws.write_file(path, args["content"])

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        # [h3] Pinned durable notes, updated in place by update_notes.
        *([{"role": "system", "content": NOTES_PREFIX + "(empty)"}] if NOTES_ENABLED else []),
        {"role": "user", "content": task},
    ]
    notes_index = 1 if NOTES_ENABLED else None

    # [h3] update_notes rewrites the pinned message and confirms.
    def update_notes(args):
        messages[notes_index]["content"] = NOTES_PREFIX + args["notes"]
        return "notes updated"

    # [h3, optional] The progress signal needs the last test result.
    signal_state = {"turn": 0, "tests": None}

    def run_tests_tracked(args):
        out = ws.run_tests()
        signal_state["tests"] = ((out.strip().splitlines() or [""])[-1], signal_state["turn"])
        return out

    def budget_signal(turn: int, chars: int):
        left = MAX_TURNS - turn
        if BUDGET_SIGNAL == "compaction" and NOTES_ENABLED and chars >= 0.85 * TRANSCRIPT_CHAR_BUDGET:
            where = (f"is at {chars:,} of its {TRANSCRIPT_CHAR_BUDGET:,}-character budget, so older "
                     f"tool results will soon be replaced by a placeholder"
                     if chars < TRANSCRIPT_CHAR_BUDGET else
                     f"is over its {TRANSCRIPT_CHAR_BUDGET:,}-character budget, so older tool "
                     f"results are being replaced by a placeholder")
            return (f"[harness] The conversation {where}. Save anything you will still need "
                    f"to your notes with update_notes.")
        if BUDGET_SIGNAL == "progress":
            tests = signal_state["tests"]
            status = (f"Last test run (turn {tests[1]}): {tests[0]}." if tests
                      else "Tests not run yet.")
            return f"[harness] Turn {turn} of {MAX_TURNS} used: {left} left. {status}"
        if BUDGET_SIGNAL == "pacing":
            if turn == MAX_TURNS // 2:
                return (f"[harness] Half of your {MAX_TURNS} turns are used. If you haven't "
                        f"started editing files, start now.")
            if left == 5:
                return ("[harness] 5 turns left. Run the tests, fix what fails, then reply "
                        "with a summary.")
        return None

    dispatch = {
        "list_files": lambda args: ws.list_files(),
        "read_file": lambda args: ws.read_file(args["path"]),
        "write_file": guarded_write,
        "search": lambda args: ws.search(args["pattern"]),
        "run_tests": run_tests_tracked,
    }
    if NOTES_ENABLED:
        dispatch["update_notes"] = update_notes
    tool_schemas = TOOL_SCHEMAS + ([NOTES_SCHEMA] if NOTES_ENABLED else [])

    result = RunResult(harness=NAME, task=workspace_dir)
    board = Scoreboard(MAX_TURNS)
    board.timing = True   # Block 3 shows how long each turn took
    board.drops_context = True   # compaction drops old tool outputs
    board.budget_told = BUDGET_SIGNAL in ("progress", "pacing")
    board.legend()
    marker_key(SPEECH_MARKER, CUT_MARKER, RECOVER_MARKER, NOTES_MARKER, MILESTONE_MARKER,
               *([BUDGET_MARKER] if BUDGET_SIGNAL else []))
    inject_turn = malformed_injection_turn()
    start = time.monotonic()
    try:
        # Chars the harness has removed from the transcript so far. Re-added to
        # a cumulative counter every turn, because the transcript is re-sent on
        # every request — a cut made at turn 5 keeps paying for the rest of the
        # run. That compounding is the real saving, not the one-time cut.
        trimmed_chars = 0
        for turn in range(1, MAX_TURNS + 1):
            signal_state["turn"] = turn
            result.notes["chars_not_resent"] = (
                result.notes.get("chars_not_resent", 0) + trimmed_chars
            )
            response = call_model(
                client,
                model=model,
                messages=messages,
                tools=tool_schemas,
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
                if name == "update_notes":
                    # [h3] Highlighted (cyan, pencil): the agent is choosing
                    # to persist memory — the behavior worth watching for.
                    print(f"\033[36m✎  [{NAME} turn {turn}] update_notes({str(args.get('notes', ''))[:60]!r}...)\033[0m")
                else:
                    board.record_tool(name, turn, args)
                    print(f"     {describe_call(name, args)}")
                try:
                    result_text = dispatch[name](args)
                except Exception as exc:
                    result_text = f"tool error: {exc}"
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
            # [h3, optional] Budget signal, after compaction so it sees the
            # conversation's real size, appended among the newest messages.
            # Not after the last turn: no turn follows for the model to read it.
            if BUDGET_SIGNAL and turn < MAX_TURNS and messages and messages[-1].get("role") == "tool":
                signal = budget_signal(turn, transcript_chars(messages))
                if signal:
                    messages[-1]["content"] += "\n" + signal
                    result.notes["budget_signals"] = result.notes.get("budget_signals", 0) + 1
                    print(f"\033[1;34m⏱  told the model: {signal}\033[0m")
            board.report(turn, messages)
    except Exception as exc:
        result.status = "crashed"
        result.error = f"{type(exc).__name__}: {exc}"
        print(f"\n[{NAME}] CRASHED: {result.error}")

    board.summary(finished=result.status == "completed", error=result.error)
    if board.rereads:
        result.notes["rereads"] = board.rereads
    result.wall_seconds = round(time.monotonic() - start, 1)
    # [h3] Report the notes content itself, not just its size — what the
    # agent chose to remember is a first-class result of the run.
    if NOTES_ENABLED:
        final_notes = messages[notes_index]["content"][len(NOTES_PREFIX):]
        result.notes["final_notes_chars"] = len(final_notes)
        result.notes["final_notes_text"] = final_notes
    return result
