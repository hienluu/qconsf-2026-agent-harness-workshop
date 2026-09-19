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

# v1 legacy name -> v2 name -> documented in MIGRATION.md? The undocumented
# renames force the agent to treat the test suite as the source of truth —
# discovery pressure is part of the task design.
RENAMES = [
    ("make_ledger", "new_ledger", True),
    ("post", "record", True),
    ("balance_of", "get_balance", True),
    ("entries_by_account", "entries_for", False),
    ("amt", "amount", True),
    ("side", "kind", False),
    ("check_entry", "validate_entry", True),
    ("to_minor", "to_cents", True),
    ("from_minor", "from_cents", True),
    ("fmt_amt", "format_amount", False),
    ("load_entries_csv", "read_entries_csv", True),
    ("dump_entries_csv", "write_entries_csv", False),
    ("summary_by_month", "monthly_summary", False),
    ("balanced", "is_balanced", False),
]

# Files whose identifiers are NOT part of the ledger API. webhook.post() is
# the HTTP verb — a blind find-and-replace across the tree breaks its tests.
RENAME_EXEMPT = {"pyledger/integrations/webhook.py"}


def to_v1(text: str) -> str:
    # Longest v2 names first so e.g. format_amount is rewritten before amount.
    for v1, v2, _doc in sorted(RENAMES, key=lambda p: -len(p[1])):
        text = re.sub(rf"\b{re.escape(v2)}\b", v1, text)
    return text


def main(target: Path = WORKSPACE) -> None:
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)

    for src in REFERENCE.rglob("*"):
        if not src.is_file() or {"__pycache__", ".pytest_cache"} & set(src.parts):
            continue
        rel = src.relative_to(REFERENCE)
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        in_tests = rel.parts[0] == "tests" or rel.name == "conftest.py"
        exempt = str(rel) in RENAME_EXEMPT
        if in_tests or exempt or src.suffix != ".py":
            shutil.copy2(src, dst)
        else:
            dst.write_text(to_v1(src.read_text()))

    rows = "\n".join(f"| `{v1}` | `{v2}` |" for v1, v2, doc in RENAMES if doc)
    (target / "MIGRATION.md").write_text(
        "# pyledger v2 API migration\n\n"
        "The test suite under `tests/` is written against the **v2** API.\n"
        "The source under `pyledger/` and `cli.py` still uses the legacy v1\n"
        "names. Rename every v1 identifier to its v2 name, everywhere it\n"
        "appears (definitions, imports, call sites, dataclass fields, dict\n"
        "keys derived from field names). Do not modify anything in `tests/`.\n\n"
        "| v1 (legacy) | v2 (target) |\n|---|---|\n" + rows + "\n\n"
        "**This changelog is known to be incomplete.** Some v1 names were\n"
        "renamed without being written down; the test suite is the source of\n"
        "truth for the full v2 API.\n\n"
        "**Out of scope:** `pyledger/integrations/webhook.py` — its `post()`\n"
        "is the HTTP verb, not the ledger API. Do not rename anything there.\n\n"
        "Done means: `pytest` exits green.\n"
    )
    print(f"workspace derived at {target}")


if __name__ == "__main__":
    main()
