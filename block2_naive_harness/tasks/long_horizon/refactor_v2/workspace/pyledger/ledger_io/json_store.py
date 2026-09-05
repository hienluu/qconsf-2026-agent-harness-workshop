import json

from pyledger.core.entry import Entry


def save_ledger(ledger: dict, path) -> None:
    payload = {
        "name": ledger["name"],
        "entries": [vars(e) for e in ledger["entries"]],
    }
    with open(path, "w") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)


def load_ledger(path) -> dict:
    with open(path) as fh:
        payload = json.load(fh)
    return {
        "name": payload["name"],
        "entries": [Entry(**e) for e in payload["entries"]],
    }
