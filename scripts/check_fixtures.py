"""Assert every task workspace is still in its unsolved state.

    uv run scripts/check_fixtures.py

Task workspaces are fixtures: they must FAIL their own test suites, or the
exercise is broken and any measurement taken against them is meaningless.
They are also, by design, the files agents edit — so a careless `git add`
after a demo run can commit a solved task. That has happened twice during
development (once to refactor_v2, once to fix_bug), each time silently.

Run this before committing anything under tasks/, and as the first step of
any workshop dry run.
"""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TASKS = REPO / "block2_naive_harness" / "tasks"

# Every workspace an exercise hands to an agent, with the state it must be in.
FIXTURES = [
    (TASKS / "short" / "01_fix_bug" / "workspace", "the off-by-one bug must still be present"),
    (TASKS / "short" / "02_add_function" / "workspace", "slugify must still be unimplemented"),
    (TASKS / "short" / "03_small_rename" / "workspace", "the legacy names must still be in place"),
    (TASKS / "medium" / "bug_hunt" / "workspace", "the three seeded bugs must still be present"),
    (TASKS / "long_horizon" / "refactor_v2" / "workspace", "the v1 API must still be in place"),
]

# References are the opposite: they define the solved state and must be green.
REFERENCES = [
    (TASKS / "medium" / "bug_hunt" / "reference", "bug_hunt reference"),
    (TASKS / "long_horizon" / "refactor_v2" / "reference", "refactor_v2 reference"),
]


def is_green(path: Path) -> bool:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=path, capture_output=True, text=True, timeout=180,
    )
    return proc.returncode == 0


def main() -> int:
    problems = []

    for path, expectation in FIXTURES:
        if not path.exists():
            problems.append(f"MISSING  {path.relative_to(REPO)} — regenerate it")
        elif is_green(path):
            problems.append(
                f"SOLVED   {path.relative_to(REPO)} — tests pass but should fail; {expectation}"
            )
        else:
            print(f"[ok  ] unsolved: {path.relative_to(REPO)}")

    for path, label in REFERENCES:
        if not is_green(path):
            problems.append(f"BROKEN   {label} — the reference must be green; fix it before re-deriving")
        else:
            print(f"[ok  ] green:    {path.relative_to(REPO)}")

    print()
    if problems:
        for p in problems:
            print(f"  {p}")
        print(
            "\nFix: `uv run scripts/reset.py` restores workspaces from git — but if the\n"
            "solved state was committed, restore the file by hand or re-derive\n"
            "(scripts/derive_workspace.py, scripts/derive_bug_hunt.py) first."
        )
        return 1

    print("ALL FIXTURES OK — workspaces unsolved, references green.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
