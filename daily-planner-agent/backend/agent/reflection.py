from typing import Dict, Any, List

def reflect_on_schedule(schedule: List[Dict[str, Any]], tasks: List[Dict[str, Any]], constraints: Dict[str, Any], validation_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Reflection process to verify if the schedule actually meets constraints and 
    does not hallucinate tasks or times.
    """
    
    reflection = {
        "status": "success",
        "message": "Schedule is valid and meets all constraints.",
        "issues": []
    }
    
    if not validation_result.get("valid", False):
        reflection["status"] = "failed"
        reflection["message"] = "Schedule failed validation."
        
        for conflict in validation_result.get("conflicts", []):
            reflection["issues"].append(f"Conflict: {conflict}")
            
        for unscheduled in validation_result.get("unscheduled_tasks", []):
            reflection["issues"].append(f"Unscheduled task: {unscheduled}")
            
        for violation in validation_result.get("deadline_violations", []):
            reflection["issues"].append(f"Deadline violation: {violation}")
            
    # Additional reflection logic: Check total requested duration vs total available time
    # This prevents the LLM from trying to schedule 12 hours of work in 9 hours.
    total_task_minutes = sum(t.get("duration_minutes", 0) for t in tasks if not t.get("fixed"))
    
    # Calculate available minutes (very simplified for reflection)
    try:
        from ..tools.availability import _time_to_minutes
    except (ImportError, ValueError):
        from tools.availability import _time_to_minutes
    if "start_time" in constraints and "end_time" in constraints:
        day_start = _time_to_minutes(constraints["start_time"])
        day_end = _time_to_minutes(constraints["end_time"])
        total_day_minutes = day_end - day_start
        
        fixed_time = sum(t.get("duration_minutes", 0) for t in tasks if t.get("fixed"))
        available = total_day_minutes - fixed_time
        
        if total_task_minutes > available:
            reflection["status"] = "failed"
            reflection["issues"].append(f"Requested {total_task_minutes} minutes of work, but only {available} minutes are available.")
            
    if reflection["status"] == "failed":
        reflection["message"] = "The schedule cannot be fully accommodated due to constraints."
        
    return reflection
