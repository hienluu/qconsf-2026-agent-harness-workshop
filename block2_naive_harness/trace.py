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
        self.input_tokens = 0
        self.output_tokens = 0
        self.first_write_turn = None
        self.last_turn = 0
        self.said = set()

    def legend(self) -> None:
        print(
            "\033[2m   ┈ scoreboard: read/write/search/tests = how many times the agent has\n"
            "     called each tool so far · transcript = the size of the conversation,\n"
            "     which is re-sent to the model on every turn · sent = tokens billed,\n"
            "     input vs output. The agent sees none of these numbers.\033[0m\n"
        )

    # --- recording (called by the harness as it runs) --------------------

    def record_usage(self, response) -> None:
        usage = getattr(response, "usage", None)
        if usage:
            self.input_tokens += getattr(usage, "prompt_tokens", 0) or 0
            self.output_tokens += getattr(usage, "completion_tokens", 0) or 0

    def record_tool(self, name: str, turn: int) -> None:
        self.counts[name] = self.counts.get(name, 0) + 1
        if name == "write_file" and self.first_write_turn is None:
            self.first_write_turn = turn

    # --- commentary ------------------------------------------------------

    def report(self, turn: int, messages: list) -> None:
        self.last_turn = turn
        chars = sum(len(m.get("content") or "") for m in messages if isinstance(m, dict))
        tally = "  ".join(
            f"{n.replace('_file', '').replace('run_', '')} {self.counts.get(n, 0)}"
            for n in ("read_file", "write_file", "search", "run_tests")
        )
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

    def summary(self, finished: bool, turn: int | None = None) -> None:
        turns = turn or self.last_turn
        print(
            f"\n   ── run over after {turns} turns: {sum(self.counts.values())} tool calls, "
            f"{self.input_tokens:,} input tokens sent "
            f"(the whole transcript went over the wire on every one of them)."
        )
        if not self.counts.get("run_tests"):
            print("   ── it never ran the tests. It had the tool the whole time.")
        elif not finished:
            print("   ── it ran the tests but never got them green inside the budget.")
