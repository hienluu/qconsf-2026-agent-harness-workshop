"""Compare each run's final code with the migration's reference solution.

    uv run compare_reference.py                    (every run under runs/)
    uv run compare_reference.py openai_agents      (just one)

"35 passed" says the tests agree. This says whether the code does what a
person migrating it by hand would have done: every line that differs from
the reference, in the source (the tests and conftest.py are left out,
since the runs can't change them). A run can pass every test and still
differ: that's the point of looking.
"""

import difflib
import sys
from pathlib import Path

BLOCK4 = Path(__file__).resolve().parent
REFERENCE = BLOCK4.parent / "block2_naive_harness" / "tasks" / "long_horizon" / "refactor_v2" / "reference"
SKIP = {"__pycache__", ".pytest_cache", "tests"}


def sources(root: Path) -> dict:
    return {f.relative_to(root): f.read_text(errors="replace") for f in sorted(root.rglob("*.py"))
            if not SKIP & set(f.relative_to(root).parts) and f.name != "conftest.py"}


def main() -> int:
    runs = BLOCK4 / "runs"
    names = sys.argv[1:] or sorted(d.name for d in runs.iterdir() if (d / "workspace").is_dir())
    if not names:
        raise SystemExit("no runs yet: run a step first")
    reference = sources(REFERENCE)
    for name in names:
        workspace = runs / name / "workspace"
        if not workspace.is_dir():
            print(f"{name}: no run found at runs/{name}/workspace")
            continue
        mine = sources(workspace)
        differing = sorted(r for r in reference.keys() | mine.keys() if reference.get(r) != mine.get(r))
        if not differing:
            print(f"\033[32m{name}: matches the reference\033[0m")
            continue
        print(f"\033[1;31m{name}: {len(differing)} file(s) differ from the reference\033[0m")
        for rel in differing:
            diff = difflib.unified_diff((reference.get(rel) or "").splitlines(), (mine.get(rel) or "").splitlines(),
                                        f"reference/{rel}", f"{name}/{rel}", lineterm="", n=0)
            for line in diff:
                print("   " + line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
