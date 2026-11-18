# Block 5: After the Workshop

## Test your choice on your own task

The worksheet ends with "how to test it". This repo is a testbed for
that.

**Your task in Block 3's runner.** Add your task under
`block2_naive_harness/tasks/` (a workspace whose tests fail, committed to
git so the runner can tell it's clean) and an entry in
`block3_measure/eval/tasks.py`, then run it through h2 and h3 as you did
in Block 3. `scripts/reset.py` leaves an uncommitted task folder alone,
but restores a committed one like the others, so commit each change to
your task before you reset.

**Your task through a production harness** isn't wired up yet: Block 4's
scripts only take the workshop's tasks. To try one now, copy the script
closest to your candidate and change its workspace, prompt and turn cap.
Its tables will still label the run as the workshop's migration, so read
the numbers, not the labels.

**Read the traces, not the verdict.** The line under each verdict says
when the agent ran the tests and whether it rewrote files it never read.
If your task has one right answer, keep it and compare against it the
way `scripts/reference_check.py` does. Passing tests is where checking
starts, not where it ends.
