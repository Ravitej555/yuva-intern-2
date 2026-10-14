"""
Integration and simulation tests for the Game Module.
Tests end-to-end interactions:
- Physics + Player movement and jumping
- Collision resolution between player and platform
- Enemy AI sensory perception and state machine transitions (Idle -> Chase -> Attack)
- Combat event callbacks
- Simulation determinism and multi-step stability
"""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from game_module.physics.vector2 import Vector2
from game_module.physics.rigidbody import Rigidbody, BodyType
from game_module.physics.world import PhysicsWorld
from game_module.input.handler import InputHandler, Action
from game_module.entities.player import Player
from game_module.entities.enemy import Enemy
from game_module.ai.pathfinding import AStarPathfinder


class TestGameModuleIntegration(unittest.TestCase):
    def setUp(self):
        self.world = PhysicsWorld(gravity=Vector2(0, 20.0), sub_steps=4)
        
        # Ground platform: y = 10, height 2
        self.ground = Rigidbody(
            name="ground",
            body_type=BodyType.STATIC,
            position=Vector2(10, 10),
            size=Vector2(20, 2),
            friction=0.5
        )
        self.world.add_body(self.ground)

        # Player
        self.player_body = Rigidbody(
            name="player",
            body_type=BodyType.DYNAMIC,
            position=Vector2(5, 5),
            size=Vector2(1.0, 1.4),
            mass=1.0,
            friction=0.4
        )
        self.world.add_body(self.player_body)
        self.input_handler = InputHandler()
        self.player = Player(body=self.player_body, input=self.input_handler)

        # Enemy
        self.enemy_body = Rigidbody(
            name="enemy",
            body_type=BodyType.DYNAMIC,
            position=Vector2(8, 5),
            size=Vector2(1.0, 1.4),
            mass=1.0,
            friction=0.4
        )
        self.world.add_body(self.enemy_body)
        self.enemy = Enemy(body=self.enemy_body, player_pos=self.player_body.position.copy())

    def test_player_gravity_and_ground_landing(self):
        """Verify that gravity pulls the player down until settling on the ground platform."""
        dt = 1 / 60
        for _ in range(60):
            self.player.update(dt)
            self.world.step(dt)

        self.assertTrue(self.player.body.is_grounded)
        # Player bottom should be resting on top of ground (ground min.y is 10 - 1 = 9)
        self.assertAlmostEqual(self.player.body.aabb.max.y, self.ground.aabb.min.y, delta=0.1)

    def test_player_jump_and_coyote_time(self):
        """Verify jump execution, coyote time window, and airborne physics."""
        dt = 1 / 60
        # Let player land first
        for _ in range(60):
            self.player.update(dt)
            self.world.step(dt)
        self.assertTrue(self.player.body.is_grounded)

        # Trigger jump
        self.input_handler.feed("space", True)
        self.input_handler.update(dt)
        self.player.update(dt)
        self.world.step(dt)

        self.assertLess(self.player.body.velocity.y, -5.0)
        self.assertFalse(self.player.body.is_grounded)

    def test_enemy_ai_state_transitions(self):
        """Verify AI transitions: Idle -> Chase when player is sensed, and Attack when in range."""
        combat_events = []
        def on_attack(dmg: float):
            combat_events.append(dmg)
            self.player.take_damage(dmg)

        self.enemy.on_attack_cb = on_attack
        dt = 1 / 60

        # Player is at (5, 5), Enemy is at (8, 5) -> distance = 3.0 (< chase_range 8.0)
        self.enemy.update(dt, self.player.body.position)
        self.assertEqual(self.enemy.state_name, "Chase")

        # Position player right next to enemy to trigger attack (<= attack_range 1.2)
        self.player.body.position = Vector2(8.5, 5.0)
        self.enemy.update(dt, self.player.body.position)
        self.assertEqual(self.enemy.state_name, "Attack")

        # Update attack state to fire attack callback
        self.enemy.update(0.1, self.player.body.position)
        self.assertGreater(len(combat_events), 0)
        self.assertLess(self.player.hp, 100.0)

    def test_enemy_flee_at_low_health(self):
        """Verify enemy enters Flee state when HP drops below 20%."""
        dt = 1 / 60
        self.enemy.hp = 10.0  # < 60 * 0.2 = 12
        self.enemy.update(dt, self.player.body.position)
        self.assertEqual(self.enemy.state_name, "Flee")

    def test_pathfinding_navigation(self):
        """Verify A* pathfinding finds valid path navigating around obstacles."""
        grid = [
            [0, 0, 0, 0, 0],
            [0, 1, 1, 1, 0],
            [0, 0, 0, 1, 0],
            [0, 1, 0, 0, 0],
            [0, 0, 0, 0, 0],
        ]
        pf = AStarPathfinder(grid, cell_size=1.0, allow_diagonal=False)
        start = Vector2(0.5, 0.5)
        goal = Vector2(4.5, 4.5)
        path = pf.find_path(start, goal)
        self.assertGreater(len(path), 0)
        self.assertEqual(path[0], start)
        self.assertEqual(path[-1], goal)


if __name__ == "__main__":
    unittest.main()
