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
import importlib
import json
import shutil
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
BLOCK3 = HERE.parent
REPO = BLOCK3.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(BLOCK3 / "harnesses"))

from tasks import TASKS  # noqa: E402

HARNESSES = {"h1": "h1_naive", "h2": "h2_managed", "h3": "h3_full"}


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


def run_one(harness_key: str, task_name: str, out_dir: Path) -> dict:
    module = importlib.import_module(HARNESSES[harness_key])
    task = TASKS[task_name]

    run_dir = out_dir / "runs" / f"{HARNESSES[harness_key]}__{task_name}"
    workspace = run_dir / "workspace"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    shutil.copytree(REPO / task["workspace"], workspace)

    print(f"\n=== {HARNESSES[harness_key]} × {task_name} ===")
    print(f"    task: {task['description']}")
    result = module.run(str(workspace), task["prompt"])

    tests_green, pytest_summary = check_tests(workspace)
    row = asdict(result)
    row.update(
        task=task_name,
        tests_green=tests_green,
        pytest_summary=pytest_summary,
        model=__import__("os").environ.get("MODEL", ""),
        timestamp=time.time(),
    )
    verdict = "SOLVED" if tests_green else f"NOT SOLVED ({result.status})"
    print(
        f"--- {verdict} | turns={result.turns} "
        f"tokens={result.input_tokens}+{result.output_tokens} "
        f"wall={result.wall_seconds}s | {pytest_summary}"
    )
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

    for harness_key in keys:
        for task_name in task_names:
            row = run_one(harness_key, task_name, out_dir)
            with results_file.open("a") as fh:
                fh.write(json.dumps(row) + "\n")

    print(f"\nresults appended to {results_file}")
    print("render the comparison table:  uv run eval/compare.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
