"""One command for workshop morning and dry runs: is everything ready?

    uv run scripts/preflight.py

Runs two independent checks and prints one verdict:

  1. fixtures  -- check_fixtures.py: task workspaces unsolved, references green.
                  Offline and free; a failure means the repo needs fixing.
  2. LLM       -- test_llm.py: one small request to the provider in .env.
                  Costs a fraction of a cent; a failure means .env, the
                  network or the provider needs attention, not the repo.

Both always run, so one failure doesn't hide the other. Use the individual
scripts when you only need one (check_fixtures.py before a commit, for
example, needs no API key).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_fixtures  # noqa: E402
import test_llm  # noqa: E402


def run(label: str, fn) -> bool:
    print(f"=== {label} " + "=" * (60 - len(label)))
    try:
        ok = fn() == 0
    except Exception as exc:  # a crash in one check shouldn't skip the other
        print(f"CRASHED: {type(exc).__name__}: {exc}", file=sys.stderr)
        ok = False
    print()
    return ok


def llm_check() -> int:
    # test_llm parses sys.argv; give it none of ours so it uses its defaults.
    sys.argv = [test_llm.__file__]
    return test_llm.main()


def main() -> int:
    results = {
        "fixtures": run("fixtures", check_fixtures.main),
        "LLM connection": run("LLM connection", llm_check),
    }

    print("=== preflight " + "=" * 50)
    for name, ok in results.items():
        print(f"  [{'ok  ' if ok else 'FAIL'}] {name}")
    if all(results.values()):
        print("\nREADY: fixtures are clean and the model answers.")
        return 0
    print("\nNOT READY: see the failing section above.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
