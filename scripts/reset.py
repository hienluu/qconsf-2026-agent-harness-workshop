"""Reset all exercise state so Blocks 2 and 3 can be rerun from scratch.

    uv run scripts/reset.py

Three kinds of state accumulate across the exercises; this resets each and
says what it did:

  1. Task workspaces  — agents edit them in place (Block 2) so they're
     restored to the committed pristine state, including deleting any new
     files an agent created (git restore + git clean).
  2. Eval run copies  — results/runs/ workspace copies and wreckage.
  3. The score table  — results.jsonl is archived with a timestamp, never
     deleted; compare.py starts fresh.

Safe to run at any time; each step is a no-op if there's nothing to do.
"""

import shutil
import subprocess
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TASKS = "block2_naive_harness/tasks/"
RESULTS = REPO / "block3_measure" / "results"


def git(*args) -> str:
    proc = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed:\n{proc.stderr}")
    return proc.stdout.strip()


def main() -> None:
    dirty = git("status", "--porcelain", "--", TASKS)
    if dirty:
        git("restore", "--", TASKS)
        git("clean", "-fdq", "--", TASKS)
        print(f"[reset] task workspaces restored ({len(dirty.splitlines())} path(s) were modified)")
    else:
        print("[reset] task workspaces already pristine")

    for runs, label in [
        (RESULTS / "runs", "block 3 eval run copies"),
        (REPO / "block4_production_harnesses" / "runs", "block 4 specimen runs + receipts"),
    ]:
        if runs.exists():
            shutil.rmtree(runs)
            print(f"[reset] {label} removed")
        else:
            print(f"[reset] no {label} to remove")

    table = RESULTS / "results.jsonl"
    if table.exists():
        archive = RESULTS / f"results.{datetime.now():%Y%m%d-%H%M%S}.jsonl"
        table.rename(archive)
        print(f"[reset] score table archived to {archive.relative_to(REPO)}")
    else:
        print("[reset] no score table to archive")

    print("[reset] done — rerun from Block 2 step 3 or Block 3 step 1")


if __name__ == "__main__":
    main()
