import json


def read_cfg(path):
    with open(path) as fh:
        return json.load(fh)


def write_cfg(path, data):
    with open(path, "w") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
