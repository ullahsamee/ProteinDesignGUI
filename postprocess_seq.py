import sys
import numpy as np
from pathlib import Path


def get_score(seq):
    f1 = seq.find(' score=') + 7
    f2 = seq.find(',', f1)
    return float(seq[f1:f2])


def post_process_mpnn(path, topN):
    with open(path, 'r') as f:
        seqs = f.read().split('>')[2:]
        scores = [get_score(s) for s in seqs]
        seqs = [seqs[i] for i in np.argsort(scores)[:min(len(seqs), topN)]]
        text = '>' + '>'.join(seqs).replace('/', ':')
    with open(path.with_suffix('.fasta'), 'w') as f:
        f.write(text)


if __name__ == '__main__':
    d = Path(sys.argv[1])
    top = int(sys.argv[2])
    for i in d.glob('*.fa'):
        post_process_mpnn(i, top)