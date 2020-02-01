from math import pi

import tensorflow as tf

from dataset.scenarios import decode_data
from utils.constants import Car
from utils.crucial_points import calculate_car_crucial_points
from utils.distances import dist, integral
from utils.poly5 import curvature, params
from utils.utils import _calculate_length, Rot
from matplotlib import pyplot as plt

tf.enable_eager_execution()


def groupAvereaging(inputs, operation):
    x = inputs
    x1 = x
    x2 = tf.roll(x, 1, 1)
    x3 = tf.roll(x, 2, 1)
    x4 = tf.roll(x, 3, 1)

    x1 = operation(x1)
    x2 = operation(x2)
    x3 = operation(x3)
    x4 = operation(x4)

    x = tf.reduce_mean(tf.stack([x1, x2, x3, x4], -1), -1)
    return x


class Conv1d(tf.keras.Model):
    def __init__(self, num_features):
        super(Conv1d, self).__init__()
        activation = tf.keras.activations.tanh
        self.last_n = 112  # * 4
        self.features = [
            tf.keras.layers.Conv1D(32, 3, activation=activation),
            # tf.keras.layers.Conv1D(64, 3, activation=activation),
            # tf.keras.layers.Conv1D(self.last_n, 1, padding='same', activation=activation),
            tf.keras.layers.Conv1D(self.last_n, 3, activation=activation),
        ]
        # self.fc = tf.keras.layers.Dense(num_features, activation=activation)
        self.fc = [
            tf.keras.layers.Dense(32, activation=activation),
            tf.keras.layers.Dense(num_features, activation=activation),
        ]

    def process(self, quad):
        # x = tf.reshape(quad, (-1, 8))
        x = tf.concat([quad, quad[:, :1]], axis=1)
        for layer in self.features:
            x = layer(x)
        x = tf.reshape(x, (-1, self.last_n))
        # x = self.fc(x)
        for layer in self.fc:
            x = layer(x)

        return x

    def call(self, inputs, training=None):
        x = groupAvereaging(inputs, self.process)
        #x = self.process(inputs)
        return x


class GroupOperationResultAveraging(tf.keras.Model):
    def __init__(self, num_features, activation=tf.keras.activations.tanh):
        super(GroupOperationResultAveraging, self).__init__()
        self.features = [
            tf.keras.layers.Dense(64, activation),
            tf.keras.layers.Dense(num_features, activation),
            tf.keras.layers.Dense(int(1.5 * num_features), activation),
            tf.keras.layers.Dense(num_features, activation),
        ]

    def call(self, inputs, training=None):
        x = inputs
        x1 = tf.reshape(x, (-1, 8))
        x2 = tf.reshape(tf.roll(x1, 1, 1), (-1, 8))
        x3 = tf.reshape(tf.roll(x2, 1, 1), (-1, 8))
        x4 = tf.reshape(tf.roll(x3, 1, 1), (-1, 8))

        for layer in self.features:
            x1 = layer(x1)
            x2 = layer(x2)
            x3 = layer(x3)
            x4 = layer(x4)

        x = tf.reduce_mean(tf.stack([x1, x2, x3, x4], -1), -1)
        # x = tf.reduce_max(tf.stack([x1, x2, x3, x4], -1), -1)
        return x


class GroupInvariance(tf.keras.Model):
    def __init__(self, num_features, activation=tf.keras.activations.tanh):
        super(GroupInvariance, self).__init__()
        self.features = [
            #tf.keras.layers.Dense(64, activation),
            tf.keras.layers.Dense(32, activation),
            # tf.keras.layers.Dense(num_features, activation),
            # tf.keras.layers.Dense(num_features, activation),
            # tf.keras.layers.Dense(num_features, activation),
            tf.keras.layers.Dense(4 * num_features, tf.keras.activations.tanh),
            #tf.keras.layers.Dense(4 * 168, tf.keras.activations.tanh),
        ]

        self.fc = [
            #tf.keras.layers.Dense(64, activation),
            tf.keras.layers.Dense(64, activation),
            tf.keras.layers.Dense(num_features, activation),
        ]

    def call(self, inputs, training=None):
        x = inputs
        bs = x.shape[0]
        n_points = x.shape[1]
        for layer in self.features:
            x = layer(x)
        x = tf.reshape(x, (bs, n_points, -1, 4))
        a, b, c, d = tf.unstack(x, axis=1)
        # a, b, c, d, e = tf.unstack(x, axis=1)
        x = a[:, :, 0] * b[:, :, 1] * c[:, :, 2] * d[:, :, 3] \
            + b[:, :, 0] * c[:, :, 1] * d[:, :, 2] * a[:, :, 3] \
            + c[:, :, 0] * d[:, :, 1] * a[:, :, 2] * b[:, :, 3] \
            + d[:, :, 0] * a[:, :, 1] * b[:, :, 2] * c[:, :, 3]

        for layer in self.fc:
            x = layer(x)

        return x



