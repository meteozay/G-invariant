import inspect
import os
import sys
from glob import glob
from time import time

import numpy as np

# os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
from dataset.scenarios import area4_dataset
from models.area4_nmid import GroupInvariance, GroupInvarianceConv

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

# add parent (root) to pythonpath
from dataset import scenarios
from argparse import ArgumentParser

import tensorflow as tf
import tensorflow.contrib as tfc
from tqdm import tqdm

from dl_work.utils import LoadFromFile

tf.enable_eager_execution()
tf.set_random_seed(444)

_tqdm = lambda t, s, i: tqdm(
    ncols=80,
    total=s,
    bar_format='%s epoch %d | {l_bar}{bar} | Remaining: {remaining}' % (t, i))


def _ds(title, ds, ds_size, i, batch_size):
    with _tqdm(title, ds_size, i) as pbar:
        for i, data in enumerate(ds):
            yield (i, data[0], data[1])
            pbar.update(batch_size)


names = ["my_inv_conv", "my_inv_fc"]
#names = ["avg_conv", "avg_fc"]
n = 32
models = [GroupInvarianceConv(n), GroupInvariance(n)]


def secondary():
    batch_size = 64
    results = []
    scenario_path = "../../data_inv/train/area4paper_shift"
    for name in names:
        #for i in [1, 2]:
        for i in [1, 2, 4, 8, 16, 32, 64, 128]:
            if "conv" in name:
                model = GroupInvarianceConv(i)
            else:
                model = GroupInvariance(i)
            fname = name + "_" + str(i)
            for ds_type in ["train", "val", "test"]:
                ds, ds_size = area4_dataset(scenario_path.replace("train", ds_type))
                mae = []
                times = []
                for k in range(1, 10):
                    p = glob("./working_dir/area_nmid/" + fname + "_" + str(k) + "/checkpoints/best*.index")
                    best_path = sorted(p, key=lambda x: (len(x), x))[-1].replace(".index", "")
                    model.load_weights(best_path).expect_partial()
                    dataset_epoch = ds.shuffle(ds_size)
                    dataset_epoch = dataset_epoch.batch(batch_size).prefetch(batch_size)

                    acc = []
                    for l, quad, area, in _ds('Train', dataset_epoch, ds_size, 0, batch_size):
                        start = time()
                        pred = model(quad, training=True)
                        stop = time()
                        times.append(stop - start)

                        model_loss = tf.keras.losses.mean_absolute_error(area[:, tf.newaxis], pred)
                        # model_loss = model_loss / area
                        acc = acc + list(model_loss.numpy())

                    print(np.mean(acc))
                    mae.append(np.mean(acc))

                print(np.mean(mae))
                print(np.std(mae))
                results.append((fname, ds_type, np.mean(mae), np.std(mae), np.mean(times[1:]), np.std(times[1:])))

    with open("./paper/area_nmid.csv", 'w') as fh:
        for r in results:
            fh.write("%s\t%s\t%.5f\t%.5f\t%.6f\t%.6f\n" % r)


if __name__ == '__main__':
    secondary()