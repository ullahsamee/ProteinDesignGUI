"""
Usage: python migrate.py settings.conf [outpath]
"""

import sys
import json
import yaml
from pathlib import Path
import shutil


if __name__ == '__main__':
    path = Path(sys.argv[1])
    with open(path, 'r') as f:
        config = yaml.safe_load(f)
    with open(f'{Path(__file__).parent.parent}/default.json', 'r') as f:
        cfg = json.load(f)
    for k, v in cfg.items():
        if k not in config:
            config[k] = v
        else:
            for kk, vv in v.items():
                if kk not in config[k]:
                    config[k][kk] = v
    prot = path.parent / config['diffusion']['protein']

    if len(sys.argv) > 2:
        path = Path(sys.argv[2])

    with open(path, 'w') as f:
        f.write(yaml.dump(config))

    diff_in = path.parent / 'diffusion_input'
    diff_in.mkdir(parents=True, exist_ok=True)
    shutil.copy(prot, diff_in)
