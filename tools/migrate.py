"""
Usage: python migrate.py settings.conf [outpath]
"""

import sys
import json
import yaml


if __name__ == '__main__':
    path = sys.argv[1]
    with open(path, 'r') as f:
        config = yaml.safe_load(f)
    with open('../default.json', 'r') as f:
        cfg = json.load(f)
    for k, v in cfg.items():
        for kk, vv in cfg.items():
            if kk not in config[k]:
                config[k][kk] = v
    if len(sys.argv) > 2:
        path = sys.argv[2]
    with open(path, 'w') as f:
        f.write(yaml.dump(config))
