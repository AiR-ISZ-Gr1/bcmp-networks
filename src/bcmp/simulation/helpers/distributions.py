import numpy as np
from typing import Iterator


def poisson(lambda_: float) -> Iterator[float]:
    while True:
        yield np.random.exponential(1/lambda_)


def exponential(lambda_: float) -> Iterator[float]:
    while True:
        yield np.random.exponential(lambda_)
