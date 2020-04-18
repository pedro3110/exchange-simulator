from src.utils.rounding import rounded


def approximating_time_advance(func):
    def ret(*args, **kwargs):
        return rounded(func(*args, **kwargs))
    return ret
