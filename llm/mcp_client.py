from typing import List, Optional, Any, Dict
from contextlib import AsyncExitStack
from .models import ToolCall

from mcp import ClientSession, StdioServerParameters, Tool
from mcp.types import CallToolResult
from mcp.client.stdio import stdio_client

servers: Dict[str, Dict[str, Any]] = {
    "git": {
        "command": "uvx",
        "args": ["mcp-server-git"],
    },
}


class MCPClient:
    """Provides methods to connect to and execute tools in an mcp server."""

    def __init__(self, server_name: str):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

        server = servers.get(server_name)
        if server is None:
            raise ValueError(f"Unknown server: {server_name}")

        # Get server command string
        self.command = str(server["command"])
        args = server.get("args")
        self.args: List[str] = list(args) if args is not None else []

    async def connect_to_mcp_server(self) -> None:
        """Connect to an MCP server asynchronously."""
        server_params = StdioServerParameters(
            command=self.command, args=self.args, env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        await self.session.initialize()

    async def list_tools(self) -> List[Tool]:
        """List available tools."""
        if self.session is None:
            raise RuntimeError("MCP client is not connected to a server.")

        response = await self.session.list_tools()
        return response.tools

    async def cleanup(self) -> None:
        """Clean up resources asynchronously."""
        await self.exit_stack.aclose()

    async def call_tools(self, tool_calls: List[ToolCall]) -> List[CallToolResult]:
        """Call tools asynchronously."""
        if self.session is None:
            raise RuntimeError("MCP client is not connected to a server.")

        results = []
        for tool_call in tool_calls:
            result = await self.session.call_tool(
                tool_call.name, tool_call.arguments or {}
            )
            results.append(result)
        return results
