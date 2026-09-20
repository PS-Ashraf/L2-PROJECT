def estimate_task_duration(task_name: str) -> dict:
    """Determine or calculate the estimated duration of a task."""
    
    # Simple deterministic logic for demonstration
    name_lower = task_name.lower()
    if "meeting" in name_lower:
        duration = 60
    elif "study" in name_lower:
        duration = 120
    elif "gym" in name_lower or "workout" in name_lower:
        duration = 60
    elif "break" in name_lower or "lunch" in name_lower:
        duration = 60
    else:
        duration = 90 # default

    return {
        "task_name": task_name,
        "estimated_duration_minutes": duration
    }
