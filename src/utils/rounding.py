import numpy as np


time_rounding_error_decimals = 3


def assert_equals_rounded(a, b):
    a = np.round(a, time_rounding_error_decimals)
    b = np.round(b, time_rounding_error_decimals)
    assert(a == b)


def lt_rounded(a, b):
    a = np.round(a, time_rounding_error_decimals)
    b = np.round(b, time_rounding_error_decimals)
    return a < b


def eq_rounded(a, b):
    a = np.round(a, time_rounding_error_decimals)
    b = np.round(b, time_rounding_error_decimals)
    return a == b


def assert_leq_rounded(a, b):
    a = np.round(a, time_rounding_error_decimals)
    b = np.round(b, time_rounding_error_decimals)
    assert(a <= b)


def rounded(value):
    return np.round(value, time_rounding_error_decimals)

