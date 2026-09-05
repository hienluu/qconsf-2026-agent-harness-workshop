# Task: fix the bug

One test in this workspace fails. Your agent must find the bug in
`stats.py` and fix it. Done means: `pytest` exits green, tests unmodified.

This file lives OUTSIDE the workspace — your agent can't read it. It only
gets the instruction you pass on the command line (from `block2_naive_harness/`):

```
python harness_skeleton.py tasks/short/01_fix_bug/workspace \
  "One test fails. Find the bug and fix it. Do not modify the tests."
```

## Before you run the agent

Run `python -m pytest tasks/short/01_fix_bug/workspace -q` yourself first
(from `block2_naive_harness/`). Seeing the red assertion diff — expected
three averages, got two — is the point: you'll know exactly what the agent
is up against, and the before/after is yours, not its word.

## What to watch in the trace

Expect ~5 turns: the agent lists files, reads `stats.py` and
`test_stats.py`, makes one edit, runs the tests, and reports green. Notice
that it diagnoses the bug by comparing code against test expectations — the
tests are its only specification.

## About the bug (spoiler — for you, not the agent)

`moving_average(values, window)` slides a fixed-width window along the list
and averages each position:

```
moving_average([1, 2, 3, 4], 2)

[ 1  2  3  4 ]
  └──┘            (1+2)/2 = 1.5
     └──┘         (2+3)/2 = 2.5
        └──┘      (3+4)/2 = 3.5   ← the buggy loop never reaches this one
```

Expected result: `[1.5, 2.5, 3.5]` — three windows.

The buggy loop is:

```python
for i in range(len(values) - window):
```

`range(len(values) - window)` yields `0 .. len-window-1`, one iteration
short — the final window is dropped, so the call above returns only
`[1.5, 2.5]`, and a window equal to the list length returns `[]` instead of
one average. Two tests catch it (`test_moving_average_covers_every_window`,
`test_moving_average_window_equals_length`). The fix is the classic
off-by-one: `range(len(values) - window + 1)`.

There is no hint in the source — the agent finds this the same way you
would: read the failing assertion, read the loop, spot the boundary error.
