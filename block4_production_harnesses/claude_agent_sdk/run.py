"""The Block 4 task through the Claude Agent SDK: Claude Code as a library.

    uv run claude_agent_sdk/run.py        (from block4_production_harnesses/)

Where it came from: product-extracted. This is the same loop, file tools and
context management that power Claude Code, driven programmatically. Notice
what we do NOT write: no loop, no dispatcher, no truncation, no compaction.
The harness ships with all of it decided. We withhold Bash so every harness
here works through file tools, which leaves us one tool to write: run_tests.

Provider note: the SDK reads ANTHROPIC_BASE_URL / ANTHROPIC_API_KEY (names
the SDK dictates — provider coupling made visible in env-var form). We
point them at the workshop provider's Anthropic-compatible endpoint and
pass the open model's name. Whether a product-extracted harness performs
off its home model is part of what this script demonstrates.

The SDK drives the Claude Code CLI — a compiled copy is bundled inside the
pip package itself (checked before any system install), so `uv sync` is
the only setup.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import end_turn, SYSTEM_PROMPT, _turn, TurnCapReached, set_tokens_sent, trace_cost, trace_note, tool_detail, TASK, TASK_MAX_TURNS, anthropic_compat_base_url, new_turn, prepare_workspace, receipt, trace_key, trace_say, trace_tool, verify, ws_run_tests  # noqa: E402

from claude_agent_sdk import (  # noqa: E402
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    create_sdk_mcp_server,
    query,
    tool,
)

load_dotenv()
NAME = "claude_agent_sdk"

# File tools only, like the other harnesses: Claude Code's own file tools,
# no Bash. Without a shell it can't run pytest, so it gets our run_tests,
# served in-process as an SDK tool. The full kit, Bash included, is in
# migration/run_claude.py (presenter demo / take-home).
CLAUDE_FILE_TOOLS = ["Read", "Write", "Edit", "Glob", "Grep"]
workspace: Path


@tool("run_tests", "Run pytest in the workspace; done means all tests pass.", {})
async def run_tests(args) -> dict:
    trace_tool(NAME, "run_tests")
    return {"content": [{"type": "text", "text": ws_run_tests(workspace)}]}



async def _stream(options) -> None:
    current = None
    async for message in query(prompt=TASK, options=options):
        if isinstance(message, AssistantMessage):
            # One model response can stream as several messages sharing a
            # message_id (parallel tool calls arrive one by one): the id,
            # not the message, is the turn.
            if message.message_id != current:
                current = message.message_id
                # The turn cap, enforced here: the SDK's max_turns counts
                # something else (runs reported 457 "turns" under max_turns=60).
                if _turn["n"] >= TASK_MAX_TURNS:
                    raise TurnCapReached(f"turn cap reached: {TASK_MAX_TURNS} model calls")
                new_turn()
            u = getattr(message, "usage", None) or {}
            sent = u.get("input_tokens") if isinstance(u, dict) else getattr(u, "input_tokens", None)
            got = (u.get("output_tokens") if isinstance(u, dict) else getattr(u, "output_tokens", 0)) or 0
            if sent:
                trace_cost(NAME, sent, got)
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    if block.name.endswith("__run_tests"):
                        continue   # traced by run_tests itself
                    trace_tool(NAME, block.name, tool_detail(block.input), harness_tool=True)
                elif isinstance(block, TextBlock) and block.text.strip():
                    trace_say(NAME, block.text)
        elif isinstance(message, ResultMessage):
            for d in (getattr(message, "permission_denials", None) or []):
                trace_note(NAME, f"permission denied: {str(d)[:80]}")
            # Through our gateway, per-message usage is empty; the run's
            # total arrives here. Its cost figure assumes Anthropic prices, so
            # it's left out.
            u = message.usage or {}
            sent = sum(u.get(k) or 0 for k in ("input_tokens", "cache_read_input_tokens",
                                                "cache_creation_input_tokens"))
            set_tokens_sent(sent)
            end_turn()
            print(f"[{NAME}] tokens sent this run: {sent:,} "
                  f"({u.get('output_tokens') or 0:,} written by the model)")


async def main() -> int:
    global workspace
    workspace = prepare_workspace(NAME)
    trace_key(NAME, ["run_tests"], "Claude Code's Read, Write, Edit, Glob, Grep (Bash withheld)")

    options = ClaudeAgentOptions(
        cwd=str(workspace),
        model=os.environ["MODEL"],
        max_turns=TASK_MAX_TURNS,
        # Without this the SDK sends an EMPTY system prompt (not Claude
        # Code's): set ours, the same as every other harness.
        system_prompt=SYSTEM_PROMPT,
        tools=CLAUDE_FILE_TOOLS,     # the base toolset; anything not listed is gone
        mcp_servers={"workspace": create_sdk_mcp_server("workspace", tools=[run_tests])},
        allowed_tools=CLAUDE_FILE_TOOLS + ["mcp__workspace__run_tests"],
        # Headless: auto-approve edits inside the copied workspace.
        permission_mode="bypassPermissions",
        env={
            # The harness's home is Anthropic's API; we redirect it to the
            # workshop provider's Anthropic-compatible endpoint.
            "ANTHROPIC_BASE_URL": anthropic_compat_base_url(),
            # Baseten's Anthropic-compatible endpoint wants Authorization:
            # Bearer, not the protocol's x-api-key — AUTH_TOKEN (not API_KEY)
            # makes Claude Code send Bearer. Found the hard way; see README.
            "ANTHROPIC_AUTH_TOKEN": os.environ["PROVIDER_API_KEY"],
            "ANTHROPIC_MODEL": os.environ["MODEL"],
            "ANTHROPIC_SMALL_FAST_MODEL": os.environ["MODEL"],
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        },
    )

    started = time.monotonic()
    try:
        await _stream(options)
    except Exception as exc:  # turn-cap and API errors are outcomes, not crashes
        end_turn()
        print(f"[{NAME}] run ended without finishing: {exc}")

    solved = verify(NAME, workspace, started) == 0
    receipt(NAME, script=__file__, started=started, solved=solved,
        origin="product-extracted (Claude Code as a library)",
        loop_owner="theirs — closed; we only configure",
        tools_we_wrote=["run_tests"],
        tools_harness_shipped="Claude Code's file tools (Read, Write, Edit, Glob, Grep); Bash withheld",
        provider_friction="2 workarounds: Bearer auth via AUTH_TOKEN; warns unrecognized_model")
    return 0 if solved else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
