import numpy as np
from collections import deque

class VolatilityEstimator:
    def __init__(self, window_size):
        self.n = window_size
        self.buffer = deque([0.0] * window_size, maxlen=window_size)
        self.sum = 0.0
        self.sum_sq = 0.0
        self.count = 0

    def update(self, x_new):
        if self.count < self.n:
            x_old = 0.0
            self.count += 1
        else:
            x_old = self.buffer[0]

        self.buffer.append(x_new)
        self.sum += x_new - x_old
        self.sum_sq += x_new**2 - x_old**2

        mean = self.sum / self.count
        var = self.sum_sq / self.count - mean**2
        if var < 0 or not np.isfinite(var):
            var = 0.0
        return np.sqrt(var)
