# Daily Planner Agent (L2 Autonomous Agentic System)

An AI-driven daily planning system that creates, validates, and refines grounded daily schedules from tasks, fixed events, priorities, and constraints. Powered by a dynamic LLM-driven reasoning loop communicating with local tools via the Model Context Protocol (FastMCP) and Ollama.

---

## 1. Objective & Problem Statement

Users often struggle to balance daily tasks, fixed calendar events (standups, consultations, client calls), energy recovery breaks, and strict deadlines. Standard fixed pipelines or direct LLM prompt generation frequently suffer from hallucinated times, ignored duration bounds, and schedule overlaps.

This project implements an **L2 Agentic System** that:
- Employs a dynamic **Observe → Reason → Act** loop where an LLM selects tools at runtime based on ongoing state.
- Discovers and calls tools through **real MCP (Model Context Protocol)** over stdio.
- Binds execution within a strict iteration ceiling (`MAX_ITERATIONS`) to prevent infinite looping.
- Employs a **Reflection and Re-planning** mechanism when schedule validation detects conflicts or constraint violations.
- Implements resilient error handling for transient timeouts, network drops, and offline services without returning fabricated successes.

---

## 2. System Architecture

```
┌────────────────────────────────────────────────────────┐
│               Frontend (React 18 + Vite)               │
│         Glassmorphism Dashboard & Energy Stats         │
└───────────────────────────┬────────────────────────────┘
                            │ HTTP (POST /api/plan, GET /api/health)
┌───────────────────────────▼────────────────────────────┐
│                    FastAPI Backend                     │
├────────────────────────────────────────────────────────┤
│                   Dynamic Agent Loop                   │
│   Bounded Iterations | Bounded Retries | Loop Guard    │
├───────────────────────────┬────────────────────────────┤
│      MCP Stdio Client     │       Ollama Client        │
│    (mcp.ClientSession)    │   (llama3.2:3b @ :11434)   │
└─────────────┬─────────────┴─────────────┬──────────────┘
              │ stdio                     │ HTTP /api/generate
┌─────────────▼─────────────┐             │
│    FastMCP Tool Server    │             │
├───────────────────────────┤             │
│ 1. get_tasks              │             │
│ 2. estimate_task_duration │             │
│ 3. get_available_time     │             │
│ 4. create_schedule        │             │
│ 5. validate_schedule      │             │
└─────────────┬─────────────┘             │
              │                           │
┌─────────────▼─────────────┐             │
│     Deterministic Tools   │             │
│  scheduler.py, etc.       │             │
└─────────────┬─────────────┘             │
              │                           │
┌─────────────▼─────────────┐             │
│   Reflection & Validator  │◄────────────┘
│    reflection.py          │ (Injected into observations)
└───────────────────────────┘
```

---

## 3. The 5 Canonical MCP Tools

All tools are registered on the FastMCP server (`backend/local_mcp/server.py`) and discovered dynamically by the agent via `client.get_tools()`:

1. **`get_tasks(date: str)`**:
   Loads the user's tasks and fixed calendar events for the specified date from storage (`data/tasks.json` and `data/events.json`).
2. **`estimate_task_duration(task_name: str)`**:
   Determines or calculates duration estimates based on task activity patterns (e.g. meetings: 60m, study: 120m, gym: 60m).
3. **`get_available_time(date: str, start_time: str, end_time: str)`**:
   Computes contiguous available time blocks between day start and day end by subtracting fixed calendar commitments.
4. **`create_schedule(tasks, available_slots, break_minutes: int = 15)`**:
   Places fixed tasks at their designated times and prioritizes flexible tasks into available slots by priority (`high` > `medium` > `low`) and deadline, inserting energy recovery breaks.
5. **`validate_schedule(schedule, tasks, constraints)`**:
   Rigorously validates the proposed schedule for task overlaps, unscheduled tasks, deadline violations, and out-of-bounds working hours.

---

## 4. Agent Workflow & Reflection Cycle

1. **Discovery**: Upon connection, the MCP Client discovers all registered tools and their JSON schemas over stdio.
2. **Reasoning Loop**:
   - The agent provides Ollama with the request, constraints, discovered tool schemas, and previous observations.
   - The LLM selects the next tool call or outputs `action: "final"`.
   - Tool arguments are validated against the tool's JSON schema using `jsonschema` before execution.
   - The tool is executed via FastMCP stdio communication, and the real output is recorded as a `ToolObservation`.
3. **Reflection & Re-Planning**:
   - Immediately after `validate_schedule` runs, `reflect_on_schedule()` evaluates whether the schedule genuinely fits constraints (e.g. detecting if requested work minutes exceed total available day minutes).
   - Reflection output is recorded as an observation and passed back into the LLM context.
   - If conflicts exist, the LLM can attempt re-planning or adjustments. If constraints are physically impossible, the agent stops and explains the violations rather than hallucinating an invalid schedule as valid.
4. **Safety & Loop Limits**:
   - Consecutive identical tool calls with identical arguments are intercepted by a duplicate-call guard.
   - Total loop iterations are bounded by `MAX_ITERATIONS` (default `10`–`15`).
   - If the iteration limit is reached without a final answer, the agent terminates safely and summarizes the progress and diagnostic issues.

---

## 5. Prerequisites & Environment Setup

### Prerequisites
- **Python**: 3.10+ (tested on Python 3.14)
- **Node.js**: v18+ & npm
- **Ollama**: Local Ollama instance running with `llama3.2:3b`.
  ```powershell
  ollama pull llama3.2:3b
  ollama serve
  ```

### Configuration (`.env`)
Copy `.env.example` to `.env`:
```powershell
copy .env.example .env
```
Configuration variables:
```ini
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
MAX_ITERATIONS=10
```

