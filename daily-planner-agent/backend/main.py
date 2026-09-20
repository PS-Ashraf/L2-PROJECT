from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from agent.loop import run_agent

app = FastAPI(title="Daily Planner Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PlanRequest(BaseModel):
    date: str
    start_time: str
    end_time: str
    tasks: List[Dict[str, Any]]
    break_minutes: int = 15
    natural_language_request: Optional[str] = None

class ChatRequest(BaseModel):
    message: str

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

@app.post("/api/plan")
async def plan_day(request: PlanRequest):
    constraints = {
        "date": request.date,
        "start_time": request.start_time,
        "end_time": request.end_time,
        "break_minutes": request.break_minutes
    }
    
    # Normally we would save tasks to data/tasks.json here or pass them as context
    import json
    import os
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)
    with open(os.path.join(data_dir, "tasks.json"), "w") as f:
        json.dump({"tasks": request.tasks}, f)
        
    prompt = request.natural_language_request or "Create a complete schedule for my day."
    
    result = await run_agent(prompt, constraints)
    
    return result

@app.post("/api/chat")
async def chat(request: ChatRequest):
    # For a pure chat request, we just pass default constraints 
    # Or extract them if we had a more complex setup
    constraints = {
        "date": "2026-09-20",
        "start_time": "08:00",
        "end_time": "20:00",
        "break_minutes": 15
    }
    result = await run_agent(request.message, constraints)
    return result
