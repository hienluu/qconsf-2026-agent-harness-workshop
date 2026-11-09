"""Shared trace and results table for the migration scripts.

Every script feeds the same events (a model response, a tool result, a
compaction), however its SDK delivers them, so all four traces read like
Block 3's: one header per turn with the tool calls by type, each call
underneath, and a short result under each call. Each run then adds a row
to runs/migration.jsonl and prints the table of the latest run per script.
"""

import json
import re
import time
from pathlib import Path

SAY, DIM, CUT, BAD, BOLD, OFF = "\033[32m", "\033[2m", "\033[33m", "\033[31m", "\033[1m", "\033[0m"
RESULTS = Path(__file__).resolve().parents[1] / "runs" / "migration.jsonl"


class Trace:
    def __init__(self, label: str, workspace: Path, virtual_paths: bool = False):
        self.label, self.workspace, self.virtual = label, workspace, virtual_paths
        self.turn, self.counts = 0, {}
        self.tokens = {}     # turn -> (sent, cached, out)
        self.said, self.calls, self.printed = [], [], True
        print(f"{DIM}   ┈ trace: one header per turn (❝ = the agent talking), its calls below,{OFF}\n"
              f"{DIM}     → each call's result, ✗ a failed call, ✂ the harness compacting{OFF}")

    # --- feeding events -------------------------------------------------
    def new_turn(self) -> None:
        self.flush()
        self.turn += 1
        self.said, self.calls, self.printed = [], [], False

    def text(self, said: str) -> None:
        if said and said.strip():
            self.said.append(said.strip())

    def usage(self, sent, cached=0, out=0) -> None:
        """This turn's tokens. Sent counts everything the model read,
        cached or not, as Block 2's scoreboard does. Set, not added: one
        response can arrive as several messages carrying the same usage."""
        if sent:
            self.tokens[self.turn] = (int(sent), int(cached or 0), int(out or 0))

    def run_total(self, sent, cached=0, out=0) -> None:
        """For an SDK that reports usage only for the whole run: used when no
        per-turn usage arrived."""
        if sent and not self.tokens:
            self.tokens[0] = (int(sent), int(cached or 0), int(out or 0))

    def call(self, name: str, args: dict) -> None:
        self.calls.append((name, args if isinstance(args, dict) else {}))

    def result(self, name: str, output) -> None:
        self.flush()
        text = str(output if output is not None else "").strip()
        # Shell tools append an exit-code marker as their last line (Deep
        # Agents: "[Command succeeded with exit code 0]"; ours: "[exit code
        # 0]"). Show the last real line instead, and a non-zero exit as ✗.
        lines = [line for line in text.splitlines() if line.strip()]
        if lines:
            m = re.match(r"^\[(?:Command (?:succeeded|failed) with )?exit code (-?\d+)\]$", lines[-1].strip())
            if m:
                lines = lines[:-1]
                if m.group(1) != "0":
                    self.failure((lines[-1] + "  " if lines else "") + f"(exit code {m.group(1)})")
                    return
                text = "\n".join(lines)
        if name in ("read_file", "Read"):
            shown = f"read {text.count(chr(10)) + 1:,} lines" if text else "(empty)"
        else:
            shown = text.splitlines()[-1] if text else "(no output)"
        print(f"{DIM}       → {shown[:100]}{OFF}")

    def failure(self, error) -> None:
        self.flush()
        lines = str(error or "failed").strip().splitlines()
        print(f"{BAD}       ✗ {(lines[-1] if lines else 'failed')[:100]}{OFF}")

    def compact(self, what: str) -> None:
        self.flush()
        print(f"{CUT}✂  [{self.label}] {what}{OFF}")

    # --- printing --------------------------------------------------------
    def rel(self, path: str) -> str:
        """Relative to the run's copy. A leading "/" is stripped only for a
        harness whose "/" is the workspace (Deep Agents); anywhere else an
        absolute path outside the copy is worth seeing as one."""
        p = str(path)
        root = str(self.workspace.resolve())
        if p.startswith(root):
            p = p[len(root):].lstrip("/")
        elif self.virtual:
            p = p.lstrip("/")
        while p.startswith("./"):
            p = p[2:]
        return p or "."

    def describe(self, name: str, args: dict) -> str:
        """One call, written like the call itself."""
        if "command" in args:
            lines = str(args["command"]).strip().splitlines() or [""]
            first = lines[0] if len(lines[0]) <= 100 else lines[0][:99] + "…"
            more = f"  …+{len(lines) - 1} more lines" if len(lines) > 1 else ""
            return f"{name}(command={first}{more})"
        parts = []
        path = args.get("file_path", args.get("path"))
        if path is not None:
            parts.append(f"file={self.rel(path)}")
        if "content" in args:
            parts.append(f"chars={len(str(args['content'])):,}")
        if "pattern" in args:
            parts.append(f"pattern={args['pattern']}")
        if "replace_all" in args:
            parts.append(f"replace_all={args['replace_all']}")
        if not parts:
            parts = [f"{k}={str(v)[:40]}" for k, v in args.items()]
        return f"{name}(" + ", ".join(parts) + ")"

    def flush(self) -> None:
        """Print the turn's header and calls once all its calls are known."""
        if self.printed:
            return
        self.printed = True
        if not self.calls:
            if self.said:
                print(f"\n\033[1;32m❝  [{self.label} turn {self.turn}] agent finished:{OFF}")
                print(SAY + "\n\n".join(self.said) + OFF)
            return
        counts: dict = {}
        for name, _ in self.calls:
            counts[name] = counts.get(name, 0) + 1
            self.counts[name] = self.counts.get(name, 0) + 1
        tally = "  [" + ", ".join(f"{k} × {v}" for k, v in counts.items()) + "]"
        said = " ".join(" ".join(self.said).split())
        if said:
            print(f"\n{SAY}❝  [{self.label} turn {self.turn}] agent says: {said}{OFF}{tally}")
        else:
            print(f"\n{DIM}   [{self.label} turn {self.turn}]{OFF}{tally}")
        for name, args in self.calls:
            print(f"     {self.describe(name, args)}")

    # --- end of run ------------------------------------------------------
    def finish(self, *, script: str, solved: bool, started: float, tools: str,
               tools_we_wrote: int) -> None:
        self.flush()
        total = sum(self.counts.values())
        by_type = ", ".join(f"{k} × {v}" for k, v in sorted(self.counts.items(), key=lambda kv: -kv[1]))
        print(f"\n{BOLD}── run summary " + "─" * 40 + OFF)
        print(f"   turns       {self.turn} model responses")
        print(f"   tool calls  {total}  ({by_type})")
        sent = sum(s for s, _, _ in self.tokens.values())
        cached = sum(c for _, c, _ in self.tokens.values())
        out = sum(o for _, _, o in self.tokens.values())
        if self.tokens:
            share = f", {cached / sent:.0%} of it cached" if sent and cached else ""
            print(f"   tokens      {sent:,} sent to the model{share}; {out:,} written by it")
        else:
            print(f"   tokens      not reported by this SDK")

        import os
        row = {"script": script, "tools": tools, "tools_we_wrote": tools_we_wrote,
               "solved": solved, "turns": self.turn, "tool_calls": total, "by_type": by_type,
               "tokens_sent": sent if self.tokens else None, "tokens_cached": cached, "tokens_out": out,
               "wall_s": round(time.monotonic() - started, 1), "model": os.environ.get("MODEL", ""),
               "timestamp": time.time()}
        RESULTS.parent.mkdir(exist_ok=True)
        with RESULTS.open("a") as fh:
            fh.write(json.dumps(row) + "\n")
        latest = {}
        for line in RESULTS.read_text().splitlines():
            r = json.loads(line)
            latest[r["script"]] = r
        print(f"\n{BOLD}── migration runs so far (latest per script) " + "─" * 20 + OFF)
        print(f"   {'script':<18}{'tools':<34}{'solved':>7}{'turns':>7}{'calls':>7}{'sent':>8}")
        for r in latest.values():
            k = r.get("tokens_sent")
            print(f"   {r['script']:<18}{r['tools'][:33]:<34}{('yes' if r['solved'] else 'NO'):>7}"
                  f"{r['turns']:>7}{r['tool_calls']:>7}{(f'{k / 1000:,.0f}k' if k else '?'):>8}")
        print(f"{DIM}   our h2 / h3 on this task: 17-34 turns, 181-299 tool calls (mostly one"
              f" write_file per file), 365k-778k sent{OFF}")
