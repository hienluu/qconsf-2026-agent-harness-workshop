"""Deep Agents' compaction, measured. Presenter research, not an attendee step.

    DEEPAGENTS_SUBAGENTS=off DEEPAGENTS_COMPACTION=early DEEPAGENTS_SUMMARY_AT=12000 \\
      BLOCK4_MAX_TURNS=40 uv run deepagents/compaction_experiment.py
                                      (from block4_production_harnesses/)

The same agent as deepagents/run.py, plus switches and markers for what
its summarization middleware does. That middleware compacts on its own:
it clips large write_file/edit_file arguments in older messages, and past
a token threshold it replaces old history with a model-written summary
(the evicted messages are saved to /conversation_history/ in the
workspace copy).

    DEEPAGENTS_COMPACTION   default  as the library ships it
                            off      the middleware replaced by a no-op: no
                                     summary, no argument clipping
                            early    the library's settings, but summarize
                                     at DEEPAGENTS_SUMMARY_AT tokens
                                     (default 25,000) so it fires on this task
    DEEPAGENTS_SUBAGENTS    on (default), or off: no general-purpose
                            subagent and no `task` tool, so the job runs in
                            one growing conversation and the cap counts the
                            main agent's calls

Each combination gets its own workspace copy and receipt row
(deepagents-exp-<arm>[-nosub]), so it never replaces the attendee row.
Large single tool results (over 20k tokens) are saved to a file by the
filesystem middleware in every arm; that part can't be switched off.

The markers (✂ lines under a turn): argument clipping, each summary, the
summary's own model call (billed, but not counted as a turn), a result
saved to a file, and a re-read of a file a summary had dropped.

Results and analysis (Nov 14, Fireworks): framework-research/
deepagents-compaction-experiment.md in the presenter's notes.
"""

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from langchain_core.callbacks import BaseCallbackHandler  # noqa: E402
from langchain_core.messages import AIMessage, ToolMessage  # noqa: E402
from common import end_turn, trace_result, tool_detail, SYSTEM_PROMPT, trace_cost, TASK, TASK_MAX_TURNS, TurnCapReached, new_turn, prepare_workspace, receipt, trace_key, trace_note, trace_say, trace_tool, verify, ws_run_tests  # noqa: E402

from deepagents import create_deep_agent  # noqa: E402
from deepagents.backends import FilesystemBackend  # noqa: E402
from deepagents.middleware.summarization import SummarizationMiddleware, compute_summarization_defaults  # noqa: E402
from langchain.agents.middleware import AgentMiddleware  # noqa: E402
from langchain_openai import ChatOpenAI  # noqa: E402

load_dotenv()
ARM = os.environ.get("DEEPAGENTS_COMPACTION", "default")
if ARM not in ("default", "off", "early"):
    raise SystemExit(f"DEEPAGENTS_COMPACTION={ARM!r}: use default, off or early")
SUMMARY_AT = int(os.environ.get("DEEPAGENTS_SUMMARY_AT", "25000"))
# DEEPAGENTS_SUBAGENTS=off: no built-in subagent and no `task` tool (the
# two settings COMPARISON.md documents), so the whole job runs in one
# growing conversation and the turn cap counts the main agent's calls.
SUBAGENTS = os.environ.get("DEEPAGENTS_SUBAGENTS", "on")
if SUBAGENTS not in ("on", "off"):
    raise SystemExit(f"DEEPAGENTS_SUBAGENTS={SUBAGENTS!r}: use on or off")
NAME = f"deepagents-exp-{ARM}"
if SUBAGENTS == "off":
    NAME += "-nosub"
workspace: Path

# What compaction did over the run, for the closing line. `read` holds the
# files read so far; `before_summary` the ones read before the latest
# summary, so a read of one of those afterwards counts as a re-read caused
# (or at least not prevented) by summarizing.
compaction = {"summaries": 0, "summarized_msgs": 0, "summary_sent": 0,
              "clipped_max": 0, "evicted": set(),
              "read": set(), "before_summary": set(), "rereads": 0,
              "rereads_after_summary": 0}


class WatchedSummarization(SummarizationMiddleware):
    """The library's own summarization middleware, unchanged except that it
    reports what it does. It takes the default one's place by name, so the
    stack order is the same (and the general-purpose subagent inherits it)."""

    @property
    def name(self) -> str:
        return "SummarizationMiddleware"

    def _truncate_args(self, messages, total_tokens):
        out, modified = super()._truncate_args(messages, total_tokens)
        if modified:
            # Re-applied to the full history on every call (the state keeps
            # the originals), so count what's clipped now, and report only
            # when that grows.
            clipped = freed = 0
            for before, after in zip(messages, out):
                if after is not before and isinstance(after, AIMessage):
                    for b, a in zip(before.tool_calls, after.tool_calls):
                        if a is not b:
                            clipped += 1
                            freed += len(str(b.get("args"))) - len(str(a.get("args")))
            if clipped > compaction["clipped_max"]:
                new = clipped - compaction["clipped_max"]
                compaction["clipped_max"] = clipped
                trace_note(NAME, f"next call: {new} more old write/edit call(s) clipped; "
                                 f"{clipped} clipped in all, {freed:,} chars kept off the wire")
        return out, modified

    def _create_summary(self, messages_to_summarize):
        summary = super()._create_summary(messages_to_summarize)
        tokens = self.token_counter(messages_to_summarize)
        compaction["summaries"] += 1
        compaction["before_summary"] = set(compaction["read"])
        compaction["summarized_msgs"] += len(messages_to_summarize)
        trace_note(NAME, f"next call: summarized {len(messages_to_summarize)} old messages "
                         f"(~{tokens:,} tokens) into {len(summary):,} chars; the originals "
                         f"are saved under /conversation_history/")
        return summary


