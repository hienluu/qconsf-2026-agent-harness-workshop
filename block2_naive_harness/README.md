# Block 2 — Build the Naive Harness

You will build the simplest possible agent harness — a loop and a tool
dispatcher — then watch it succeed on small tasks and fall apart on a
long-horizon one. That failure is the setup for Block 3, where harness
components fix it measurably.

## Exercise flow

1. Open `harness_skeleton.py` and fill in the two small TODOs in the agent
   loop: the model call (~4 lines) and the tool execution + result
   feedback (~5 lines). The loop structure, dispatcher, and client are
   provided. `tools.py` — the tool implementations and schemas — is also
   provided; read it.
2. Run the short tasks (see each `TASK.md` under `tasks/short/`). All three
   should finish green in under a minute each.
3. Run the long-horizon task (`tasks/long_horizon/refactor_v2/TASK.md`).
   Watch the transcript grow and progress stall.
4. Debrief: map each failure you observed to the missing harness component.

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
