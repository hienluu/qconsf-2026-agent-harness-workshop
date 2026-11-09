"""The migration through the Claude Agent SDK, with its own tools.

    uv run migration/run_claude.py      (from block4_production_harnesses/)

Block 2's migration, through Claude Code's harness as a library. We define
no tools: it brings its own, including Bash. The trace comes from the
SDK's hooks (PostToolUse, PostToolUseFailure, PreCompact) and its message
stream, printed the way Block 3's harnesses print.

Compare with the other scripts in this folder: same task, same model, and
what changes is which tools the harness hands the model.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import SYSTEM_PROMPT, MIGRATION_MAX_TURNS, REFACTOR_SOURCE, REFACTOR_TASK, anthropic_compat_base_url, prepare_workspace, verify  # noqa: E402
from migration_trace import Trace  # noqa: E402

from claude_agent_sdk import (  # noqa: E402
    AssistantMessage,
    ClaudeAgentOptions,
    HookMatcher,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    query,
)

load_dotenv()
NAME = "migration_claude_agent_sdk"


async def main() -> int:
    workspace = prepare_workspace(NAME, source=REFACTOR_SOURCE)
    trace = Trace("claude", workspace)
    names: dict = {}           # tool_use_id -> tool name, for the result line

    async def on_result(inp, tool_use_id, context):
        r = inp.get("tool_response")
        if isinstance(r, dict) and "stdout" in r:
            out = (str(r.get("stdout") or "") + "\n" + str(r.get("stderr") or "")).strip()
        elif isinstance(r, dict) and isinstance(r.get("file"), dict):
            out = str(r["file"].get("content", ""))
        else:
            out = str(r or "")
        trace.result(inp.get("tool_name", ""), out)
        return {}

    async def on_failure(inp, tool_use_id, context):
        trace.failure(inp.get("error"))
        return {}

    async def on_compact(inp, tool_use_id, context):
        trace.compact(f"Claude Code is compacting its conversation (trigger: {inp.get('trigger', '?')})")
        return {}

    options = ClaudeAgentOptions(
        cwd=str(workspace),
        model=os.environ["MODEL"],
        max_turns=MIGRATION_MAX_TURNS,
        # Without this the SDK sends an empty system prompt; set ours.
        system_prompt=SYSTEM_PROMPT,
        permission_mode="bypassPermissions",
        env={
            "ANTHROPIC_BASE_URL": anthropic_compat_base_url(),
            "ANTHROPIC_AUTH_TOKEN": os.environ["PROVIDER_API_KEY"],
            "ANTHROPIC_MODEL": os.environ["MODEL"],
            "ANTHROPIC_SMALL_FAST_MODEL": os.environ["MODEL"],
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        },
        hooks={
            "PostToolUse": [HookMatcher(hooks=[on_result])],
            "PostToolUseFailure": [HookMatcher(hooks=[on_failure])],
            "PreCompact": [HookMatcher(hooks=[on_compact])],
        },
    )

    started = time.monotonic()
    current = None
    # One model response can stream as several messages sharing a
    # message_id (parallel calls arrive one by one); that id is the turn.
    try:
        async for message in query(prompt=REFACTOR_TASK, options=options):
            if isinstance(message, AssistantMessage):
                if message.message_id != current:
                    current = message.message_id
                    # Our counter is the cap: the SDK's max_turns counts something else.
                    if trace.turn >= MIGRATION_MAX_TURNS:
                        trace.flush()
                        print(f"[claude] run ended without finishing: turn cap reached ({MIGRATION_MAX_TURNS})")
                        break
                    trace.new_turn()
                u = message.usage or {}
                # Anthropic counts cache reads and writes apart from input_tokens.
                cached = u.get("cache_read_input_tokens") or 0
                trace.usage((u.get("input_tokens") or 0) + cached + (u.get("cache_creation_input_tokens") or 0),
                            cached, u.get("output_tokens"))
                for block in message.content:
                    if isinstance(block, ToolUseBlock):
                        trace.call(block.name, block.input)
                        names[block.id] = block.name
                    elif isinstance(block, TextBlock):
                        trace.text(block.text)
            elif isinstance(message, ResultMessage):
                # Through our gateway, per-message usage is empty; the run's total
                # arrives here at the end.
                u = message.usage or {}
                cached = u.get("cache_read_input_tokens") or 0
                trace.run_total((u.get("input_tokens") or 0) + cached + (u.get("cache_creation_input_tokens") or 0),
                                cached, u.get("output_tokens"))
    except Exception as exc:  # the SDK's own turn limit is an outcome, not a crash
        trace.flush()
        print(f"[claude] run ended without finishing: {str(exc).splitlines()[0][:120]}")

    solved = verify(NAME, workspace, started) == 0
    trace.finish(script="claude_agent_sdk", solved=solved, started=started,
                 tools="Claude Code's own, incl. Bash", tools_we_wrote=0)
    return 0 if solved else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
