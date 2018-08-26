#! /usr/bin/python
# -*- coding: utf-8 -*-

import tensorflow as tf

from tensorlayer.layers.core import Layer

from tensorlayer.layers.utils.quantization import quantize

from tensorlayer import logging

from tensorlayer.decorators import auto_parse_inputs
from tensorlayer.decorators import deprecated_alias
from tensorlayer.decorators import deprecated_args

__all__ = [
    'BinaryDenseLayer',
]


class BinaryDenseLayer(Layer):
    """The :class:`BinaryDenseLayer` class is a binary fully connected layer, which weights are either -1 or 1 while inferencing.

    Note that, the bias vector would not be binarized.

    Parameters
    ----------
    prev_layer : :class:`Layer`
        Previous layer.
    n_units : int
        The number of units of this layer.
    act : activation function
        The activation function of this layer, usually set to ``tf.act.sign`` or apply :class:`SignLayer` after :class:`BatchNormLayer`.
    gemmlowp_at_inference : boolean
        If True, use gemmlowp instead of ``tf.matmul`` (gemm) for inference. (TODO).
    W_init : initializer
        The initializer for the weight matrix.
    b_init : initializer or None
        The initializer for the bias vector. If None, skip biases.
    W_init_args : dictionary
        The arguments for the weight matrix initializer.
    b_init_args : dictionary
        The arguments for the bias vector initializer.
    name : a str
        A unique layer name.

    """

    @deprecated_alias(
        layer='prev_layer', end_support_version="2.0.0"
    )  # TODO: remove this line before releasing TL 2.0.0
    @deprecated_args(
        end_support_version="2.1.0",
        instructions="`prev_layer` is deprecated, use the functional API instead",
        deprecated_args=("prev_layer", ),
    )  # TODO: remove this line before releasing TL 2.1.0
    def __init__(
        self,
        n_units=100,
        act=None,
        gemmlowp_at_inference=False,
        W_init=tf.truncated_normal_initializer(stddev=0.1),
        b_init=tf.constant_initializer(value=0.0),
        W_init_args=None,
        b_init_args=None,
        name='binary_dense',
    ):
        if gemmlowp_at_inference:
            raise NotImplementedError("TODO. The current version use tf.matmul for inferencing.")
        self.n_units=n_units
        self.act=act,
        self.gemmlowp_at_inference=gemmlowp_at_inference,
        self.W_init=W_init
        self.b_init=b_init
        self.W_init_args=W_init_args
        self.b_init_args=b_init_args
        self.name=name

        super(BinaryDenseLayer, self).__init__(W_init_args=W_init_args, b_init_args=b_init_args)

    def __str__(self):
        additional_str = []

        try:
            additional_str.append("n_units: %d" % self.n_units)
        except AttributeError:
            pass

        try:
            additional_str.append("act: %s" % self.act.__name__ if self.act is not None else 'No Activation')
        except AttributeError:
            pass

        return self._str(additional_str)


    @auto_parse_inputs
    def compile(self, prev_layer):

        if self._temp_data['inputs'].get_shape().ndims != 2:
            raise Exception("The input dimension must be rank 2, please reshape or flatten it")

        n_in = int(self._temp_data['inputs'].get_shape()[-1])

        with tf.variable_scope(self.name):
            weight_matrix = self._get_tf_variable(
                name='W',
                shape=(n_in, self.n_units),
                initializer=self.W_init,
                dtype=self._temp_data['inputs'].dtype,
                **self.W_init_args
            )
            # weight_matrix = tl.act.sign(weight_matrix)    # dont update ...
            weight_matrix = quantize(weight_matrix)
            # weight_matrix = tf.Variable(weight_matrix)
            # print(weight_matrix)

            self._temp_data['outputs'] = tf.matmul(self._temp_data['inputs'], weight_matrix)
            # self._temp_data['outputs'] = xnor_gemm(self._temp_data['inputs'], weight_matrix) # TODO

            if self.b_init:
                try:
                    b = self._get_tf_variable(
                        name='b',
                        shape=(self.n_units),
                        initializer=self.b_init,
                        dtype=self._temp_data['inputs'].dtype,
                        **self.b_init_args
                    )

                except Exception:  # If initializer is a constant, do not specify shape.
                    b = self._get_tf_variable(
                        name='b', initializer=self.b_init, dtype=self._temp_data['inputs'].dtype, **self.b_init_args
                    )

                self._temp_data['outputs'] = tf.nn.bias_add(self._temp_data['outputs'], b, name='bias_add')

            self._temp_data['outputs'] = self._apply_activation(self._temp_data['outputs'])
