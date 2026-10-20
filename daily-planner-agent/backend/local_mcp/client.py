import asyncio
from typing import Dict, Any, List
import sys
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPClient:
    def __init__(self):
        server_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")
        self.server_params = StdioServerParameters(
            command=sys.executable,
            args=[server_path]
        )
        self.session = None
        self._client = None
        self._exit_stack = None

    async def connect(self):
        from contextlib import AsyncExitStack
        self._exit_stack = AsyncExitStack()
        try:
            self._client = await self._exit_stack.enter_async_context(stdio_client(self.server_params))
            read, write = self._client
            self.session = await self._exit_stack.enter_async_context(ClientSession(read, write))
            await self.session.initialize()
        except Exception:
            if self._exit_stack:
                await self._exit_stack.aclose()
            self._exit_stack = None
            self.session = None
            self._client = None
            raise

    async def disconnect(self):
        if self._exit_stack:
            try:
                await self._exit_stack.aclose()
            finally:
                self._exit_stack = None
                self.session = None
                self._client = None
            
    async def get_tools(self) -> List[Dict[str, Any]]:
        if not self.session:
            raise RuntimeError("Client not connected")
        tools = await self.session.list_tools()
        return [{"name": t.name, "description": t.description, "inputSchema": t.inputSchema} for t in tools.tools]

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        if not self.session:
            raise RuntimeError("Client not connected")
        result = await self.session.call_tool(name, arguments)
        
        # Result content is usually a list of TextContent objects
        # We'll extract the JSON if it's text
        import json
        if result.content and len(result.content) > 0:
            text = result.content[0].text
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
        return None
