import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from backend.agent.reflection import reflect_on_schedule
except ImportError:
    from agent.reflection import reflect_on_schedule


class TestFailures(unittest.TestCase):
    def test_reflection_detects_impossible_schedule(self):
        # User asks for 12 hours (720 min) of work but only has 9 hours (540 min)
        tasks = [
            {"name": "Work", "duration_minutes": 720, "fixed": False}
        ]

        schedule = [{"start": "08:00", "end": "17:00", "task": "Work"}]

        val_res = {"valid": True}  # assume validator passed basic overlap

        constraints = {"start_time": "08:00", "end_time": "17:00"}

        reflection = reflect_on_schedule(schedule, tasks, constraints, val_res)

        self.assertEqual(reflection["status"], "failed")
        self.assertIn("720 minutes of work, but only 540 minutes are available", str(reflection["issues"]))
