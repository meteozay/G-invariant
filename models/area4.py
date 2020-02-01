from itertools import permutations
from math import pi

import tensorflow as tf
from matplotlib import pyplot as plt
import numpy as np

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


class GroupInvariance(tf.keras.Model):
    def __init__(self, num_features, activation=tf.keras.activations.tanh):
        super(GroupInvariance, self).__init__()
        self.features = [
            tf.keras.layers.Dense(16, activation),
            tf.keras.layers.Dense(64, activation),
            # tf.keras.layers.Dense(4 * 64, tf.keras.activations.tanh),
            # tf.keras.layers.Dense(4 * 64, tf.keras.activations.sigmoid),
            tf.keras.layers.Dense(4 * 64, None),
        ]

        self.fc = [
            tf.keras.layers.Dense(num_features, activation),
            # tf.keras.layers.Dense(num_features, tf.keras.activations.relu),
            # tf.keras.layers.Dense(num_features, tf.keras.activations.relu, use_bias=False),
            tf.keras.layers.Dense(1),
        ]

    def call(self, inputs, training=None):
        x = inputs
        bs = x.shape[0]
        n_points = x.shape[1]
        for layer in self.features:
            x = layer(x)
        x = tf.reshape(x, (bs, n_points, -1, 4))
        a, b, c, d = tf.unstack(x, axis=1)
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
        self.last_n = 128
        self.features = [
            tf.keras.layers.Conv1D(32, 3, activation=activation),
            tf.keras.layers.Conv1D(4 * self.last_n, 1, padding='same'),
        ]
        self.fc = [
            tf.keras.layers.Dense(32, activation=activation),
            tf.keras.layers.Dense(num_features, activation=activation),
            tf.keras.layers.Dense(1),
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

        # x = a[:, 0] * b[:, 1] * c[:, 2] \
        #    + b[:, 0] * c[:, 1] * a[:, 2] \
        #    + c[:, 0] * a[:, 1] * b[:, 2]

        x = a[:, 0] * b[:, 1] * c[:, 2] * d[:, 3] \
            + b[:, 0] * c[:, 1] * d[:, 2] * a[:, 3] \
            + c[:, 0] * d[:, 1] * a[:, 2] * b[:, 3] \
            + d[:, 0] * a[:, 1] * b[:, 2] * c[:, 3]

        for layer in self.fc:
            x = layer(x)

        return x


class Conv1d(tf.keras.Model):
    def __init__(self, num_features):
        super(Conv1d, self).__init__()
        activation = tf.keras.activations.tanh
        self.last_n = 128  # 128
        self.features = [
            tf.keras.layers.Conv1D(32, 3, activation=activation),
            # tf.keras.layers.Conv1D(64, 3, activation=activation),
            tf.keras.layers.Conv1D(self.last_n, 1, padding='same', activation=activation),
            # tf.keras.layers.Conv1D(self.last_n, 2, activation=activation),
        ]
        # self.fc = tf.keras.layers.Dense(num_features, activation=activation)
        self.fc = [
            tf.keras.layers.Dense(32, activation=activation),
            tf.keras.layers.Dense(num_features, activation=activation),
            tf.keras.layers.Dense(1),
        ]

    def process(self, quad):
        x = quad
        bs = x.shape[0]
        # x = tf.reshape(quad, (-1, 8))
        #x = tf.concat([quad, quad[:, :1]], axis=1)
        x = tf.concat([quad[:, -1:], quad, quad[:, :1]], axis=1)
        for layer in self.features:
            x = layer(x)
        x = tf.reshape(x, (bs, -1))
        # x = self.fc(x)
        for layer in self.fc:
            x = layer(x)

        return x

    def call(self, inputs, training=None):
        x = groupAvereaging(inputs, self.process)
        # x = self.process(inputs)
        return x


class SimpleNet(tf.keras.Model):
    def __init__(self, num_features):
        super(SimpleNet, self).__init__()
        activation = tf.keras.activations.tanh
        self.features = [
            tf.keras.layers.Dense(64, activation),
            # tf.keras.layers.Dense(2048, activation),
            tf.keras.layers.Dense(6 * num_features, activation),
            tf.keras.layers.Dense(num_features, activation),
            # tf.keras.layers.Dense(1024, activation),
            # tf.keras.layers.Dense(16, activation),
            tf.keras.layers.Dense(1),
        ]

    def process(self, quad):
        x = tf.reshape(quad, (-1, 8))
        for layer in self.features:
            x = layer(x)

        return x

    def call(self, inputs, training=None):
        x = groupAvereaging(inputs, self.process)
        # x = self.process(inputs)
        return x


class SegmentNet(tf.keras.Model):
    def __init__(self, num_features):
        super(SegmentNet, self).__init__()
        activation = tf.keras.activations.tanh
        self.features = [
            tf.keras.layers.Dense(64, activation),
            tf.keras.layers.Dense(6 * num_features, activation),
        ]

        self.fc = [
            tf.keras.layers.Dense(num_features, activation),
            tf.keras.layers.Dense(1),
        ]

    def process(self, quad):
        s1 = tf.concat([quad[:, 0], quad[:, 1]], axis=-1)
        s2 = tf.concat([quad[:, 1], quad[:, 2]], axis=-1)
        s3 = tf.concat([quad[:, 2], quad[:, 3]], axis=-1)
        s4 = tf.concat([quad[:, 3], quad[:, 0]], axis=-1)

        for layer in self.features:
            s1 = layer(s1)
            s2 = layer(s2)
            s3 = layer(s3)
            s4 = layer(s4)

        x = s1 + s2 + s3 + s4
        for layer in self.fc:
            x = layer(x)
        return x

    def call(self, inputs, training=None):
        # x = groupAvereaging(inputs, self.process)
        x = self.process(inputs)
        return x


class ConvImg(tf.keras.Model):
    def __init__(self, num_features):
        super(ConvImg, self).__init__()
        activation = tf.keras.activations.tanh
        self.last_n = 128  # * 3
        self.features = [
            # tf.keras.layers.Conv2D(16, 3, activation=activation),
            tf.keras.layers.Conv2D(8, 3, padding='same', activation=activation),
            tf.keras.layers.MaxPool2D((2, 2), padding='same'),
            # tf.keras.layers.Conv2D(16, 3, padding='same', activation=activation),
            tf.keras.layers.Conv2D(16, 3, padding='same', activation=activation),
            tf.keras.layers.MaxPool2D((2, 2), padding='same'),
            # tf.keras.layers.Conv2D(32, 3, padding='same', activation=activation),
            tf.keras.layers.Conv2D(16, 3, padding='same', activation=activation),
            tf.keras.layers.MaxPool2D((2, 2), padding='same'),
            # tf.keras.layers.Conv2D(32, 3, padding='same', activation=activation),
            tf.keras.layers.Conv2D(16, 3, padding='same', activation=activation),
            tf.keras.layers.MaxPool2D((2, 2), padding='same'),
            # tf.keras.layers.Conv2D(64, 3, padding='same', activation=activation),
            tf.keras.layers.Conv2D(32, 3, padding='same', activation=activation),
            tf.keras.layers.MaxPool2D((2, 2), padding='same'),
            # tf.keras.layers.Conv2D(64, 3, padding='same', activation=activation),
            tf.keras.layers.Conv2D(32, 3, padding='same', activation=activation),
            tf.keras.layers.MaxPool2D((2, 2), padding='same'),
        ]
        # self.fc = tf.keras.layers.Dense(num_features, activation=activation)
        self.fc = [
            tf.keras.layers.Dense(64, activation=activation),
            tf.keras.layers.Dense(16, activation=activation),
            tf.keras.layers.Dense(1),
        ]

        self.f = tf.keras.layers.Flatten()

    def process(self, quad):
        x = quad
        for layer in self.features:
            x = layer(x)
        x = self.f(x)

        for layer in self.fc:
            x = layer(x)

        return x

    def call(self, inputs, training=None):
        x = groupAvereaging(inputs, self.process)
        # x = self.process(inputs)
        return x


def partitionfunc(n, k, l=1):
    '''n is the integer to partition, k is the length of partitions, l is the min partition element size'''
    if k < 1:
        raise StopIteration
    if k == 1:
        if n >= l:
            yield (n,)
        raise StopIteration
    for i in range(l, n + 1):
        for result in partitionfunc(n - i, k - 1, i):
            yield (i,) + result


class MulNet(tf.keras.Model):
    def __init__(self):
        super(MulNet, self).__init__()
        activation = tf.keras.activations.tanh

        self.fc = [
            tf.keras.layers.Dense(64, activation),
            #tf.keras.layers.Dense(128, activation),
            tf.keras.layers.Dense(1),
        ]

    def call(self, x):
        for l in self.fc:
            x = l(x)
        return x


class Maron(tf.keras.Model):
    def __init__(self, num_features, activation=tf.keras.activations.tanh):
        super(Maron, self).__init__()

        self.features = [
            tf.keras.layers.Dense(64, activation),
            # tf.keras.layers.Dense(2048, activation),
            # tf.keras.layers.Dense(6 * num_features, activation),
            tf.keras.layers.Dense(num_features, activation),
            # tf.keras.layers.Dense(1024, activation),
            #tf.keras.layers.Dense(16, activation),
            tf.keras.layers.Dense(1),
        ]

        self.mulnn = MulNet()

        self.a = list(set([p for x in partitionfunc(4, 8, l=0) for p in permutations(x)]))
        self.f = np.array(self.a)

    def call(self, x, training=None):
        def inv(a, b, c, d, e, f, g, h):
            p = self.f
            x1 = a ** p[:, 0]
            x2 = b ** p[:, 1]
            x3 = c ** p[:, 2]
            x4 = d ** p[:, 3]
            x5 = e ** p[:, 4]
            x6 = f ** p[:, 5]
            x7 = g ** p[:, 6]
            x8 = h ** p[:, 7]
            mul = x1 * x2 * x3 * x4 * x5
            mulnn = self.mulnn(tf.stack([x1, x2, x3, x4, x5, x6, x7, x8], axis=-1))[:, :, 0]
            mul_loss = tf.keras.losses.mean_absolute_error(mul, mulnn)
            return mulnn, mul_loss

            # p = self.f
            # return a ** p[:, 0] * b ** p[:, 1] * c ** p[:, 2] * d ** p[:, 3] * e ** p[:, 4] * f ** p[:, 5] *\
            # g ** p[:, 6] * h ** p[:, 7]

        x = tf.transpose(x, (0, 2, 1))
        x = tf.reshape(x, (-1, 8))
        a, b, c, d, e, f, g, h = tf.unstack(x[:, :, tf.newaxis], axis=1)

        def term():
            p1, l1 = inv(a, b, c, d, e, f, g, h)
            p2, l2 = inv(d, a, b, c, h, e, f, g)
            p3, l3 = inv(c, d, a, b, g, h, e, f)
            p4, l4 = inv(b, c, d, a, f, g, h, e)
            q1 = p1 + p2 + p3 + p4
            L = l1 + l2 + l3 + l4
            return q1, L

        x, L = term()

        for layer in self.features:
            x = layer(x)

        return x, L


class MessagePassing(tf.keras.Model):
    def __init__(self, num_features, activation=tf.keras.activations.tanh):
        super(MessagePassing, self).__init__()
        self.features = [
            tf.keras.layers.Dense(16, activation),
            tf.keras.layers.Dense(64, activation),
            tf.keras.layers.Dense(32, tf.keras.activations.tanh),
        ]
        self.M = [
            tf.keras.layers.Dense(64, activation),
            tf.keras.layers.Dense(32, activation),
        ]

        self.U = [
            tf.keras.layers.Dense(64, activation),
            tf.keras.layers.Dense(32, activation),
        ]

        self.R = [
            tf.keras.layers.Dense(32, activation),
            tf.keras.layers.Dense(1),
        ]

    def process(self, input, layers):
        for l in layers:
            input = l(input)
        return input

    def call(self, inputs, training=None):
        #x = inputs[:, :, tf.newaxis]
        x = inputs
        for layer in self.features:
            x = layer(x)
        a, b, c, d = tf.unstack(x, axis=1)

        Ua = a
        Ub = b
        Uc = c
        Ud = d

        for i in range(1):
            Mab = self.process(tf.concat([Ua, Ub], axis=1), self.M)
            Mbc = self.process(tf.concat([Ub, Uc], axis=1), self.M)
            Mcd = self.process(tf.concat([Uc, Ud], axis=1), self.M)
            Mda = self.process(tf.concat([Ud, Ua], axis=1), self.M)

            Ua = self.process(tf.concat([Mda, Ua, a], axis=1), self.U)
            Ub = self.process(tf.concat([Mab, Ub, b], axis=1), self.U)
            Uc = self.process(tf.concat([Mbc, Uc, c], axis=1), self.U)
            Ud = self.process(tf.concat([Mcd, Ud, d], axis=1), self.U)

        x = self.process(tf.concat([Ua, Ub, Uc, Ud], axis=1), self.R)

        return x

def _plot(x_path, y_path, th_path, data, step, print=False):
    _, _, free_space, _ = data

    for i in range(free_space.shape[1]):
        for j in range(3):
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