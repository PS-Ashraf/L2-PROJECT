import json
import os
from typing import Dict, Any, List

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

def load_json_file(filename: str) -> Dict[str, Any]:
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)

def get_tasks(date: str) -> Dict[str, Any]:
    """Retrieve the user's current tasks and events."""
    tasks_data = load_json_file("tasks.json").get("tasks", [])
    events_data = load_json_file("events.json").get("events", [])
    
    # Combine tasks and events for the scheduler
    all_tasks = tasks_data + events_data
    
    return {"tasks": all_tasks}
