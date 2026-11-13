"""Run harnesses against the task suite and record what actually happened.

    uv run eval/run_eval.py h1                       # one harness, all tasks
    uv run eval/run_eval.py h1 h2 h3 --task refactor_v2
    uv run eval/run_eval.py all --task fix_bug

Each (harness, task) run gets a fresh COPY of the pristine workspace under
results/runs/, so runs never contaminate each other or the repo, and the
wreckage of failed runs is preserved for inspection. Success is judged by
pytest on the resulting workspace — never by the agent's self-report.

Results append to results/results.jsonl; render with eval/compare.py.
"""

import argparse
import contextlib
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path


class Tee:
    """Write harness output to the terminal AND a per-run log file, so
    'why did this run cost what it cost' stays answerable afterward. The
    file gets plain text, without color codes, so grep works on it."""

    ANSI = re.compile(r"\x1b\[[0-9;]*m")

    def __init__(self, terminal, log):
        self.terminal, self.log = terminal, log

    def write(self, text):
        self.terminal.write(text)
        self.log.write(self.ANSI.sub("", text))
        return len(text)

    def flush(self):
        self.terminal.flush()
        self.log.flush()

HERE = Path(__file__).resolve().parent
BLOCK3 = HERE.parent
REPO = BLOCK3.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(BLOCK3 / "harnesses"))

from tasks import TASKS  # noqa: E402
import base  # noqa: E402  (the harnesses' shared helpers: habits_line)
from tools import print_run_header  # noqa: E402  (Block 2's, so both blocks open a run alike)

sys.path.insert(0, str(REPO / "scripts"))
from reference_check import summary_line  # noqa: E402

HARNESSES = {"h1": "h1_naive", "h2": "h2_managed", "h3": "h3_full"}


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
        "temperature": base.sampling().get("temperature", "provider default"),
        "repo_commit": commit,
    }

def check_tests(workspace: Path) -> tuple[bool, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=180,
    )
    summary = (proc.stdout.strip().splitlines() or ["(no output)"])[-1]
    return proc.returncode == 0, summary


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


