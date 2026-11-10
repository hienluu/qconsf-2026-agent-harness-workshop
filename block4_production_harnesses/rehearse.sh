#!/bin/sh

echo "======= Block 4 rehearsal ======="

echo "Resetting and checking fixtures..."
uv run ../scripts/reset.py 
uv run ../scripts/check_fixtures.py

echo "Clearing receipts..."
rm -f runs/receipts.jsonl

echo "Running OpenAI Agents..."
uv run openai_agents/run.py

echo "Running Claude Agents..."
uv run claude_agent_sdk/run.py

echo "Running OpenAI Agent Replace in Files..."
uv run openai_agents/run_replace_in_files.py

echo "Running OpenAI Shell with its own tools..."
uv run tool_design/run_openai_shell.py

echo "Running Claude with its own tools..."
uv run tool_design/run_claude.py
