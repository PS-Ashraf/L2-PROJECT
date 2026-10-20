from mcp.server.fastmcp import FastMCP
from typing import Dict, Any, List
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools import (
    get_tasks as get_tasks_impl,
    estimate_task_duration as estimate_task_duration_impl,
    get_available_time as get_available_time_impl,
    create_schedule as create_schedule_impl,
    validate_schedule as validate_schedule_impl,
)

mcp = FastMCP("DailyPlanner")

# Register tools with clean names
@mcp.tool()
def get_tasks(date: str = "") -> Dict[str, Any]:
    """Retrieve the user's current tasks and events for the day."""
    return get_tasks_impl(date)

@mcp.tool()
def estimate_task_duration(task_name: str) -> Dict[str, Any]:
    """Determine or calculate the estimated duration of tasks."""
    return estimate_task_duration_impl(task_name)

@mcp.tool()
def get_available_time(date: str = "", start_time: str = "08:00", end_time: str = "20:00") -> Dict[str, Any]:
    """Determine the user's available time slots based on start time and end time."""
    return get_available_time_impl(date, start_time, end_time)

@mcp.tool()
def create_schedule(tasks: Any = None, available_slots: Any = None, break_minutes: int = 15) -> Dict[str, Any]:
    """Create a schedule from the actual tasks and available time slots."""
    return create_schedule_impl(tasks, available_slots, break_minutes)

@mcp.tool()
def validate_schedule(schedule: Any = None, tasks: Any = None, constraints: Dict[str, Any] = None) -> Dict[str, Any]:
    """Verify the generated schedule for conflicts, unscheduled tasks, and deadline violations."""
    return validate_schedule_impl(schedule, tasks, constraints)



if __name__ == "__main__":
    mcp.run()
