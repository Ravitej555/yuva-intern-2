"""
Player entity - uses Rigidbody + InputHandler.

Features: movement, jump with coyote time & input buffer, dash, grounded check.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from game_module.physics.vector2 import Vector2
from game_module.physics.rigidbody import Rigidbody, BodyType
from game_module.input.handler import InputHandler, Action


@dataclass
class Player:
    body: Rigidbody
    input: InputHandler
    move_speed: float = 7.0
    jump_force: float = 11.0
    dash_force: float = 14.0
    dash_cooldown: float = 0.6
    max_hp: float = 100.0
    hp: float = 100.0

    # Internal timers
    _coyote_time: float = 0.12
    _coyote_timer: float = field(default=0.0, init=False)
    _jump_buffer: float = 0.15
    _dash_timer: float = field(default=0.0, init=False)
    facing: int = field(default=1, init=False)  # 1 right, -1 left

    def update(self, dt: float) -> None:
        # Coyote timer
        if self.body.is_grounded:
            self._coyote_timer = self._coyote_time
        else:
            self._coyote_timer = max(0, self._coyote_timer - dt)

        self._dash_timer = max(0, self._dash_timer - dt)

        # Horizontal movement via forces for natural acceleration
        axis = self.input.get_axis(Action.MOVE_LEFT, Action.MOVE_RIGHT)
        if axis != 0:
            self.facing = 1 if axis > 0 else -1
            # Direct velocity control for responsive platformer feel
            target_vx = axis * self.move_speed
            # Smooth towards target
            diff = target_vx - self.body.velocity.x
            # Apply as impulse-like correction
            self.body.velocity.x += diff * min(1.0, 12 * dt)
        else:
            # Friction when no input
            self.body.velocity.x *= max(0, 1 - 8 * dt)
            if abs(self.body.velocity.x) < 0.05:
                self.body.velocity.x = 0

        # Jump: buffered + coyote
        self.input.auto_buffer_on_press(Action.JUMP, self._jump_buffer)
        can_jump = self._coyote_timer > 0 or self.body.is_grounded
        if self.input.consume_buffer(Action.JUMP) and can_jump:
            self.body.velocity.y = -self.jump_force
            self._coyote_timer = 0
            self.body.is_grounded = False

        # Dash
        if self.input.is_action_just_pressed(Action.DASH) and self._dash_timer == 0:
            self.body.add_impulse(Vector2(self.facing * self.dash_force, 0))
            self._dash_timer = self.dash_cooldown

        # Attack placeholder (could trigger hitbox)
        if self.input.is_action_just_pressed(Action.ATTACK):
            pass  # handled by game loop

    def take_damage(self, amount: float) -> None:
        self.hp = max(0, self.hp - amount)

    @property
    def is_alive(self) -> bool:
        return self.hp > 0
