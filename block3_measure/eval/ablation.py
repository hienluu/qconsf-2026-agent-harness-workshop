"""Measure what h3's durable notes are actually worth.

    uv run eval/ablation.py                 # 3 runs per arm on refactor_v2
    uv run eval/ablation.py --runs 2 --task bug_hunt

Two arms, identical except for one capability:

  h3_full      — truncation, compaction, recovery, guardrail, AND notes
  h3_no_notes  — the same harness with update_notes and the pinned notes
                 message removed

Everything else is held constant: same model, same task, same fresh copy
of the workspace per run, same 40-turn budget. Each run is a separate
process because the harness decides at import time whether notes exist.

Prints a summary at the end: solve rate, turns, input tokens, and
re-reads per arm. Read it with the same scepticism the block teaches —
three runs per arm is enough to see a direction, not to settle a number.
"""

import argparse
import json
import os
import subprocess
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BLOCK3 = HERE.parent
RESULTS = BLOCK3 / "results" / "results.jsonl"

ARMS = [("h3_full", {}), ("h3_no_notes", {"H3_NO_NOTES": "1"})]


def summarize(rows: list, label: str) -> None:
    if not rows:
        print(f"  {label:<14} no runs recorded")
        return
    solved = sum(1 for r in rows if r["tests_green"])
    turns = [r["turns"] for r in rows]
    tokens = [r["input_tokens"] for r in rows]
    rereads = [(r.get("notes") or {}).get("rereads", 0) for r in rows]
    notes_chars = [(r.get("notes") or {}).get("final_notes_chars", 0) for r in rows]
    print(
        f"  {label:<14} solved {solved}/{len(rows)}  "
        f"turns {min(turns)}–{max(turns)} (med {int(statistics.median(turns))})  "
        f"input {min(tokens):,}–{max(tokens):,} (med {int(statistics.median(tokens)):,})  "
        f"re-reads {min(rereads)}–{max(rereads)}"
        + (f"  notes {min(notes_chars)}–{max(notes_chars)} chars" if any(notes_chars) else "")
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Ablate h3's durable notes.")
    ap.add_argument("--runs", type=int, default=3, help="runs per arm (default 3)")
    ap.add_argument("--task", default="refactor_v2")
    args = ap.parse_args()

    started_at = time.time()
    total = args.runs * len(ARMS)
    n = 0
    for arm, env_extra in ARMS:
        for i in range(args.runs):
            n += 1
            print(f"\n{'=' * 70}\n[ablation {n}/{total}] {arm} — run {i + 1} of {args.runs}\n{'=' * 70}")
            env = {**os.environ, **env_extra}
            proc = subprocess.run(
                ["uv", "run", "eval/run_eval.py", "h3", "--task", args.task],
                cwd=BLOCK3, env=env,
            )
            if proc.returncode != 0:
                print(f"[ablation] run failed (exit {proc.returncode}) — continuing")

    rows = [json.loads(line) for line in RESULTS.read_text(encoding="utf-8").splitlines()]
    rows = [r for r in rows if r["timestamp"] >= started_at and r["task"] == args.task]

    print(f"\n{'=' * 70}\nABLATION SUMMARY — {args.task}, {args.runs} run(s) per arm")
    print(f"{'=' * 70}")
    for arm, _ in ARMS:
        summarize([r for r in rows if r["harness"] == arm], arm)
    print(
        "\nThe claim under test: durable notes reduce re-reads after compaction\n"
        "drops old tool output, and therefore reduce cost. Compare the re-read\n"
        "and input-token ranges. Overlapping ranges mean the sample is too small\n"
        "to tell — which is itself a finding worth reporting honestly."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
