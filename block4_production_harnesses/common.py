"""Shared plumbing for the Block 4 harness scripts.

Every script runs the SAME task (by default the migration from Blocks 2
and 3) against a fresh copy of the workspace, under the same turn cap, and
is judged the same way: pytest afterward against the original tests,
never the agent's self-report. What varies is the harness driving the run; the runner
scripts exist to be read side by side.
"""

import shutil
import subprocess
import sys
import time
from pathlib import Path

BLOCK4 = Path(__file__).resolve().parent
REPO = BLOCK4.parent
FIX_BUG_SOURCE = REPO / "block2_naive_harness" / "tasks" / "short" / "01_fix_bug" / "workspace"
BUG_HUNT_SOURCE = REPO / "block2_naive_harness" / "tasks" / "medium" / "bug_hunt" / "workspace"
REFACTOR_SOURCE = REPO / "block2_naive_harness" / "tasks" / "long_horizon" / "refactor_v2" / "workspace"

# The Block 4 task is Blocks 2 and 3's migration (refactor_v2), so every
# receipt lines up with h1/h2/h3 on the same task. BLOCK4_TASK=bug_hunt is
# the quick fallback (three interacting bugs, about a minute per harness);
# BLOCK4_TASK=fix_bug is the trivial Block 2 task, where the spread
# between harnesses collapses because there's nothing to differentiate on.
import os as _os

REFACTOR_TASK = (
    "Migrate the source code to the v2 API following MIGRATION.md until all "
    "tests pass. Do not modify the tests."
)

# One system prompt for every harness and every script, file tools or shell,
# so the harness is the only thing that changes. (Harness-added text, like
# its tool descriptions, is the harness's own.)
SYSTEM_PROMPT = (
    "You work in a small Python workspace using the provided tools. The task "
    "is complete only when every test passes. Do not modify the tests."
)

# One turn cap for every harness: a turn is one model call, a subagent's
# included. 50 covers every successful run we measured (h2 needed up to
# 34 turns, Claude up to 45) and stops a runaway one (Deep Agents once
# made 164 calls and sent 8M tokens). Each SDK counts differently, so
# Claude and Deep Agents get the cap enforced by our own counter.
MIGRATION_MAX_TURNS = int(_os.environ.get("BLOCK4_MAX_TURNS", "50"))

BLOCK4_TASK = _os.environ.get("BLOCK4_TASK", "migration")
if BLOCK4_TASK == "fix_bug":
    TASK_SOURCE = FIX_BUG_SOURCE
    TASK = "One test fails. Find the bug and fix it. Do not modify the tests."
    TASK_MAX_TURNS = 12
elif BLOCK4_TASK == "bug_hunt":
    TASK_SOURCE = BUG_HUNT_SOURCE
    TASK = ("Several tests fail. Diagnose and fix all the bugs until every "
            "test passes. Do not modify the tests.")
    TASK_MAX_TURNS = 24
elif BLOCK4_TASK == "migration":
    TASK_SOURCE, TASK, TASK_MAX_TURNS = REFACTOR_SOURCE, REFACTOR_TASK, MIGRATION_MAX_TURNS
else:
    raise SystemExit(f"BLOCK4_TASK={BLOCK4_TASK!r}: use migration (default), bug_hunt or fix_bug")
if "BLOCK4_MAX_TURNS" in _os.environ:
    TASK_MAX_TURNS = MIGRATION_MAX_TURNS


class TurnCapReached(Exception):
    """Raised by our own counter where an SDK's cap doesn't count model calls."""


# --- trace output -----------------------------------------------------
# Same layout as Block 3, so a Block 4 trace reads like the ones you already
# know: one header per turn (green ❝ when the model talked) with its tool
# calls counted by type, then each call indented underneath.
# Every harness routes through these, so what differs on screen is the
# harness rather than five authors' print statements.
SAY = "\033[32m"
DIM = "\033[2m"
OFF = "\033[0m"


# Turn counting. Block 3 could just print `turn` because it owned the loop;
# here the harness owns it, so each script bumps this from whatever hook its
# SDK offers. How much work that takes varies a lot — which is itself a
# harness property worth noticing (see COMPARISON.md).
_turn = {"n": 0}
# The current turn, held until it's complete: the harness reports a turn's
# text, calls and costs in whatever order its hooks fire, and the header
# needs all of them (the counts come from the calls).
_pending = {"harness": "", "said": [], "calls": [], "after": []}
# What each run measures for its receipt: tool calls and tokens sent (all
# input the model read, cached or not, as Block 2's scoreboard counts it).
_usage = {"calls": 0, "sent": 0}


