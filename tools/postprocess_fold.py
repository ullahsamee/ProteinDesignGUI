import sys
from pathlib import Path
import numpy as np
import shutil


def get_field(name, key):
    f1 = name.find(f'_{key}_') + len(key) + 2
    f2 = name.find('_', f1)
    return name[f1:f2]


if __name__ == '__main__':
    path = Path(sys.argv[1])
    for i in path.glob('*'):
        if not i.is_dir():
            continue
        pdbs = [*i.glob('*.pdb')]
        flag = False
        for j in pdbs:
            if '_relaxed_' in j.name:
                flag = True
                break
        if flag:
            pdbs = [j for j in pdbs if '_relaxed_' in j.name]
        scores = [float(get_field(j.name, 'score')) for j in pdbs]
        samples = [get_field(j.name, 'sample') for j in pdbs]
        models = [get_field(j.name, 'model') for j in pdbs]
        od = np.argsort(scores)
        rank = 1
        last_score = None
        for j in od:
            name = f'{i.name}_Sample{samples[j]}_model{models[j]}_Rank{rank}.pdb'
            print(name)
            shutil.copy(pdbs[j], path / name)
            if last_score is not None and last_score < scores[j]:
                last_score = scores[j]
                rank += 1
