"""Run all five Block 4 scripts at once, then print the tables.

    uv run run_all.py        (from block4_production_harnesses/)

One after another, the five take 12 minutes or more on the migration; side
by side, as long as the slowest (usually 4 to 6 minutes). Each script
still works on its own copy of the task, with the same model and turn
cap. Its full trace goes to runs/logs/<script>.log: open one in another
terminal (`tail -f runs/logs/deepagents.log`) to watch a harness work.

While they run, a status line per script shows its latest turn. Pass
script names to run only some:  uv run run_all.py pydantic_ai google_adk
"""

import os
import re
import subprocess
import sys
import time
from pathlib import Path

BLOCK4 = Path(__file__).resolve().parent
SCRIPTS = {
    "google_adk": "google_adk/run.py",
    "pydantic_ai": "pydantic_ai/run.py",
    "claude_agent_sdk": "claude_agent_sdk/run.py",
    "openai_agents": "openai_agents/run.py",
    "deepagents": "deepagents/run.py",
}
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def status(log: Path) -> str:
    text = ANSI.sub("", log.read_text(errors="replace")) if log.exists() else ""
    verdict = re.search(r"^--- \S+: (SOLVED|NOT SOLVED)", text, re.M)
    if verdict:
        return verdict.group(1)
    if "source fixture is" in text:
        return "REFUSED: the task needs a reset (see its log)"
    turns = re.findall(r"turn (\d+)[\]:]", text)
    return f"turn {turns[-1]}" if turns else "starting"


def main() -> int:
    sys.path.insert(0, str(BLOCK4))
    import common  # noqa: E402  (task, cap, table printing)

    names = sys.argv[1:] or list(SCRIPTS)
    unknown = [n for n in names if n not in SCRIPTS]
    if unknown:
        raise SystemExit(f"unknown script(s): {', '.join(unknown)}; choose from {', '.join(SCRIPTS)}")

    logs = BLOCK4 / "runs" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    print(f"task: {common.BLOCK4_TASK} · turn cap: {common.TASK_MAX_TURNS} model calls per harness · "
          f"traces in runs/logs/\n")
    procs = {}
    for name in names:
        log = logs / f"{name}.log"
        procs[name] = (subprocess.Popen([sys.executable, SCRIPTS[name]], cwd=BLOCK4,
                                         stdout=log.open("w"), stderr=subprocess.STDOUT,
                                         env={**os.environ, "PYTHONUNBUFFERED": "1",
                                              "BLOCK4_LOGGED": "1"}),   # we capture it here
                       log, time.monotonic())
        time.sleep(1)   # stagger the starts a little

    tty = sys.stdout.isatty()
    shown = 0
    done: dict = {}
    while len(done) < len(procs):
        lines = []
        for name, (proc, log, started) in procs.items():
            if name not in done and proc.poll() is not None:
                done[name] = time.monotonic() - started
            secs = done.get(name, time.monotonic() - started)
            lines.append(f"  {name:<18}{int(secs) // 60:>2}:{int(secs) % 60:02d}  {status(log)}")
        if tty and shown:
            print(f"\033[{shown}A", end="")          # redraw in place
        if tty or len(done) == len(procs):
            print("\n".join(f"{line}\033[K" if tty else line for line in lines), flush=True)
            shown = len(lines)
        time.sleep(2)

    common.print_tables(common.BLOCK4_TASK, quiet_progress=True)
    return 0 if all(p.returncode == 0 for p, _, _ in procs.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
