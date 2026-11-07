"""Shared plumbing for the Block 4 harness scripts.

Every script runs the SAME task — by default bug_hunt, three interacting
bugs in a small pricing package — against a fresh copy of the workspace,
and is judged the same way: pytest afterward, never the agent's
self-report. What varies is the harness driving the run; the runner
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

# The official Block 4 task is bug_hunt — three interacting bugs across 8
# modules, enough work that differences in how each harness works
# (exploration, planning, batching) have room to show. BLOCK4_TASK=fix_bug switches to the trivial
# Block 2 task as extra credit: watch the spread collapse when
# there's nothing to differentiate on.
import os as _os

if _os.environ.get("BLOCK4_TASK") == "fix_bug":
    TASK_SOURCE = FIX_BUG_SOURCE
    TASK = "One test fails. Find the bug and fix it. Do not modify the tests."
    TASK_MAX_TURNS = 12
else:
    TASK_SOURCE = BUG_HUNT_SOURCE
    TASK = ("Several tests fail. Diagnose and fix all the bugs until every "
            "test passes. Do not modify the tests.")
    TASK_MAX_TURNS = 24
REFACTOR_TASK = (
    "Migrate the source code to the v2 API following MIGRATION.md until all "
    "tests pass. Do not modify the tests."
)


# --- trace output -----------------------------------------------------
# Same vocabulary as Block 3, so a Block 4 trace reads like the ones you
# already know: green ❝ is the model talking, plain lines are tool calls.
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

def new_turn() -> int:
    """Call once per model request. Prints a blank line between turns (not
    before the first), so a long trace reads as blocks the way Block 3's
    does — the turn boundary is the only structure these traces have."""
    if _turn["n"]:
        print()
    _turn["n"] += 1
    return _turn["n"]


def trace_tool(harness: str, name: str, detail: str = "", shipped: bool = False) -> None:
    """One tool call. Args are shown because *which* file it reached for is
    the interesting part when comparing how harnesses explore. `shipped`
    marks a tool the harness brought rather than one we wrote — the whole
    point of the block, made visible line by line."""
    where = f"{harness} turn {_turn['n']}" if _turn["n"] else harness
    mark = f"{DIM}·shipped{OFF}" if shipped else ""
    print(f"[{where}] {name}({detail}){mark}")


def trace_reject(harness: str, why: str) -> None:
    """A tool call the harness refused before running it."""
    print(f"\033[35m↻  [{harness} turn {_turn['n']}] rejected before execution: {why}{OFF}")


def trace_state(harness: str, delta: dict) -> None:
    """Session-state changes. Only ADK surfaces these, and state IS what a
    construction kit gives you instead of a finished harness."""
    keys = ", ".join(f"{k}={str(v)[:30]}" for k, v in list(delta.items())[:3])
    print(f"{DIM}   ⚙ [{harness}] session state: {keys}{OFF}")


def trace_note(harness: str, text: str) -> None:
    """Something the harness did on its own — the kind of event you wrote
    by hand in Block 3 and are now only a spectator to."""
    print(f"\033[33m✂  [{harness} turn {_turn['n']}] {text}{OFF}")


def tool_detail(payload) -> str:
    """Render a tool's input for the trace. Bash commands are shown whole:
    the single most interesting artifact in this block is the shell command
    the model writes when a harness hands it a shell, and truncating it to
    60 characters threw that away."""
    if not isinstance(payload, dict):
        return str(payload)[:70]
    if "command" in payload:
        return str(payload["command"])
    for k in ("file_path", "path", "pattern"):
        if k in payload:
            return f"{k}={payload[k]!r}"
    return str(payload)[:70]


def trace_cost(harness: str, sent: int, out: int, cumulative: int | None = None) -> None:
    """What this turn put on the wire. Block 3's whole cost argument was
    that the transcript is re-sent every turn; here you can watch the
    `sent` number climb while the task stays the same size."""
    tail = f" · {cumulative:,} in total" if cumulative is not None else ""
    print(f"{DIM}   ┈ turn {_turn['n']}: {sent:,} in / {out:,} out{tail}{OFF}")


def trace_say(harness: str, text: str) -> None:
    """The model talking — narration mid-run, or its closing summary.
    Printed whole: truncating the one place the agent explains itself was
    never a good trade."""
    if text and text.strip():
        where = f"{harness} turn {_turn['n']}" if _turn["n"] else harness
        print(f"{SAY}❝  [{where}] {text.strip()}{OFF}")


def trace_key(harness: str, ours: list, shipped: str = "", shipped_traced: bool = False) -> None:
    """Printed once at the start of a run, so nobody has to guess what the
    markers mean — and so the tools we wrote are distinguishable from the
    ones the harness brought."""
    print(f"{DIM}   ┈ trace markers{OFF}")
    print(f"     {SAY}❝{OFF}  {DIM}the model talking{OFF}")
    print(f"     {DIM}plain lines are tool calls{OFF}")
    print(f"     {DIM}tools we wrote for this run: {', '.join(ours) if ours else 'none'}{OFF}")
    if shipped:
        print(f"     {DIM}shipped by the harness: {shipped}{OFF}")
        if shipped_traced:
            print(f"     {DIM}this SDK streams its own tool calls, so the harness's"
                  f" tools appear below too{OFF}")
        else:
            print(f"     {DIM}heads up: harness-shipped calls do NOT appear below, so this"
                  f" trace looks shorter than the work actually done{OFF}")
    print()


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
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    return f"wrote {len(content)} chars"


def ws_run_tests(workspace: Path) -> str:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=workspace, capture_output=True, text=True, timeout=120,
    )
    return proc.stdout + proc.stderr


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
    if probe.returncode == 0:
        raise SystemExit(
            f"source fixture is already solved: {source}\n"
            f"A previous run (Block 2?) fixed it in place, so measuring against "
            f"it is meaningless. Reset first, from block4_production_harnesses/:\n"
            f"  uv run ../scripts/reset.py && uv run ../scripts/check_fixtures.py"
        )

    run_dir = BLOCK4 / "runs" / harness
    workspace = run_dir / "workspace"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    shutil.copytree(source, workspace)
    return workspace


def verify(harness: str, workspace: Path, started: float) -> int:
    """Pytest is the judge. Returns a process exit code."""
    wall = time.monotonic() - started
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=workspace, capture_output=True, text=True, timeout=120,
    )
    summary = (proc.stdout.strip().splitlines() or ["(no output)"])[-1]
    verdict = "SOLVED" if proc.returncode == 0 else "NOT SOLVED"
    print(f"\n--- {harness}: {verdict} | wall={wall:.1f}s | {summary}")
    return 0 if proc.returncode == 0 else 1


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

    The six scripts produce nearly identical RESULTS on purpose — the
    outcome is the controlled variable. What differs is everything on this
    receipt, which is why it prints after every run and accumulates: by
    your last run, the table IS the comparison.
    """
    import json

    task_name = _os.environ.get("BLOCK4_TASK", "bug_hunt")
    row = {
        "harness": harness,
        "task": task_name,
        "solved": solved,
        "wall_s": round(time.monotonic() - started, 1),
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

    latest: dict = {}
    with receipts.open() as fh:
        for line in fh:
            r = json.loads(line)
            # rows recorded before task tracking existed show as "?"
            latest[(r.get("harness") or r["specimen"], r.get("task", "?"))] = r

    from rich.console import Console
    from rich.table import Table

    table = Table(
        title="Harness receipts — same model throughout; per-row task in column 2; the rest is the harness",
        title_style="bold",
    )
    for col in ("harness", "task", "wall s", "loop", "tools we wrote", "harness shipped", "provider friction", "lines"):
        table.add_column(col, overflow="fold")
    for r in latest.values():
        table.add_row(
            (r.get("harness") or r["specimen"]) + ("" if r["solved"] else " ✗"),
            r.get("task", "?"),
            str(r["wall_s"]),
            r["loop_owner"],
            r["tools_we_wrote"],
            r["tools_harness_shipped"],
            r["provider_friction"],
            str(r["code_lines"]),
        )
    print(f"this run's task: {task_name}")
    Console().print(table)
    print(
        "where these cells come from — measured this run: wall s, solved, task, lines · "
        "authored facts from the build record (hardcoded in each script's "
        "receipt() call; verify against its run.py): loop, tools, shipped, friction"
    )
    remaining = 6 - sum(1 for (_, t) in latest if t == task_name)
    if remaining > 0:
        print(f"({remaining} harness(es) left on {task_name} — each adds a row)")
