# Daily Planner Agent

An AI-powered full-stack application that dynamically plans a user's day by reasoning about tasks, available time, priorities, fixed events, deadlines, and constraints.

## Objective

Build a practical Agentic AI system using Ollama to process natural-language scheduling requests. It leverages a dynamic agent loop calling real MCP tools to generate and validate a grounded schedule, without hallucinating tool results.

## Architecture

- **Frontend:** React + Vite, designed with modern glassmorphism UI.
- **Backend:** FastAPI, providing the REST API for the frontend.
- **Agent Loop:** A custom dynamic reasoning loop integrating Ollama via HTTP.
- **MCP Server/Client:** The backend exposes 5 core scheduling tools through FastMCP. The agent uses an MCP Client to discover and execute these tools.

## Setup Instructions

### Prerequisites
- Python 3.10+
- Node.js & npm
- [Ollama](https://ollama.com/) running locally with `llama3.2:3b` (or update `.env` to your preferred model).

### Backend Setup
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cd backend
uvicorn main:app --reload
```

### Frontend Setup
```powershell
cd frontend
npm install
npm run dev
```

## Agent Workflow (Dynamic Loop)

The agent operates in an open-ended loop:
1. Receives the user request and constraints.
2. Queries Ollama with the available MCP tools and past observations.
3. Decides to call a tool (e.g., `get_tasks`) or output a final schedule.
4. Executes the tool via the MCP client.
5. Feeds the real observation back to Ollama.
6. Once enough data is gathered (e.g., scheduling and validation completed), the agent reflects on the schedule.
7. Produces the final grounded response.

### Example Trace
```
✓ Agent analyzed request
→ Calling get_tasks
✓ Observation received (4 tasks found)
→ Calling get_available_time
✓ Observation received (Available slots returned)
→ Calling create_schedule
✓ Observation received (Schedule created)
→ Calling validate_schedule
✓ Schedule validated
✓ Reflection completed (All constraints met)
✓ Final response generated
```

## L2 Requirement Mapping

| L2 Requirement         | Project Implementation                  |
| ---------------------- | --------------------------------------- |
| Practical user problem | Automated daily scheduling              |
| LLM policy layer       | Ollama + agent system prompt            |
| Reasoning/planning     | LLM chooses next action                 |
| Defined model config   | `.env` configuration                    |
| Structured outputs     | Pydantic                                |
| Multiple tools         | 5 MCP tools                             |
| Tool descriptions      | MCP definitions                         |
| Input schemas          | MCP/Pydantic schemas                    |
| MCP server             | FastMCP server                          |
| MCP client             | MCP client                              |
| Dynamic agent loop     | Iterative LLM → tool → observation loop |
| Real execution         | Python scheduling/data tools            |
| Tool observations      | Returned to LLM                         |
| Grounded response      | Final plan based on observations        |
| Reflection             | Schedule validation + reflection        |
| Unknown tools          | Error handling in loop                  |
| Malformed output       | Try-except validation                   |
| API/tool failures      | Safe error observations                 |
| Iteration limit        | MAX_ITERATIONS in config                |
| Secret management      | `.env`                                  |
| Runnable evidence      | Pytest suite + runnable UI              |
| Frontend               | React/Vite                              |
| Backend                | FastAPI                                 |

## Course Concept Mapping
- **Agentic AI**: Uses the Observe → Reason → Act cycle.
- **MCP**: Real Model Context Protocol implementation for tools.
- **Dynamic Tool Calling**: LLM determines sequence instead of a fixed pipeline.
- **Reflection**: Output is rigorously validated against constraints before finalization.
