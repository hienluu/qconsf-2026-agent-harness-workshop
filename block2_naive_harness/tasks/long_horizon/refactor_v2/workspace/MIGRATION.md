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
| `entries_by_account` | `entries_for` |
| `amt` | `amount` |
| `side` | `kind` |
| `check_entry` | `validate_entry` |
| `to_minor` | `to_cents` |
| `from_minor` | `from_cents` |
| `fmt_amt` | `format_amount` |
| `load_entries_csv` | `read_entries_csv` |
| `dump_entries_csv` | `write_entries_csv` |
| `summary_by_month` | `monthly_summary` |
| `balanced` | `is_balanced` |

Done means: `pytest` exits green.
