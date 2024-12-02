import sys
from pathlib import Path
import numpy as np
import shutil
import re


def is_numeric(s):
    # Regular expression to match integers and floats
    pattern = r'^-?\d+(\.\d+)?$'
    return bool(re.match(pattern, s))


def get_field(name, key):
    name = name.split(f'_{key}_')[-1]
    f = name.find('_')
    name = name[:f]
    if f < 0 or not is_numeric(name):
        return '0'
    return name


if __name__ == '__main__':
    path = Path(sys.argv[1])
    for i in path.glob('*'):
        if not i.is_dir():
            continue
        pdbs = [*i.glob('*.pdb')]
        flag = False
        for j in pdbs:
            if '_relaxed_' in j.stem:
                flag = True
                break
        if flag:
            pdbs = [j for j in pdbs if '_relaxed_' in j.stem]
        scores = [float(get_field(j.stem, 'score')) for j in pdbs]
        samples = [get_field(j.stem, 'sample') for j in pdbs]
        models = [get_field(j.stem, 'model') for j in pdbs]
        od = np.argsort(scores)
        rank = 1
        last_score = None
        name = i.name
        if name.startswith('design_'):
            name = f'Design{name[7:]}'
        for j in od:
            shutil.copy(pdbs[j], path / f'{name}_Sample{samples[j]}_model{models[j]}_Rank{rank}.pdb')
            if last_score is None or last_score < scores[j]:
                last_score = scores[j]
                rank += 1