def set_tokens_sent(total: int) -> None:
    """For an SDK that reports usage only as a run total."""
    _usage["sent"] = int(total or 0)


def run_context() -> dict:
    """Where a result came from, so results from different setups are never
    mixed up: the provider's host (never the key) and the repo commit."""
    from urllib.parse import urlparse
    import os
    base_url = os.environ.get("PROVIDER_BASE_URL", "")
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
    except Exception:
        commit = ""
    return {
        "model": os.environ.get("MODEL", ""),
        "provider": urlparse(base_url).netloc or base_url,
        "repo_commit": commit,
    }

def end_turn() -> None:
    """Print the turn held so far. new_turn() calls it; scripts call it once
    after the run, so their summary lines land below the last turn."""
    h, said, calls, after = (_pending["harness"], _pending["said"],
                             _pending["calls"], _pending["after"])
    _pending.update(said=[], calls=[], after=[])
    if not (said or calls or after):
        return
    where = f"{h} turn {_turn['n']}" if _turn["n"] else h
    if calls:
        counts: dict = {}
        for name, _, _, _ in calls:
            counts[name] = counts.get(name, 0) + 1
        tally = "  [" + ", ".join(f"{k} × {v}" for k, v in counts.items()) + "]"
        text = " ".join(" ".join(said).split())
        if text:
            print(f"\n{SAY}❝  [{where}] agent says: {text}{OFF}{tally}")
        else:
            print(f"\n{DIM}   [{where}]{OFF}{tally}")
        for name, detail, theirs, result in calls:
            mark = f"{DIM}  · harness tool{OFF}" if theirs else ""
            print(f"     {name}({detail}){mark}")
            if result:
                print(result)
    elif said:
        print(f"\n\033[1;32m❝  [{where}] agent finished:{OFF}")
        print(SAY + "\n\n".join(said) + OFF)
    for line in after:
        print(line)


def new_turn() -> int:
    """Call once per model request: prints the previous turn, starts this one."""
    end_turn()
    _turn["n"] += 1
    return _turn["n"]


def trace_tool(harness: str, name: str, detail: str = "", harness_tool: bool = False) -> None:
    """One tool call, held for the turn's block. Args are shown because
    *which* file it reached for is the interesting part when comparing how
    harnesses explore. `harness_tool` marks a tool the harness brought rather
    than one we wrote: the whole point of the block, made visible."""
    _usage["calls"] += 1
    _pending["harness"] = harness
    _pending["calls"].append([name, detail, harness_tool, None])


def trace_result(harness: str, name: str, output, failed: bool = False) -> None:
    """A call's result, printed under it as one line: the last line of its
    output (`→`), or `✗` when it failed. Only where a result says something
    a call doesn't: a shell command's output, a rename's count. Shell tools
    end with an exit-code line (ours "[exit code N]", Deep Agents'
    "[Command succeeded with exit code N]"): a non-zero one is a failure."""
    import re
    lines = [ln for ln in str(output if output is not None else "").splitlines() if ln.strip()]
    if lines:
        m = re.match(r"^\[(?:Command (?:succeeded|failed) with )?exit code (-?\d+)\]$", lines[-1].strip())
        if m:
            lines = lines[:-1]
            failed = failed or m.group(1) != "0"
            if failed:
                lines.append(f"(exit code {m.group(1)})")
    shown = (" ".join(lines[-2:]) if failed and len(lines) > 1 else lines[-1]) if lines else "(no output)"
    line = f"\033[31m       ✗ {shown[:110]}{OFF}" if failed else f"{DIM}       → {shown[:110]}{OFF}"
    for call in _pending["calls"]:          # results come back in the order the calls ran
        if call[0] == name and call[3] is None:
            call[3] = line
            return
    _pending["after"].append(line)


def trace_reject(harness: str, why: str) -> None:
    """A tool call the harness refused before running it."""
    _pending["harness"] = harness
    _pending["after"].append(f"\033[35m     ↻ rejected before execution: {why}{OFF}")


