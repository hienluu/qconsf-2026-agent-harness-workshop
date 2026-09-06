"""The Block 3 task suite — the same tasks attendees ran in Block 2.

Workspace paths are relative to the repo root. The checker for every task
is identical and external to the agent: copy the pristine workspace, run
the harness, then run pytest on the result. The agent's opinion of its own
success is never consulted.
"""

TASKS = {
    "fix_bug": {
        "description": "Find and fix an off-by-one bug in a stats module (1 file, 4 tests).",
        "workspace": "block2_naive_harness/tasks/short/01_fix_bug/workspace",
        "prompt": "One test fails. Find the bug and fix it. Do not modify the tests.",
    },
    "add_function": {
        "description": "Implement the missing slugify function from its 5 tests.",
        "workspace": "block2_naive_harness/tasks/short/02_add_function/workspace",
        "prompt": "Implement the unimplemented function so all tests pass. Do not modify the tests.",
    },
    "small_rename": {
        "description": "Rename two legacy config functions across 2 files.",
        "workspace": "block2_naive_harness/tasks/short/03_small_rename/workspace",
        "prompt": "The tests expect renamed functions. Rename the legacy functions everywhere until all tests pass. Do not modify the tests.",
    },
    "bug_hunt": {
        "description": "Diagnose and fix 3 interacting bugs in a 6-file pricing package (14 tests, 5 failing). Medium horizon.",
        "workspace": "block2_naive_harness/tasks/medium/bug_hunt/workspace",
        "prompt": "Several tests fail. Diagnose and fix all the bugs until every test passes. Do not modify the tests.",
    },
    "refactor_v2": {
        "description": "Migrate a ~150-file bookkeeping library to its v2 API from an incomplete changelog (35 tests). The long-horizon harness-killer.",
        "workspace": "block2_naive_harness/tasks/long_horizon/refactor_v2/workspace",
        "prompt": "Migrate the source code to the v2 API following MIGRATION.md until all tests pass. Do not modify the tests.",
    },
}