class GroupInvarianceConv(tf.keras.Model):
    def __init__(self, num_features, activation=tf.keras.activations.tanh):
        super(GroupInvarianceConv, self).__init__()

        activation = tf.keras.activations.tanh
        self.last_n = 88
        self.features = [
            tf.keras.layers.Conv1D(32, 3, activation=activation),
            tf.keras.layers.Conv1D(4 * self.last_n, 1, padding='same'),
        ]
        self.fc = [
            tf.keras.layers.Dense(32, activation=activation),
            tf.keras.layers.Dense(num_features, activation=activation),
        ]

    def call(self, inputs, training=None):
        x = tf.concat([inputs[:, -1:], inputs, inputs[:, :1]], axis=1)
        for layer in self.features:
            x = layer(x)
        # x =
        a, b, c, d = tf.unstack(x, axis=1)
        a = tf.reshape(a, (-1, 4, self.last_n))
        b = tf.reshape(b, (-1, 4, self.last_n))
        c = tf.reshape(c, (-1, 4, self.last_n))
        d = tf.reshape(d, (-1, 4, self.last_n))

        x = a[:, 0] * b[:, 1] * c[:, 2] * d[:, 3] \
            + b[:, 0] * c[:, 1] * d[:, 2] * a[:, 3] \
            + c[:, 0] * d[:, 1] * a[:, 2] * b[:, 3] \
            + d[:, 0] * a[:, 1] * b[:, 2] * c[:, 3]

        for layer in self.fc:
            x = layer(x)

        return x


class InsideNet(tf.keras.Model):
    def __init__(self):
        super(InsideNet, self).__init__()
        n = 64
        #self.quadrangle_processor = GroupOperationResultAveraging(n)
        #self.quadrangle_processor = Conv1d(n)
        self.quadrangle_processor = GroupInvarianceConv(n)
        #self.quadrangle_processor = GroupInvariance(n)

        self.fc = [
            tf.keras.layers.Dense(32, tf.keras.activations.tanh),
            tf.keras.layers.Dense(1, tf.keras.activations.sigmoid),
        ]

    def call(self, quad1, quad2, training=None):
        quad1_ft = self.quadrangle_processor(quad1)
        quad2_ft = self.quadrangle_processor(quad2)

        x = tf.concat([quad1_ft, quad2_ft], -1)

        for layer in self.fc:
            x = layer(x)

        return x


class SimpleNet(tf.keras.Model):
    def __init__(self):
        super(SimpleNet, self).__init__()
        self.fc = [
            tf.keras.layers.Dense(32, tf.keras.activations.tanh),
            tf.keras.layers.Dense(64, tf.keras.activations.tanh),
            tf.keras.layers.Dense(32, tf.keras.activations.tanh),
            tf.keras.layers.Dense(1, tf.keras.activations.sigmoid),
        ]

    def call(self, quad, point, training=None):
        x = tf.concat([tf.layers.flatten(quad), point], 1)
        for layer in self.fc:
            x = layer(x)

        return x


def _plot(x_path, y_path, th_path, data, step, print=False):
    _, _, free_space, _ = data

    for i in range(free_space.shape[1]):
        for j in range(4):
            fs = free_space
            plt.plot([fs[0, i, j - 1, 0], fs[0, i, j, 0]], [fs[0, i, j - 1, 1], fs[0, i, j, 1]])
    plt.xlim(-25.0, 25.0)
    plt.ylim(0.0, 50.0)
    # plt.xlim(-15.0, 20.0)
    # plt.ylim(0.0, 35.0)
    if print:
        plt.show()
    else:
        plt.savefig("last_path" + str(step).zfill(6) + ".png")
        plt.clf()