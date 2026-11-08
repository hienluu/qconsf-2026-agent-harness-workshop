"""Shared plumbing for the measured harnesses.

Every harness in this directory exposes the same function:

    run(workspace_dir: str, task: str) -> RunResult

The agent-facing behavior of each harness is what varies; this module holds
only the neutral parts — the result record, the client factory, and access
to the same tools Block 2 used. Tools are NOT the experimental variable, so
all harnesses share them.
"""

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# The harnesses wrap the exact tools attendees used in Block 2.
_BLOCK2 = Path(__file__).resolve().parents[2] / "block2_naive_harness"
sys.path.insert(0, str(_BLOCK2))
from tools import TOOL_SCHEMAS, Workspace  # noqa: E402

SYSTEM_PROMPT = """You are a coding agent operating on a local workspace via tools.
Work step by step: inspect files, make edits, and run the tests to check yourself.
The task is complete only when run_tests reports that every test passed.
When the tests are green, reply with a short summary instead of calling tools."""

# Block 2 caps the naive harness at 20 turns as a spend guardrail. Here the
# budget is 40 for ALL harnesses — held constant and deliberately generous,
# so the experiment measures the protections, never the budget.
MAX_TURNS = 40

# For experiments only: MAX_TURNS=20 overrides the budget. A run with a
# different budget isn't comparable to the 40-turn ones, so every harness
# adds BUDGET_SUFFIX to its recorded name.
if os.environ.get("MAX_TURNS"):
    try:
        MAX_TURNS = int(os.environ["MAX_TURNS"])
    except ValueError:
        MAX_TURNS = 0
    if MAX_TURNS < 1:
        raise SystemExit(f"MAX_TURNS must be a positive whole number; got {os.environ['MAX_TURNS']!r}")
BUDGET_SUFFIX = "" if MAX_TURNS == 40 else f"-{MAX_TURNS}turns"


@dataclass
class RunResult:
    """What a harness run reports back — the row in Block 3's score table."""

    harness: str
    task: str
    status: str = "turn_capped"  # completed | crashed | turn_capped
    turns: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    wall_seconds: float = 0.0
    final_message: str = ""
    error: str = ""
    notes: dict = field(default_factory=dict)  # harness-specific extras


def make_client() -> OpenAI:
    return OpenAI(
        base_url=os.environ["PROVIDER_BASE_URL"],
        api_key=os.environ["PROVIDER_API_KEY"],
    )


def model_name() -> str:
    return os.environ["MODEL"]


def add_usage(result: RunResult, response) -> None:
    usage = getattr(response, "usage", None)
    if usage:
        result.input_tokens += getattr(usage, "prompt_tokens", 0) or 0
        result.output_tokens += getattr(usage, "completion_tokens", 0) or 0


def malformed_injection_turn():
    """Opt-in fault injection for demos: INJECT_MALFORMED_TURN=<n> corrupts
    the first tool call of turn n (its JSON arguments are cut off mid-string,
    reproducing a model that hit its output ceiling). This simulates a
    MODEL-side failure — harness behavior is untouched — so h1 shows its
    authentic crash and h2/h3 show authentic recovery, on demand."""
    value = os.environ.get("INJECT_MALFORMED_TURN")
    return int(value) if value else None


def corrupt(arguments: str) -> str:
    """Cut the JSON off mid-string, like an output-ceiling truncation."""
    return arguments[: max(1, int(len(arguments) * 0.6))]


def transcript_chars(messages: list) -> int:
    total = 0
    for m in messages:
        content = m.get("content") if isinstance(m, dict) else None
        if isinstance(content, str):
            total += len(content)
    return total


# Each harness prints only the markers it can actually emit, so the key
# doubles as a statement of what that harness is capable of doing.
SPEECH_MARKER = ("\033[32m❝\033[0m", "the agent talking — narration mid-run, and its final summary")
CUT_MARKER = ("\033[33m✂\033[0m", "the harness managing context — capping a tool result, or dropping old ones")
RECOVER_MARKER = ("\033[35m↻\033[0m", "the harness recovering from a malformed tool call instead of crashing")
NOTES_MARKER = ("\033[36m✎\033[0m", "the agent writing to its durable notes")
MILESTONE_MARKER = ("\033[33m▸\033[0m", "a scoreboard milestone, e.g. the turn the agent first edited a file")
BUDGET_MARKER = ("\033[1;34m⏱\033[0m", "the harness telling the model its budget (BUDGET_SIGNAL / TURN_NOTICE)")


def marker_key(*entries) -> None:
    """Print a key for the trace markers this harness can emit."""
    print("\033[2m   ┈ trace markers\033[0m")
    for symbol, meaning in entries:
        print(f"     {symbol}  \033[2m{meaning}\033[0m")
    print("     \033[2mplain lines are the agent's tool calls; dim ┈ lines are the scoreboard.\033[0m\n")


def describe_call(name: str, args: dict) -> str:
    """One trace line per tool call, written like the call itself: what it's
    about (the file, the pattern, how much was written), never a slice of
    file content."""
    if name == "write_file":
        size = len(str(args.get("content", "")))
        return f"write_file(file={args.get('path', '')}, chars={size:,})"
    if name == "update_notes":
        return f"update_notes(chars={len(str(args.get('notes', ''))):,})"
    if name == "read_file":
        return f"read_file(file={args.get('path', '')})"
    if name == "search":
        return f"search(pattern={args.get('pattern', '')})"
    return name + "(" + ", ".join(f"{k}={str(v)[:40]}" for k, v in args.items()) + ")"


def print_turn(harness: str, turn: int, said: str | None, calls: list = ()) -> None:
    """One header per turn: the harness and turn, the agent's words if it
    said anything, and how many calls of each tool it made, in order. The
    calls themselves are indented below."""
    counts: dict = {}
    for call in calls:
        counts[call] = counts.get(call, 0) + 1
    tally = ("  [" + ", ".join(f"{n} × {k}" for n, k in counts.items()) + "]") if counts else ""
    if said and said.strip():
        print(f"\033[32m❝  [{harness} turn {turn}] agent says: {said.strip()}\033[0m{tally}")
    else:
        print(f"\033[2m   [{harness} turn {turn}]\033[0m{tally}")
