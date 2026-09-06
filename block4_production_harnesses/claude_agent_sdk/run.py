"""fix_bug through the Claude Agent SDK — Claude Code as a library.

    uv run --group block4 claude_agent_sdk/run.py        (from block4_production_harnesses/)

Pedigree: product-extracted. This is the same loop, tools, and context
management that power Claude Code, driven programmatically. Notice what we
do NOT write: no loop, no tool definitions, no dispatcher, no truncation,
no compaction — the harness ships with all of it decided. Our whole job is
configuration.

Provider note: the SDK reads ANTHROPIC_BASE_URL / ANTHROPIC_API_KEY (names
the SDK dictates — provider coupling made visible in env-var form). We
point them at the workshop provider's Anthropic-compatible endpoint and
pass the open model's name. Whether a product-extracted harness performs
off its home model is part of what this specimen demonstrates.

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
from common import anthropic_compat_base_url, TASK, TASK_MAX_TURNS, prepare_workspace, receipt, verify  # noqa: E402

from claude_agent_sdk import (  # noqa: E402
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    query,
)

load_dotenv()
NAME = "claude_agent_sdk"



async def _stream(options) -> None:
    async for message in query(prompt=TASK, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    print(f"[{NAME}] tool: {block.name}({str(block.input)[:60]})")
                elif isinstance(block, TextBlock) and block.text.strip():
                    print(f"[{NAME}] says: {block.text.strip()[:100]}")
        elif isinstance(message, ResultMessage):
            print(f"[{NAME}] result: turns={message.num_turns} "
                  f"cost=${message.total_cost_usd or 0:.4f} "
                  f"duration={message.duration_ms}ms")


async def main() -> int:
    workspace = prepare_workspace(NAME)

    options = ClaudeAgentOptions(
        cwd=str(workspace),
        model=os.environ["MODEL"],
        max_turns=TASK_MAX_TURNS,
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
        print(f"[{NAME}] run ended without finishing: {exc}")

    solved = verify(NAME, workspace, started) == 0
    receipt(NAME, script=__file__, started=started, solved=solved,
        pedigree="product-extracted (Claude Code as a library)",
        loop_owner="theirs — closed; we only configure",
        tools_we_wrote=[],
        tools_harness_shipped="full Claude Code kit: Bash, Read, Edit, Grep, web...",
        provider_friction="2 workarounds: Bearer auth via AUTH_TOKEN; warns unrecognized_model")
    return 0 if solved else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
