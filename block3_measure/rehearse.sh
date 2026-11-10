#!/bin/sh

echo "======= Block 3 rehearsal ======="

echo "Archiving the score table, restoring fixtures and checking them..."
uv run ../scripts/reset.py 
uv run ../scripts/check_fixtures.py

echo "Running h2_managed harness"
uv run eval/run_eval.py h2 --task refactor_v2

echo "Running h3_full harness"
uv run eval/run_eval.py h3 --task refactor_v2

echo "Running h3_full harness with 20 max turns"
MAX_TURNS=20 uv run eval/run_eval.py h3 --task refactor_v2

echo "Running h3_full harness with 20 max turns and the progress budget signal"
MAX_TURNS=20 BUDGET_SIGNAL=progress uv run eval/run_eval.py h3 --task refactor_v2
