"""
Behaviour states for Enemy AI.

States:
- IdleState   : wait / look around, transitions to Chase if player in range
- PatrolState : walk between waypoints
- ChaseState  : pursue player, uses steering; fails -> Search
- AttackState : melee / ranged attack with cooldown
- FleeState   : retreat when low HP
"""
from __future__ import annotations
import math
import random
from game_module.ai.state_machine import State
from game_module.physics.vector2 import Vector2


class IdleState(State):
    name = "Idle"

    def __init__(self, idle_duration: float = 1.5,
                 chase_range: float = 8.0) -> None:
        self.idle_duration = idle_duration
        self.chase_range = chase_range
        self._t = 0.0

    def on_enter(self, entity) -> None:
        self._t = 0.0
        entity.velocity_hint = Vector2.zero()

    def on_update(self, entity, dt: float) -> str | None:
        self._t += dt
        if entity.hp is not None and entity.hp < entity.max_hp * 0.25:
            return "Flee"
        # Check for player
        if entity.can_see_player(self.chase_range):
            return "Chase"
        if self._t >= self.idle_duration:
            # Randomly patrol or keep idling
            return "Patrol" if random.random() < 0.7 else None
        return None


class PatrolState(State):
    name = "Patrol"

    def __init__(self, speed: float = 3.0, chase_range: float = 8.0) -> None:
        self.speed = speed
        self.chase_range = chase_range

    def on_enter(self, entity) -> None:
        if not entity.waypoints:
            entity.waypoints = [entity.body.position.copy()]
        entity.current_waypoint_idx = getattr(entity, "current_waypoint_idx", 0)

    def on_update(self, entity, dt: float) -> str | None:
        if entity.hp is not None and entity.hp < entity.max_hp * 0.25:
            return "Flee"
        if entity.can_see_player(self.chase_range):
            return "Chase"

        target = entity.waypoints[entity.current_waypoint_idx]
        to_target = target - entity.body.position
        dist = to_target.magnitude()
        if dist < 0.4:
            entity.current_waypoint_idx = (entity.current_waypoint_idx + 1) % len(entity.waypoints)
            return None
        # Steering: desired velocity
        desired = to_target.normalized() * self.speed
        entity.velocity_hint = desired
        # Smooth move via physics
        entity.steer_towards(desired, dt)
        return None


class ChaseState(State):
    name = "Chase"

    def __init__(self, speed: float = 5.0, attack_range: float = 1.2,
                 lose_range: float = 12.0) -> None:
        self.speed = speed
        self.attack_range = attack_range
        self.lose_range = lose_range

    def on_update(self, entity, dt: float) -> str | None:
        if entity.hp is not None and entity.hp < entity.max_hp * 0.2:
            return "Flee"
        dist = entity.distance_to_player()
        if dist is None:
            return "Idle"
        if dist > self.lose_range:
            return "Idle"
        if dist <= self.attack_range:
            return "Attack"
        # Chase steering with obstacle avoidance via pathfinding if available
        if entity.path and len(entity.path) > 0:
            # Follow path waypoints
            wp = entity.path[0]
            to_wp = wp - entity.body.position
            if to_wp.magnitude() < 0.5:
                entity.path.pop(0)
                if not entity.path:
                    # Recompute path periodically
                    entity.request_path_recalc = True
            else:
                desired = to_wp.normalized() * self.speed
                entity.steer_towards(desired, dt)
                return None
        # Direct steering
        to_player = entity.player_pos - entity.body.position
        desired = to_player.normalized() * self.speed
        entity.steer_towards(desired, dt)
        # Periodically request path
        entity.path_timer = getattr(entity, "path_timer", 0) + dt
        if entity.path_timer > 0.4:
            entity.path_timer = 0
            entity.request_path_recalc = True
        return None


class AttackState(State):
    name = "Attack"

    def __init__(self, cooldown: float = 0.8, attack_range: float = 1.5,
                 damage: float = 10.0) -> None:
        self.cooldown = cooldown
        self.attack_range = attack_range
        self.damage = damage
        self._t = 0.0

    def on_enter(self, entity) -> None:
        self._t = self.cooldown  # attack immediately
        entity.velocity_hint = Vector2.zero()

    def on_update(self, entity, dt: float) -> str | None:
        self._t += dt
        dist = entity.distance_to_player()
        if dist is None or dist > self.attack_range * 1.8:
            return "Chase"
        if self._t >= self.cooldown:
            self._t = 0.0
            entity.attack_player(self.damage)
        # Face player (set velocity hint for animation)
        to_player = entity.player_pos - entity.body.position
        if to_player.magnitude_sq() > 1e-6:
            entity.facing = to_player.normalized()
        return None


class FleeState(State):
    name = "Flee"

    def __init__(self, speed: float = 6.0, safe_duration: float = 3.0) -> None:
        self.speed = speed
        self.safe_duration = safe_duration
        self._t = 0.0

    def on_enter(self, entity) -> None:
        self._t = 0.0

    def on_update(self, entity, dt: float) -> str | None:
        self._t += dt
        # Run away from player
        away = entity.body.position - entity.player_pos
        if away.magnitude_sq() < 1e-6:
            away = Vector2(1, 0)
        desired = away.normalized() * self.speed
        entity.steer_towards(desired, dt)
        if self._t >= self.safe_duration:
            # Heal a bit or go idle
            return "Idle"
        return None
