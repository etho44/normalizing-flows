import tensorflow as tf
import tensorflow_probability as tfp
import numpy as np
from normalizing_flows.flows import Transform

class Planar(Transform):
    def __init__(self, use_residual=True, **kwargs):
        super(Planar, self).__init__(**kwargs)
        self.use_residual = use_residual
        # define nonlinearity function
        self.h = lambda x: tf.math.tanh(x)
        self.dh = lambda x: 1.0 - tf.square(tf.tanh(x))

    def _alpha(self, u, w):
        wu = tf.matmul(w, u)
        m = -1 + tf.nn.softplus(wu)
        return m - wu

    def _u_hat(self, u, w):
        alpha = self._alpha(u, w)
        alpha_w = alpha*w / tf.reduce_sum(w**2.0)
        return u + tf.transpose(alpha_w, (0,2,1))

    def _wzb(self, w, z, b):
        wz = tf.matmul(w, z) # (b, 1, 1)
        return wz + b

    def _forward(self, z, args: tf.Tensor):
        """
        Computes the forward pass of the transformation:
        residual:  z' = z + uh(wz + b)
        otherwise: z' = uh(wz+b)

        Tensor shapes
        z    : (batch_size, d)
        args : (batch_size, 2*d + 1)
        """
        # set up parameters
        d = tf.shape(z)[1]
        u, w, b = args[:,:d], args[:,d:-1], args[:,-1]
        u = tf.reshape(u, (-1, d, 1))
        w = tf.reshape(w, (-1, 1, d))
        b = tf.reshape(b, (-1, 1, 1))
        z = tf.expand_dims(z, axis=-1)
        # compute forward pass z_k -> z_k+1
        wzb = self._wzb(w, z, b) # (batch_size, 1)
        u_hat = self._u_hat(u, w)
        if self.use_residual:
            z_ = z + tf.multiply(u_hat, self.h(wzb))
        else:
            z_ = tf.multiply(u_hat, self.h(wzb))
        # compute log det jacobian
        dh_dz = tf.multiply(self.dh(wzb), w) # (batch_size, 1, d)
        r = 1.0 if self.use_residual else 0.0
        ldj = tf.math.log(tf.math.abs(r + tf.matmul(dh_dz, u_hat)))
        return tf.squeeze(z_, axis=-1), ldj
    
    def _inverse(self, z, args: tf.Tensor):
        assert not self.use_residual, 'inverse transform is not supported with residual'
        d = tf.shape(z)[1]
        u, w, b = args[:,:d], args[:,d:-1], args[:,-1]
        u = tf.reshape(u, (-1, d, 1))
        w = tf.reshape(w, (-1, 1, d))
        b = tf.reshape(b, (-1, 1, 1))
        z = tf.expand_dims(z, axis=-1)
        # compute inverse pass z_k -> z_k-1
        # (batch_size, 1)
        u_hat = self._u_hat(u, w)
        if self.use_residual:
            z_ = z + tf.multiply(u_hat, self.h(wzb))
        else:
            z_ = tf.multiply(u_hat, self.h(wzb))
        # compute log det jacobian
        dh_dz = tf.multiply(self.dh(wzb), w) # (batch_size, 1, d)
        ldj = tf.math.log(tf.math.abs(tf.matmul(dh_dz, u_hat)))
        return tf.squeeze(z_, axis=-1), -ldj

    def _param_count(self, shape):
        d = shape[-1]
        return 2*d + 1
