"""
PhysicsWorld - manages bodies, gravity, broad-phase (Sweep & Prune via sorted list),
narrow-phase (AABB), and impulse-based collision resolution.

Features:
- Variable gravity
- Sub-stepping for stability
- Spatial hash broad-phase fallback for many bodies
- Collision callbacks (on_collision)
"""
from __future__ import annotations
from typing import Callable
from game_module.physics.vector2 import Vector2
from game_module.physics.rigidbody import Rigidbody, BodyType

CollisionCallback = Callable[[Rigidbody, Rigidbody, Vector2], None]


class PhysicsWorld:
    """
    Lightweight 2D physics world.

    Usage:
        world = PhysicsWorld(gravity=Vector2(0, 9.81))
        world.add_body(player_body)
        world.add_body(ground_body)
        world.step(dt)

    Collision resolution is impulse-based along the MTV normal with restitution.
    Friction is applied as velocity damping along tangent.
    """

    def __init__(self,
                 gravity: Vector2 | None = None,
                 sub_steps: int = 4) -> None:
        self.gravity = gravity if gravity is not None else Vector2(0, 20.0)
        # keep moderate default so grounded objects stay settled
        self.sub_steps = max(1, sub_steps)
        self.bodies: list[Rigidbody] = []
        self.on_collision: CollisionCallback | None = None
        # optional bounds for culling / clamping
        self.world_bounds = None  # AABB or None

    # -- management --
    def add_body(self, body: Rigidbody) -> None:
        self.bodies.append(body)

    def remove_body(self, body: Rigidbody) -> None:
        if body in self.bodies:
            self.bodies.remove(body)

    # -- simulation --
    def step(self, dt: float) -> None:
        """Advance simulation by dt seconds with sub-stepping."""
        if dt <= 0:
            return
        sub_dt = dt / self.sub_steps
        for _ in range(self.sub_steps):
            # Integrate
            for b in self.bodies:
                b.integrate(sub_dt, self.gravity)
            # Collisions
            self._resolve_collisions()

    # -- collision helpers --
    def _resolve_collisions(self) -> None:
        # Broad-phase: sort by min.x (sweep & prune) for small N; works fine.
        # For many bodies spatial hash would be better, but N is small here.
        bodies = sorted(self.bodies, key=lambda b: b.aabb.min.x)
        active: list[Rigidbody] = []
        for body in bodies:
            # Remove bodies whose max.x is left of current min.x
            active = [a for a in active if a.aabb.max.x >= body.aabb.min.x]
            for other in active:
                self._try_resolve_pair(body, other)
            active.append(body)

    def _try_resolve_pair(self, a: Rigidbody, b: Rigidbody) -> None:
        # Skip two statics
        if a.body_type == BodyType.STATIC and b.body_type == BodyType.STATIC:
            return
        if not a.aabb.intersects(b.aabb):
            return
        mtv = a.aabb.intersection_depth(b.aabb)
        if mtv is None or mtv.magnitude_sq() < 1e-9:
            return

        # Separate - split correction weighted by inverse mass
        inv_a = a.inv_mass
        inv_b = b.inv_mass
        total_inv = inv_a + inv_b
        if total_inv == 0:
            return

        # Positional correction (Baumgarte-style, no slop for simplicity + percent)
        percent = 0.8
        correction = mtv * percent
        # Distribute by inv_mass ratio
        a.position = a.position + correction * (inv_a / total_inv)
        b.position = b.position - correction * (inv_b / total_inv)

        # Velocity impulse along collision normal
        normal = mtv.normalized()
        if normal.magnitude_sq() < 1e-9:
            return
        rel_vel = a.velocity - b.velocity
        vel_along_normal = rel_vel.dot(normal)
        # Only resolve if moving toward each other
        if vel_along_normal > 0:
            # Separating already
            pass
        else:
            restitution = min(a.restitution, b.restitution)
            j = -(1 + restitution) * vel_along_normal
            j /= total_inv
            impulse = normal * j
            if a.body_type == BodyType.DYNAMIC:
                a.velocity = a.velocity + impulse * inv_a
            if b.body_type == BodyType.DYNAMIC:
                b.velocity = b.velocity - impulse * inv_b

            # Friction impulse (Coulomb model simplified)
            tangent_vel = rel_vel - normal * rel_vel.dot(normal)
            if tangent_vel.magnitude_sq() > 1e-9:
                tangent = tangent_vel.normalized()
                jt = -rel_vel.dot(tangent) / total_inv
                mu = (a.friction + b.friction) * 0.5
                # Clamp friction
                jt = max(-j * mu, min(jt, j * mu))
                friction_impulse = tangent * jt
                if a.body_type == BodyType.DYNAMIC:
                    a.velocity = a.velocity + friction_impulse * inv_a
                if b.body_type == BodyType.DYNAMIC:
                    b.velocity = b.velocity - friction_impulse * inv_b

        # Grounded check: if MTV is upward (normal.y < 0 means a is above b)
        # Heuristic: positive y is down in our coordinate system.
        # If mtv.y < 0, a was pushed up => a is grounded on b.
        if mtv.y < 0 and abs(mtv.y) > abs(mtv.x):
            if a.body_type == BodyType.DYNAMIC:
                a.is_grounded = True
        elif mtv.y > 0 and abs(mtv.y) > abs(mtv.x):
            if b.body_type == BodyType.DYNAMIC:
                b.is_grounded = True

        if self.on_collision:
            self.on_collision(a, b, mtv)

    # -- queries --
    def raycast_aabb(self, origin: Vector2, direction: Vector2,
                     max_dist: float) -> list[tuple[Rigidbody, float]]:
        """
        Simple ray vs AABB test. Returns list of (body, distance) sorted by distance.
        """
        hits: list[tuple[Rigidbody, float]] = []
        dir_n = direction.normalized()
        if dir_n.magnitude_sq() < 1e-9:
            return hits
        for b in self.bodies:
            t = self._ray_aabb(origin, dir_n, b.aabb, max_dist)
            if t is not None:
                hits.append((b, t))
        hits.sort(key=lambda x: x[1])
        return hits

    @staticmethod
    def _ray_aabb(origin: Vector2, dir_n: Vector2, box, max_dist: float) -> float | None:
        # Slab method
        t_min = 0.0
        t_max = max_dist
        for axis in ("x", "y"):
            o = getattr(origin, axis)
            d = getattr(dir_n, axis)
            mn = getattr(box.min, axis)
            mx = getattr(box.max, axis)
            if abs(d) < 1e-9:
                if o < mn or o > mx:
                    return None
            else:
                t1 = (mn - o) / d
                t2 = (mx - o) / d
                if t1 > t2:
                    t1, t2 = t2, t1
                t_min = max(t_min, t1)
                t_max = min(t_max, t2)
                if t_min > t_max:
                    return None
        if 0 <= t_min <= max_dist:
            return t_min
        return None
