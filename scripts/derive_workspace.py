"""Derive the v1 (pre-refactor) workspace from the v2 reference codebase.

The reference under tasks/long_horizon/refactor_v2/reference/ is the ground
truth: v2 source + v2 tests, all green. This script rewrites the *source*
files back to the legacy v1 names and copies the tests unchanged, producing
a workspace where the suite fails until an agent performs the migration.

Editing the task = edit the reference, re-run this script. Never hand-edit
the workspace.

Usage: python scripts/derive_workspace.py
"""

import re
import shutil
from pathlib import Path

TASK_DIR = Path(__file__).resolve().parent.parent / "block2_naive_harness" / "tasks" / "long_horizon" / "refactor_v2"
REFERENCE = TASK_DIR / "reference"
WORKSPACE = TASK_DIR / "workspace"

# v1 legacy name -> v2 name. MIGRATION.md in the workspace is generated from
# this table, so the agent-facing spec can never drift from the derivation.
RENAMES = [
    ("make_ledger", "new_ledger"),
    ("post", "record"),
    ("balance_of", "get_balance"),
    ("entries_by_account", "entries_for"),
    ("amt", "amount"),
    ("side", "kind"),
    ("check_entry", "validate_entry"),
    ("to_minor", "to_cents"),
    ("from_minor", "from_cents"),
    ("fmt_amt", "format_amount"),
    ("load_entries_csv", "read_entries_csv"),
    ("dump_entries_csv", "write_entries_csv"),
    ("summary_by_month", "monthly_summary"),
    ("balanced", "is_balanced"),
]


def to_v1(text: str) -> str:
    # Longest v2 names first so e.g. format_amount is rewritten before amount.
    for v1, v2 in sorted(RENAMES, key=lambda p: -len(p[1])):
        text = re.sub(rf"\b{re.escape(v2)}\b", v1, text)
    return text


def main() -> None:
    if WORKSPACE.exists():
        shutil.rmtree(WORKSPACE)
    WORKSPACE.mkdir(parents=True)

    for src in REFERENCE.rglob("*"):
        if "__pycache__" in src.parts or not src.is_file():
            continue
        rel = src.relative_to(REFERENCE)
        dst = WORKSPACE / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        in_tests = rel.parts[0] == "tests" or rel.name == "conftest.py"
        if in_tests or src.suffix != ".py":
            shutil.copy2(src, dst)
        else:
            dst.write_text(to_v1(src.read_text()))

    rows = "\n".join(f"| `{v1}` | `{v2}` |" for v1, v2 in RENAMES)
    (WORKSPACE / "MIGRATION.md").write_text(
        "# pyledger v2 API migration\n\n"
        "The test suite under `tests/` is written against the **v2** API.\n"
        "The source under `pyledger/` and `cli.py` still uses the legacy v1\n"
        "names. Rename every v1 identifier to its v2 name, everywhere it\n"
        "appears (definitions, imports, call sites, dataclass fields, dict\n"
        "keys derived from field names). Do not modify anything in `tests/`.\n\n"
        "| v1 (legacy) | v2 (target) |\n|---|---|\n" + rows + "\n\n"
        "Done means: `pytest` exits green.\n"
    )
    print(f"workspace derived at {WORKSPACE}")


if __name__ == "__main__":
    main()
