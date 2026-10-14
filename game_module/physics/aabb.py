"""
AABB - Axis-Aligned Bounding Box for collision detection.
"""
from __future__ import annotations
from dataclasses import dataclass
from game_module.physics.vector2 import Vector2


@dataclass
class AABB:
    """AABB defined by center and half-extents."""

    center: Vector2
    half_size: Vector2  # half-width, half-height

    @property
    def min(self) -> Vector2:
        return Vector2(self.center.x - self.half_size.x,
                       self.center.y - self.half_size.y)

    @property
    def max(self) -> Vector2:
        return Vector2(self.center.x + self.half_size.x,
                       self.center.y + self.half_size.y)

    @property
    def width(self) -> float:
        return self.half_size.x * 2

    @property
    def height(self) -> float:
        return self.half_size.y * 2

    @classmethod
    def from_min_max(cls, min_pt: Vector2, max_pt: Vector2) -> AABB:
        center = Vector2((min_pt.x + max_pt.x) * 0.5,
                         (min_pt.y + max_pt.y) * 0.5)
        half = Vector2((max_pt.x - min_pt.x) * 0.5,
                       (max_pt.y - min_pt.y) * 0.5)
        return cls(center, half)

    def contains_point(self, pt: Vector2) -> bool:
        mi, ma = self.min, self.max
        return mi.x <= pt.x <= ma.x and mi.y <= pt.y <= ma.y

    def intersects(self, other: AABB) -> bool:
        """AABB-AABB overlap test."""
        return abs(self.center.x - other.center.x) <= (self.half_size.x + other.half_size.x) and \
               abs(self.center.y - other.center.y) <= (self.half_size.y + other.half_size.y)

    def intersection_depth(self, other: AABB) -> Vector2 | None:
        """
        Returns minimum translation vector (MTV) to separate self from other.
        None if not intersecting.
        """
        if not self.intersects(other):
            return None
        dx = self.center.x - other.center.x
        px = (self.half_size.x + other.half_size.x) - abs(dx)
        dy = self.center.y - other.center.y
        py = (self.half_size.y + other.half_size.y) - abs(dy)
        if px < py:
            return Vector2(px * (1 if dx > 0 else -1), 0)
        else:
            return Vector2(0, py * (1 if dy > 0 else -1))

    def expanded(self, amount: float) -> AABB:
        return AABB(self.center.copy(),
                    Vector2(self.half_size.x + amount, self.half_size.y + amount))
