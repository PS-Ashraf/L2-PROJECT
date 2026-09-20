from typing import Dict, Any, List
from .availability import _time_to_minutes, _minutes_to_time

def create_schedule(tasks: Any, available_slots: Any, break_minutes: int = 15) -> Dict[str, Any]:
    """Create a schedule from actual tasks and available time."""
    schedule = []
    unscheduled = []
    
    # Handle dict or list formats gracefully
    if isinstance(tasks, dict):
        tasks = tasks.get("tasks", [])
    if not isinstance(tasks, list):
        tasks = []
        
    if isinstance(available_slots, dict):
        available_slots = available_slots.get("available_slots", [])
    if not isinstance(available_slots, list):
        available_slots = []
        
    try:
        break_minutes = int(break_minutes)
    except (ValueError, TypeError):
        break_minutes = 15
        
    # If tasks are empty, try to load from tasks.json
    if not tasks:
        from .tasks import load_json_file
        tasks = load_json_file("tasks.json").get("tasks", [])
        
    # If available_slots are empty, create a default slot 08:00 - 20:00
    if not available_slots:
        available_slots = [{"start": "08:00", "end": "20:00", "duration_minutes": 720}]
    
    # Separate fixed vs flexible
    fixed_tasks = [t for t in tasks if isinstance(t, dict) and t.get("fixed")]
    flexible_tasks = [t for t in tasks if isinstance(t, dict) and not t.get("fixed")]
    
    # Sort flexible tasks by priority (high > medium > low) and deadline
    priority_order = {"high": 1, "medium": 2, "low": 3}
    flexible_tasks.sort(key=lambda x: (
        priority_order.get(x.get("priority", "medium"), 2),
        _time_to_minutes(x["deadline"]) if x.get("deadline") else 9999
    ))
    
    # Add fixed tasks directly to schedule
    for t in fixed_tasks:
        start_min = _time_to_minutes(t["start_time"])
        end_min = start_min + t["duration_minutes"]
        schedule.append({
            "start": t["start_time"],
            "end": _minutes_to_time(end_min),
            "task": t["name"]
        })
        
    # Keep track of available slots state
    slots = [{"start_min": _time_to_minutes(s["start"]), "end_min": _time_to_minutes(s["end"])} for s in available_slots]
    
    for task in flexible_tasks:
        task_dur = task["duration_minutes"]
        scheduled = False
        
        for i, slot in enumerate(slots):
            slot_dur = slot["end_min"] - slot["start_min"]
            
            # Check if task fits in slot
            if slot_dur >= task_dur:
                start_str = _minutes_to_time(slot["start_min"])
                end_str = _minutes_to_time(slot["start_min"] + task_dur)
                
                schedule.append({
                    "start": start_str,
                    "end": end_str,
                    "task": task["name"]
                })
                
                # Update slot
                slot["start_min"] += task_dur
                
                # Add break if possible
                if slot["end_min"] - slot["start_min"] >= break_minutes:
                    break_end = slot["start_min"] + break_minutes
                    schedule.append({
                        "start": _minutes_to_time(slot["start_min"]),
                        "end": _minutes_to_time(break_end),
                        "task": "Break"
                    })
                    slot["start_min"] = break_end
                    
                scheduled = True
                break
                
        if not scheduled:
            unscheduled.append(task)
            
    schedule.sort(key=lambda x: _time_to_minutes(x["start"]))
    
    return {
        "schedule": schedule,
        "unscheduled_tasks": unscheduled
    }
