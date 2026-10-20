import json
import asyncio
import httpx
from typing import Dict, Any, List, Optional, Tuple
import jsonschema

from .prompts import SYSTEM_PROMPT
from .reflection import reflect_on_schedule
from local_mcp.client import MCPClient
from config import settings
from schemas.models import AgentAction, ToolObservation


def _clean_json_text(text: str) -> str:
    """Strip markdown code fence formatting if present."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def validate_tool_arguments(tool_meta: Dict[str, Any], arguments: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validate tool call arguments against MCP inputSchema."""
    schema = tool_meta.get("inputSchema")
    if not schema or not isinstance(schema, dict):
        return True, None
    try:
        jsonschema.validate(instance=arguments, schema=schema)
        return True, None
    except jsonschema.ValidationError as err:
        return False, err.message
    except Exception:
        return True, None


MAX_TRANSIENT_RETRIES = 2
OLLAMA_TIMEOUT_SECONDS = 30.0


async def ask_llm(
    request: str,
    constraints: Dict[str, Any],
    tools: List[Dict[str, Any]],
    observations: List[ToolObservation]
) -> AgentAction:
    """Query the Ollama LLM to dynamically decide the next action with bounded retries."""
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

    last_error = None
    prompt_to_send = prompt

    for attempt in range(MAX_TRANSIENT_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{settings.OLLAMA_HOST}/api/generate",
                    json={
                        "model": settings.OLLAMA_MODEL,
                        "prompt": prompt_to_send,
                        "stream": False,
                        "format": "json"
                    }
                )

                if response.status_code == 404:
                    raise RuntimeError(
                        f"Model '{settings.OLLAMA_MODEL}' was not found on Ollama server at {settings.OLLAMA_HOST}. "
                        "Please run `ollama pull " + settings.OLLAMA_MODEL + "`."
                    )
                response.raise_for_status()

                result_json = response.json()
                llm_text = _clean_json_text(result_json.get("response", ""))

                try:
                    action_dict = json.loads(llm_text)
                except json.JSONDecodeError as jde:
                    # Attempt a single repair if this was the first try
                    if attempt == 0:
                        prompt_to_send = (
                            prompt + "\n\nCRITICAL ERROR: Your previous response was not valid JSON. "
                            "You must return ONLY a JSON object matching the requested schema."
                        )
                        continue
                    raise ValueError(f"Ollama returned malformed JSON: {str(jde)}")

                # Normalize potential model output variations
                known_tool_names = [t["name"] for t in tools]
                raw_action = action_dict.get("action")

                if raw_action in known_tool_names:
                    action_dict["tool_name"] = raw_action
                    action_dict["action"] = "tool_call"
                elif raw_action in ["tool", "call", "tool_call"]:
                    action_dict["action"] = "tool_call"
                elif raw_action in ["final", "finish", "done", "complete"]:
                    action_dict["action"] = "final"
                elif "action" not in action_dict:
                    if "tool_name" in action_dict or "tool" in action_dict:
                        action_dict["action"] = "tool_call"
                    elif "answer" in action_dict:
                        action_dict["action"] = "final"
                    else:
                        action_dict["action"] = "final"
                        action_dict["answer"] = llm_text

                if "tool" in action_dict and "tool_name" not in action_dict:
                    action_dict["tool_name"] = action_dict["tool"]

                if isinstance(action_dict.get("arguments"), str):
                    try:
                        action_dict["arguments"] = json.loads(action_dict["arguments"])
                    except Exception:
                        pass

                return AgentAction(**action_dict)

        except httpx.ConnectError:
            # Service offline - do not retry in an endless loop
            raise RuntimeError(
                f"Ollama is unreachable at {settings.OLLAMA_HOST}. Please verify that the Ollama service is running."
            )
        except (httpx.TimeoutException, httpx.NetworkError) as transient_err:
            last_error = transient_err
            if attempt < MAX_TRANSIENT_RETRIES:
                await asyncio.sleep(0.5 * (attempt + 1))
                continue
            raise RuntimeError(
                f"Ollama request timed out after {MAX_TRANSIENT_RETRIES + 1} attempts ({OLLAMA_TIMEOUT_SECONDS}s timeout)."
            )
        except Exception as e:
            raise

    raise RuntimeError(f"Error querying LLM: {str(last_error)}")