def trace_state(harness: str, delta: dict) -> None:
    """Session-state changes. Only ADK surfaces these, and state IS what a
    construction kit gives you instead of a finished harness."""
    keys = ", ".join(f"{k}={str(v)[:30]}" for k, v in list(delta.items())[:3])
    _pending["after"].append(f"{DIM}     ⚙ session state: {keys}{OFF}")


def trace_note(harness: str, text: str) -> None:
    """Something the harness did on its own: the kind of event you wrote
    by hand in Block 3 and are now only a spectator to."""
    _pending["after"].append(f"\033[33m     ✂ {text}{OFF}")


def _rel(path, virtual: bool = False) -> str:
    """A path inside the run's copy, shown relative to it: the absolute
    prefix is the same for every call and says nothing. `virtual` is for
    Deep Agents, whose "/" IS the workspace; anywhere else a leading "/"
    is kept, because an absolute path outside the copy is worth noticing."""
    s = str(path)
    for ws in _SOURCES:
        root = str(ws.resolve())
        if s.startswith(root):
            s = s[len(root):].lstrip("/") or "."
            break
    else:
        if virtual:
            s = s.lstrip("/") or "."
    while s.startswith("./"):
        s = s[2:]
    return s or "."


def tool_detail(payload, virtual: bool = False) -> str:
    """Render a tool's input for the trace. Bash commands are shown whole:
    the single most interesting artifact in this block is the shell command
    the model writes when a harness hands it a shell. Everything else is
    summarized: paths relative to the workspace, sizes instead of file
    contents, and the flags that change what a call does."""
    if not isinstance(payload, dict):
        return str(payload)[:70]
    if "command" in payload:
        return str(payload["command"])
    parts = [f"{k}={_rel(payload[k], virtual)!r}" for k in ("file_path", "path") if k in payload]
    parts += [f"{k}={payload[k]!r}" for k in ("pattern", "glob", "description") if k in payload]
    parts += [f"{k}: {len(str(payload[k]))} chars" for k in ("content", "old_string", "new_string") if k in payload]
    if payload.get("replace_all"):
        parts.append("replace_all=True")
    return ", ".join(parts) or (str(payload)[:70] if payload else "")


def trace_cost(harness: str, sent: int, out: int, cumulative: int | None = None) -> None:
    """What this turn put on the wire. Block 3's whole cost argument was
    that the transcript is re-sent every turn; here you can watch the
    `sent` number climb while the task stays the same size."""
    _usage["sent"] += sent
    tail = f" · {cumulative:,} in total" if cumulative is not None else ""
    _pending["after"].append(f"{DIM}     ┈ {sent:,} tokens in / {out:,} out{tail}{OFF}")


def trace_say(harness: str, text: str) -> None:
    """The model talking: narration mid-run, or its closing summary. Kept
    whole, and only once (some scripts hand the final answer over twice)."""
    if text and text.strip() and text.strip() not in _pending["said"]:
        _pending["harness"] = harness
        _pending["said"].append(text.strip())


def trace_key(harness: str, ours: list, theirs: str = "") -> None:
    """Printed once at the start of a run, so nobody has to guess what the
    markers mean, and so the tools we wrote can be told apart from the
    ones the harness brought."""
    print(f"{DIM}   ┈ trace markers{OFF}")
    print(f"     {DIM}one header per turn ({OFF}{SAY}❝{OFF}{DIM} = the model talking), its tool calls"
          f" counted by type, each call indented below{OFF}")
    print(f"     {DIM}tools we wrote: {', '.join(ours) if ours else 'none'}{OFF}")
    if theirs:
        print(f"     {DIM}the harness's own tools, marked \"· harness tool\": {theirs}{OFF}")

