from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

class Task(BaseModel):
    id: str
    name: str
    duration_minutes: int
    priority: str = Field(..., description="high, medium, or low")
    deadline: Optional[str] = Field(None, description="HH:MM format")
    fixed: bool = False
    start_time: Optional[str] = Field(None, description="HH:MM format, required if fixed is true")

class TimeSlot(BaseModel):
    start: str
    end: str
    duration_minutes: int

class ScheduleItem(BaseModel):
    start: str
    end: str
    task: str

class ValidationResult(BaseModel):
    valid: bool
    conflicts: List[str] = []
    unscheduled_tasks: List[str] = []
    deadline_violations: List[str] = []
    warnings: List[str] = []

class AgentAction(BaseModel):
    action: str = Field(..., description="'tool_call' or 'final'")
    tool_name: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None
    answer: Optional[str] = None

class ToolObservation(BaseModel):
    tool_name: str
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
