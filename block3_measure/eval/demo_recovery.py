"""Show malformed-tool-call recovery on demand — no API calls, no cost.

    uv run eval/demo_recovery.py

The recovery protection fires rarely in live runs (it's tail-risk
insurance), so this demo replays the triggering event deterministically: a
write_file tool call whose JSON arguments were cut off mid-string — the
exact failure that killed a real naive-harness run at turn 11 during task
tuning (the model hit its output ceiling while batching large writes).

Both harnesses receive the same bytes. Watch what each does next.
"""

import json

# A write_file call truncated mid-content, as emitted by a model that ran
# out of output budget while batching several large file rewrites.
TRUNCATED_ARGUMENTS = (
    '{"path": "pyledger/core/ledger.py", '
    '"content": "from pyledger.core.validation import validate_entry\\n\\n\\ndef new_led'
)


def h1_path(arguments: str):
    """h1_naive: unguarded parse — one bad call ends the entire run."""
    args = json.loads(arguments)  # raises; nothing catches it upstream
    return args


def h2_path(arguments: str):
    """h2_managed: guarded parse — the failure becomes feedback."""
    try:
        return json.loads(arguments), None
    except json.JSONDecodeError as exc:
        feedback = (
            f"harness error: tool call arguments were not valid JSON ({exc}). "
            f"Your output was probably truncated — retry with smaller file "
            f"content or fewer tool calls per turn."
        )
        return None, feedback


def main() -> None:
    print("The model emitted this tool call (truncated at its output ceiling):\n")
    print(f"  write_file arguments = {TRUNCATED_ARGUMENTS[:70]}...\n")

    print("=" * 72)
    print("h1_naive receives it:")
    print("=" * 72)
    try:
        h1_path(TRUNCATED_ARGUMENTS)
    except json.JSONDecodeError as exc:
        print(f"\n  UNHANDLED {type(exc).__name__}: {exc}")
        print("  The process dies here. Run over, workspace stranded mid-task,")
        print("  everything the agent knew gone with the transcript.\n")

    print("=" * 72)
    print("h2_managed receives the same bytes:")
    print("=" * 72)
    _, feedback = h2_path(TRUNCATED_ARGUMENTS)
    print(f"\n\033[35m↻  malformed tool call — fed back as a recoverable error\033[0m")
    print(f"\n  The model sees, as an ordinary tool result:\n    {feedback!r}")
    print("\n  The loop continues; next turn, the model retries with smaller")
    print("  writes. Same bytes in — crash vs. conversation.\n")


if __name__ == "__main__":
    main()
