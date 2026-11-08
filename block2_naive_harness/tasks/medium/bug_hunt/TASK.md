# Medium task: the ordercalc bug hunt

A small order-pricing package (8 modules, 18 tests, 5 failing) with
**three seeded bugs that interact** — sized between `fix_bug` (one obvious
bug, a few turns) and `refactor_v2` (bulk migration, dozens of turns).
The work here is *diagnosis*: no single file read reveals everything, and
fixing one bug changes which tests fail, so the agent must iterate —
fix, re-run, re-diagnose.

Done means: `pytest` exits green, tests unmodified.

**Its place in the suite:** wide but shallow. Eight files instead of one,
and a real diagnosis, but small enough to read in one pass, so it takes a
handful of turns rather than dozens.

Run it through any harness, e.g. (from `block3_measure/`):

```
uv run eval/run_eval.py h1 --task bug_hunt
```

## About the bugs (spoiler — for you, not the agent)

1. **`discounts.percent_off` floors instead of rounding half-up.** The
   sneaky part: `tax.py` reuses this helper, so the bug contaminates both
   discounts *and* taxes — several failures across two modules share one
   root cause.
2. **`pricing.price_cart` taxes the pre-discount subtotal.** Invisible on
   carts with no discount (`test_small_cart_no_discounts` passes — a
   diagnostic clue), compounds with bug 1 everywhere else.
3. **`receipt.format_receipt` drops the empty-cart guard** — a
   ZeroDivisionError that sits at the top of the pytest output and has
   nothing to do with the arithmetic. Misdirection by position.

The interaction is the point: a mechanical "fix what the traceback says"
pass handles bug 3 and then stalls; getting to green requires connecting
failures in `test_discounts` and `test_pricing` to shared root causes.

## Maintenance

`workspace/` is generated — never edit it by hand. The green ground truth
is `reference/`; the three bugs are exact substitutions applied by
`scripts/derive_bug_hunt.py`. Edit reference or bugs there and re-derive.
