"""Render the harness comparison table from results/results.jsonl.

    uv run eval/compare.py

Shows the LATEST run for each (harness, task) pair. This table is the
payoff of Block 3: same model, same tasks, same tools — the harness is
the only variable, and here is what it was worth.
"""

import json
import time
from pathlib import Path

from rich.console import Console
from rich.table import Table


def age(timestamp: float) -> str:
    seconds = int(time.time() - timestamp)
    if seconds < 90:
        return f"{seconds}s ago"
    if seconds < 5400:
        return f"{seconds // 60}m ago"
    return f"{seconds // 3600}h ago"

RESULTS = Path(__file__).resolve().parent.parent / "results" / "results.jsonl"
HARNESS_ORDER = ["h1_naive", "h2_managed", "h3_full", "h3_no_notes"]
TASK_ORDER = ["fix_bug", "add_function", "small_rename", "bug_hunt", "refactor_v2"]


def main() -> int:
    if not RESULTS.exists():
        print(f"no results yet — run eval/run_eval.py first ({RESULTS})")
        return 1

    # Reference rows ship with the repo so the h1 baseline is present without
    # every attendee paying to re-measure it. Their own runs always win.
    latest = {}
    reference = RESULTS.parent.parent / "reference_results.jsonl"
    if reference.exists():
        for line in reference.read_text().splitlines():
            row = json.loads(line)
            if row["harness"] == "h1_naive" and row["task"] == "refactor_v2":
                row["is_reference"] = True
                latest[(row["harness"], row["task"])] = row

    with RESULTS.open() as fh:
        for line in fh:
            row = json.loads(line)
            latest[(row["harness"], row["task"])] = row

    console = Console()
    table = Table(title="Same model, same tasks — the harness is the only variable")
    table.add_column("harness", style="bold")
    table.add_column("task")
    table.add_column("solved?")
    table.add_column("status")
    table.add_column("turns", justify="right")
    table.add_column("tokens in+out", justify="right")
    table.add_column("wall s", justify="right")
    table.add_column("when")
    table.add_column("detail")

    for harness in HARNESS_ORDER:
        for task in TASK_ORDER:
            row = latest.get((harness, task))
            if not row:
                continue
            solved = "[green]YES[/green]" if row["tests_green"] else "[red]no[/red]"
            detail = row.get("error") or row.get("pytest_summary", "")
            extras = row.get("notes") or {}
            if extras:
                detail += "  " + " ".join(f"{k}={v}" for k, v in extras.items())
            table.add_row(
                harness,
                task,
                solved,
                row["status"],
                str(row["turns"]),
                f"{row['input_tokens']:,}+{row['output_tokens']:,}",
                str(row["wall_seconds"]),
                "reference" if row.get("is_reference") else age(row["timestamp"]),
                detail[:80],
            )
        table.add_section()

    console.print(table)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
