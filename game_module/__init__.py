"""
Game Module - Week 2 Deliverable
A modular game framework combining Physics, AI, and Input handling.

Author: Week 2 Task Submission
Language: Python 3.10+
No external dependencies required for core simulation.
Optional: pygame for visual demo (pip install pygame)
"""

__version__ = "1.0.0"
__author__ = "Week 2 Submission"

from game_module.physics import Vector2, AABB, Rigidbody, PhysicsWorld
from game_module.ai import StateMachine, State, AStarPathfinder
from game_module.input import InputHandler, Action, BufferedInput

__all__ = [
    "Vector2", "AABB", "Rigidbody", "PhysicsWorld",
    "StateMachine", "State", "AStarPathfinder",
    "InputHandler", "Action", "BufferedInput",
]
