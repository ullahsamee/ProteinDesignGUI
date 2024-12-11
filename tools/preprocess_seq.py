import sys
import pickle
from Bio.PDB import PDBParser
import numpy as np


def erosion_1d_left_to_right(vector):
    eroded = np.copy(vector)
    for i in range(1, len(vector)):  # Start from the second element
        if vector[i - 1] == 0:
            eroded[i] = 0

    # Preserve the first element
    eroded[0] = vector[0]
    return eroded


def erosion_1d_right_to_left(vector):
    eroded = np.copy(vector)
    for i in range(len(vector) - 2, -1, -1):  # Start from the second-to-last element
        if vector[i + 1] == 0:
            eroded[i] = 0

    # Preserve the last element
    eroded[-1] = vector[-1]
    return eroded


if __name__ == '__main__':
    trb = sys.argv[1]
    erode_n = int(sys.argv[2])
    erode_c = int(sys.argv[3])
    pdb = sys.argv[4]
    with open(trb, 'rb') as f:
        t = pickle.load(f)
    to_fix = {}
    for i, j in t['con_hal_pdb_idx']:
        if i not in to_fix:
            to_fix[i] = []
        to_fix[i].append(j)
    # erosion
    if erode_n > 0 or erode_c > 0:
        pdb = PDBParser().get_structure('X', pdb)
        for chain in pdb[0]:
            chain_id = chain.id
            residues = [res for res in chain if res.id[0] == ' ']
            v = np.zeros(shape=(len(residues),))
            i = np.array(to_fix[chain_id]) - 1
            v[i] = 1

            c = erode_n
            while c > 0:
                c -= 1
                v = erosion_1d_left_to_right(v)

            c = erode_c
            while c > 0:
                c -= 1
                v = erosion_1d_right_to_left(v)

            to_fix[chain_id] = (np.where(v == 1)[0] + 1).tolist()
    chains = sorted(to_fix.keys())
    print(' '.join(chains))
    print(','.join([' '.join([str(j) for j in to_fix[i]]) for i in chains]))