class NoCompaction(AgentMiddleware):
    """Takes the summarization middleware's place and does nothing."""

    @property
    def name(self) -> str:
        return "SummarizationMiddleware"


def compaction_middleware(model, backend) -> tuple[AgentMiddleware, str]:
    if ARM == "off":
        return NoCompaction(), "off (no summary, no argument clipping)"
    d = compute_summarization_defaults(model)
    trigger = ("tokens", SUMMARY_AT) if ARM == "early" else d["trigger"]
    t = d["truncate_args_settings"]
    mw = WatchedSummarization(
        model=model,
        backend=backend,
        trigger=trigger,
        keep=d["keep"],
        # What create_summarization_middleware passes; the class default is 4000.
        trim_tokens_to_summarize=None,
        truncate_args_settings=t,
    )
    how = (f"{ARM}: summarize at {trigger[1]:,} {trigger[0]}, keep the last {d['keep'][1]} "
           f"{d['keep'][0]}; clip old write/edit args over 2,000 chars once past "
           f"{t['trigger'][1]} {t['trigger'][0]}, keeping the last {t['keep'][1]} whole")
    return mw, how


def run_tests() -> str:
    """Run pytest in the workspace; done means all tests pass."""
    call = trace_tool(NAME, "run_tests")
    out = ws_run_tests(workspace)
    trace_result(NAME, "run_tests", out, call=call)
    return out


class Watch(BaseCallbackHandler):
    """LangGraph accepts LangChain callbacks, which buys us two things a
    plain .invoke() hides: turn boundaries, and the harness's OWN tool
    calls. Without on_tool_start this trace showed 2 calls where other
    harnesses showed 12 — because Deep Agents does its file work through
    tools it brought, and we never see them."""

    main_calls = sub_calls = sent = 0
    summary_runs: set = set()
    raise_error = True   # let TurnCapReached stop the graph instead of being logged

    def on_chat_model_start(self, serialized, messages, **kwargs) -> None:
        meta = kwargs.get("metadata") or {}
        # The summarization middleware's own call to the model: billed, but
        # not a turn. Without this it counted against the cap and its
        # summary was traced as the agent talking.
        if meta.get("lc_source") == "summarization":
            Watch.summary_runs.add(kwargs.get("run_id"))
            return
        # A tool result too big to keep inline, saved to a file by the
        # filesystem middleware: it shows up as a placeholder message.
        for batch in messages or []:
            for m in batch:
                if (isinstance(m, ToolMessage) and m.tool_call_id not in compaction["evicted"]
                        and str(m.content).startswith("Tool result too large")):
                    compaction["evicted"].add(m.tool_call_id)
                    trace_note(NAME, "a tool result over 20k tokens was saved to a file; "
                                     "the model sees a head/tail preview")
        # The turn cap, enforced here: recursion_limit counts graph steps,
        # and each subagent gets its own, so neither caps model calls.
        if Watch.main_calls + Watch.sub_calls >= TASK_MAX_TURNS:
            raise TurnCapReached(f"turn cap reached: {TASK_MAX_TURNS} model calls")
        new_turn()
        # Deep Agents tags a subagent's runs: ls_agent_type "subagent", and
        # lc_agent_name set to the subagent's name ("general-purpose" for the
        # built-in one).
        if meta.get("ls_agent_type") == "subagent" or meta.get("lc_agent_name") == "general-purpose":
            Watch.sub_calls += 1
        else:
            Watch.main_calls += 1

    def on_llm_end(self, response, **kwargs) -> None:
        is_summary = kwargs.get("run_id") in Watch.summary_runs
        for batch in (getattr(response, "generations", None) or []):
            for gen in batch:
                u = getattr(getattr(gen, "message", None), "usage_metadata", None) or {}
                if u.get("input_tokens"):
                    Watch.sent += u["input_tokens"]
                    cached = (u.get("input_token_details") or {}).get("cache_read") or 0
                    trace_cost(NAME, u["input_tokens"], u.get("output_tokens") or 0, Watch.sent,
                               cached=cached)
                    if is_summary:
                        compaction["summary_sent"] += u["input_tokens"]
                        trace_note(NAME, "the cost line above is the summary call, not a turn")
                if is_summary:
                    continue                 # the summary text isn't the agent talking
                said = getattr(gen, "text", None)
                if said and said.strip():
                    trace_say(NAME, said)

    def on_tool_start(self, serialized, input_str, **kwargs) -> None:
        name = (serialized or {}).get("name") or kwargs.get("name") or "tool"
        if name == "run_tests":
            return                       # already traced by the tool itself
        # The arguments, summarized (relative paths, sizes not contents,
        # replace_all when set): cutting the raw string at a fixed length
        # hid the fields that matter.
        args = kwargs.get("inputs")
        detail = tool_detail(args, virtual=True) if isinstance(args, dict) else str(input_str)[:70]
        trace_tool(NAME, name, detail, harness_tool=True)
        if name == "read_file" and isinstance(args, dict) and args.get("file_path"):
            path = str(args["file_path"])
            if path in compaction["read"]:
                compaction["rereads"] += 1
                if path in compaction["before_summary"]:
                    compaction["rereads_after_summary"] += 1
                    trace_note(NAME, f"re-read after a summary: {path.lstrip('/')}")
            compaction["read"].add(path)


