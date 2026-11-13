"""Presenter demo: the Claude Agent SDK with Claude Code's own tools, Bash included.

    uv run tool_design/run_claude.py      (from block4_production_harnesses/)

Step 2 ran this harness on our four file tools. Here it gets Claude Code's
whole kit instead, Bash included, and we define nothing except the
system prompt everyone shares: what a product gives you out of the box.
Given a shell, it greps for the old names and writes a rename script.

The trace comes from the SDK's message stream (one header per model
response) and its hooks: PostToolUse for each call's result,
PostToolUseFailure for a failed one (✗), PreCompact when Claude Code
compacts its conversation (✂).

The shell runs as you, with bypassPermissions: Claude Code's permission
rules and sandboxing are exactly what we've switched off. Not a sandbox.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import _turn, TurnCapReached, end_turn, set_tokens_sent, trace_cost, tool_detail, SYSTEM_PROMPT, TASK, TASK_MAX_TURNS, anthropic_compat_base_url, new_turn, prepare_workspace, receipt, trace_key, trace_note, trace_result, trace_say, trace_tool, verify  # noqa: E402

from claude_agent_sdk import (  # noqa: E402
    AssistantMessage,
    ClaudeAgentOptions,
    HookMatcher,
    ResultMessage,
    StreamEvent,
    TextBlock,
    ToolUseBlock,
    query,
)

load_dotenv()
NAME = "claude_agent_sdk+bash"


async def on_result(inp, tool_use_id, context):
    r = inp.get("tool_response")
    if isinstance(r, dict) and "stdout" in r:
        out = (str(r.get("stdout") or "") + "\n" + str(r.get("stderr") or "")).strip()
    elif isinstance(r, dict) and isinstance(r.get("file"), dict):
        content = str(r["file"].get("content", ""))
        out = f"read {content.count(chr(10)) + 1:,} lines"
    else:
        out = str(r or "")
    trace_result(NAME, inp.get("tool_name", ""), out, call_id=tool_use_id)
    return {}


async def on_failure(inp, tool_use_id, context):
    trace_result(NAME, inp.get("tool_name", ""), inp.get("error") or "failed", failed=True, call_id=tool_use_id)
    return {}


async def on_compact(inp, tool_use_id, context):
    trace_note(NAME, f"Claude Code compacted its conversation (trigger: {inp.get('trigger', '?')})")
    return {}


async def main() -> int:
    workspace = prepare_workspace(NAME)
    trace_key(NAME, [], "Claude Code's whole kit: Bash, Read, Write, Edit, Glob, Grep and more")

    options = ClaudeAgentOptions(
        cwd=str(workspace),
        model=os.environ["LLM_MODEL"],
        max_turns=TASK_MAX_TURNS,
        include_partial_messages=True,   # per-turn token counts arrive as stream events
        system_prompt=SYSTEM_PROMPT,  # unset, the SDK sends an empty one
        permission_mode="bypassPermissions",
        env={
            "ANTHROPIC_BASE_URL": anthropic_compat_base_url(),
            "ANTHROPIC_AUTH_TOKEN": os.environ["LLM_API_KEY"],
            "ANTHROPIC_MODEL": os.environ["LLM_MODEL"],
            "ANTHROPIC_SMALL_FAST_MODEL": os.environ["LLM_MODEL"],
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        },
        hooks={
            "PostToolUse": [HookMatcher(hooks=[on_result])],
            "PostToolUseFailure": [HookMatcher(hooks=[on_failure])],
            "PreCompact": [HookMatcher(hooks=[on_compact])],
        },
    )

    started = time.monotonic()
    current, total = None, 0
    try:
        async for message in query(prompt=TASK, options=options):
            if isinstance(message, AssistantMessage):
                # One model response streams as several messages sharing a
                # message_id: the id, not the message, is the turn.
                if message.message_id != current:
                    current = message.message_id
                    if _turn["n"] >= TASK_MAX_TURNS:   # our cap; see claude_agent_sdk/run.py
                        raise TurnCapReached(f"turn cap reached: {TASK_MAX_TURNS} model calls")
                    new_turn()
                for block in message.content:
                    if isinstance(block, ToolUseBlock):
                        trace_tool(NAME, block.name, tool_detail(block.input), harness_tool=True, call_id=block.id)
                    elif isinstance(block, TextBlock) and block.text.strip():
                        trace_say(NAME, block.text)
            elif isinstance(message, StreamEvent) and message.event.get("type") == "message_delta":
                # Per-turn tokens: only the closing message_delta carries
                # them through our gateway (see claude_agent_sdk/run.py).
                u = message.event.get("usage") or {}
                sent = sum(u.get(k) or 0 for k in ("input_tokens", "cache_read_input_tokens",
                                                    "cache_creation_input_tokens"))
                if sent:
                    total += sent
                    trace_cost(NAME, sent, u.get("output_tokens") or 0, total,
                               cached=u.get("cache_read_input_tokens") or 0)
            elif isinstance(message, ResultMessage):
                u = message.usage or {}
                set_tokens_sent(sum(u.get(k) or 0 for k in ("input_tokens", "cache_read_input_tokens",
                                                             "cache_creation_input_tokens")),
                                u.get("output_tokens"), u.get("cache_read_input_tokens") or 0)
    except Exception as exc:  # the turn cap is an outcome, not a crash
        end_turn()
        print(f"[{NAME}] run ended without finishing: {str(exc).splitlines()[0][:120]}")

    solved = verify(NAME, workspace, started) == 0
    receipt(NAME, script=__file__, started=started, solved=solved,
        origin="product-extracted (Claude Code as a library)",
        loop_owner="theirs: closed; we only configure",
        tools_we_wrote=[],
        tools_harness_shipped="Claude Code's whole kit, Bash included",
        provider_friction="same as claude_agent_sdk")
    return 0 if solved else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
