# pyledger v2 API migration

The test suite under `tests/` is written against the **v2** API.
The source under `pyledger/` and `cli.py` still uses the legacy v1
names. Rename every v1 identifier to its v2 name, everywhere it
appears (definitions, imports, call sites, dataclass fields, dict
keys derived from field names). Do not modify anything in `tests/`.

| v1 (legacy) | v2 (target) |
|---|---|
| `make_ledger` | `new_ledger` |
| `post` | `record` |
| `balance_of` | `get_balance` |
| `amt` | `amount` |
| `check_entry` | `validate_entry` |
| `to_minor` | `to_cents` |
| `from_minor` | `from_cents` |
| `load_entries_csv` | `read_entries_csv` |

**This changelog is known to be incomplete.** Some v1 names were
renamed without being written down; the test suite is the source of
truth for the full v2 API.

**Out of scope:** `pyledger/integrations/webhook.py` — its `post()`
is the HTTP verb, not the ledger API. Do not rename anything there.

Done means: `pytest` exits green.