---

## 6. Installation & Running Locally (Windows PowerShell)

### Backend Setup
```powershell
cd "daily-planner-agent"
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

cd backend
..\venv\Scripts\uvicorn main:app --reload --port 8000
```

### Frontend Setup
In a new PowerShell terminal:
```powershell
cd "daily-planner-agent\frontend"
npm install
npm run dev
```
Open your browser at: **`http://localhost:5173`**

### Unified Launcher
Alternatively, run both backend and frontend together:
```powershell
cd "daily-planner-agent"
.\venv\Scripts\python main.py
```
*(Or double-click `run.bat`)*

---

## 7. Running the Automated Test Suite

The test suite supports both Python's built-in `unittest` runner and `pytest`.

### Run via Pytest:
```powershell
cd "daily-planner-agent"
.\venv\Scripts\python -m pytest
```

### Run via Unittest:
```powershell
cd "daily-planner-agent"
.\venv\Scripts\python -m unittest discover -s tests -p "test_*.py"
```

### Test Coverage Summary:
- **`tests/test_tools.py`**: Unit tests for duration estimation, priority slot fitting, and overlap validation.
- **`tests/test_failures.py`**: Reflection test verifying impossible workload detection (e.g. 12 hours of work requested in a 9-hour day).
- **`tests/test_agent_loop.py`**:
  - Real FastMCP stdio tool discovery and canonical tool registry verification.
  - JSON Schema argument validation.
  - Early termination on `final` action.
  - `MAX_ITERATIONS` upper bound enforcement.
  - Handling of unknown tool names.
  - Reflection integration following schedule validation.
- **`tests/test_resilience.py`**:
  - Ollama unavailable (`httpx.ConnectError`) clean diagnostic failure without infinite retries.
  - Transient network timeouts with bounded retries (`MAX_TRANSIENT_RETRIES = 2`).
  - Model malformed JSON output repair query and fallback.
  - MCP startup and tool discovery failure handling.
  - MCP tool runtime execution errors captured as observations.
  - MCPClient resource cleanup ensuring no hanging subprocesses.
  - Active `/api/health` probes returning HTTP 200 (healthy) and HTTP 503 (degraded).

---

## 8. API Reference

### Health Check Endpoint
```http
GET /api/health
```
Probes backend availability and tests connectivity to the local Ollama provider.

**Healthy Response (HTTP 200 OK):**
```json
{
  "status": "ok",
  "backend": "ok",
  "ollama": {
    "status": "ok",
    "host": "http://localhost:11434",
    "model": "llama3.2:3b",
    "model_found": true
  }
}
```

**Degraded Response (HTTP 503 Service Unavailable):**
```json
{
  "status": "degraded",
  "backend": "ok",
  "ollama": {
    "status": "unavailable",
    "host": "http://localhost:11434",
    "model": "llama3.2:3b",
    "error": "Connection refused to Ollama server at http://localhost:11434"
  }
}
```

---

### Plan Generation Endpoint
```http
POST /api/plan
Content-Type: application/json
```

**Request Payload:**
```json
{
  "date": "2026-09-20",
  "start_time": "08:00",
  "end_time": "20:00",
  "break_minutes": 15,
  "tasks": [
    {
      "name": "Python Study & Architecture",
      "duration_minutes": 120,
      "priority": "high",
      "fixed": false
    },
    {
      "name": "Daily Team Standup",
      "duration_minutes": 30,
      "priority": "high",
      "fixed": true,
      "start_time": "10:00"
    }
  ],
  "natural_language_request": "Optimize my day for deep coding focus with buffer after standup."
}
```

**Response Payload:**
```json
{
  "success": true,
  "answer": "Here is your planned schedule for 2026-09-20...",
  "trace": [
    { "type": "discovery", "message": "Discovered 5 MCP tools: ..." },
    { "type": "decision", "action": "tool_call", "tool": "get_tasks" },
    { "type": "observation", "tool": "get_tasks", "success": true },
    { "type": "decision", "action": "tool_call", "tool": "create_schedule" },
    { "type": "observation", "tool": "create_schedule", "success": true },
    { "type": "decision", "action": "tool_call", "tool": "validate_schedule" },
    { "type": "observation", "tool": "validate_schedule", "success": true },
    { "type": "reflection", "success": true, "data": { "status": "success", "issues": [] } },
    { "type": "final", "answer": "..." }
  ],
  "observations": [
    {
      "tool_name": "create_schedule",
      "success": true,
      "data": {
        "schedule": [
          { "start": "08:00", "end": "10:00", "task": "Python Study & Architecture" },
          { "start": "10:00", "end": "10:30", "task": "Daily Team Standup" },
          { "start": "10:30", "end": "10:45", "task": "Break" }
        ],
        "unscheduled_tasks": []
      }
    },
    {
      "tool_name": "validate_schedule",
      "success": true,
      "data": {
        "valid": true,
        "conflicts": [],
        "unscheduled_tasks": [],
        "deadline_violations": [],
        "warnings": []
      }
    }
  ]
}
```

---

## 9. Known Limitations & Troubleshooting

1. **Ollama Service Offline**:
   - If the backend returns `Planning stopped: Ollama is unreachable`, verify Ollama is active (`ollama list` or `ollama serve`). Check `GET /api/health` to confirm provider status.
2. **Model Availability**:
   - If you encounter `Model 'llama3.2:3b' was not found`, pull the model using `ollama pull llama3.2:3b` or update `OLLAMA_MODEL` in `.env` to match an installed model.
3. **Iteration Limits on Over-Constrained Schedules**:
   - If more work is requested than available hours allow, reflection will flag the impossibility. The agent is strictly instructed not to hallucinate validity and will conclude with an explanation of unscheduled tasks or constraint conflicts.
