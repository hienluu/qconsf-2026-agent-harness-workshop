# Task: implement `slugify`

`textutil.py` declares `slugify` but doesn't implement it. The tests in
`test_textutil.py` define the expected behavior (lowercase, hyphens,
punctuation stripped, whitespace collapsed, digits kept). The agent must
implement it. Done means: `pytest` exits green, tests unmodified.

Run it (from `block2_naive_harness/`):

```
python harness_skeleton.py tasks/short/02_add_function/workspace \
  "Implement the unimplemented function so all tests pass. Do not modify the tests."
```
