"""The Block 4 task through the Claude Agent SDK: Claude Code as a library.

    uv run claude_agent_sdk/run.py        (from block4_production_harnesses/)

Where it came from: product-extracted. This is the same loop and context
management that power Claude Code, driven programmatically. Notice what we
do NOT write: no loop, no dispatcher, no truncation, no compaction. The
harness ships with all of it decided.

The tools are ours: the same four as OpenAI Agents, Pydantic AI and ADK,
served to Claude Code as in-process SDK tools, with its own built-in tools
switched off. Same tools, so what differs from step 1 is the harness.
CLAUDE_TOOLS=own gives it Claude Code's own file tools instead (Read,
Write, Edit, Glob, Grep; still no Bash): that's where the Edit-per-string
numbers in COMPARISON.md come from. Bash is in tool_design/run_claude.py.

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
from common import end_turn, trace_result, ws_list, ws_read, ws_write, SYSTEM_PROMPT, _turn, TurnCapReached, set_tokens_sent, trace_cost, trace_note, tool_detail, TASK, TASK_MAX_TURNS, anthropic_compat_base_url, new_turn, prepare_workspace, receipt, trace_key, trace_say, trace_tool, verify, ws_run_tests  # noqa: E402

from claude_agent_sdk import (  # noqa: E402
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    StreamEvent,
    TextBlock,
    ToolUseBlock,
    create_sdk_mcp_server,
    query,
    tool,
)

load_dotenv()
NAME = "claude_agent_sdk"

# Our four tools by default; CLAUDE_TOOLS=own for Claude Code's own file
# tools (run_tests stays ours either way: without a shell, it's the only
# way to run pytest).
OWN_TOOLS = os.environ.get("CLAUDE_TOOLS") == "own"
if OWN_TOOLS:
    NAME = "claude_agent_sdk_own"   # its own row in the tables, its own workspace
CLAUDE_FILE_TOOLS = ["Read", "Write", "Edit", "Glob", "Grep"]
workspace: Path


def _text(s: str) -> dict:
    return {"content": [{"type": "text", "text": s}]}


@tool("list_files", "List every file in the workspace as relative paths.", {})
async def list_files(args) -> dict:
    trace_tool(NAME, "list_files")
    return _text(ws_list(workspace))


@tool("read_file", "Read one file, path relative to the workspace.", {"path": str})
async def read_file(args) -> dict:
    trace_tool(NAME, "read_file", tool_detail({"path": args["path"]}))
    return _text(ws_read(workspace, args["path"]))


@tool("write_file", "Overwrite one file, path relative to the workspace.", {"path": str, "content": str})
async def write_file(args) -> dict:
    trace_tool(NAME, "write_file", tool_detail({"path": args["path"], "content": args["content"]}))
    return _text(ws_write(workspace, args["path"], args["content"]))


@tool("run_tests", "Run pytest in the workspace; done means all tests pass.", {})
async def run_tests(args) -> dict:
    call = trace_tool(NAME, "run_tests")
    out = ws_run_tests(workspace)
    trace_result(NAME, "run_tests", out, call=call)
    return _text(out)


OUR_TOOLS = [run_tests] if OWN_TOOLS else [list_files, read_file, write_file, run_tests]



_sent = {"total": 0}


def _turn_cost(event: dict) -> None:
    """A model call's tokens. Through our gateway, the AssistantMessage's
    usage is all zeros; the real numbers arrive in the raw API's closing
    `message_delta` event, which the SDK streams only with
    include_partial_messages=True. Sent counts cached input too, as the
    other harnesses' lines do."""
    if event.get("type") != "message_delta":
        return
    u = event.get("usage") or {}
    sent = sum(u.get(k) or 0 for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
    if sent:
        _sent["total"] += sent
        trace_cost(NAME, sent, u.get("output_tokens") or 0, _sent["total"],
                   cached=u.get("cache_read_input_tokens") or 0)


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
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    if block.name.startswith("mcp__workspace__"):
                        continue   # our tools trace themselves as they run
                    trace_tool(NAME, block.name, tool_detail(block.input), harness_tool=True)
                elif isinstance(block, TextBlock) and block.text.strip():
                    trace_say(NAME, block.text)
        elif isinstance(message, StreamEvent):
            _turn_cost(message.event)
        elif isinstance(message, ResultMessage):
            for d in (getattr(message, "permission_denials", None) or []):
                trace_note(NAME, f"permission denied: {str(d)[:80]}")
            # Through our gateway, per-message usage is empty; the run's
            # total arrives here. Its cost figure assumes Anthropic prices, so
            # it's left out.
            u = message.usage or {}
            sent = sum(u.get(k) or 0 for k in ("input_tokens", "cache_read_input_tokens",
                                                "cache_creation_input_tokens"))
            cached = u.get("cache_read_input_tokens") or 0
            set_tokens_sent(sent, u.get("output_tokens"), cached)
            end_turn()
            print(f"[{NAME}] tokens sent this run: {sent:,}, {cached:,} of them from the "
                  f"provider's cache ({u.get('output_tokens') or 0:,} written by the model)")


async def main() -> int:
    global workspace
    workspace = prepare_workspace(NAME)
    if OWN_TOOLS:
        trace_key(NAME, ["run_tests"], "Claude Code's Read, Write, Edit, Glob, Grep (Bash withheld)")
    else:
        trace_key(NAME, ["list_files", "read_file", "write_file", "run_tests"])

    options = ClaudeAgentOptions(
        cwd=str(workspace),
        model=os.environ["LLM_MODEL"],
        max_turns=TASK_MAX_TURNS,
        include_partial_messages=True,   # for per-turn token counts; see _turn_cost
        # Without this the SDK sends an EMPTY system prompt (not Claude
        # Code's): set ours, the same as every other harness.
        system_prompt=SYSTEM_PROMPT,
        # The base toolset: anything not listed is gone. [] switches off
        # every built-in tool, so ours are all it has.
        tools=CLAUDE_FILE_TOOLS if OWN_TOOLS else [],
        mcp_servers={"workspace": create_sdk_mcp_server("workspace", tools=OUR_TOOLS)},
        allowed_tools=(CLAUDE_FILE_TOOLS if OWN_TOOLS else []) + [f"mcp__workspace__{t.name}" for t in OUR_TOOLS],
        # Headless: auto-approve edits inside the copied workspace.
        permission_mode="bypassPermissions",
        env={
            # The harness's home is Anthropic's API; we redirect it to the
            # workshop provider's Anthropic-compatible endpoint.
            "ANTHROPIC_BASE_URL": anthropic_compat_base_url(),
            # Some providers' Anthropic-compatible endpoints want
            # Authorization: Bearer, not the protocol's x-api-key. AUTH_TOKEN
            # (not API_KEY) makes Claude Code send Bearer. Found the hard way;
            # see "Provider coupling" in COMPARISON.md.
            "ANTHROPIC_AUTH_TOKEN": os.environ["LLM_API_KEY"],
            "ANTHROPIC_MODEL": os.environ["LLM_MODEL"],
            "ANTHROPIC_SMALL_FAST_MODEL": os.environ["LLM_MODEL"],
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
        loop_owner="theirs: closed; we only configure",
        tools_we_wrote=[t.name for t in OUR_TOOLS],
        tools_harness_shipped=("Claude Code's file tools (Read, Write, Edit, Glob, Grep); Bash withheld" if OWN_TOOLS
                               else "Read, Edit, Bash and more, all switched off for this run"),
        provider_friction="2 workarounds: Bearer auth via AUTH_TOKEN; warns unrecognized_model")
    return 0 if solved else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