def ws_list(workspace: Path) -> str:
    """Relative paths of every file in the workspace."""
    return "\n".join(
        str(p.relative_to(workspace))
        for p in sorted(workspace.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts and ".pytest_cache" not in p.parts
    )


def _inside(workspace: Path, path: str) -> Path | None:
    """Resolve a tool's path, or None if it lands outside the workspace.
    `workspace / path` alone is not a boundary: "../x" climbs out, and an
    absolute path replaces the workspace entirely. Same rule as Block 2's
    Workspace._path."""
    root = workspace.resolve()
    target = (root / path).resolve()
    return target if target.is_relative_to(root) else None


def ws_read(workspace: Path, path: str) -> str:
    """Read a file; errors come back as messages the model can act on,
    never exceptions — some harnesses (ADK) crash the whole run on a
    raised tool error, which is the h2 lesson in reverse."""
    target = _inside(workspace, path)
    if target is None:
        return f"error: {path!r} is outside the workspace"
    if target.is_dir():
        return f"error: {path!r} is a directory, not a file. Files:\n{ws_list(workspace)}"
    if not target.is_file():
        return f"error: {path!r} not found. Files:\n{ws_list(workspace)}"
    return target.read_text()


def ws_write(workspace: Path, path: str, content: str) -> str:
    target = _inside(workspace, path)
    if target is None:
        return f"error: {path!r} is outside the workspace"
    if target.is_dir():
        return f"error: {path!r} is a directory"
    if is_test_path(target.relative_to(workspace.resolve())):
        return f"error: {path!r} is a test file; tests are read-only in this run"
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        target.write_text(content)
    except PermissionError:
        return f"error: {path!r} is read-only"
    return f"wrote {len(content)} chars"


def changed_tests(workspace: Path) -> list:
    """Test files that differ from the originals (changed, added or deleted)."""
    source = _SOURCES.get(workspace)
    if source is None:
        return []
    before, after = test_files(source), test_files(workspace)
    return sorted(r for r in before.keys() | after.keys() if before.get(r) != after.get(r))


# Test files changed at some point during a run, even if put back later.
_violations: dict = {}


def ws_run_tests(workspace: Path) -> str:
    # Running pytest executes conftest.py, so a modified one is a way to run
    # any code: one agent wrote a rename script into the (empty) conftest.py,
    # ran the tests to execute it, then emptied the file again. So the tests
    # must be the originals before they run, and a run that changed them
    # fails even if it changes them back.
    changed = changed_tests(workspace)
    if changed:
        _violations.setdefault(workspace, set()).update(map(str, changed))
        return ("refused: test files differ from the originals: " + ", ".join(map(str, changed))
                + ". Tests (including conftest.py) are read-only in this run; restore them to run the tests.")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=workspace, capture_output=True, text=True, timeout=120,
    )
    return proc.stdout + proc.stderr


def ws_shell(workspace: Path, command: str, max_output: int = 30_000) -> str:
    """Run a shell command in the workspace: output plus exit code. Only PATH
    and HOME come from our environment, so no API keys. Not a sandbox: a
    command can reach anything you can."""
    try:
        proc = subprocess.run(
            command, shell=True, cwd=workspace, capture_output=True, text=True, timeout=120,
            env={"PATH": _os.environ.get("PATH", ""), "HOME": _os.environ.get("HOME", "")},
        )
        out, code = proc.stdout + proc.stderr, proc.returncode
    except subprocess.TimeoutExpired:
        out, code = "command timed out after 120s", -1
    if len(out) > max_output:
        half = max_output // 2
        out = out[:half] + f"\n... [{len(out) - max_output:,} chars cut] ...\n" + out[-half:]
    return f"{out}\n[exit code {code}]"


def anthropic_compat_base_url() -> str:
    """The provider's Anthropic-dialect endpoint, derived from the one
    already-configured URL: the OpenAI dialect mounts at {host}/v1, the
    Anthropic dialect wants the bare {host} (its client appends
    /v1/messages). Holds for Baseten and Fireworks; set
    ANTHROPIC_COMPAT_BASE_URL explicitly for a provider where it doesn't."""
    override = _os.environ.get("ANTHROPIC_COMPAT_BASE_URL")
    if override:
        return override
    return _os.environ["PROVIDER_BASE_URL"].removesuffix("/v1")


def changed_files(path: Path):
    """Files in `path` that differ from the last commit (modified, added or
    deleted). A task an agent has touched still fails its tests if the work
    is only half done, so "tests fail" alone can't prove a fixture is
    pristine; git can. Returns None when this isn't a git checkout."""
    proc = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all", "--", "."],
        cwd=path, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return None
    return [line[3:] for line in proc.stdout.splitlines() if line.strip()]


# Which source each run copied, so verify() can compare its tests against
# the originals. Kept here, not in the workspace, where an agent could edit it.
_SOURCES: dict = {}


