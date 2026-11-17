# Block 3: After the Workshop

Two extras for after the session. Run every command from
`block3_measure/`, and reset first if you've run anything since the
workshop (see "Starting over" in the [README](README.md)).

## Make the rare protections fire

Each on a short task. The first two are demos and aren't recorded.

```bash
INJECT_MALFORMED_TURN=3 uv run eval/run_eval.py h1 --task fix_bug
```

```bash
INJECT_MALFORMED_TURN=3 uv run eval/run_eval.py h2 --task fix_bug
```

A corrupted tool call on turn 3: h1 (your Block 2 harness, run here)
crashes (`the harness crashed (JSONDecodeError ...)`); h2 prints `↻`,
carries on and solves it.

```bash
TRANSCRIPT_CHAR_BUDGET=4000 uv run eval/run_eval.py h2 --task bug_hunt
```

A 4,000-character budget, far too small. `✂✂` fires on most turns,
`added` goes negative, and `cached` falls (64% to 10% in one of our runs):
compaction changes the start of the conversation, so the provider's cache
stops matching. Watch `re-read` too. In another run the agent re-read the
same files every few turns until it ran out, 84 re-reads in 40 turns:
too small a budget makes the agent forget what it just read.

```bash
uv run eval/run_eval.py h2 --task touch_tests
```

```bash
uv run eval/run_eval.py h3 --task touch_tests
```

This task asks the agent to fix the bug *and* add a test. h2 adds it (5
pass). h3 refuses (`⛔`), still fixes the bug, and carries on, because the
refusal is an ordinary tool result. Ours said so in its summary: it tried
to add the test "but the workspace blocks writes to test files."

## Do h3's notes earn their place?

h3 with and without notes, nothing else changed:

```bash
uv run eval/ablation.py --runs 1 --task refactor_v2
```

Two more long runs. Predict the direction first. We ran three of each:
with notes 365k to 702k tokens, without 187k to 492k, ranges overlapping,
and no run in either arm re-read a single file. **The notes bought
nothing measurable**, because this migration never sends the agent back
for something it already had, so there was nothing for the notes to
preserve. Durable memory is a good feature; it did nothing here because
this workload doesn't produce the failure it prevents. Raw rows:
`ablation_results.jsonl`.
