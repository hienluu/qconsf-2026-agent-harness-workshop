"""Render the harness comparison table from results/results.jsonl.

    uv run eval/compare.py

Shows the LATEST run for each (harness, task) pair. This table is the
payoff of Block 3: same model, same tasks, same tools, different
harnesses. Two things it can't separate out: the model's run-to-run
randomness (one run per row), and which of a harness's protections did the
work (h2 adds three at once).
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
HARNESS_ORDER = ["h1_naive", "h2_managed", "h2_managed+turns", "h3_full", "h3_no_notes"]
TASK_ORDER = ["fix_bug", "touch_tests", "add_function", "small_rename", "bug_hunt", "refactor_v2"]


def main() -> int:
    if not RESULTS.exists():
        print(f"no results yet — run eval/run_eval.py first ({RESULTS})")
        return 1

    latest = {}
    with RESULTS.open() as fh:
        for line in fh:
            row = json.loads(line)
            latest[(row["harness"], row["task"])] = row

    console = Console()
    table = Table(
        title="Same model, same tasks, different harnesses (one run each)",
        caption=(
            "fired = times each protection acted: ✂cut tool output · ✂✂dropped old output · ↻recovered\n"
            "not re-sent = conversation characters the harness kept off the wire, counted once per\n"
            "turn they would otherwise have been re-sent (the whole conversation goes over on every turn)\n"
            "wall-clock is in results.jsonl but not here — it is run-to-run noise, not a harness property"
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

    # Variants (e.g. h2 with a TURN_NOTICE schedule) get their own rows after
    # the known harnesses.
    extras = sorted({h for h, _ in latest} - set(HARNESS_ORDER))
    for harness in HARNESS_ORDER + extras:
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
            if n.get("guardrail_refusals"):
                fired.append(f"⛔{n['guardrail_refusals']}")
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
                age(row["timestamp"]),
            )
        table.add_section()

    console.print(table)
    # Rows only compare if they came from the same model and provider; say so
    # when they didn't.
    setups = {}
    for (harness, task), row in latest.items():
        setup = row.get("model") or "unknown model"
        if row.get("provider"):
            setup += f" via {row['provider']}"
        setups.setdefault(setup, []).append(f"{harness}/{task}")
    if len(setups) > 1:
        console.print("[yellow]These rows came from different setups, so they don't "
                      "compare directly:[/yellow]")
        for setup, rows in setups.items():
            console.print(f"[yellow]  {setup}: {', '.join(sorted(rows))}[/yellow]")
    if not any((latest.get(k, {}).get("notes") or {}).get("chars_not_resent")
               for k in latest):
        console.print(
            "[dim]No 'not re-sent' figures yet — that column fills in once you run "
            "h2 or h3 on refactor_v2, the only task big enough to trip the limits.[/dim]"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
