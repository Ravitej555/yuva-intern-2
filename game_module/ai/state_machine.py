"""
StateMachine - generic finite state machine for AI.

Design:
- State is a base class with on_enter / on_update / on_exit.
- StateMachine holds current state and handles transitions.
- Supports transition via string keys mapped to State classes/instances.
"""
from __future__ import annotations
from typing import Dict, Optional


class State:
    """Base state. Subclass and override callbacks."""

    name: str = "State"

    def on_enter(self, entity) -> None:
        pass

    def on_update(self, entity, dt: float) -> str | None:
        """
        Return the name of the next state to transition to, or None to stay.
        """
        return None

    def on_exit(self, entity) -> None:
        pass


class StateMachine:
    """
    Finite State Machine.

    Example:
        sm = StateMachine(entity, PatrolState())
        sm.add_state(ChaseState())
        sm.update(dt)
    """

    def __init__(self, entity, initial_state: State) -> None:
        self.entity = entity
        self.states: Dict[str, State] = {}
        self.current: State | None = None
        self.add_state(initial_state)
        self.change_state(initial_state.name)

    def add_state(self, state: State) -> None:
        self.states[state.name] = state

    def change_state(self, name: str) -> bool:
        if name not in self.states:
            return False
        if self.current is not None:
            self.current.on_exit(self.entity)
        self.current = self.states[name]
        self.current.on_enter(self.entity)
        return True

    def update(self, dt: float) -> None:
        if self.current is None:
            return
        nxt = self.current.on_update(self.entity, dt)
        if nxt is not None and nxt != self.current.name:
            self.change_state(nxt)

    @property
    def current_name(self) -> str:
        return self.current.name if self.current else "None"