async def run_agent(request: str, constraints: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the bounded dynamic agent loop via FastMCP and Ollama with resilient error handling."""
    client = MCPClient()
    connected = False

    observations: List[ToolObservation] = []
    agent_trace: List[Dict[str, Any]] = []

    # Discovered state cache
    cached_schedule: List[Dict[str, Any]] = []
    cached_tasks: List[Dict[str, Any]] = []

    # Loop state
    max_iterations = getattr(settings, "MAX_ITERATIONS", 10)
    seen_calls: Dict[str, int] = {}
    final_answer: Optional[str] = None
    iteration = 0

    try:
        # Step 0A: Safely connect to MCP Server
        try:
            await client.connect()
            connected = True
        except Exception as conn_err:
            err_msg = f"Failed to start/connect to MCP server: {str(conn_err)}"
            agent_trace.append({"type": "error", "message": err_msg})
            return {
                "success": False,
                "error": err_msg,
                "answer": "Planning stopped: unable to start or connect to the local MCP tool server.",
                "trace": agent_trace,
                "observations": []
            }

        # Step 0B: Dynamically discover tools from MCP server
        try:
            discovered_tools = await client.get_tools()
            tool_dict = {t["name"]: t for t in discovered_tools}
        except Exception as disc_err:
            err_msg = f"Failed to discover tools from MCP server: {str(disc_err)}"
            agent_trace.append({"type": "error", "message": err_msg})
            return {
                "success": False,
                "error": err_msg,
                "answer": "Planning stopped: failed to discover tools from the MCP server.",
                "trace": agent_trace,
                "observations": []
            }

        agent_trace.append({
            "type": "discovery",
            "message": f"Discovered {len(discovered_tools)} MCP tools: {list(tool_dict.keys())}"
        })

        # Main dynamic reasoning loop bounded by max_iterations
        while iteration < max_iterations:
            iteration += 1

            try:
                action = await ask_llm(request, constraints, discovered_tools, observations)
            except Exception as llm_err:
                agent_trace.append({"type": "error", "message": str(llm_err)})
                return {
                    "success": False,
                    "error": str(llm_err),
                    "answer": f"Planning stopped: {str(llm_err)}",
                    "trace": agent_trace,
                    "observations": [o.model_dump() for o in observations]
                }

            # Case A: LLM decided on final answer
            if action.action == "final":
                final_answer = action.answer or "Daily schedule planning complete."
                agent_trace.append({"type": "final", "answer": final_answer})
                break

            # Case B: LLM chose a tool call
            is_tool_call = (action.action == "tool_call") or (action.tool_name in tool_dict) or (action.action in tool_dict)
            if is_tool_call:
                tool_name = action.tool_name or action.action
                arguments = action.arguments or {}

                # 1. Validate tool name
                if not tool_name or tool_name not in tool_dict:
                    err_msg = (
                        f"Unknown tool '{tool_name}'. "
                        f"Available tools are: {list(tool_dict.keys())}"
                    )
                    obs = ToolObservation(
                        tool_name=tool_name or "unknown",
                        success=False,
                        error=err_msg
                    )
                    observations.append(obs)
                    agent_trace.append({
                        "type": "observation",
                        "tool": tool_name or "unknown",
                        "success": False,
                        "error": err_msg
                    })
                    continue

                # 2. Validate arguments against MCP tool inputSchema
                is_valid, arg_err = validate_tool_arguments(tool_dict[tool_name], arguments)
                if not is_valid:
                    err_msg = f"Invalid arguments for '{tool_name}': {arg_err}"
                    obs = ToolObservation(tool_name=tool_name, success=False, error=err_msg)
                    observations.append(obs)
                    agent_trace.append({
                        "type": "observation",
                        "tool": tool_name,
                        "success": False,
                        "error": err_msg
                    })
                    continue

                # 3. Detect and prevent infinite identical call loops
                call_sig = f"{tool_name}:{json.dumps(arguments, sort_keys=True)}"
                seen_calls[call_sig] = seen_calls.get(call_sig, 0) + 1
                if seen_calls[call_sig] > 1:
                    warn_msg = (
                        f"Loop prevented: '{tool_name}' was already executed and its output is recorded. "
                        f"DO NOT call '{tool_name}' again. Advance to the next workflow tool "
                        f"(e.g. get_available_time, create_schedule, validate_schedule, or finalize)."
                    )
                    obs = ToolObservation(tool_name=tool_name, success=False, error=warn_msg)
                    observations.append(obs)
                    agent_trace.append({
                        "type": "observation",
                        "tool": tool_name,
                        "success": False,
                        "error": warn_msg
                    })
                    continue

                # Record decision in trace
                agent_trace.append({
                    "type": "decision",
                    "action": "tool_call",
                    "tool": tool_name,
                    "arguments": arguments
                })

                # 4. Execute tool through MCP Client
                try:
                    tool_data = await client.call_tool(tool_name, arguments)
                    obs = ToolObservation(tool_name=tool_name, success=True, data=tool_data)

                    # Update cached data for reflection
                    if tool_name == "get_tasks" and isinstance(tool_data, dict):
                        cached_tasks = tool_data.get("tasks", [])
                    elif tool_name == "create_schedule" and isinstance(tool_data, dict):
                        cached_schedule = tool_data.get("schedule", [])

                except Exception as tool_err:
                    obs = ToolObservation(
                        tool_name=tool_name,
                        success=False,
                        error=f"MCP call failed: {str(tool_err)}"
                    )

                observations.append(obs)
                agent_trace.append({
                    "type": "observation",
                    "tool": tool_name,
                    "success": obs.success,
                    "data": obs.data if obs.success else None,
                    "error": obs.error if not obs.success else None
                })

                # 5. Immediate Reflection after validation tool
                if tool_name == "validate_schedule" and obs.success:
                    sched_for_ref = arguments.get("schedule") or cached_schedule
                    tasks_for_ref = arguments.get("tasks") or cached_tasks
                    val_result = obs.data if isinstance(obs.data, dict) else {}

                    ref_output = reflect_on_schedule(
                        schedule=sched_for_ref,
                        tasks=tasks_for_ref,
                        constraints=constraints,
                        validation_result=val_result
                    )

                    ref_success = (ref_output.get("status") == "success")
                    ref_obs = ToolObservation(
                        tool_name="reflection",
                        success=ref_success,
                        data=ref_output
                    )
                    observations.append(ref_obs)
                    agent_trace.append({
                        "type": "reflection",
                        "success": ref_success,
                        "data": ref_output
                    })

        # Check if loop terminated because of MAX_ITERATIONS without a final action
        if not final_answer:
            reflection_issues = []
            for o in reversed(observations):
                if o.tool_name == "reflection" and isinstance(o.data, dict):
                    if o.data.get("status") == "failed":
                        reflection_issues.extend(o.data.get("issues", []))
                    break

            if reflection_issues:
                final_answer = (
                    f"Agent reached maximum iterations ({max_iterations}). "
                    f"The requested schedule cannot be fully accommodated due to constraints: "
                    f"{'; '.join(reflection_issues)}."
                )
            elif cached_schedule:
                final_answer = (
                    f"Schedule planned with {len(cached_schedule)} items, but iteration limit "
                    f"({max_iterations}) was reached before final review."
                )
            else:
                final_answer = (
                    f"Agent reached maximum iterations ({max_iterations}) before schedule completion."
                )

            agent_trace.append({"type": "final", "answer": final_answer})

        return {
            "success": True,
            "answer": final_answer,
            "trace": agent_trace,
            "observations": [o.model_dump() for o in observations]
        }

    finally:
        if connected:
            try:
                await client.disconnect()
            except Exception:
                pass