def is_test_path(rel: Path) -> bool:
    """Tests decide whether a run passed, so they're off limits: anything
    under tests/, test_*.py or *_test.py, and conftest.py (which can
    change how tests run)."""
    if "__pycache__" in rel.parts or ".pytest_cache" in rel.parts:
        return False
    return ("tests" in rel.parts[:-1] or rel.name == "conftest.py"
            or (rel.suffix == ".py" and (rel.name.startswith("test_") or rel.stem.endswith("_test"))))


def test_files(root: Path) -> dict:
    """Every test file under root: relative path -> contents."""
    return {f.relative_to(root): f.read_bytes() for f in sorted(root.rglob("*"))
            if f.is_file() and is_test_path(f.relative_to(root))}


def _lock_tests(workspace: Path) -> None:
    """The guard: test files read-only, and directories under tests/ too, so
    a shell can't swap a file in with `sed -i` either. It stops honest
    mistakes, not a determined agent (chmod undoes it); verify() is the
    backstop."""
    for rel in test_files(workspace):
        (workspace / rel).chmod(0o444)
    for d in sorted(workspace.rglob("tests"), reverse=True):
        if d.is_dir():
            for sub in [*d.rglob("*"), d]:
                if sub.is_dir():
                    sub.chmod(0o555)


def remove_run_dir(path: Path) -> None:
    """rmtree that first makes locked test files and folders writable again."""
    if not path.exists():
        return
    for p in [path, *path.rglob("*")]:
        if not p.is_symlink():
            p.chmod(0o755 if p.is_dir() else 0o644)
    shutil.rmtree(path)


