"""Render the harness comparison table from results/results.jsonl.

    uv run eval/compare.py

Shows the LATEST run for each (harness, task) pair. This table is the
payoff of Block 3: same model, same tasks, same tools, different
harnesses. Two things it can't separate out: the model's run-to-run
randomness (one run per row), and which of a harness's protections did the
work (h2 adds three at once).
"""

import json
import re
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.markup import escape
from rich.table import Table


def age(timestamp: float) -> str:
    seconds = int(time.time() - timestamp)
    if seconds < 90:
        return f"{seconds}s ago"
    if seconds < 5400:
        return f"{seconds // 60}m ago"
    return f"{seconds // 3600}h ago"

def short(harness: str) -> str:
    """The table's label: h3+progress·20t for h3_full+progress-20turns, so
    the name survives a narrow terminal. Folders and results keep full names."""
    for full, brief in (("h1_naive", "h1"), ("h2_managed", "h2"), ("h3_no_notes", "h3·no-notes"), ("h3_full", "h3")):
        harness = harness.replace(full, brief)
    return re.sub(r"-(\d+)turns", r"·\1t", harness)


RESULTS = Path(__file__).resolve().parent.parent / "results" / "results.jsonl"
HARNESS_ORDER = ["h1_naive", "h2_managed", "h2_managed+turns", "h3_full", "h3_no_notes"]
TASK_ORDER = ["fix_bug", "touch_tests", "add_function", "small_rename", "bug_hunt", "refactor_v2"]


def main() -> int:
    if not RESULTS.exists():
        print(f"no results yet — run eval/run_eval.py first ({RESULTS})")
        return 1

    latest = {}
    with RESULTS.open(encoding="utf-8") as fh:
        for line in fh:
            row = json.loads(line)
            latest[(row["harness"], row["task"])] = row

    console = Console()
    table = Table(
        title="Same model, same tasks, different harnesses (one run each)",
        caption=(
            "fired = times each protection acted: ✂cut tool output · ✂✂dropped old output · ↻recovered\n"
            "· ⛔refused test write. re-read isn't a protection: it's the agent fetching a file again,\n"
            "shown here because after a ✂✂ it's what compaction cost\n"
            "not re-sent = conversation characters the harness kept off the wire, counted once per\n"
            "turn they would otherwise have been re-sent (the whole conversation goes over on every turn)\n"
            "harness: h2 = h2_managed, h3 = h3_full, ·20t = run with MAX_TURNS=20\n"
            "wall-clock is in results.jsonl but not here — it is run-to-run noise, not a harness property"
        ),
        caption_justify="left",
    )
    table.add_column("harness", style="bold", no_wrap=True)
    table.add_column("task")
    table.add_column("solved?", justify="center")
    table.add_column("turns", justify="right")
    table.add_column("input tokens", justify="right", no_wrap=True)
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
                short(harness),
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
    # A CRASH cell alone doesn't say why; the reason is in the row.
    crashed = [(h, t, r) for (h, t), r in latest.items() if r["status"] == "crashed"]
    if crashed:
        sys.path.insert(0, str(RESULTS.parents[1] / "harnesses"))
        import base
        # Runs that crashed the same way share one explanation.
        reasons = {}
        for harness, task, row in crashed:
            reason = tuple(base.explain_crash(row.get("error") or "no error recorded", row["turns"]))
            reasons.setdefault(reason, []).append(f"{harness}/{task} (turn {row['turns']})")
        console.print("[red]Why the crashed runs crashed:[/red]")
        for reason, runs in reasons.items():
            console.print(f"[red]  {', '.join(runs)}:[/red]", highlight=False)
            for line in reason:
                console.print(f"    {escape(line)}", highlight=False)
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
