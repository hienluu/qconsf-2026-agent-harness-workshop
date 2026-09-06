# Medium task: the ordercalc bug hunt

A small order-pricing package (8 modules, 18 tests, 5 failing) with
**three seeded bugs that interact** — sized between `fix_bug` (one obvious
bug, a few turns) and `refactor_v2` (bulk migration, dozens of turns).
The work here is *diagnosis*: no single file read reveals everything, and
fixing one bug changes which tests fail, so the agent must iterate —
fix, re-run, re-diagnose.

Done means: `pytest` exits green, tests unmodified.

**Tuning status (Sep 2026):** GLM-5.3 through the naive harness solves
this in ~6 turns / ~13k tokens — the diagnosis is real but the package is
small enough to read in one pass, so strong models batch-fix without
iterating. That places bug_hunt between fix_bug and refactor_v2 in
*tokens and breadth* (3× fix_bug's context, 8 files vs 1) but not yet in
*turns*. October options if a longer horizon is wanted: scale the package
(the refactor task's lesson — only exceeding one-read capacity forces
iteration) or accept this as the "wide but shallow" middle step.

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