def prepare_workspace(harness: str, source: Path = TASK_SOURCE) -> Path:
    """Fresh copy of a task workspace under runs/<harness>/.

    Refuses to run if the source fixture is already solved. Block 2 edits
    the fix_bug workspace IN PLACE, so an attendee who does Block 2 and then
    BLOCK4_TASK=fix_bug here would copy a finished task: every harness
    "succeeds" in one turn and the receipts compare nothing.
    """
    probe = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=source, capture_output=True, text=True, timeout=180,
    )
    changed = changed_files(source)
    if probe.returncode == 0 or changed:
        what = "already solved" if probe.returncode == 0 else f"edited ({len(changed)} file(s) differ from git)"
        raise SystemExit(
            f"source fixture is {what}: {source}\n"
            f"A previous run (Block 2?) fixed it in place, so measuring against "
            f"it is meaningless. Reset first, from block4_production_harnesses/:\n"
            f"  uv run ../scripts/reset.py && uv run ../scripts/check_fixtures.py"
        )

    run_dir = BLOCK4 / "runs" / harness
    workspace = run_dir / "workspace"
    remove_run_dir(run_dir)
    shutil.copytree(source, workspace, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    _lock_tests(workspace)
    _SOURCES[workspace] = source
    return workspace


def verify(harness: str, workspace: Path, started: float) -> int:
    """Pytest is the judge, run against the ORIGINAL tests. Returns a process
    exit code.

    Any test file the agent changed, added or deleted fails the run, whatever
    pytest says: an agent that edits the tests can make them agree with
    anything. The originals are then put back and pytest runs on them, so
    the summary line shows where the code really stands."""
    end_turn()
    wall = time.monotonic() - started
    source = _SOURCES.get(workspace)
    tampered, earlier = [], []
    if source is not None:
        before, after = test_files(source), test_files(workspace)
        tampered = sorted(r for r in before.keys() | after.keys() if before.get(r) != after.get(r))
        earlier = sorted(_violations.get(workspace, set()) - {str(r) for r in tampered})
        for rel in tampered:                       # restore the originals
            target = workspace / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.parent.chmod(0o755)
            if target.exists():
                target.chmod(0o644)
                target.unlink()
            if rel in before:
                target.write_bytes(before[rel])
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
        cwd=workspace, capture_output=True, text=True, timeout=120,
        env={**_os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    summary = (proc.stdout.strip().splitlines() or ["(no output)"])[-1]
    solved = proc.returncode == 0 and not tampered and not earlier
    verdict = "SOLVED" if solved else "NOT SOLVED"
    print(f"\n--- {harness}: {verdict} | wall={wall:.1f}s | {summary} (original tests)")
    if tampered:
        print(f"\033[1;31m--- {harness}: the agent modified {len(tampered)} test file(s), which fails "
              f"the run: {', '.join(map(str, tampered))}\033[0m")
    if earlier:
        print(f"\033[1;31m--- {harness}: the agent modified test file(s) during the run and tried to run "
              f"the tests on them, which fails the run: {', '.join(earlier)}\033[0m")
    return 0 if solved else 1


def receipt(
    harness: str,
    *,
    script: str,
    started: float,
    solved: bool,
    origin: str,
    loop_owner: str,
    tools_we_wrote: list,
    tools_harness_shipped: str,
    provider_friction: str,
) -> None:
    """Print this run's harness receipt and the comparison table so far.

    The five scripts produce nearly identical RESULTS on purpose: the
    outcome is the controlled variable. What differs is everything on this
    receipt, which is why it prints after every run and accumulates: by
    your last run, the table IS the comparison.
    """
    import json

    task_name = BLOCK4_TASK
    row = {
        "harness": harness,
        "task": task_name,
        "solved": solved,
        "wall_s": round(time.monotonic() - started, 1),
        "turns": _turn["n"],
        "tool_calls": _usage["calls"],
        "tokens_sent": _usage["sent"] or None,
        "origin": origin,
        "loop_owner": loop_owner,
        "tools_we_wrote": f"{len(tools_we_wrote)} ({', '.join(tools_we_wrote) or '—'})",
        "tools_harness_shipped": tools_harness_shipped,
        "provider_friction": provider_friction,
        "code_lines": len(Path(script).read_text().splitlines()),
        "timestamp": time.time(),
        **run_context(),
    }

    receipts = BLOCK4 / "runs" / "receipts.jsonl"
    receipts.parent.mkdir(exist_ok=True)
    with receipts.open("a") as fh:
        fh.write(json.dumps(row) + "\n")

    print_tables(task_name)


def print_tables(task_name: str = BLOCK4_TASK, *, quiet_progress: bool = False) -> None:
    """The results and receipts tables: the latest run of each harness."""
    import json

    receipts = BLOCK4 / "runs" / "receipts.jsonl"
    if not receipts.exists():
        print("no receipts yet")
        return
    latest: dict = {}
    with receipts.open() as fh:
        for line in fh:
            r = json.loads(line)
            # rows recorded before task tracking existed show as "?"
            latest[(r.get("harness") or r["specimen"], r.get("task", "?"))] = r

    from rich.console import Console
    from rich.table import Table

    def k(n):
        return f"{n / 1e6:.2f}M" if n else "?"

    results = Table(title="Results: what each harness did with the same task, model and turn cap",
                    title_style="bold")
    for col in ("harness", "solved", "turns", "tool calls", "tokens sent", "wall s"):
        results.add_column(col, justify="left" if col == "harness" else "right",
                           no_wrap=col == "harness")
    for r in latest.values():
        if r.get("task", "?") != task_name:
            continue
        results.add_row(r.get("harness") or r["specimen"],
                        "yes" if r["solved"] else "NO", str(r.get("turns", "?")),
                        str(r.get("tool_calls", "?")), k(r.get("tokens_sent")), str(r["wall_s"]))
    if task_name == "migration":
        results.add_row("[dim]our h2 / h3 (Block 3)[/dim]", "", "[dim]17–34[/dim]",
                        "[dim]181–299[/dim]", "[dim]0.37–0.78M[/dim]", "")

    table = Table(
        title="Receipts: what each harness decided for you, and what it left to you",
        title_style="bold",
    )
    for col in ("harness", "loop", "tools we wrote", "harness's own tools", "provider friction", "lines"):
        table.add_column(col, overflow="fold")
    for r in latest.values():
        if r.get("task", "?") != task_name:
            continue
        table.add_row(
            r.get("harness") or r["specimen"],
            r["loop_owner"],
            r["tools_we_wrote"],
            r["tools_harness_shipped"],
            r["provider_friction"],
            str(r["code_lines"]),
        )
    print(f"\nthis run's task: {task_name}")
    Console().print(results)
    Console().print(table)
    print(
        "where these cells come from: the results table is measured this run; the "
        "receipt cells are authored facts from the build record (hardcoded in each "
        "script's receipt() call; check them against its run.py)"
    )
    remaining = 0 if quiet_progress else 5 - sum(1 for (_, t) in latest if t == task_name)
    if remaining > 0:
        print(f"({remaining} harness(es) left on {task_name} — each adds a row)")
