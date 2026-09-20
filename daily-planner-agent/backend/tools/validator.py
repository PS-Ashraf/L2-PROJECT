from typing import Dict, Any, List
from .availability import _time_to_minutes

def validate_schedule(schedule: Any, tasks: Any, constraints: Dict[str, Any] = None) -> Dict[str, Any]:
    """Verify the generated schedule."""
    conflicts = []
    unscheduled = []
    deadline_violations = []
    warnings = []
    
    if isinstance(schedule, dict):
        schedule = schedule.get("schedule", [])
    if not isinstance(schedule, list):
        schedule = []
        
    if isinstance(tasks, dict):
        tasks = tasks.get("tasks", [])
    if not isinstance(tasks, list):
        from .tasks import load_json_file
        tasks = load_json_file("tasks.json").get("tasks", [])
        
    if constraints is None or not isinstance(constraints, dict):
        constraints = {}
    
    # Map tasks by name for easy lookup
    task_map = {t["name"]: t for t in tasks}
    
    # 1. Check overlaps
    sorted_schedule = sorted(schedule, key=lambda x: _time_to_minutes(x["start"]))
    for i in range(len(sorted_schedule) - 1):
        curr_item = sorted_schedule[i]
        next_item = sorted_schedule[i+1]
        
        curr_end = _time_to_minutes(curr_item["end"])
        next_start = _time_to_minutes(next_item["start"])
        
        if curr_end > next_start:
            conflicts.append(f"Overlap between {curr_item['task']} and {next_item['task']}")
            
    # 2. Check missing/unscheduled tasks & deadlines
    scheduled_task_names = set(item["task"] for item in schedule)
    
    for task in tasks:
        name = task["name"]
        if name not in scheduled_task_names:
            unscheduled.append(name)
        else:
            # Check deadline
            if task.get("deadline"):
                deadline_min = _time_to_minutes(task["deadline"])
                # Find when this task ends in schedule
                for item in schedule:
                    if item["task"] == name:
                        end_min = _time_to_minutes(item["end"])
                        if end_min > deadline_min:
                            deadline_violations.append(f"{name} ends at {item['end']}, past deadline {task['deadline']}")
                            
    # 3. Check allowed hours
    if "start_time" in constraints and "end_time" in constraints:
        day_start = _time_to_minutes(constraints["start_time"])
        day_end = _time_to_minutes(constraints["end_time"])
        for item in schedule:
            s = _time_to_minutes(item["start"])
            e = _time_to_minutes(item["end"])
            if s < day_start or e > day_end:
                warnings.append(f"Task {item['task']} is outside allowed hours ({constraints['start_time']} - {constraints['end_time']})")
                
    valid = len(conflicts) == 0 and len(unscheduled) == 0 and len(deadline_violations) == 0
    
    return {
        "valid": valid,
        "conflicts": conflicts,
        "unscheduled_tasks": unscheduled,
        "deadline_violations": deadline_violations,
        "warnings": warnings
    }
