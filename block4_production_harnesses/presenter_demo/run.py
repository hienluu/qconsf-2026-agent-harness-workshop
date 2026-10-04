"""Presenter demo: refactor_v2 through Claude Code's harness.

    uv run --group block4 presenter_demo/run.py      (from block4_production_harnesses/)

The closing question of Block 4: our hand-built h3 solved this task in
22-38 turns and 336k-1,087k input tokens. **Did the professionals' harness
beat our 285-line h3?** One run, ~3 minutes, same model, same provider —
watch the turn count and the cost line at the end.

Whatever the answer, it teaches: if Claude Code's harness wins big, that's
what years of production harness engineering buys; if it doesn't, that's
the Astra lesson again — harness-model fit matters, and this harness is
tuned for Claude, not GLM.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import tool_detail, REFACTOR_SOURCE, REFACTOR_TASK, anthropic_compat_base_url, prepare_workspace, trace_key, trace_say, trace_tool, verify  # noqa: E402

from claude_agent_sdk import (  # noqa: E402
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    query,
)

load_dotenv()
NAME = "presenter_refactor_claude_sdk"


async def main() -> int:
    workspace = prepare_workspace(NAME, source=REFACTOR_SOURCE)

    options = ClaudeAgentOptions(
        cwd=str(workspace),
        model=os.environ["MODEL"],
        max_turns=60,
        permission_mode="bypassPermissions",
        env={
            "ANTHROPIC_BASE_URL": anthropic_compat_base_url(),
            "ANTHROPIC_AUTH_TOKEN": os.environ["PROVIDER_API_KEY"],
            "ANTHROPIC_MODEL": os.environ["MODEL"],
            "ANTHROPIC_SMALL_FAST_MODEL": os.environ["MODEL"],
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        },
    )

    started = time.monotonic()
    tool_calls = 0
    async for message in query(prompt=REFACTOR_TASK, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    tool_calls += 1
                    trace_tool(NAME, block.name, tool_detail(block.input))
                elif isinstance(block, TextBlock) and block.text.strip():
                    trace_say(NAME, block.text)
        elif isinstance(message, ResultMessage):
            usage = message.usage or {}
            print(
                f"\n[{NAME}] result: turns={message.num_turns} "
                f"tool_calls={tool_calls} "
                f"cost=${message.total_cost_usd or 0:.4f} "
                f"input_tokens={usage.get('input_tokens', '?')} "
                f"duration={message.duration_ms}ms"
            )

    print("\nCompare with the hand-built harnesses (block3 reference samples):")
    print("  h1_naive:  30-31 turns, 850k-932k input tokens (or crashed)")
    print("  h2_managed: 25-28 turns, 550k-593k input tokens")
    print("  h3_full:   22-38 turns, 336k-1,087k input tokens")
    return verify(NAME, workspace, started)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
