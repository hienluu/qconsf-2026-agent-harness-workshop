"""Shared plumbing for the Block 4 specimens.

Every specimen runs the SAME task — fix the off-by-one in stats.py from
Block 2 — against a fresh copy of the workspace, and is judged the same
way: pytest afterward, never the agent's self-report. What varies is the
harness driving the run; the specimen scripts exist to be read side by
side.
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

# Round two: BLOCK4_TASK=bug_hunt reruns any specimen against the medium
# task (3 interacting bugs, ~8-15 turns) — enough work that harness
# character (planning, batching, todos) has room to show.
import os as _os

if _os.environ.get("BLOCK4_TASK") == "bug_hunt":
    FIX_BUG_SOURCE = BUG_HUNT_SOURCE
    TASK = ("Several tests fail. Diagnose and fix all the bugs until every "
            "test passes. Do not modify the tests.")
    TASK_MAX_TURNS = 24  # medium task: diagnosis across 8 modules
else:
    TASK = "One test fails. Find the bug and fix it. Do not modify the tests."
    TASK_MAX_TURNS = 12
REFACTOR_TASK = (
    "Migrate the source code to the v2 API following MIGRATION.md until all "
    "tests pass. Do not modify the tests."
)


def ws_list(workspace: Path) -> str:
    """Relative paths of every file in the workspace."""
    return "\n".join(
        str(p.relative_to(workspace))
        for p in sorted(workspace.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts and ".pytest_cache" not in p.parts
    )


def ws_read(workspace: Path, path: str) -> str:
    """Read a file; errors come back as messages the model can act on,
    never exceptions — some harnesses (ADK) crash the whole run on a
    raised tool error, which is the h2 lesson in reverse."""
    target = workspace / path
    if target.is_dir():
        return f"error: {path!r} is a directory, not a file. Files:\n{ws_list(workspace)}"
    if not target.is_file():
        return f"error: {path!r} not found. Files:\n{ws_list(workspace)}"
    return target.read_text()


def ws_write(workspace: Path, path: str, content: str) -> str:
    target = workspace / path
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


def prepare_workspace(specimen: str, source: Path = FIX_BUG_SOURCE) -> Path:
    """Fresh copy of a task workspace under runs/<specimen>/."""
    run_dir = BLOCK4 / "runs" / specimen
    workspace = run_dir / "workspace"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    shutil.copytree(source, workspace)
    return workspace


def verify(specimen: str, workspace: Path, started: float) -> int:
    """Pytest is the judge. Returns a process exit code."""
    wall = time.monotonic() - started
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=workspace, capture_output=True, text=True, timeout=120,
    )
    summary = (proc.stdout.strip().splitlines() or ["(no output)"])[-1]
    verdict = "SOLVED" if proc.returncode == 0 else "NOT SOLVED"
    print(f"\n--- {specimen}: {verdict} | wall={wall:.1f}s | {summary}")
    return 0 if proc.returncode == 0 else 1


def receipt(
    specimen: str,
    *,
    script: str,
    started: float,
    solved: bool,
    pedigree: str,
    loop_owner: str,
    tools_we_wrote: list,
    tools_harness_shipped: str,
    provider_friction: str,
) -> None:
    """Print this run's harness receipt and the comparison table so far.

    The six specimens produce nearly identical RESULTS on purpose — the
    outcome is the controlled variable. What differs is everything on this
    receipt, which is why it prints after every run and accumulates: by
    your last specimen, the table IS the comparison.
    """
    import json

    task_name = _os.environ.get("BLOCK4_TASK", "fix_bug")
    row = {
        "specimen": specimen,
        "task": task_name,
        "solved": solved,
        "wall_s": round(time.monotonic() - started, 1),
        "pedigree": pedigree,
        "loop_owner": loop_owner,
        "tools_we_wrote": f"{len(tools_we_wrote)} ({', '.join(tools_we_wrote) or '—'})",
        "tools_harness_shipped": tools_harness_shipped,
        "provider_friction": provider_friction,
        "code_lines": Path(script).read_text().count("\n") + 1,
        "timestamp": time.time(),
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
            latest[(r["specimen"], r.get("task", "?"))] = r

    from rich.console import Console
    from rich.table import Table

    table = Table(
        title="Harness receipts — same model throughout; per-row task in column 2; the rest is the harness",
        title_style="bold",
    )
    for col in ("specimen", "task", "wall s", "loop", "tools we wrote", "harness shipped", "provider friction", "lines"):
        table.add_column(col, overflow="fold")
    for r in latest.values():
        table.add_row(
            r["specimen"] + ("" if r["solved"] else " ✗"),
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
        "provenance — measured this run: wall s, solved, task, lines · "
        "authored facts from the build record (hardcoded in each specimen's "
        "receipt() call; verify against its run.py): loop, tools, shipped, friction"
    )
    remaining = 6 - sum(1 for (_, t) in latest if t == task_name)
    if remaining > 0:
        print(f"({remaining} specimen(s) left on {task_name} — each adds a row)")
