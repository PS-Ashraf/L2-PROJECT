import unittest
import asyncio
import sys
import os
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

from backend.local_mcp.client import MCPClient
from backend.agent.loop import run_agent, validate_tool_arguments
from backend.schemas.models import AgentAction, ToolObservation


class TestAgentLoop(unittest.IsolatedAsyncioTestCase):

    async def test_mcp_tool_discovery(self):
        """Verify real MCP client connects and discovers the 5 canonical tools without aliases."""
        client = MCPClient()
        await client.connect()
        try:
            tools = await client.get_tools()
            tool_names = [t["name"] for t in tools]

            expected_tools = [
                "get_tasks",
                "estimate_task_duration",
                "get_available_time",
                "create_schedule",
                "validate_schedule"
            ]

            for expected in expected_tools:
                self.assertIn(expected, tool_names, f"Expected canonical tool '{expected}' to be discovered")

            # Verify duplicate tool_* aliases have been removed
            for name in tool_names:
                self.assertFalse(name.startswith("tool_"), f"Unexpected duplicate alias '{name}' found")

            # Check that each tool has valid schema metadata
            for tool in tools:
                self.assertIn("description", tool)
                self.assertIn("inputSchema", tool)
                self.assertIsInstance(tool["inputSchema"], dict)
        finally:
            await client.disconnect()

    def test_argument_validation(self):
        """Verify tool argument validation against inputSchema."""
        meta = {
            "name": "get_available_time",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "start_time": {"type": "string"},
                    "end_time": {"type": "string"}
                },
                "required": ["start_time"]
            }
        }

        # Valid arguments
        is_valid, err = validate_tool_arguments(meta, {"start_time": "08:00", "end_time": "17:00"})
        self.assertTrue(is_valid)
        self.assertIsNone(err)

        # Missing required argument
        is_valid, err = validate_tool_arguments(meta, {"end_time": "17:00"})
        self.assertFalse(is_valid)
        self.assertIsNotNone(err)

    @patch("backend.agent.loop.ask_llm")
    async def test_early_termination_on_final(self, mock_ask_llm):
        """Verify agent terminates immediately when LLM returns 'final' action."""
        mock_ask_llm.return_value = AgentAction(
            action="final",
            answer="Here is your requested schedule."
        )

        constraints = {
            "date": "2026-09-20",
            "start_time": "08:00",
            "end_time": "20:00",
            "break_minutes": 15
        }

        result = await run_agent("Plan my day", constraints)

        self.assertTrue(result["success"])
        self.assertEqual(result["answer"], "Here is your requested schedule.")
        self.assertEqual(mock_ask_llm.call_count, 1)

    @patch("backend.agent.loop.ask_llm")
    async def test_max_iterations_bound(self, mock_ask_llm):
        """Verify agent terminates safely when MAX_ITERATIONS limit is reached."""
        # Always return a tool call that never finishes
        mock_ask_llm.return_value = AgentAction(
            action="tool_call",
            tool_name="estimate_task_duration",
            arguments={"task_name": "Coding"}
        )

        with patch("backend.agent.loop.settings") as mock_settings:
            mock_settings.MAX_ITERATIONS = 4
            mock_settings.OLLAMA_HOST = "http://localhost:11434"
            mock_settings.OLLAMA_MODEL = "llama3.2:3b"

            constraints = {"date": "2026-09-20", "start_time": "08:00", "end_time": "20:00"}
            result = await run_agent("Plan my day", constraints)

            self.assertTrue(result["success"])
            self.assertIn("maximum iterations (4)", result["answer"])
            self.assertLessEqual(mock_ask_llm.call_count, 4)

    @patch("backend.agent.loop.ask_llm")
    async def test_unknown_tool_handling(self, mock_ask_llm):
        """Verify unknown tool call results in a clean error observation without crashing."""
        mock_ask_llm.side_effect = [
            AgentAction(action="tool_call", tool_name="nonexistent_tool", arguments={}),
            AgentAction(action="final", answer="Recovered after invalid tool")
        ]

        constraints = {"date": "2026-09-20", "start_time": "08:00", "end_time": "20:00"}
        result = await run_agent("Plan my day", constraints)

        self.assertTrue(result["success"])
        self.assertEqual(result["answer"], "Recovered after invalid tool")
        # Check that error observation was recorded
        obs_errors = [o for o in result["observations"] if not o["success"]]
        self.assertTrue(len(obs_errors) > 0)
        self.assertIn("Unknown tool 'nonexistent_tool'", obs_errors[0]["error"])

    @patch("backend.agent.loop.ask_llm")
    async def test_reflection_integrated_after_validation(self, mock_ask_llm):
        """Verify reflection runs immediately after validate_schedule observation."""
        mock_ask_llm.side_effect = [
            AgentAction(action="tool_call", tool_name="validate_schedule", arguments={
                "schedule": [{"start": "08:00", "end": "10:00", "task": "Study"}],
                "tasks": [{"name": "Study", "duration_minutes": 120, "fixed": False}],
                "constraints": {"start_time": "08:00", "end_time": "12:00"}
            }),
            AgentAction(action="final", answer="Schedule is valid and verified.")
        ]

        constraints = {"start_time": "08:00", "end_time": "12:00"}
        result = await run_agent("Verify my schedule", constraints)

        self.assertTrue(result["success"])
        # Verify reflection tool observation exists in result
        reflection_obs = [o for o in result["observations"] if o["tool_name"] == "reflection"]
        self.assertEqual(len(reflection_obs), 1)
        self.assertTrue(reflection_obs[0]["success"])
        self.assertEqual(reflection_obs[0]["data"]["status"], "success")


if __name__ == "__main__":
    unittest.main()
