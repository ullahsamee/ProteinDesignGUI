import sys
import pickle


if __name__ == '__main__':
    trb = sys.argv[1]
    with open(trb, 'rb') as f:
        t = pickle.load(f)
    to_fix = {}
    for i, j in t['con_hal_pdb_idx']:
        if i not in to_fix:
            to_fix[i] = []
        to_fix[i].append(j)
    chains = sorted(to_fix.keys())
    print(' '.join(chains))
    print(','.join([' '.join(sorted(to_fix[i])) for i in chains]))
