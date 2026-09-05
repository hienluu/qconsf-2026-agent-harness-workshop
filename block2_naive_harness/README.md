# Block 2 — Build the Naive Harness

You will complete a minimal agent harness — a loop and a tool dispatcher —
verify it on small tasks, then run it on a long-horizon task sized past
its design limits and characterize how it fails. Block 3 adds the missing
components one configuration at a time and measures what each one buys.

## Exercise flow

1. Open `harness_skeleton.py` and fill in the two small TODOs in the agent
   loop: the model call (~4 lines) and the tool execution + result
   feedback (~5 lines). The loop structure, dispatcher, and client are
   provided. `tools.py` — the tool implementations and schemas — is also
   provided; read it.
2. Run the short tasks (see each `TASK.md` under `tasks/short/`). All three
   should finish green in under a minute each.
3. Run the long-horizon task (`tasks/long_horizon/refactor_v2/TASK.md`)
   and observe how the transcript grows and where progress stalls.
4. Debrief: map each failure mode you observed to the missing harness
   component.

Stuck on the TODOs? The finished harness is in `solution/harness.py`.

## What this harness deliberately lacks

| Missing component | Symptom you'll see |
|---|---|
| Tool-output limits | Full pytest tracebacks flood the context every test run |
| Context compaction | Transcript grows monotonically until quality degrades or the request fails |
| Durable memory / plan | Rename rules and per-file progress live only in the transcript |
| Error recovery | A malformed tool call or transient API error derails the run |
| Loop budget & progress detection | The agent can redo and undo the same work indefinitely |

Block 3 adds these one config at a time — and measures each addition against
the same task suite.
