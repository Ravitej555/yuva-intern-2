"""Tests for AI module."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from game_module.physics.vector2 import Vector2
from game_module.ai.pathfinding import AStarPathfinder
from game_module.ai.state_machine import StateMachine, State


class TestAI(unittest.TestCase):
    def test_astar_simple(self):
        grid = [
            [0, 0, 0],
            [0, 1, 0],
            [0, 0, 0],
        ]
        pf = AStarPathfinder(grid, cell_size=1.0)
        path = pf.find_path(Vector2(0.5, 0.5), Vector2(2.5, 2.5))
        self.assertGreater(len(path), 0)
        self.assertLess(path[0].distance_to(Vector2(0.5, 0.5)), 1e-6)
        self.assertLess(path[-1].distance_to(Vector2(2.5, 2.5)), 1e-6)

    def test_astar_blocked(self):
        grid = [
            [0, 1, 0],
            [1, 1, 1],
            [0, 1, 0],
        ]
        pf = AStarPathfinder(grid)
        path = pf.find_path(Vector2(0.5, 0.5), Vector2(2.5, 2.5))
        self.assertEqual(path, [])

    def test_astar_smoothing(self):
        grid = [[0]*10 for _ in range(10)]
        pf = AStarPathfinder(grid)
        path = pf.find_path(Vector2(0.5, 0.5), Vector2(9.5, 9.5))
        smoothed = pf.smooth_path(path)
        self.assertLessEqual(len(smoothed), len(path))

    def test_state_machine(self):
        class A(State):
            name = "A"
            def on_update(self, e, dt):
                return "B"

        class B(State):
            name = "B"

        class Entity:
            pass

        e = Entity()
        sm = StateMachine(e, A())
        sm.add_state(B())
        self.assertEqual(sm.current_name, "A")
        sm.update(0.1)
        self.assertEqual(sm.current_name, "B")


if __name__ == "__main__":
    unittest.main()

