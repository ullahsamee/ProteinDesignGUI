"""
Usage: python migrate.py settings.conf [outpath]
"""

import sys
import json
from common import get_config, put_config


if __name__ == '__main__':
    path = sys.argv[1]
    config = get_config(path)
    with open('default.json', 'r') as f:
        cfg = json.load(f)
    for k, v in cfg.items():
        for kk, vv in cfg.items():
            if kk not in config[k]:
                config[k][kk] = v
    if len(sys.argv) > 2:
        path = sys.argv[2]
    put_config(config, path)