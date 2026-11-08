"""Play-by-play commentary for a harness run — for you, not for the agent.

Everything here is observer-side. It reads the conversation and the API's
usage numbers and prints a scoreboard; it never changes what the model
sees, what tools exist, or how the loop behaves. The harness stays as
naive as it was.

What it shows you that the agent cannot see:

  - how much of the turn budget is gone
  - how large the conversation has grown, and therefore how much is being
    re-sent on every single call
  - how many tokens the run has cost so far
  - whether it has verified anything yet

The agent has none of this. Watching a run with the scoreboard on is the
fastest way to understand why: it is flying with no fuel gauge, no map,
and no memory of the ground it already covered.
"""


def transcript_chars(messages: list) -> int:
    """Everything in the conversation that gets re-sent each turn: message
    text, plus the arguments of every tool call. The arguments matter: when
    the agent writes a file, the whole file is in them, not in `content`."""
    total = 0
    for m in messages:
        if not isinstance(m, dict):
            continue
        total += len(m.get("content") or "")
        for call in m.get("tool_calls") or []:
            total += len((call.get("function") or {}).get("arguments") or "")
    return total

class Scoreboard:
    def __init__(self, max_turns: int):
        self.max_turns = max_turns
        self.counts: dict = {}
        self.paths_read: dict = {}
        self.input_tokens = 0
        self.output_tokens = 0
        self.first_write_turn = None
        self.last_turn = 0
        self.last_chars = 0
        self.cached_tokens = 0
        self.turns: list = []  # one dict per model call, for the turn-by-turn table
        self._counts_at_last_report: dict = {}
        self.cache_reported = False
        self.said = set()

    def legend(self) -> None:
        print(
            "\033[2m   ┈ scoreboard legend\n"
            "     read/write/search/tests — how many times the agent has called each\n"
            "       tool so far, cumulative.\n"
            "     conversation — everything so far: your task, every message\n"
            "       the model produced (including the full text of every file it wrote),\n"
            "       and every tool result it got back (file contents, search hits, test\n"
            "       output). It is the agent's only memory, AND it is re-sent to the\n"
            "       model on every single turn.\n"
            "     sent so far — tokens billed, input vs output. Input climbs far faster\n"
            "       than the conversation grows, because each turn re-sends all of it.\n"
            "     re-read — files fetched again that the agent had already read. Appears\n"
            "       only when it happens. Nothing was dropped: the first copy is still in\n"
            "       the conversation, so every re-read pays for the same file twice.\n"
            "     The agent sees none of these numbers.\033[0m\n"
        )

    # --- recording (called by the harness as it runs) --------------------

    def record_usage(self, response) -> None:
        usage = getattr(response, "usage", None)
        if usage:
            self.input_tokens += getattr(usage, "prompt_tokens", 0) or 0
            self.output_tokens += getattr(usage, "completion_tokens", 0) or 0
            # Prompt caching: how much of the re-sent input the provider served
            # from its cache. Only some providers report it.
            details = getattr(usage, "prompt_tokens_details", None)
            cached = getattr(details, "cached_tokens", None) if details else None
            if cached is not None:
                self.cache_reported = True
                self.cached_tokens += cached
            choices = getattr(response, "choices", None) or []
            says = (choices[0].message.content or "").strip() if choices else ""
            self.turns.append({
                "sent": getattr(usage, "prompt_tokens", 0) or 0,
                "cached": cached or 0,
                "says": says,
                "did": "",
                "conversation": None,
            })

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
        chars = transcript_chars(messages)
        self.last_chars = chars
        if not hasattr(self, "_chars_before"):
            # Turn 1 starts from the system prompt and the task: everything
            # before the model's first message.
            first_reply = next((i for i, m in enumerate(messages)
                                if isinstance(m, dict) and m.get("role") == "assistant"), 0)
            self._chars_before = transcript_chars(messages[:first_reply])
        if self.turns and self.turns[-1]["conversation"] is None:
            done = {n: self.counts.get(n, 0) - self._counts_at_last_report.get(n, 0)
                    for n in ("list_files", "read_file", "write_file", "search", "run_tests")}
            self.turns[-1]["did"] = " ".join(
                f"{n.replace('_files', '').replace('_file', '').replace('run_', '')} {k}" for n, k in done.items() if k)
            self.turns[-1]["conversation"] = chars // 4
            # Can be negative: a harness that drops old output (Block 3's h2)
            # shrinks the conversation, and this column shows it.
            self.turns[-1]["added"] = (chars - self._chars_before) // 4
            self._chars_before = chars
            self.turns[-1]["turn"] = turn
            self._counts_at_last_report = dict(self.counts)
        tally = "  ".join(
            f"{n.replace('_file', '').replace('run_', '')} {self.counts.get(n, 0)}"
            for n in ("read_file", "write_file", "search", "run_tests")
        )
        if self.rereads:
            tally += f"  \033[35mre-read {self.rereads}\033[0m\033[2m"
        print(
            f"\033[2m   ┈ turn {turn}/{self.max_turns} │ {tally} │ "
            f"conversation {chars:,} chars (~{chars // 4:,} tokens) │ "
            f"sent so far {self.input_tokens:,} in / {self.output_tokens:,} out\033[0m"
        )

        for key, condition, line in [
            ("first_write", self.first_write_turn == turn,
             f"first edit — {turn - 1} turns went to reading before anything changed"),
            ("big", chars > 150_000,
             "conversation past 150k chars — every remaining turn re-sends all of it"),
            ("low_budget", turn == self.max_turns - 4,
             f"{self.max_turns - turn} turns left, and nothing is tracking how much work remains"),
        ]:
            if condition and key not in self.said:
                self.said.add(key)
                print(f"\033[33m   ▸ {line}\033[0m")

        # One blank line per turn: long runs are much easier to scan when the
        # turn boundary is visible, and this line IS the end of a turn.
        print()

    def turn_table(self) -> None:
        """One row per turn: what the agent did, how big the conversation was
        afterwards, and what that turn's call sent. Every call re-sends the
        whole conversation, so the bars only grow, unless a harness drops
        something (Block 3's h2)."""
        if not self.turns:
            return
        last_turn = 0
        for row in self.turns:
            if row["conversation"] is None:  # the final call: nothing reported after it
                row["turn"] = last_turn + 1
                row["did"] = row["did"] or "none (finished)"
                row["conversation"] = self.last_chars // 4 + len(row["says"]) // 4
                row["added"] = len(row["says"]) // 4
            last_turn = row["turn"]
        self.final_conversation = self.turns[-1]["conversation"]
        top = max(r["sent"] for r in self.turns) or 1
        show_cache = self.cache_reported
        # Columns run in the order things happen: what the call sent, what
        # the model did with it, and what the conversation grew to.
        head = f"   {'turn':>4}  {'sent to model':>13}"
        if show_cache:
            head += f"{'cached':>8}"
        head += f"  {'':<20}  {'tool calls':<17}{'added':>9}"
        # What the agent said goes in a last column sized to the terminal. On a
        # window too narrow for a useful column, it goes under the row instead.
        import shutil
        room = shutil.get_terminal_size((120, 20)).columns - len(head) - 3
        says_column = room >= 20
        if says_column:
            head += "   agent says"
        width = len(head) + (room - len("agent says") if says_column else 0)
        print("\n\033[1m── turn by turn " + "─" * max(0, width - 16) + "\033[0m")
        print(head)
        print("   " + "─" * (width - 3))
        for r in self.turns:
            line = f"   {r['turn']:>4}  {r['sent']:>13,}"
            if show_cache:
                pct = f"{round(100 * r['cached'] / r['sent'])}%" if r["cached"] and r["sent"] else "–"
                line += f"{pct:>8}"
            bar = "█" * max(1, round(20 * r["sent"] / top))
            line += f"  {bar:<20}  {r['did']:<17}{r['added']:>+9,}"
            said = " ".join(r["says"].split())
            if said and says_column:
                said = said if len(said) <= room else said[: room - 1] + "…"
                line += f"   \033[32m{said}\033[0m"
            print(line)
            if said and not says_column:
                said = said if len(said) <= 100 else said[:99] + "…"
                print(f"\033[32m         ❝ {said}\033[0m")
        total = sum(r["sent"] for r in self.turns)
        line = f"   {'total':>4}  {total:>13,}"
        if show_cache:
            cached = sum(r["cached"] for r in self.turns)
            line += f"{(str(round(100 * cached / total)) + '%') if cached and total else '–':>8}"
        calls = sum(self.counts.values())
        line += f"  {'':<20}  {str(calls) + (' call' if calls == 1 else ' calls'):<17}"
        print("   " + "─" * (width - 3))
        print(line)
        print("\033[2m   sent to model: what the call cost to send, as billed: the whole conversation so far,\n"
              "     plus the tool definitions that go out with every call.\n"
              "   added: what the turn added to the conversation: the model's reply (its words and tool\n"
              "     calls) plus the tool results (≈, characters ÷ 4). On the last turn that's just its\n"
              "     closing message. Every later turn pays to send it again. A negative number\n"
              "     means the harness dropped something from the conversation.\033[0m")

    def summary(self, finished: bool, turn: int | None = None, workspace=None) -> None:
        self.turn_table()
        # The table counts the final call too; harnesses that don't pass `turn`
        # (Block 3's) would otherwise report the last turn that used a tool.
        turns = turn or (self.turns[-1]["turn"] if self.turns else self.last_turn)
        rows = []

        # How it ended. Judge by running the tests, never by whether the agent
        # SAID it was done: a run can finish the work on its last turn and run
        # out of budget before it reads the result.
        ended = f"turn {turns} of {self.max_turns}, "
        if finished:
            ended += "the agent said it was done"
        elif workspace is None:
            ended += "out of turns before saying it was done"
        else:
            last = (workspace.run_tests().strip().splitlines() or [""])[-1]
            green = "passed" in last and "failed" not in last and "error" not in last
            if green:
                ended += (f"out of turns, but the work was finished: the tests pass "
                          f"({last}). It never got to tell you")
            else:
                ended += f"out of turns with the job unfinished ({last})"
        rows.append(("ended", ended))

        # Everything else is in the table above. What's left is the verdict
        # and the lesson: what was sent against what the conversation weighed.
        conversation = getattr(self, "final_conversation", None) or self.last_chars // 4
        if conversation:
            times = round(self.input_tokens / conversation)
            rows.append(("re-sent", f"{self.input_tokens:,} tokens sent for a conversation that ended "
                                    f"at ~{conversation:,}: {times}× its final size."))
            rows.append(("", "Each turn re-sends the whole conversation plus the tool definitions."))
        if self.rereads:
            rows.append(("re-reads", f"{self.rereads} file(s) read again, though the first copy "
                                     f"was still in the conversation"))
        if not self.counts.get("run_tests"):
            rows.append(("note", "it never ran the tests. It had the tool the whole time"))

        print("\n\033[1m── run summary " + "─" * 40 + "\033[0m")
        for label, text in rows:
            print(f"   {label:<9} {text}")
