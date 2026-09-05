# Task: two-file rename

A miniature of the long-horizon migration. The tests expect `parse_config`
and `dump_config`; the source still uses the legacy names `read_cfg` and
`write_cfg`, across two files. Rename them everywhere.
Done means: `pytest` exits green. Do not modify the tests.

Run it (from `block2_naive_harness/`):

```
python harness_skeleton.py tasks/short/03_small_rename/workspace \
  "The tests expect renamed functions. Rename the legacy functions everywhere until all tests pass. Do not modify the tests."
```
