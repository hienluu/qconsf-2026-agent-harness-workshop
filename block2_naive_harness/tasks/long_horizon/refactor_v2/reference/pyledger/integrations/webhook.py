"""Outbound HTTP notifications (stub — no real network).

NOTE: post() here is the HTTP verb. It is NOT part of the ledger API and
is NOT covered by the v2 migration.
"""

SENT = []


def post(url: str, payload: dict) -> dict:
    SENT.append((url, payload))
    return {"status": 202, "url": url}


def ping(url: str) -> dict:
    return post(url, {"event": "ping"})
