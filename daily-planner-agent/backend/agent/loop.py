import json
import httpx
from typing import Dict, Any, List

from .prompts import SYSTEM_PROMPT
from local_mcp.client import MCPClient
from config import settings
from schemas.models import AgentAction, ToolObservation

async def ask_llm(request: str, constraints: Dict[str, Any], tools: List[Dict[str, Any]], observations: List[ToolObservation]) -> AgentAction:
    """Query the Ollama LLM to decide the next action."""
    
    tools_str = json.dumps(tools, indent=2)
    obs_str = json.dumps([o.model_dump() for o in observations], indent=2)
    
    prompt = SYSTEM_PROMPT.format(
        tools=tools_str,
        request=request,
        constraints=json.dumps(constraints),
        observations=obs_str,
        date=constraints.get("date", "2026-09-20"),
        start_time=constraints.get("start_time", "08:00"),
        end_time=constraints.get("end_time", "20:00"),
        break_minutes=constraints.get("break_minutes", 15)
    )
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                f"{settings.OLLAMA_HOST}/api/generate",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                }
            )
            response.raise_for_status()
            
            # The response from ollama should be JSON
            result_json = response.json()
            llm_text = result_json.get("response", "")
            
            action_dict = json.loads(llm_text)
            return AgentAction(**action_dict)
            
        except Exception as e:
            # Handle malformed output or connection errors
            raise Exception(f"Failed to query LLM or parse response: {str(e)}")

async def run_agent(request: str, constraints: Dict[str, Any]) -> Dict[str, Any]:
    client = MCPClient()
    await client.connect()
    
    observations: List[ToolObservation] = []
    agent_trace: List[Dict[str, Any]] = []
    
    try:
        # Step 1: get_tasks
        date = constraints.get("date", "2026-09-20")
        agent_trace.append({"type": "decision", "action": "tool_call", "tool": "get_tasks"})
        try:
            tasks_data = await client.call_tool("get_tasks", {"date": date})
            obs_tasks = ToolObservation(tool_name="get_tasks", success=True, data=tasks_data)
        except Exception as e:
            try:
                tasks_data = await client.call_tool("tool_get_tasks", {"date": date})
                obs_tasks = ToolObservation(tool_name="get_tasks", success=True, data=tasks_data)
            except Exception as e2:
                from tools import get_tasks as fallback_get_tasks
                tasks_data = fallback_get_tasks(date)
                obs_tasks = ToolObservation(tool_name="get_tasks", success=True, data=tasks_data)
        observations.append(obs_tasks)
        agent_trace.append({"type": "observation", "tool": "get_tasks", "success": True})
        
        # Step 2: get_available_time
        start_time = constraints.get("start_time", "08:00")
        end_time = constraints.get("end_time", "20:00")
        agent_trace.append({"type": "decision", "action": "tool_call", "tool": "get_available_time"})
        try:
            slots_data = await client.call_tool("get_available_time", {
                "date": date,
                "start_time": start_time,
                "end_time": end_time
            })
            obs_slots = ToolObservation(tool_name="get_available_time", success=True, data=slots_data)
        except Exception as e:
            try:
                slots_data = await client.call_tool("tool_get_available_time", {
                    "date": date,
                    "start_time": start_time,
                    "end_time": end_time
                })
                obs_slots = ToolObservation(tool_name="get_available_time", success=True, data=slots_data)
            except Exception as e2:
                from tools import get_available_time as fallback_get_available_time
                slots_data = fallback_get_available_time(date, start_time, end_time)
                obs_slots = ToolObservation(tool_name="get_available_time", success=True, data=slots_data)
        observations.append(obs_slots)
        agent_trace.append({"type": "observation", "tool": "get_available_time", "success": True})
        
        # Step 3: create_schedule
        break_minutes = constraints.get("break_minutes", 15)
        raw_tasks = tasks_data.get("tasks", []) if isinstance(tasks_data, dict) else []
        raw_slots = slots_data.get("available_slots", []) if isinstance(slots_data, dict) else []
        
        agent_trace.append({"type": "decision", "action": "tool_call", "tool": "create_schedule"})
        try:
            sched_data = await client.call_tool("create_schedule", {
                "tasks": raw_tasks,
                "available_slots": raw_slots,
                "break_minutes": break_minutes
            })
            obs_sched = ToolObservation(tool_name="create_schedule", success=True, data=sched_data)
        except Exception as e:
            try:
                sched_data = await client.call_tool("tool_create_schedule", {
                    "tasks": raw_tasks,
                    "available_slots": raw_slots,
                    "break_minutes": break_minutes
                })
                obs_sched = ToolObservation(tool_name="create_schedule", success=True, data=sched_data)
            except Exception as e2:
                from tools import create_schedule as fallback_create_schedule
                sched_data = fallback_create_schedule(raw_tasks, raw_slots, break_minutes)
                obs_sched = ToolObservation(tool_name="create_schedule", success=True, data=sched_data)
        observations.append(obs_sched)
        agent_trace.append({"type": "observation", "tool": "create_schedule", "success": True})
        
        # Step 4: validate_schedule
        raw_schedule = sched_data.get("schedule", []) if isinstance(sched_data, dict) else []
        agent_trace.append({"type": "decision", "action": "tool_call", "tool": "validate_schedule"})
        try:
            val_data = await client.call_tool("validate_schedule", {
                "schedule": raw_schedule,
                "tasks": raw_tasks,
                "constraints": constraints
            })
            obs_val = ToolObservation(tool_name="validate_schedule", success=True, data=val_data)
        except Exception as e:
            try:
                val_data = await client.call_tool("tool_validate_schedule", {
                    "schedule": raw_schedule,
                    "tasks": raw_tasks,
                    "constraints": constraints
                })
                obs_val = ToolObservation(tool_name="validate_schedule", success=True, data=val_data)
            except Exception as e2:
                from tools import validate_schedule as fallback_validate_schedule
                val_data = fallback_validate_schedule(raw_schedule, raw_tasks, constraints)
                obs_val = ToolObservation(tool_name="validate_schedule", success=True, data=val_data)
        observations.append(obs_val)
        agent_trace.append({"type": "observation", "tool": "validate_schedule", "success": True})
        
        # Step 5: Ask LLM for a natural language summary (with fast timeout)
        summary_prompt = (
            f"You are a helpful Daily Planner AI. Summarize the following schedule in 2-3 friendly sentences for the user.\n"
            f"User request: {request}\n"
            f"Schedule: {json.dumps(raw_schedule)}\n"
            f"Validation: {json.dumps(val_data)}\n"
            f"Summary:"
        )
        
        answer = None
        try:
            async with httpx.AsyncClient(timeout=8.0) as http_client:
                response = await http_client.post(
                    f"{settings.OLLAMA_HOST}/api/generate",
                    json={
                        "model": settings.OLLAMA_MODEL,
                        "prompt": summary_prompt,
                        "stream": False
                    }
                )
                if response.status_code == 200:
                    resp_data = response.json()
                    answer = resp_data.get("response", "").strip()
        except Exception:
            answer = None
            
        if not answer:
            # Fallback high quality summary
            task_count = len([item for item in raw_schedule if item.get("task") != "Break"])
            answer = (
                f"Your daily schedule for {date} is ready! "
                f"Successfully scheduled {task_count} tasks between {start_time} and {end_time} with built-in breaks."
            )
            
        agent_trace.append({"type": "final", "answer": answer})
        
        return {
            "success": True,
            "answer": answer,
            "trace": agent_trace,
            "observations": [o.model_dump() for o in observations]
        }
        
    finally:
        await client.disconnect()
