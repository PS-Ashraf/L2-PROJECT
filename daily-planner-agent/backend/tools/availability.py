from datetime import datetime, timedelta
from typing import Dict, Any, List
from .tasks import load_json_file

def _time_to_minutes(time_str: str) -> int:
    h, m = map(int, time_str.split(':'))
    return h * 60 + m

def _minutes_to_time(minutes: int) -> str:
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"

def get_available_time(date: str, start_time: str, end_time: str) -> Dict[str, Any]:
    """Determine available time slots based on start/end time and fixed events."""
    start_min = _time_to_minutes(start_time)
    end_min = _time_to_minutes(end_time)
    
    events_data = load_json_file("events.json").get("events", [])
    
    # Sort events by start time
    fixed_events = []
    for e in events_data:
        if e.get("fixed") and e.get("start_time"):
            s_min = _time_to_minutes(e["start_time"])
            e_min = s_min + e["duration_minutes"]
            fixed_events.append((s_min, e_min))
            
    fixed_events.sort()
    
    available_slots = []
    current_time = start_min
    
    for e_start, e_end in fixed_events:
        if current_time < e_start:
            available_slots.append({
                "start": _minutes_to_time(current_time),
                "end": _minutes_to_time(e_start),
                "duration_minutes": e_start - current_time
            })
        current_time = max(current_time, e_end)
        
    if current_time < end_min:
        available_slots.append({
            "start": _minutes_to_time(current_time),
            "end": _minutes_to_time(end_min),
            "duration_minutes": end_min - current_time
        })
        
    total_available_minutes = sum(slot["duration_minutes"] for slot in available_slots)
    
    return {
        "available_slots": available_slots,
        "total_available_minutes": total_available_minutes
    }
