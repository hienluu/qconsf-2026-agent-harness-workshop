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
    table = Table(
        title="Same model, same tasks — the harness is the only variable",
        caption=(
            "fired = times each protection acted: ✂cut tool output · ✂✂dropped old output · ↻recovered\n"
            "not re-sent = transcript characters the harness kept off the wire, counted once per\n"
            "turn they would otherwise have been re-sent (the whole transcript goes over on every turn)\n"
            "wall-clock is in results.jsonl but not here — it is run-to-run noise, not a harness property\n"
            "\"not your run\" = our h1 baseline on refactor_v2, shipped with the repo so you don't pay to\n"
            "re-measure it. It is not in results.jsonl, so reset.py never clears it. Every other row is yours."
        ),
        caption_justify="left",
    )
    table.add_column("harness", style="bold")
    table.add_column("task")
    table.add_column("solved?", justify="center")
    table.add_column("turns", justify="right")
    table.add_column("input tokens", justify="right")
    table.add_column("protections fired")
    table.add_column("not re-sent", justify="right")
    table.add_column("when")

    for harness in HARNESS_ORDER:
        for task in TASK_ORDER:
            row = latest.get((harness, task))
            if not row:
                continue
            if row["status"] == "crashed":
                solved = "[red]CRASH[/red]"
            else:
                solved = "[green]YES[/green]" if row["tests_green"] else "[red]no[/red]"

            n = row.get("notes") or {}
            fired = []
            if n.get("truncations"):
                fired.append(f"✂{n['truncations']}")
            if n.get("dropped_tool_outputs"):
                fired.append(f"✂✂{n['dropped_tool_outputs']}")
            if n.get("malformed_calls"):
                fired.append(f"↻{n['malformed_calls']}")
            if n.get("rereads"):
                fired.append(f"[magenta]re-read {n['rereads']}[/magenta]")

            saved = n.get("chars_not_resent") or 0
            table.add_row(
                harness,
                task,
                solved,
                str(row["turns"]),
                f"{row['input_tokens']:,}",
                " ".join(fired) if fired else "[dim]none[/dim]",
                f"{saved // 1000:,}k" if saved else "[dim]—[/dim]",
                "[dim]not your run[/dim]" if row.get("is_reference") else age(row["timestamp"]),
            )
        table.add_section()

    console.print(table)
    if not any((latest.get(k, {}).get("notes") or {}).get("chars_not_resent")
               for k in latest):
        console.print(
            "[dim]No 'not re-sent' figures yet — that column fills in once you run "
            "h2 or h3 on refactor_v2, the only task big enough to trip the limits.[/dim]"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
