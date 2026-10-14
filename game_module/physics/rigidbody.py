"""
Rigidbody - simple 2D rigid body with Newtonian integration.

Supports forces, impulses, gravity, friction, restitution, and static/kinematic modes.
Uses semi-implicit Euler integration and sweep-friendly AABB.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from game_module.physics.vector2 import Vector2
from game_module.physics.aabb import AABB


class BodyType(Enum):
    DYNAMIC = auto()    # affected by forces & collisions
    KINEMATIC = auto()  # moved explicitly, infinite mass
    STATIC = auto()     # immovable


@dataclass
class Rigidbody:
    """
    Minimal rigid body.
    - mass <= 0 treated as infinite mass (static-like).
    - Use add_force for continuous forces, add_impulse for instant velocity change.
    """

    # Identity
    name: str = "body"
    body_type: BodyType = BodyType.DYNAMIC
    position: Vector2 = field(default_factory=Vector2.zero)
    velocity: Vector2 = field(default_factory=Vector2.zero)

    # Physical properties
    mass: float = 1.0
    size: Vector2 = field(default_factory=lambda: Vector2(1, 1))  # full width/height
    restitution: float = 0.2   # bounciness [0,1]
    friction: float = 0.3      # [0,1]
    drag: float = 0.01         # linear air drag
    gravity_scale: float = 1.0

    # State
    is_grounded: bool = False
    _force: Vector2 = field(default_factory=Vector2.zero, init=False, repr=False)

    @property
    def inv_mass(self) -> float:
        if self.body_type != BodyType.DYNAMIC or self.mass <= 0:
            return 0.0
        return 1.0 / self.mass

    @property
    def aabb(self) -> AABB:
        return AABB(self.position.copy(),
                    Vector2(self.size.x * 0.5, self.size.y * 0.5))

    # ---- Force application ----
    def add_force(self, force: Vector2) -> None:
        """Accumulate force for next integration step (F = m*a)."""
        if self.body_type == BodyType.DYNAMIC:
            self._force = self._force + force

    def add_impulse(self, impulse: Vector2) -> None:
        """Instant velocity change: delta_v = impulse / mass."""
        if self.body_type == BodyType.DYNAMIC and self.inv_mass > 0:
            self.velocity = self.velocity + impulse * self.inv_mass

    def add_force_at_position(self, force: Vector2, world_pos: Vector2) -> None:
        """Simplified: treat as force at center (no torque in this 2D model)."""
        self.add_force(force)

    # ---- Integration ----
    def integrate(self, dt: float, gravity: Vector2) -> None:
        """
        Semi-implicit Euler:
            v += (F/m + gravity*gravity_scale - drag*v) * dt
            p += v * dt
        """
        if self.body_type != BodyType.DYNAMIC:
            return
        # Gravity
        # a = F/m + g*scale
        accel = self._force * self.inv_mass + gravity * self.gravity_scale
        # Drag
        accel = accel + self.velocity * (-self.drag)
        self.velocity = self.velocity + accel * dt
        self.position = self.position + self.velocity * dt
        # Clear accumulator
        self._force = Vector2.zero()
        self.is_grounded = False  # reset; collision will set again

    def move_kinematic(self, delta: Vector2) -> None:
        if self.body_type == BodyType.KINEMATIC:
            self.position = self.position + delta
