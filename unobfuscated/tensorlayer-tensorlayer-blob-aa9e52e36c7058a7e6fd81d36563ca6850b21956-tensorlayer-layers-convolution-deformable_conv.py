


import tensorflow as tf

from tensorlayer.layers.core import Layer
from tensorlayer.layers.core import LayersConfig

from tensorlayer import logging

from tensorlayer.decorators import deprecated_alias
from tensorlayer.decorators import private_method

__all__ = [
    'DeformableConv2d',
]


class DeformableConv2d(Layer):
    


    @deprecated_alias(layer='prev_layer', end_support_version=1.9)  
    def __init__(
            self,
            prev_layer,
            offset_layer=None,
            
            n_filter=32,
            filter_size=(3, 3),
            act=None,
            name='deformable_conv_2d',
            W_init=tf.truncated_normal_initializer(stddev=0.02),
            b_init=tf.constant_initializer(value=0.0),
            W_init_args=None,
            b_init_args=None
    ):

        super(DeformableConv2d, self
             ).__init__(prev_layer=prev_layer, act=act, W_init_args=W_init_args, b_init_args=b_init_args, name=name)

        logging.info(
            "DeformableConv2d %s: n_filter: %d, filter_size: %s act: %s" %
            (self.name, n_filter, str(filter_size), self.act.__name__ if self.act is not None else 'No Activation')
        )

        self.offset_layer = offset_layer

        try:
            pre_channel = int(prev_layer.outputs.get_shape()[-1])
        except Exception:  
            pre_channel = 1
            logging.info("[warnings] unknow input channels, set to 1")
        shape = (filter_size[0], filter_size[1], pre_channel, n_filter)

        with tf.variable_scope(name):
            offset = self.offset_layer.outputs

            if offset.get_shape()[-1] != 2 * shape[0] * shape[1]:
                raise AssertionError("offset.get_shape()[-1] is not equal to: %d" % 2 * shape[0] * shape[1])

            
            input_h = int(self.inputs.get_shape()[1])
            input_w = int(self.inputs.get_shape()[2])
            kernel_n = shape[0] * shape[1]
            initial_offsets = tf.stack(
                tf.meshgrid(tf.range(shape[0]), tf.range(shape[1]), indexing='ij')
            )  
            initial_offsets = tf.reshape(initial_offsets, (-1, 2))  
            initial_offsets = tf.expand_dims(initial_offsets, 0)  
            initial_offsets = tf.expand_dims(initial_offsets, 0)  
            initial_offsets = tf.tile(initial_offsets, [input_h, input_w, 1, 1])  
            initial_offsets = tf.cast(initial_offsets, 'float32')
            grid = tf.meshgrid(
                tf.range(-int((shape[0] - 1) / 2.0), int(input_h - int((shape[0] - 1) / 2.0)), 1),
                tf.range(-int((shape[1] - 1) / 2.0), int(input_w - int((shape[1] - 1) / 2.0)), 1), indexing='ij'
            )

            grid = tf.stack(grid, axis=-1)
            grid = tf.cast(grid, 'float32')  
            grid = tf.expand_dims(grid, 2)  
            grid = tf.tile(grid, [1, 1, kernel_n, 1])  
            grid_offset = grid + initial_offsets  

            input_deform = self._tf_batch_map_offsets(self.inputs, offset, grid_offset)

            W = tf.get_variable(
                name='W_deformableconv2d', shape=[1, 1, shape[0] * shape[1], shape[-2], shape[-1]], initializer=W_init,
                dtype=LayersConfig.tf_dtype, **self.W_init_args
            )

            _tensor = tf.nn.conv3d(input_deform, W, strides=[1, 1, 1, 1, 1], padding='VALID', name=None)

            if b_init:
                b = tf.get_variable(
                    name='b_deformableconv2d', shape=(shape[-1]), initializer=b_init, dtype=LayersConfig.tf_dtype,
                    **self.b_init_args
                )

                _tensor = tf.nn.bias_add(_tensor, b, name='bias_add')

            self.outputs = tf.reshape(
                tensor=self._apply_activation(_tensor), shape=[tf.shape(self.inputs)[0], input_h, input_w, shape[-1]]
            )

        self._add_layers(self.outputs)

        if b_init:
            self._add_params([W, b])
        else:
            self._add_params(W)

    @private_method
    def _to_bc_h_w(self, x, x_shape):
        

        x = tf.transpose(x, [0, 3, 1, 2])
        x = tf.reshape(x, (-1, x_shape[1], x_shape[2]))
        return x

    @private_method
    def _to_b_h_w_n_c(self, x, x_shape):
        

        x = tf.reshape(x, (-1, x_shape[4], x_shape[1], x_shape[2], x_shape[3]))
        x = tf.transpose(x, [0, 2, 3, 4, 1])
        return x

    @private_method
    def tf_flatten(self, a):
        

        return tf.reshape(a, [-1])

    @private_method
    def _get_vals_by_coords(self, inputs, coords, idx, out_shape):
        indices = tf.stack(
            [idx, self.tf_flatten(coords[:, :, :, :, 0]),
             self.tf_flatten(coords[:, :, :, :, 1])], axis=-1
        )
        vals = tf.gather_nd(inputs, indices)
        vals = tf.reshape(vals, out_shape)
        return vals

    @private_method
    def _tf_repeat(self, a, repeats):
        

        

        if len(a.get_shape()) != 1:
            raise AssertionError("This is not a 1D Tensor")

        a = tf.expand_dims(a, -1)
        a = tf.tile(a, [1, repeats])
        a = self.tf_flatten(a)
        return a

    @private_method
    def _tf_batch_map_coordinates(self, inputs, coords):
        

        input_shape = inputs.get_shape()
        coords_shape = coords.get_shape()
        batch_channel = tf.shape(inputs)[0]
        input_h = int(input_shape[1])
        input_w = int(input_shape[2])
        kernel_n = int(coords_shape[3])
        n_coords = input_h * input_w * kernel_n

        coords_lt = tf.cast(tf.floor(coords), 'int32')
        coords_rb = tf.cast(tf.ceil(coords), 'int32')
        coords_lb = tf.stack([coords_lt[:, :, :, :, 0], coords_rb[:, :, :, :, 1]], axis=-1)
        coords_rt = tf.stack([coords_rb[:, :, :, :, 0], coords_lt[:, :, :, :, 1]], axis=-1)

        idx = self._tf_repeat(tf.range(batch_channel), n_coords)

        vals_lt = self._get_vals_by_coords(inputs, coords_lt, idx, (batch_channel, input_h, input_w, kernel_n))
        vals_rb = self._get_vals_by_coords(inputs, coords_rb, idx, (batch_channel, input_h, input_w, kernel_n))
        vals_lb = self._get_vals_by_coords(inputs, coords_lb, idx, (batch_channel, input_h, input_w, kernel_n))
        vals_rt = self._get_vals_by_coords(inputs, coords_rt, idx, (batch_channel, input_h, input_w, kernel_n))

        coords_offset_lt = coords - tf.cast(coords_lt, 'float32')

        vals_t = vals_lt + (vals_rt - vals_lt) * coords_offset_lt[:, :, :, :, 0]
        vals_b = vals_lb + (vals_rb - vals_lb) * coords_offset_lt[:, :, :, :, 0]
        mapped_vals = vals_t + (vals_b - vals_t) * coords_offset_lt[:, :, :, :, 1]

        return mapped_vals

    @private_method
    def _tf_batch_map_offsets(self, inputs, offsets, grid_offset):
        

        input_shape = inputs.get_shape()
        batch_size = tf.shape(inputs)[0]
        kernel_n = int(int(offsets.get_shape()[3]) / 2)
        input_h = input_shape[1]
        input_w = input_shape[2]
        channel = input_shape[3]

        
        inputs = self._to_bc_h_w(inputs, input_shape)

        
        offsets = tf.reshape(offsets, (batch_size, input_h, input_w, kernel_n, 2))
        
        

        coords = tf.expand_dims(grid_offset, 0)  
        coords = tf.tile(coords, [batch_size, 1, 1, 1, 1]) + offsets  

        
        coords = tf.stack(
            [
                tf.clip_by_value(coords[:, :, :, :, 0], 0.0, tf.cast(input_h - 1, 'float32')),
                tf.clip_by_value(coords[:, :, :, :, 1], 0.0, tf.cast(input_w - 1, 'float32'))
            ], axis=-1
        )
        coords = tf.tile(coords, [channel, 1, 1, 1, 1])

        mapped_vals = self._tf_batch_map_coordinates(inputs, coords)
        
        mapped_vals = self._to_b_h_w_n_c(mapped_vals, [batch_size, input_h, input_w, kernel_n, channel])

        return mapped_vals
