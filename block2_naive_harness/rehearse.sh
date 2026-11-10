#!/bin/sh

echo "======= Block 2 rehearsal ======="

echo "Restoring the task fixtures and checking them..."
uv run ../scripts/reset.py 
uv run ../scripts/check_fixtures.py

echo "see the bug..."
uv run python -m pytest tasks/short/01_fix_bug/workspace -q

echo "Running the harness (the solution)..."
uv run ./solution/harness.py tasks/short/01_fix_bug/workspace "One test fails. Find the bug and fix it. Do not modify the tests."

echo "Checking the fix..."
uv run python -m pytest tasks/short/01_fix_bug/workspace -q

echo "Checking the tests before refactoring..."
uv run python -m pytest tasks/long_horizon/refactor_v2/workspace -q

echo "Running refactoring task..."
uv run ./solution/harness.py tasks/long_horizon/refactor_v2/workspace "Migrate the source code to the v2 API following MIGRATION.md until all tests pass. Do not modify the tests."

echo "Restoring the task fixtures (the harness edits them in place)..."
uv run ../scripts/reset.py
uv run ../scripts/check_fixtures.py
