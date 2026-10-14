"""
Enemy entity - Rigidbody + AI StateMachine + steering.

The enemy holds a reference to player position for sensing. Pathfinding is
injected optionally (AStarPathfinder) for grid-based worlds.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from game_module.physics.vector2 import Vector2
from game_module.physics.rigidbody import Rigidbody
from game_module.physics.world import PhysicsWorld
from game_module.ai.state_machine import StateMachine
from game_module.ai.behaviours import IdleState, PatrolState, ChaseState, AttackState, FleeState
from game_module.ai.pathfinding import AStarPathfinder


@dataclass
class Enemy:
    body: Rigidbody
    player_pos: Vector2 = field(default_factory=Vector2.zero)
    max_hp: float = 60.0
    hp: float = 60.0
    waypoints: list[Vector2] = field(default_factory=list)
    current_waypoint_idx: int = 0
    facing: Vector2 = field(default_factory=lambda: Vector2(1, 0))
    velocity_hint: Vector2 = field(default_factory=Vector2.zero)
    path: list[Vector2] = field(default_factory=list)
    request_path_recalc: bool = False
    path_timer: float = 0.0
    world: Optional[PhysicsWorld] = None
    pathfinder: Optional[AStarPathfinder] = None
    sm: Optional[StateMachine] = field(default=None, init=False)
    on_attack_cb: Optional[callable] = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.sm = StateMachine(self, IdleState())
        self.sm.add_state(PatrolState())
        self.sm.add_state(ChaseState())
        self.sm.add_state(AttackState())
        self.sm.add_state(FleeState())

    # -- sensing helpers used by states --
    def distance_to_player(self) -> Optional[float]:
        return self.body.position.distance_to(self.player_pos)

    def can_see_player(self, range_: float) -> bool:
        dist = self.distance_to_player()
        if dist is None or dist > range_:
            return False
        # Optional line-of-sight via raycast
        if self.world is not None:
            direction = self.player_pos - self.body.position
            hits = self.world.raycast_aabb(self.body.position, direction, dist)
            # If first hit is not the player body, blocked - but we don't have
            # player body separately, so treat any static between as block.
            # Simplify: check pathfinder grid
            if self.pathfinder is not None:
                if not self.pathfinder._has_line_of_sight(self.body.position, self.player_pos):
                    return False
        return True

    def steer_towards(self, desired_velocity: Vector2, dt: float) -> None:
        """Apply steering force towards desired velocity."""
        steer = desired_velocity - self.body.velocity
        # Clamp steering force
        max_force = 25.0
        if steer.magnitude_sq() > max_force * max_force:
            steer = steer.normalized() * max_force
        self.body.add_force(steer * self.body.mass)
        if desired_velocity.magnitude_sq() > 1e-6:
            self.facing = desired_velocity.normalized()

    def attack_player(self, damage: float) -> None:
        if self.on_attack_cb:
            self.on_attack_cb(damage)

    def take_damage(self, amount: float) -> None:
        self.hp = max(0, self.hp - amount)

    @property
    def is_alive(self) -> bool:
        return self.hp > 0

    def update(self, dt: float, player_pos: Vector2) -> None:
        self.player_pos = player_pos
        # Path recalc
        if self.request_path_recalc and self.pathfinder is not None:
            self.request_path_recalc = False
            raw = self.pathfinder.find_path(self.body.position, self.player_pos)
            if raw:
                self.path = self.pathfinder.smooth_path(raw)
            else:
                self.path = []
        if self.sm:
            self.sm.update(dt)

    @property
    def state_name(self) -> str:
        return self.sm.current_name if self.sm else "None"
