import numpy as np 
from typing import Optional

#@njit(float64(float64, float64, float64), cache=True)
def nbclip(val: float, min: float, max: float) -> float:
    if val < min:
        return min
    elif val > max:
        return max
    else:
        return val
    
#@njit(float64(float64), cache=True)
def nbabs(val: float) -> float:
    return np.abs(val)

def nbisin(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.isin(a, b)

def nblinspace(start: float, end: float, n: int) -> np.ndarray:
    return np.linspace(start, end, int(n))

def nbgeomspace(start: float, end: float, n: int) -> np.ndarray:
    log_start = np.log(start)
    log_end = np.log(end)
    linear_space = np.linspace(0, 1, int(n))
    return np.exp(log_start + linear_space * (log_end - log_start))

def geometric_weights(num: int, r: Optional[float] = None) -> np.ndarray:
    assert num > 0, "Number of weights generated cannot be <1."
    num = int(num)
    r = r if r is not None else 0.75
    powers = np.arange(num)
    weights = r ** powers
    return weights / weights.sum()