def main() -> int:
    global workspace
    workspace = prepare_workspace(NAME)
    trace_key(NAME, ["run_tests"], "ls, read_file, write_file, edit_file, glob, grep, write_todos"
              + (", task (subagents)" if SUBAGENTS == "on" else ""))
    if SUBAGENTS == "off":
        from deepagents import GeneralPurposeSubagentProfile, HarnessProfile, register_harness_profile
        # "openai" is the provider key for ChatOpenAI, whatever the base URL.
        register_harness_profile("openai", HarnessProfile(
            excluded_tools=frozenset({"task"}),
            general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False)))
        print(f"[{NAME}] subagents: off (no general-purpose subagent, no task tool)")

    model = ChatOpenAI(
        model=os.environ["LLM_MODEL"],
        base_url=os.environ["LLM_BASE_URL"],
        api_key=os.environ["LLM_API_KEY"],
        max_retries=5,  # the workshop provider throws occasional 500s
    )
    # The harness's own file tools, aimed at the run's private copy.
    # virtual_mode=True is the confined mode: paths are kept inside
    # root_dir. With virtual_mode=False the library documents that
    # "absolute paths are allowed as-is" — root_dir becomes a default
    # for relative paths, not a boundary — and we watched an agent walk
    # out of its copy and edit the source fixture in place.
    backend = FilesystemBackend(root_dir=workspace, virtual_mode=True)
    summarization, how = compaction_middleware(model, backend)
    print(f"[{NAME}] compaction: {how}")
    agent = create_deep_agent(
        model=model,
        backend=backend,
        tools=[run_tests],
        system_prompt=SYSTEM_PROMPT,
        middleware=[summarization],
    )

    started = time.monotonic()
    try:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": TASK}]},
            # recursion_limit counts graph steps (a turn takes two or more);
            # set well above the cap so our counter is the one that stops it.
            config={"recursion_limit": TASK_MAX_TURNS * 10,
                    "callbacks": [Watch()]},
        )
        trace_say(NAME, str(result["messages"][-1].content))
        end_turn()
        print(f"[{NAME}] messages in transcript: {len(result['messages'])}")
    except Exception as exc:  # hitting the recursion limit is an outcome, not a crash
        end_turn()
        print(f"[{NAME}] run ended without finishing: {type(exc).__name__}: {str(exc)[:120]}")
    end_turn()
    print(f"[{NAME}] model calls: {Watch.main_calls + Watch.sub_calls} "
          f"({Watch.main_calls} by the main agent, {Watch.sub_calls} by subagents); "
          f"tokens sent: {Watch.sent:,}")
    print(f"[{NAME}] compaction: {compaction['summaries']} summar"
          f"{'y' if compaction['summaries'] == 1 else 'ies'} "
          f"({compaction['summarized_msgs']} messages; the summary calls sent "
          f"{compaction['summary_sent']:,} of those tokens), "
          f"{compaction['clipped_max']} old write/edit call(s) clipped, "
          f"{len(compaction['evicted'])} tool result(s) saved to a file")
    print(f"[{NAME}] re-reads: {compaction['rereads']} read(s) of a file already read, "
          f"{compaction['rereads_after_summary']} of them after a summary had dropped it")
    solved = verify(NAME, workspace, started) == 0
    receipt(NAME, script=__file__, started=started, solved=solved,
        origin="harness on a runtime (LangGraph underneath)",
        loop_owner="theirs: ReAct + middleware onion",
        tools_we_wrote=["run_tests"],
        tools_harness_shipped="filesystem suite on the real workspace, write_todos"
                              + (", subagents" if SUBAGENTS == "on" else ""),
        provider_friction="none for the model; retries added for provider 500s")
    return 0 if solved else 1


if __name__ == "__main__":
    raise SystemExit(main())
