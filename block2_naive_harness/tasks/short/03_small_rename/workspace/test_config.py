from app import load_or_init
from config import parse_config, dump_config


def test_round_trip(tmp_path):
    path = tmp_path / "cfg.json"
    dump_config(path, {"a": 1})
    assert parse_config(path) == {"a": 1}


def test_load_or_init_creates_defaults(tmp_path):
    path = tmp_path / "cfg.json"
    assert load_or_init(path) == {"retries": 3, "timeout_s": 30}
    assert parse_config(path) == {"retries": 3, "timeout_s": 30}
