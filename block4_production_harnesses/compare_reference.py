"""Compare each run's final code with the migration's reference solution.

    uv run compare_reference.py                    (every run under runs/)
    uv run compare_reference.py openai_agents      (just one)

"35 passed" says the tests agree. This says whether the code does what a
careful hand migration does: every line that differs from the reference,
in the source (tests and conftest.py are left out, since the runs can't
change them). A run can pass every test and still differ: that's the point
of looking. The comparison itself is ../scripts/reference_check.py, which
Block 3 uses too.
"""

import sys
from pathlib import Path

BLOCK4 = Path(__file__).resolve().parent
sys.path.insert(0, str(BLOCK4.parent / "scripts"))
from reference_check import diff_lines, differing  # noqa: E402


def main() -> int:
    runs = BLOCK4 / "runs"
    names = sys.argv[1:] or sorted(d.name for d in runs.iterdir() if (d / "workspace").is_dir())
    if not names:
        raise SystemExit("no runs yet: run a step first")
    for name in names:
        workspace = runs / name / "workspace"
        if not workspace.is_dir():
            print(f"{name}: no run found at runs/{name}/workspace")
            continue
        if not (workspace / "pyledger").is_dir():
            print(f"{name}: not a migration run (only the migration has one right answer to compare)")
            continue
        files = differing(workspace)
        if not files:
            print(f"\033[32m{name}: matches the reference\033[0m")
            continue
        print(f"\033[1;31m{name}: {len(files)} file(s) differ from the reference\033[0m")
        for rel in files:
            for line in diff_lines(workspace, rel, name):
                print("   " + line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
