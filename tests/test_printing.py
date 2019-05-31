# Copyright (C) PROWLER.io 2019 - All Rights Reserved
# Unauthorised copying of this file, via any medium is strictly prohibited
# Proprietary and confidential


import numpy as np
import tensorflow as tf

import gpflow
from gpflow.utilities.printing import get_component_variables

import pytest

rng = np.random.RandomState(0)


class Data:
    H0 = 5
    H1 = 2
    M = 10
    D = 1
    Z = rng.rand(M, 1)
    ls = 2.0
    var = 1.0


# ------------------------------------------
# Helpers
# ------------------------------------------


class A(tf.Module):
    def __init__(self, name=None):
        super().__init__(name)
        self.var_trainable = tf.Variable(tf.zeros((2, 2, 1)), trainable=True)
        self.var_fixed = tf.Variable(tf.ones((2, 2, 1)), trainable=False)


class B(tf.Module):
    def __init__(self, name=None):
        super().__init__(name)
        self.submodule_list = [A(), A()]
        self.var_trainable = tf.Variable(tf.zeros((2, 2, 1)), trainable=True)
        self.var_fixed = tf.Variable(tf.ones((2, 2, 1)), trainable=False)


example_tf_module = A()
example_tf_module_variable_dict = {
    'A.var_trainable': {'value': np.zeros((2, 2, 1)), 'trainable': True, 'shape': (2, 2, 1)},
    'A.var_fixed': {'value': np.ones((2, 2, 1)), 'trainable': False, 'shape': (2, 2, 1)},
}

kernel = gpflow.kernels.RBF(lengthscale=Data.ls, variance=Data.var)
kernel.lengthscale.trainable = False
kernel_param_dict = {
    'RBF.lengthscale': {'value': Data.ls, 'trainable': False, 'shape': ()},
    'RBF.variance': {'value': Data.var, 'trainable': True, 'shape': ()}
}

model_gp = gpflow.models.SVGP(
    kernel=kernel,
    likelihood=gpflow.likelihoods.Gaussian(),
    feature=Data.Z,
    q_diag=True
)
model_gp.q_mu.trainable = False
model_gp_param_dict = {'kernel.lengthscale': kernel_param_dict['RBF.lengthscale'],
                       'kernel.variance': kernel_param_dict['RBF.variance'],
                       'likelihood.variance': {'value': 1.0, 'trainable': True, 'shape': ()},
                       'feature.Z': {'value': Data.Z, 'trainable': True, 'shape': (Data.M, Data.D)},
                       'SVGP.q_mu': {'value': np.zeros((Data.M, 1)), 'trainable': False,
                                     'shape': (Data.M, 1)},
                       'SVGP.q_sqrt': {'value': np.ones((Data.M, 1)), 'trainable': True,
                                       'shape': (Data.M, 1)}}

example_module_list = B()
example_module_list_variable_dict = {
    'A_0.var_trainable': example_tf_module_variable_dict['A.var_trainable'],
    'A_0.var_fixed': example_tf_module_variable_dict['A.var_fixed'],
    'A_1.var_trainable': example_tf_module_variable_dict['A.var_trainable'],
    'A_1.var_fixed': example_tf_module_variable_dict['A.var_fixed'],
    'B.var_trainable': example_tf_module_variable_dict['A.var_trainable'],
    'B.var_fixed': example_tf_module_variable_dict['A.var_fixed'],
}

model_keras = tf.keras.Sequential([
    tf.keras.layers.Dense(Data.H0, activation='relu', kernel_initializer='ones'),
    tf.keras.layers.Dense(Data.H1, activation='relu', kernel_initializer='ones', use_bias=False)
])
model_keras.build(input_shape=(Data.M, Data.D))
model_keras_variable_dict = {
    'Dense_0.kernel': {'value': np.ones((Data.D, Data.H0)), 'trainable': True,
                       'shape': (Data.D, Data.H0)},
    'Dense_0.bias': {'value': np.zeros((Data.H0,)), 'trainable': True, 'shape': (Data.H0,)},
    'Dense_1.kernel': {'value': np.ones((Data.H0, Data.H1)), 'trainable': True,
                       'shape': (Data.H0, Data.H1)}
}


@pytest.mark.parametrize('module', [A(), kernel, model_gp, B(), model_keras])
def test_get_component_variables_only_returns_parameters_and_variables(module):
    for path, variable in get_component_variables(module):
        assert isinstance(variable, tf.Variable) or isinstance(variable, gpflow.Parameter)


@pytest.mark.parametrize('module, expected_param_dicts', [
    (kernel, kernel_param_dict),
    (model_gp, model_gp_param_dict)
])
def test_get_component_variables_registers_variable_properties(module, expected_param_dicts):
    for path, variable in get_component_variables(module):
        param_name = path.split('.')[-2] + '.' + path.split('.')[-1]
        assert isinstance(variable, gpflow.Parameter)
        np.testing.assert_equal(variable.value().numpy(), expected_param_dicts[param_name]['value'])
        assert variable.trainable == expected_param_dicts[param_name]['trainable']
        assert variable.shape == expected_param_dicts[param_name]['shape']


@pytest.mark.parametrize('module, expected_var_dicts', [
    (example_tf_module, example_tf_module_variable_dict),
    (example_module_list, example_module_list_variable_dict),
    (model_keras, model_keras_variable_dict),
])
def test_get_component_variables_registers_param_properties(module, expected_var_dicts):
    for path, variable in get_component_variables(module):
        var_name = path.split('.')[-2] + '.' + path.split('.')[-1]
        assert isinstance(variable, tf.Variable)
        np.testing.assert_equal(variable.numpy(), expected_var_dicts[var_name]['value'])
        assert variable.trainable == expected_var_dicts[var_name]['trainable']
        assert variable.shape == expected_var_dicts[var_name]['shape']
