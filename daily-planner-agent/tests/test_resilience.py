import unittest
import asyncio
import sys
import os
import json
from unittest.mock import patch, AsyncMock, MagicMock
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

from backend.agent.loop import run_agent, ask_llm
from backend.local_mcp.client import MCPClient
from backend.schemas.models import AgentAction
from backend.main import app
from fastapi.testclient import TestClient


class TestResilienceMocked(unittest.IsolatedAsyncioTestCase):
    """Mocked unit tests for resilience and error handling (deterministic & repeatable)."""

    @patch("httpx.AsyncClient.post")
    async def test_ollama_unavailable_connection_error(self, mock_post):
        """Verify clean failure when Ollama service is unreachable (ConnectError)."""
        mock_post.side_effect = httpx.ConnectError("Connection refused to Ollama")

        constraints = {"date": "2026-09-20", "start_time": "08:00", "end_time": "20:00"}
        result = await run_agent("Plan my day", constraints)

        self.assertFalse(result["success"])
        self.assertIn("Ollama is unreachable", result["error"])
        self.assertIn("Planning stopped", result["answer"])
        # Verify no endless retries on ConnectError (should fail after 1 attempt)
        self.assertEqual(mock_post.call_count, 1)

    @patch("httpx.AsyncClient.post")
    async def test_ollama_timeout_and_retry_limits(self, mock_post):
        """Verify Ollama timeouts trigger bounded retries up to MAX_TRANSIENT_RETRIES."""
        mock_post.side_effect = httpx.TimeoutException("Read timed out")

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            constraints = {"date": "2026-09-20", "start_time": "08:00", "end_time": "20:00"}
            result = await run_agent("Plan my day", constraints)

            self.assertFalse(result["success"])
            self.assertIn("timed out after 3 attempts", result["error"])
            # 1 initial + 2 retries = 3 total attempts
            self.assertEqual(mock_post.call_count, 3)

    @patch("httpx.AsyncClient.post")
    async def test_ollama_malformed_json_repair_and_failure(self, mock_post):
        """Verify malformed JSON from model attempts 1 repair and fails cleanly if still invalid."""
        bad_response = MagicMock()
        bad_response.status_code = 200
        bad_response.json.return_value = {"response": "I cannot output JSON right now!"}
        bad_response.raise_for_status = MagicMock()

        mock_post.return_value = bad_response

        constraints = {"date": "2026-09-20", "start_time": "08:00", "end_time": "20:00"}
        result = await run_agent("Plan my day", constraints)

        self.assertFalse(result["success"])
        self.assertIn("malformed JSON", result["error"])
        # Should attempt initial + 1 repair query = 2 attempts
        self.assertEqual(mock_post.call_count, 2)

    @patch("backend.agent.loop.MCPClient.connect")
    async def test_mcp_startup_failure(self, mock_connect):
        """Verify agent handles MCP server startup failure without crashing."""
        mock_connect.side_effect = RuntimeError("Failed to spawn MCP server process")

        constraints = {"date": "2026-09-20", "start_time": "08:00", "end_time": "20:00"}
        result = await run_agent("Plan my day", constraints)

        self.assertFalse(result["success"])
        self.assertIn("Failed to start/connect to MCP server", result["error"])
        self.assertEqual(len(result["observations"]), 0)

    @patch("backend.agent.loop.MCPClient.get_tools")
    async def test_mcp_tool_discovery_failure(self, mock_get_tools):
        """Verify agent handles MCP tool discovery failure gracefully."""
        mock_get_tools.side_effect = RuntimeError("Tool listing failed")

        constraints = {"date": "2026-09-20", "start_time": "08:00", "end_time": "20:00"}
        result = await run_agent("Plan my day", constraints)

        self.assertFalse(result["success"])
        self.assertIn("Failed to discover tools", result["error"])

    @patch("backend.agent.loop.ask_llm")
    @patch("backend.agent.loop.MCPClient.call_tool")
    async def test_mcp_tool_execution_failure(self, mock_call_tool, mock_ask_llm):
        """Verify tool execution errors are recorded as failed observations without crashing."""
        mock_ask_llm.side_effect = [
            AgentAction(action="tool_call", tool_name="get_tasks", arguments={"date": "2026-09-20"}),
            AgentAction(action="final", answer="Finished after tool error.")
        ]
        mock_call_tool.side_effect = RuntimeError("Subprocess communication error")

        constraints = {"date": "2026-09-20", "start_time": "08:00", "end_time": "20:00"}
        result = await run_agent("Plan my day", constraints)

        self.assertTrue(result["success"])
        failed_obs = [o for o in result["observations"] if not o["success"]]
        self.assertEqual(len(failed_obs), 1)
        self.assertIn("Subprocess communication error", failed_obs[0]["error"])

    async def test_mcp_client_cleanup_after_failed_connect(self):
        """Verify MCPClient cleans up exit stack and references on failed connection."""
        client = MCPClient()
        # Point to a nonexistent executable to force startup error
        client.server_params.command = "nonexistent_executable_12345"

        with self.assertRaises(Exception):
            await client.connect()

        # Check that state was reset cleanly
        self.assertIsNone(client.session)
        self.assertIsNone(client._client)
        self.assertIsNone(client._exit_stack)


class TestHealthEndpoint(unittest.TestCase):
    """Tests for the active /api/health endpoint."""

    def setUp(self):
        self.client = TestClient(app)

    @patch("httpx.AsyncClient.get")
    def test_health_healthy_ollama(self, mock_get):
        """Verify /api/health returns 200 OK when Ollama is available."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "models": [{"name": "llama3.2:3b:latest"}]
        }
        mock_get.return_value = mock_resp

        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["backend"], "ok")
        self.assertEqual(data["ollama"]["status"], "ok")
        self.assertTrue(data["ollama"]["model_found"])

    @patch("httpx.AsyncClient.get")
    def test_health_unavailable_ollama(self, mock_get):
        """Verify /api/health returns 503 Service Unavailable when Ollama is offline."""
        mock_get.side_effect = httpx.ConnectError("Connection refused")

        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 503)

        data = response.json()
        self.assertEqual(data["status"], "degraded")
        self.assertEqual(data["backend"], "ok")
        self.assertEqual(data["ollama"]["status"], "unavailable")
        self.assertTrue(len(data["ollama"]["error"]) > 0)
        self.assertIn("Connection refused", data["ollama"]["error"])


if __name__ == "__main__":
    unittest.main()
