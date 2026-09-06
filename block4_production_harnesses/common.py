"""Shared plumbing for the Block 4 specimens.

Every specimen runs the SAME task — fix the off-by-one in stats.py from
Block 2 — against a fresh copy of the workspace, and is judged the same
way: pytest afterward, never the agent's self-report. What varies is the
harness driving the run; the specimen scripts exist to be read side by
side.
"""

import shutil
import subprocess
import sys
import time
from pathlib import Path

BLOCK4 = Path(__file__).resolve().parent
REPO = BLOCK4.parent
FIX_BUG_SOURCE = REPO / "block2_naive_harness" / "tasks" / "short" / "01_fix_bug" / "workspace"

TASK = "One test fails. Find the bug and fix it. Do not modify the tests."


def prepare_workspace(specimen: str) -> Path:
    """Fresh copy of the fix_bug workspace under runs/<specimen>/."""
    run_dir = BLOCK4 / "runs" / specimen
    workspace = run_dir / "workspace"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    shutil.copytree(FIX_BUG_SOURCE, workspace)
    return workspace


def verify(specimen: str, workspace: Path, started: float) -> int:
    """Pytest is the judge. Returns a process exit code."""
    wall = time.monotonic() - started
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=workspace, capture_output=True, text=True, timeout=120,
    )
    summary = (proc.stdout.strip().splitlines() or ["(no output)"])[-1]
    verdict = "SOLVED" if proc.returncode == 0 else "NOT SOLVED"
    print(f"\n--- {specimen}: {verdict} | wall={wall:.1f}s | {summary}")
    return 0 if proc.returncode == 0 else 1
