from collections.abc import Iterable
from typing import Protocol

import numpy as np


class Coordinate2D(Protocol):
    x: float
    y: float


def angle_degrees(a: Coordinate2D, vertex: Coordinate2D, c: Coordinate2D) -> float:
    """Return the smaller angle ABC in degrees."""
    first = np.array([a.x - vertex.x, a.y - vertex.y], dtype=float)
    second = np.array([c.x - vertex.x, c.y - vertex.y], dtype=float)
    denominator = np.linalg.norm(first) * np.linalg.norm(second)
    if denominator == 0:
        raise ValueError("Cannot calculate an angle from coincident points")
    cosine = float(np.clip(np.dot(first, second) / denominator, -1, 1))
    return float(np.degrees(np.arccos(cosine)))


def moving_average(values: Iterable[float], window: int = 5) -> np.ndarray:
    data = np.asarray(list(values), dtype=float)
    if data.size < window:
        return data
    padding = window // 2
    padded = np.pad(data, (padding, padding), mode="edge")
    return np.convolve(padded, np.ones(window) / window, mode="valid")[: data.size]
