"""Play-by-play commentary for a harness run — for you, not for the agent.

Everything here is observer-side. It reads the conversation and the API's
usage numbers and prints a scoreboard; it never changes what the model
sees, what tools exist, or how the loop behaves. The harness stays as
naive as it was.

What it shows you that the agent cannot see:

  - how much of the turn budget is gone
  - how large the transcript has grown, and therefore how much is being
    re-sent on every single call
  - how many tokens the run has cost so far
  - whether it has verified anything yet

The agent has none of this. Watching a run with the scoreboard on is the
fastest way to understand why: it is flying with no fuel gauge, no map,
and no memory of the ground it already covered.
"""


class Scoreboard:
    def __init__(self, max_turns: int):
        self.max_turns = max_turns
        self.counts: dict = {}
        self.paths_read: dict = {}
        self.input_tokens = 0
        self.output_tokens = 0
        self.first_write_turn = None
        self.last_turn = 0
        self.said = set()

    def legend(self) -> None:
        print(
            "\033[2m   ┈ scoreboard legend\n"
            "     read/write/search/tests — how many times the agent has called each\n"
            "       tool so far, cumulative.\n"
            "     transcript — the whole conversation so far: your task, every message\n"
            "       the model produced, and every tool result it got back (all the file\n"
            "       contents, search hits, and test output). It is the agent's only\n"
            "       memory, AND it is re-sent to the model on every single turn.\n"
            "     sent so far — tokens billed, input vs output. Input climbs far faster\n"
            "       than the transcript grows, because each turn re-sends all of it.\n"
            "     re-read — files fetched again that the agent had already read. Appears\n"
            "       only when it happens; it is the price of information the agent no\n"
            "       longer has.\n"
            "     The agent sees none of these numbers.\033[0m\n"
        )

    # --- recording (called by the harness as it runs) --------------------

    def record_usage(self, response) -> None:
        usage = getattr(response, "usage", None)
        if usage:
            self.input_tokens += getattr(usage, "prompt_tokens", 0) or 0
            self.output_tokens += getattr(usage, "completion_tokens", 0) or 0

    def record_tool(self, name: str, turn: int, args: dict | None = None) -> None:
        self.counts[name] = self.counts.get(name, 0) + 1
        if name == "write_file" and self.first_write_turn is None:
            self.first_write_turn = turn
        # Re-reads are the cost of forgetting: a file the agent already had
        # in context, fetched again because that context is gone.
        if name == "read_file" and args and args.get("path"):
            path = args["path"]
            self.paths_read[path] = self.paths_read.get(path, 0) + 1

    @property
    def rereads(self) -> int:
        return sum(n - 1 for n in self.paths_read.values() if n > 1)

    # --- commentary ------------------------------------------------------

    def report(self, turn: int, messages: list) -> None:
        self.last_turn = turn
        chars = sum(len(m.get("content") or "") for m in messages if isinstance(m, dict))
        tally = "  ".join(
            f"{n.replace('_file', '').replace('run_', '')} {self.counts.get(n, 0)}"
            for n in ("read_file", "write_file", "search", "run_tests")
        )
        if self.rereads:
            tally += f"  \033[35mre-read {self.rereads}\033[0m\033[2m"
        print(
            f"\033[2m   ┈ turn {turn}/{self.max_turns} │ {tally} │ "
            f"transcript {chars:,} chars (~{chars // 4:,} tokens) │ "
            f"sent so far {self.input_tokens:,} in / {self.output_tokens:,} out\033[0m"
        )

        for key, condition, line in [
            ("first_write", self.first_write_turn == turn,
             f"first edit — {turn - 1} turns went to reading before anything changed"),
            ("big", chars > 150_000,
             "transcript past 150k chars — every remaining turn re-sends all of it"),
            ("low_budget", turn == self.max_turns - 4,
             f"{self.max_turns - turn} turns left, and nothing is tracking how much work remains"),
        ]:
            if condition and key not in self.said:
                self.said.add(key)
                print(f"\033[33m   ▸ {line}\033[0m")

        # One blank line per turn: long runs are much easier to scan when the
        # turn boundary is visible, and this line IS the end of a turn.
        print()

    def summary(self, finished: bool, turn: int | None = None, workspace=None) -> None:
        turns = turn or self.last_turn
        print(
            f"\n   ── run over after {turns} turns: {sum(self.counts.values())} tool calls, "
            f"{self.input_tokens:,} input tokens sent "
            f"(the whole transcript went over the wire on every one of them)."
        )
        if self.rereads:
            print(f"   ── it re-read {self.rereads} file(s) it had already seen: "
                  f"information it had, then didn't.")
        if not self.counts.get("run_tests"):
            print("   ── it never ran the tests. It had the tool the whole time.")
        elif not finished:
            # Judge by running the tests, never by whether the agent SAID it was
            # done. A run can finish the work on its last turn and run out of
            # budget before it reads the result: that's a different story from
            # a run that ran out mid-job, and the old message told both as one.
            last = ""
            if workspace is not None:
                last = (workspace.run_tests().strip().splitlines() or [""])[-1]
            green = "passed" in last and "failed" not in last and "error" not in last
            if workspace is None:
                print("   ── it ran out of turns before saying it was done.")
            elif green:
                print(f"   ── it ran out of turns before saying it was done, but the work was "
                      f"finished: the tests pass ({last}). It just never got to tell you.")
            else:
                print(f"   ── it ran out of turns with the job unfinished: {last}.")
