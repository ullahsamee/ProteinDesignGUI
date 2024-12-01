import sys
from pathlib import Path
import shutil


if __name__ == '__main__':
    indir = Path(sys.argv[1])
    for i in (indir / 'predictions').rglob('*.pdb'):
        model = i.stem.split('_model_')[-1]
        fields = i.stem.split('_')
        fields.insert(-2, f'model{model}')
        new_name = '_'.join(fields) + '.pdb'
        shutil.copy(i, indir / new_name)