"""
InputHandler - dynamic input mapping with buffering, combos, and rebinding.

Features:
- Action-based mapping (e.g., "jump" -> [SPACE, W, GAMEPAD_A])
- is_pressed / is_just_pressed / is_just_released
- Input buffering (e.g., jump buffer for platformers)
- Stateful key tracking without requiring a windowing library
- feed() method for pumping raw key events; integrates with pygame / keyboard hooks
- Combo detection (sequence within time window)
"""
from __future__ import annotations
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto


class Action(Enum):
    MOVE_LEFT = auto()
    MOVE_RIGHT = auto()
    MOVE_UP = auto()
    MOVE_DOWN = auto()
    JUMP = auto()
    DASH = auto()
    ATTACK = auto()
    INTERACT = auto()
    PAUSE = auto()


@dataclass
class KeyState:
    pressed: bool = False
    just_pressed: bool = False
    just_released: bool = False
    press_time: float = 0.0
    buffer_until: float = 0.0


@dataclass
class BufferedInput:
    """Buffered action that stays active for a short window after press."""
    action: Action
    duration: float = 0.15  # seconds


class InputHandler:
    """
    Action-centric input handler.

    Usage:
        handler = InputHandler()
        handler.bind(Action.JUMP, ["space", "w", "up"])
        handler.feed("space", pressed=True)   # on keydown
        handler.update(dt)
        if handler.is_action_pressed(Action.JUMP):
            player.jump()
        if handler.consume_buffer(Action.JUMP):
            # buffered jump (coyote / input buffer)
            player.jump()
    """

    def __init__(self) -> None:
        # action -> set of key names (lowercase)
        self.bindings: dict[Action, set[str]] = {}
        # key -> KeyState
        self._keys: dict[str, KeyState] = {}
        # action -> KeyState-like aggregated state
        self._action_state: dict[Action, KeyState] = {}
        # buffer
        self._buffers: dict[Action, float] = {}  # action -> expiry time
        self._time: float = 0.0
        # combo history: deque of (key, time)
        self._history: deque[tuple[str, float]] = deque(maxlen=32)

        # Default bindings
        self.bind(Action.MOVE_LEFT, ["a", "left", "arrow_left"])
        self.bind(Action.MOVE_RIGHT, ["d", "right", "arrow_right"])
        self.bind(Action.MOVE_UP, ["w", "up", "arrow_up"])
        self.bind(Action.MOVE_DOWN, ["s", "down", "arrow_down"])
        self.bind(Action.JUMP, ["space", "w", "up"])
        self.bind(Action.DASH, ["shift", "left_shift", "right_shift"])
        self.bind(Action.ATTACK, ["j", "mouse_left", "ctrl"])
        self.bind(Action.INTERACT, ["e", "enter"])
        self.bind(Action.PAUSE, ["escape", "p"])

    # -- binding --
    def bind(self, action: Action, keys: list[str]) -> None:
        self.bindings[action] = {k.lower() for k in keys}
        if action not in self._action_state:
            self._action_state[action] = KeyState()

    def rebind(self, action: Action, keys: list[str]) -> None:
        self.bind(action, keys)

    def add_binding(self, action: Action, key: str) -> None:
        self.bindings.setdefault(action, set()).add(key.lower())

    # -- feeding raw events --
    def feed(self, key: str, pressed: bool) -> None:
        """
        Feed a raw key event. key is case-insensitive name.
        Call this from your windowing / pygame event loop.
        """
        k = key.lower().strip()
        st = self._keys.get(k)
        if st is None:
            st = KeyState()
            self._keys[k] = st
        if pressed:
            if not st.pressed:
                st.just_pressed = True
                st.press_time = self._time
                self._history.append((k, self._time))
            st.pressed = True
        else:
            if st.pressed:
                st.just_released = True
            st.pressed = False

    def feed_text(self, text: str) -> None:
        """Feed multiple keys from a string like 'wd ' (space included)."""
        for ch in text:
            self.feed(ch, True)

    # -- per-frame update --
    def update(self, dt: float) -> None:
        self._time += dt
        # Aggregate per-action state
        for action, keys in self.bindings.items():
            astate = self._action_state[action]
            # Reset transient flags before recomputing
            prev_pressed = astate.pressed
            any_pressed = False
            any_just_pressed = False
            any_just_released = False
            for k in keys:
                ks = self._keys.get(k)
                if ks is None:
                    continue
                if ks.pressed:
                    any_pressed = True
                if ks.just_pressed:
                    any_just_pressed = True
                if ks.just_released:
                    any_just_released = True
            astate.pressed = any_pressed
            astate.just_pressed = any_just_pressed
            astate.just_released = any_just_released
            if any_just_pressed:
                astate.press_time = self._time

        # Clear per-key transient flags
        for ks in self._keys.values():
            ks.just_pressed = False
            ks.just_released = False

        # Expire buffers
        expired = [a for a, exp in self._buffers.items() if self._time >= exp]
        for a in expired:
            del self._buffers[a]

    # -- queries --
    def is_action_pressed(self, action: Action) -> bool:
        return self._action_state.get(action, KeyState()).pressed

    def is_action_just_pressed(self, action: Action) -> bool:
        return self._action_state.get(action, KeyState()).just_pressed

    def is_action_just_released(self, action: Action) -> bool:
        return self._action_state.get(action, KeyState()).just_released

    def is_key_pressed(self, key: str) -> bool:
        ks = self._keys.get(key.lower())
        return ks.pressed if ks else False

    def get_axis(self, negative: Action, positive: Action) -> float:
        """Return -1, 0, or 1 for axis pair (e.g., left/right)."""
        v = 0.0
        if self.is_action_pressed(positive):
            v += 1.0
        if self.is_action_pressed(negative):
            v -= 1.0
        return v

    def get_vector(self) -> tuple[float, float]:
        """Return normalized-ish movement vector from WASD/arrows."""
        x = self.get_axis(Action.MOVE_LEFT, Action.MOVE_RIGHT)
        y = self.get_axis(Action.MOVE_UP, Action.MOVE_DOWN)
        # Note: y negative is up if needed; keep as is
        return (x, y)

    # -- buffering --
    def buffer_action(self, action: Action, duration: float = 0.15) -> None:
        """Buffer an action so it can be consumed shortly after press."""
        self._buffers[action] = self._time + duration

    def is_buffered(self, action: Action) -> bool:
        return action in self._buffers

    def consume_buffer(self, action: Action) -> bool:
        """Consume buffered action if present. Returns True if consumed."""
        if action in self._buffers:
            del self._buffers[action]
            return True
        return False

    def auto_buffer_on_press(self, action: Action, duration: float = 0.15) -> None:
        """If action was just pressed this frame, buffer it."""
        if self.is_action_just_pressed(action):
            self.buffer_action(action, duration)

    # -- combo detection --
    def check_combo(self, sequence: list[str], max_interval: float = 0.5,
                    window: float = 1.5) -> bool:
        """
        Check if the last keys in history match the sequence within timing.
        sequence: list of key names in order.
        max_interval: max time between consecutive keys.
        window: total window for sequence.
        """
        if len(self._history) < len(sequence):
            return False
        # Take last N entries
        recent = list(self._history)[-len(sequence):]
        keys = [k for k, _ in recent]
        times = [t for _, t in recent]
        # Check key match
        seq_lower = [s.lower() for s in sequence]
        if keys != seq_lower:
            return False
        # Check timing
        if times[-1] - times[0] > window:
            return False
        for i in range(1, len(times)):
            if times[i] - times[i - 1] > max_interval:
                return False
        return True

    def clear_history(self) -> None:
        self._history.clear()

    # -- debug --
    def debug_state(self) -> str:
        lines = [f"time={self._time:.2f}"]
        for action in Action:
            st = self._action_state.get(action)
            if st and st.pressed:
                lines.append(f"  {action.name}: pressed")
        if self._buffers:
            lines.append(f"  buffers: {[a.name for a in self._buffers]}")
        return "\n".join(lines)
