from config import read_cfg, write_cfg

DEFAULTS = {"retries": 3, "timeout_s": 30}


def load_or_init(path):
    try:
        return read_cfg(path)
    except FileNotFoundError:
        write_cfg(path, DEFAULTS)
        return dict(DEFAULTS)
