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

import httpx
from fastapi.responses import JSONResponse
from fastapi import status
from config import settings

@app.get("/api/health")
async def health_check():
    """
    Active system health check for backend API and Ollama LLM provider.

    Response fields:
        - status: "ok" if all services healthy, otherwise "degraded"
        - backend: "ok"
        - ollama: object containing host, model, status ("ok"|"unavailable"|"degraded"), and error if any

    Returns:
        HTTP 200: All components healthy.
        HTTP 503: Critical dependency (Ollama) unavailable.
    """
    ollama_info = {
        "status": "unknown",
        "host": settings.OLLAMA_HOST,
        "model": settings.OLLAMA_MODEL
    }
    is_healthy = True

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.OLLAMA_HOST}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                model_found = any(settings.OLLAMA_MODEL in m for m in models)
                ollama_info["status"] = "ok"
                ollama_info["model_found"] = model_found
                if not model_found:
                    ollama_info["warning"] = f"Model '{settings.OLLAMA_MODEL}' not found in installed models: {models}"
            else:
                is_healthy = False
                ollama_info["status"] = "degraded"
                ollama_info["error"] = f"Ollama returned HTTP status {resp.status_code}"
    except httpx.ConnectError:
        is_healthy = False
        ollama_info["status"] = "unavailable"
        ollama_info["error"] = f"Connection refused to Ollama server at {settings.OLLAMA_HOST}"
    except httpx.TimeoutException:
        is_healthy = False
        ollama_info["status"] = "unavailable"
        ollama_info["error"] = f"Connection timed out connecting to Ollama server at {settings.OLLAMA_HOST}"
    except Exception as e:
        is_healthy = False
        ollama_info["status"] = "unavailable"
        err_msg = str(e).strip() or type(e).__name__
        ollama_info["error"] = f"Unable to reach Ollama: {err_msg}"

    payload = {
        "status": "ok" if is_healthy else "degraded",
        "backend": "ok",
        "ollama": ollama_info
    }

    status_code = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status_code, content=payload)


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
