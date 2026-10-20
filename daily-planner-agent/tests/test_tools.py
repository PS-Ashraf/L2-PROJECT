import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.tools.availability import get_available_time, _time_to_minutes
from backend.tools.duration import estimate_task_duration
from backend.tools.scheduler import create_schedule
from backend.tools.validator import validate_schedule


class TestTools(unittest.TestCase):
    def test_duration_estimation(self):
        res1 = estimate_task_duration("Python Study")
        self.assertEqual(res1["estimated_duration_minutes"], 120)

        res2 = estimate_task_duration("Gym Workout")
        self.assertEqual(res2["estimated_duration_minutes"], 60)

    def test_scheduler_and_validator(self):
        tasks = [
            {"name": "Study", "duration_minutes": 120, "priority": "high", "fixed": False},
            {"name": "Meeting", "duration_minutes": 60, "priority": "high", "fixed": True, "start_time": "10:00"}
        ]

        # 08:00 to 12:00 -> 240 mins total
        available_slots = [
            {"start": "08:00", "end": "10:00", "duration_minutes": 120},
            {"start": "11:00", "end": "12:00", "duration_minutes": 60}
        ]

        res = create_schedule(tasks, available_slots, break_minutes=15)
        schedule = res["schedule"]

        self.assertEqual(len(schedule), 2)  # Study and Meeting
        self.assertEqual(schedule[0]["task"], "Study")
        self.assertEqual(schedule[0]["start"], "08:00")
        self.assertEqual(schedule[0]["end"], "10:00")

        val_res = validate_schedule(schedule, tasks, {"start_time": "08:00", "end_time": "12:00"})
        self.assertTrue(val_res["valid"])
        self.assertEqual(len(val_res["conflicts"]), 0)
