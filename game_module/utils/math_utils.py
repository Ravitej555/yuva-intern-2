"""Utility math helpers used across the module."""
from __future__ import annotations


def clamp(value: float, lo: float, hi: float) -> float:
    """Clamp value to [lo, hi]."""
    return lo if value < lo else hi if value > hi else value


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation."""
    return a + (b - a) * t


def smooth_step(t: float) -> float:
    """Smooth hermite interpolation for t in [0,1]."""
    t = clamp(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)
