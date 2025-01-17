"""
Usage: python migrate.py settings.conf [outpath]
"""

import sys
import json
import yaml
from pathlib import Path
import shutil
import os


if __name__ == '__main__':
    path = Path(sys.argv[1])
    if path.is_file():
        to_search = [path]
    else:
        to_search = [*path.rglob('config.yml')]
    for path in to_search:
        print(path)
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
                        config[k][kk] = vv

        fold = path.parent / 'fold'

        with open(path, 'w') as f:
            f.write(yaml.dump(config))

        if config['diffusion']['protein']:
            prot = path.parent / config['diffusion']['protein']
            if prot.exists():
                diff_in = path.parent / 'diffusion_input'
                diff_in.mkdir(parents=True, exist_ok=True)
                shutil.move(prot, diff_in)

        if fold.exists():
            os.system(f'python {Path(__file__).parent}/postprocess_colabfold.py {fold}')