def run_one(harness_key: str, task_name: str, out_dir: Path) -> dict:
    module = importlib.import_module(HARNESSES[harness_key])
    task = TASKS[task_name]

    # Pre-flight: the source workspace must be in its unsolved state, or the
    # "measurement" is a no-op against an already-finished task. This
    # happens in practice: a Block 2 run migrates the workspace in place.
    source = REPO / task["workspace"]
    already_green, _ = check_tests(source)
    changed = changed_files(source)
    if already_green or changed:
        what = "already solved" if already_green else f"edited ({len(changed)} file(s) differ from git)"
        raise SystemExit(
            f"source workspace is {what}: {task['workspace']}\n"
            f"A previous run (Block 2?) modified it in place, so this run would\n"
            f"start with a head start. Reset it first:\n"
            f"  uv run ../scripts/reset.py && uv run ../scripts/check_fixtures.py"
        )

    # Use the module's own NAME — h3 renames itself under ablation, and its
    # artifacts must not overwrite the unmodified run's.
    label = getattr(module, "NAME", HARNESSES[harness_key])

    # Unique per run: repeated runs of a cell must not clobber each other's
    # traces — during the ablation we lost 4 of 6 console logs that way.
    stamp = time.strftime("%H%M%S")
    run_dir = out_dir / "runs" / f"{label}__{task_name}__{stamp}"
    workspace = run_dir / "workspace"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    shutil.copytree(source, workspace)
    log_path = run_dir / "console.log"
    base.reset_habits()
    with log_path.open("w") as log, contextlib.redirect_stdout(Tee(sys.stdout, log)):
        # The header goes in the saved trace too: which endpoint and model
        # produced a run is the first thing to know when comparing runs.
        rows = [("harness", (module.__doc__ or "").strip().splitlines()[0])]
        if label != HARNESSES[harness_key]:
            rows.append(("variant", f"running {HARNESSES[harness_key]} with an option changed, recorded as {label}"))
        rows += [("task", task["description"]),
                 ("workspace", workspace.relative_to(BLOCK3)),
                 ("provider", os.environ.get("PROVIDER_BASE_URL", "(PROVIDER_BASE_URL not set)")),
                 ("model", os.environ.get("MODEL", "(MODEL not set)"))]
        print_run_header(f"{label} × {task_name}", rows)
        result = module.run(str(workspace), task["prompt"])
    print(f"    trace saved: {log_path.relative_to(BLOCK3)}")

    tests_green, pytest_summary = check_tests(workspace)
    row = asdict(result)

    # If the harness kept durable notes, persist them as a readable run
    # artifact (and keep the bulky text out of the score table).
    notes_text = row.get("notes", {}).pop("final_notes_text", None)
    if notes_text is not None:
        notes_path = run_dir / "agent_notes.md"
        if notes_text.strip() == "(empty)":
            # The pinned notes still hold h3's starting placeholder. Say what
            # that means, so an empty file doesn't read as a broken run.
            notes_text = ("The agent never called update_notes in this run: the notes "
                          "stayed empty.\nh3 offers the tool; using it is the model's call.")
            print(f"    agent notes: none, the agent never called update_notes "
                  f"({notes_path.relative_to(BLOCK3)})")
        else:
            print(f"    agent notes saved: {notes_path.relative_to(BLOCK3)}")
        notes_path.write_text(notes_text + "\n")
    row.update(
        task=task_name,
        tests_green=tests_green,
        pytest_summary=pytest_summary,
        timestamp=time.time(),
        **run_context(),
    )
    if result.status == "crashed":
        # Say why, plainly. The usual ending (habits, the reference check)
        # describes work the agent never got to do.
        ending = (f"--- CRASHED on turn {result.turns} | tokens={result.input_tokens}+"
                  f"{result.output_tokens} wall={result.wall_seconds}s\n"
                  + "\n".join(f"    {line}" for line in base.explain_crash(result.error, result.turns)))
        print(f"\033[31m{ending}\033[0m")
    else:
        verdict = "SOLVED" if tests_green else f"NOT SOLVED ({result.status})"
        ending = (f"--- {verdict} | turns={result.turns} "
                  f"tokens={result.input_tokens}+{result.output_tokens} "
                  f"wall={result.wall_seconds}s | {pytest_summary}\n{base.habits_line(result.turns)}")
        if task_name == "refactor_v2":   # a rename has one right answer: compare it
            ending += "\n" + summary_line(workspace)
        print(ending)
    with log_path.open("a") as log:   # the saved trace ends the way the screen does
        log.write(ending + "\n")
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure harnesses against the task suite.")
    parser.add_argument("harnesses", nargs="+", choices=[*HARNESSES, "all"],
                        help="which harness(es) to run: h1 h2 h3, or all")
    parser.add_argument("--task", action="append", choices=list(TASKS),
                        help="limit to specific task(s); default: all four")
    args = parser.parse_args()

    keys = list(HARNESSES) if "all" in args.harnesses else list(dict.fromkeys(args.harnesses))
    task_names = args.task or list(TASKS)

    out_dir = BLOCK3 / "results"
    out_dir.mkdir(exist_ok=True)
    results_file = out_dir / "results.jsonl"

    # A run with a fault injected or the compaction budget changed is a demo,
    # not a measurement: it isn't the harness as defined. Keep it out of the
    # results, or it would replace a real run in the comparison table.
    demo = [v for v in ("INJECT_MALFORMED_TURN", "TRANSCRIPT_CHAR_BUDGET") if os.environ.get(v)]

    for harness_key in keys:
        for task_name in task_names:
            row = run_one(harness_key, task_name, out_dir)
            if not demo:
                with results_file.open("a") as fh:
                    fh.write(json.dumps(row) + "\n")
            if row["status"] == "crashed" and row["turns"] == 0:
                # The first model call failed: every run left would fail the
                # same way, so stop here instead of crashing the rest.
                print("\033[31mstopping: fix the setup above, then run it again\033[0m")
                return 1

    if demo:
        print(f"\ndemo run ({', '.join(demo)} set): not recorded, so it can't replace a "
              f"real run in the comparison table")
        return 0
    print(f"\nresults appended to {results_file}")
    import compare

    compare.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
