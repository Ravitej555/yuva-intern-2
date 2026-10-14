"""
Vector2 - 2D vector math for physics and gameplay.

Uses operator overloading and provides common game-math utilities.
"""
from __future__ import annotations
import math


class Vector2:
    """Immutable-friendly 2D vector. Mutable via in-place ops for perf."""

    __slots__ = ("x", "y")

    def __init__(self, x: float = 0.0, y: float = 0.0) -> None:
        self.x = float(x)
        self.y = float(y)

    # --- Factory ---
    @staticmethod
    def zero() -> Vector2:
        return Vector2(0, 0)

    @staticmethod
    def one() -> Vector2:
        return Vector2(1, 1)

    @staticmethod
    def from_angle(angle_rad: float, magnitude: float = 1.0) -> Vector2:
        return Vector2(math.cos(angle_rad) * magnitude,
                       math.sin(angle_rad) * magnitude)

    # --- Arithmetic ---
    def __add__(self, other: Vector2) -> Vector2:
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vector2) -> Vector2:
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Vector2:
        return Vector2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> Vector2:
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> Vector2:
        return Vector2(self.x / scalar, self.y / scalar)

    def __neg__(self) -> Vector2:
        return Vector2(-self.x, -self.y)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vector2):
            return NotImplemented
        return math.isclose(self.x, other.x, abs_tol=1e-6) and \
               math.isclose(self.y, other.y, abs_tol=1e-6)

    def __repr__(self) -> str:
        return f"Vector2({self.x:.3f}, {self.y:.3f})"

    # --- Vector operations ---
    def dot(self, other: Vector2) -> float:
        """Dot product."""
        return self.x * other.x + self.y * other.y

    def cross(self, other: Vector2) -> float:
        """2D cross product (scalar z-component)."""
        return self.x * other.y - self.y * other.x

    def magnitude(self) -> float:
        return math.hypot(self.x, self.y)

    def magnitude_sq(self) -> float:
        return self.x * self.x + self.y * self.y

    def normalized(self) -> Vector2:
        """Return unit vector. Zero vector returns zero."""
        mag = self.magnitude()
        if mag < 1e-9:
            return Vector2.zero()
        return self / mag

    def distance_to(self, other: Vector2) -> float:
        return (other - self).magnitude()

    def angle(self) -> float:
        """Angle in radians from +X axis."""
        return math.atan2(self.y, self.x)

    def lerp(self, other: Vector2, t: float) -> Vector2:
        return Vector2(self.x + (other.x - self.x) * t,
                       self.y + (other.y - self.y) * t)

    def clamp_magnitude(self, max_len: float) -> Vector2:
        sq = self.magnitude_sq()
        if sq > max_len * max_len:
            return self.normalized() * max_len
        return Vector2(self.x, self.y)

    def copy(self) -> Vector2:
        return Vector2(self.x, self.y)

    def to_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)
