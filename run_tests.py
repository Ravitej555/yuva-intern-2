"""
Test Runner for Game Module.
Discovers and executes all unit and integration tests across tests/.
Compatible with both standard unittest and pytest.
"""
import sys
import unittest
from pathlib import Path

# Ensure root directory is in sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def run_all_tests():
    print("=" * 70)
    print("          GAME MODULE - COMPREHENSIVE TEST SUITE RUNNER")
    print("=" * 70)
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(ROOT_DIR / "tests"), pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 70)
    print(f"Tests Run:      {result.testsRun}")
    print(f"Failures:       {len(result.failures)}")
    print(f"Errors:         {len(result.errors)}")
    print(f"Success Status: {'PASSED [OK]' if result.wasSuccessful() else 'FAILED'}")
    print("=" * 70)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
