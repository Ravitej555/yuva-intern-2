"""Tests for physics module."""
import sys
from pathlib import Path
import math
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from game_module.physics.vector2 import Vector2
from game_module.physics.aabb import AABB
from game_module.physics.rigidbody import Rigidbody, BodyType
from game_module.physics.world import PhysicsWorld


class TestPhysics(unittest.TestCase):
    def test_vector2(self):
        a = Vector2(3, 4)
        self.assertAlmostEqual(a.magnitude(), 5.0)
        self.assertAlmostEqual(a.normalized().magnitude(), 1.0)
        self.assertEqual(a + Vector2(1, 1), Vector2(4, 5))
        self.assertEqual(a.dot(Vector2(1, 0)), 3)
        self.assertEqual(Vector2.zero().normalized(), Vector2.zero())


    def test_aabb(self):
        b1 = AABB(Vector2(0, 0), Vector2(1, 1))
        b2 = AABB(Vector2(1.5, 0), Vector2(1, 1))
        self.assertTrue(b1.intersects(b2))
        b3 = AABB(Vector2(5, 5), Vector2(1, 1))
        self.assertFalse(b1.intersects(b3))
        mtv = b1.intersection_depth(b2)
        self.assertIsNotNone(mtv)

    def test_rigidbody_gravity(self):
        body = Rigidbody(position=Vector2(0, 0), velocity=Vector2(0, 0), mass=1.0)
        world = PhysicsWorld(gravity=Vector2(0, 10), sub_steps=1)
        world.add_body(body)
        world.step(1.0)
        self.assertGreater(body.velocity.y, 0)
        self.assertGreater(body.position.y, 0)

    def test_collision_resolution(self):
        world = PhysicsWorld(gravity=Vector2(0, 0), sub_steps=1)
        ground = Rigidbody(name="ground", body_type=BodyType.STATIC,
                           position=Vector2(0, 5), size=Vector2(10, 1))
        falling = Rigidbody(name="fall", body_type=BodyType.DYNAMIC,
                            position=Vector2(0, 3), size=Vector2(1, 1),
                            velocity=Vector2(0, 5), mass=1)
        world.add_body(ground)
        world.add_body(falling)
        for _ in range(20):
            world.step(1/60)
        # Should have collided and not penetrated
        self.assertLessEqual(falling.aabb.max.y, ground.aabb.min.y + 0.15)

    def test_impulse(self):
        b = Rigidbody(mass=2.0, velocity=Vector2(0, 0))
        b.add_impulse(Vector2(10, 0))
        self.assertAlmostEqual(b.velocity.x, 5.0)


if __name__ == "__main__":
    unittest.main()

