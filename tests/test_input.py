"""Tests for input handler."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from game_module.input.handler import InputHandler, Action


class TestInput(unittest.TestCase):
    def test_binding_and_press(self):
        ih = InputHandler()
        ih.feed("space", True)
        ih.update(0.016)
        self.assertTrue(ih.is_action_pressed(Action.JUMP))
        self.assertTrue(ih.is_action_just_pressed(Action.JUMP))
        ih.update(0.016)
        self.assertTrue(ih.is_action_pressed(Action.JUMP))
        self.assertFalse(ih.is_action_just_pressed(Action.JUMP))
        ih.feed("space", False)
        ih.update(0.016)
        self.assertFalse(ih.is_action_pressed(Action.JUMP))
        self.assertTrue(ih.is_action_just_released(Action.JUMP))

    def test_axis(self):
        ih = InputHandler()
        ih.feed("d", True)
        ih.update(0.016)
        self.assertEqual(ih.get_axis(Action.MOVE_LEFT, Action.MOVE_RIGHT), 1.0)
        ih.feed("a", True)
        ih.update(0.016)
        self.assertEqual(ih.get_axis(Action.MOVE_LEFT, Action.MOVE_RIGHT), 0.0)

    def test_buffer(self):
        ih = InputHandler()
        ih.buffer_action(Action.JUMP, duration=0.2)
        self.assertTrue(ih.is_buffered(Action.JUMP))
        ih.update(0.1)
        self.assertTrue(ih.is_buffered(Action.JUMP))
        self.assertTrue(ih.consume_buffer(Action.JUMP))
        self.assertFalse(ih.is_buffered(Action.JUMP))

    def test_combo(self):
        ih = InputHandler()
        for k in ["a", "b", "c"]:
            ih.feed(k, True)
            ih.update(0.05)
            ih.feed(k, False)
            ih.update(0.05)
        self.assertTrue(ih.check_combo(["a", "b", "c"], max_interval=0.2))
        self.assertFalse(ih.check_combo(["x", "y"], max_interval=0.2))

    def test_rebind(self):
        ih = InputHandler()
        ih.rebind(Action.JUMP, ["j"])
        ih.feed("space", True)
        ih.update(0.016)
        self.assertFalse(ih.is_action_pressed(Action.JUMP))
        ih.feed("space", False)
        ih.feed("j", True)
        ih.update(0.016)
        self.assertTrue(ih.is_action_pressed(Action.JUMP))


if __name__ == "__main__":
    unittest.main()

