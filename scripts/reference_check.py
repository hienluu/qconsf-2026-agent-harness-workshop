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
    return {f.relative_to(root): f.read_text(encoding="utf-8", errors="replace") for f in sorted(root.rglob("*.py"))
            if not SKIP & set(f.relative_to(root).parts) and f.name != "conftest.py"}


def differing(workspace: Path) -> list:
    """The source files that differ from the reference, as relative paths."""
    reference, mine = sources(REFERENCE), sources(workspace)
    return sorted(r for r in reference.keys() | mine.keys() if reference.get(r) != mine.get(r))


def diff_lines(workspace: Path, rel: Path, label: str) -> list:
    """A unified diff of one file, reference first."""
    ref = (REFERENCE / rel).read_text(encoding="utf-8", errors="replace") if (REFERENCE / rel).exists() else ""
    mine = (workspace / rel).read_text(encoding="utf-8", errors="replace") if (workspace / rel).exists() else ""
    return list(difflib.unified_diff(ref.splitlines(), mine.splitlines(),
                                     f"reference/{rel}", f"{label}/{rel}", lineterm="", n=0))


def summary_line(workspace: Path, solved: bool) -> str:
    """One line for the end of a migration run. The warning about passing
    tests only makes sense when the tests passed."""
    files = differing(workspace)
    if not files:
        return "--- against the reference migration: matches"
    shown = ", ".join(str(f) for f in files[:3]) + (f" and {len(files) - 3} more" if len(files) > 3 else "")
    one = len(files) == 1
    line = (f"--- against the reference migration: {len(files)} file{'' if one else 's'} "
            f"{'differs' if one else 'differ'} ({shown}).")
    if solved:
        line += " Passing the tests isn't the same as doing the job."
    return line


def main(argv: list) -> int:
    """Print what differs, for one run folder (or its workspace)."""
    if len(argv) != 1:
        raise SystemExit("usage: uv run ../scripts/reference_check.py results/runs/<run folder>")
    folder = Path(argv[0])
    workspace = folder / "workspace" if (folder / "workspace").is_dir() else folder
    if not (workspace / "pyledger").is_dir():
        raise SystemExit(f"{folder}: not a migration run (only refactor_v2 has a reference to compare)")
    files = differing(workspace)
    if not files:
        print("\033[32mmatches the reference\033[0m")
        return 0
    print(f"\033[1;31m{len(files)} file(s) differ from the reference\033[0m")
    for rel in files:
        for line in diff_lines(workspace, rel, "yours"):
            print("   " + line)
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv[1:]))
