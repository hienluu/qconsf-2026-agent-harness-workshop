"""Compare a run's final code with the migration's reference solution.

Shared by Block 3 (eval/run_eval.py prints one line after each migration
run) and Block 4 (compare_reference.py prints the differences).

"35 passed" says the tests agree. This says whether the code is what a
careful hand migration produces. Only the migration (refactor_v2) is
checked: a rename has one right answer, while a bug can be fixed correctly
in more than one way, so diffing bug_hunt against its reference would
flag correct fixes. Tests and conftest.py are left out, since a run can't
change them.
"""

import difflib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REFERENCE = REPO / "block2_naive_harness" / "tasks" / "long_horizon" / "refactor_v2" / "reference"
SKIP = {"__pycache__", ".pytest_cache", "tests"}


def sources(root: Path) -> dict:
    """Every .py file under root except tests: relative path -> text."""
    return {f.relative_to(root): f.read_text(errors="replace") for f in sorted(root.rglob("*.py"))
            if not SKIP & set(f.relative_to(root).parts) and f.name != "conftest.py"}


def differing(workspace: Path) -> list:
    """The source files that differ from the reference, as relative paths."""
    reference, mine = sources(REFERENCE), sources(workspace)
    return sorted(r for r in reference.keys() | mine.keys() if reference.get(r) != mine.get(r))


def diff_lines(workspace: Path, rel: Path, label: str) -> list:
    """A unified diff of one file, reference first."""
    ref = (REFERENCE / rel).read_text(errors="replace") if (REFERENCE / rel).exists() else ""
    mine = (workspace / rel).read_text(errors="replace") if (workspace / rel).exists() else ""
    return list(difflib.unified_diff(ref.splitlines(), mine.splitlines(),
                                     f"reference/{rel}", f"{label}/{rel}", lineterm="", n=0))


def summary_line(workspace: Path) -> str:
    """One line for the end of a migration run."""
    files = differing(workspace)
    if not files:
        return "--- against the reference migration: matches"
    shown = ", ".join(str(f) for f in files[:3]) + (f" and {len(files) - 3} more" if len(files) > 3 else "")
    return (f"--- against the reference migration: {len(files)} file{'s' if len(files) != 1 else ''} "
            f"differ ({shown}). Passing the tests isn't the same as doing the job.")
