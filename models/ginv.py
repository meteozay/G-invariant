import numpy as np


def sigmaPi(fin, m, n, p):
    fin = np.transpose(fin, (0, 2, 1, 3))
    fin = fin[:, :, np.newaxis]
    fin = np.tile(fin, (1, 1, m, 1, 1))
    y = fin @ p
    y = y[:, :, :, np.arange(n), np.arange(n)]
    y = np.prod(y, axis=3)
    y = np.sum(y, axis=2)
    return y


def prepare_permutation_matices(perm, n, m):
    p1 = np.eye(n, dtype=np.float32)
    p = np.tile(p1[np.newaxis], (m, 1, 1))
    for i, x in enumerate(perm):
        p[i, x, :] = p1[np.arange(n)]
    return p