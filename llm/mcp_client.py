from typing import List, Optional, Any, Coroutine
from contextlib import AsyncExitStack
import asyncio
from .models import ToolCall

from mcp import ClientSession, StdioServerParameters, Tool
from mcp.types import CallToolResult
from mcp.client.stdio import stdio_client

servers = {
    "git": {
        "command": "uvx",
        "args": ["mcp-server-git"],
        "env": None,
    },
}

class AsyncMCPClient:
    """Asynchronous implementation of MCP client."""

    def __init__(self, server: str):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

        server = servers.get(server)
        if server is None:
            raise ValueError(f"Unknown server: {server}")
        self.command = server["command"]
        self.args = server["args"]
        self.env = server["env"]

    async def connect_to_mcp_server(self) -> None:
        """Connect to an MCP server asynchronously."""
        server_params = StdioServerParameters(
            command=self.command, args=self.args, env=self.env
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


class MCPClient:
    """Synchronous implementation of MCP client."""

    def __init__(self, server: str):
        self.async_client = AsyncMCPClient(server)
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._connected = False

    def _ensure_loop(self):
        """Ensure we have an event loop."""
        if self.loop is None or self.loop.is_closed():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

    def _run_async(self, coro: Coroutine) -> Any:
        """Run async coroutine in the event loop."""
        self._ensure_loop()
        try:
            if self.loop is None:
                raise RuntimeError("No event loop available")
            return self.loop.run_until_complete(coro)
        except RuntimeError as e:
            # Handle "Event loop is closed" errors
            if "Event loop is closed" in str(e):
                self._ensure_loop()
                if self.loop is None:
                    raise RuntimeError("No event loop available")
                return self.loop.run_until_complete(coro)
            raise

    def connect_to_mcp_server(self) -> None:
        """Connect to an MCP server synchronously."""
        try:
            self._run_async(self.async_client.connect_to_mcp_server())
            self._connected = True
        except Exception as e:
            self.cleanup()
            raise e

    def list_tools(self) -> List[Tool]:
        """List available tools."""
        if not self._connected:
            raise RuntimeError("MCP client is not connected to a server.")
        try:
            return self._run_async(self.async_client.list_tools())
        except Exception as e:
            self.cleanup()
            raise e

    def cleanup(self) -> None:
        """Clean up resources synchronously."""
        self._connected = False

        # First clean up the async client
        if self.loop and not self.loop.is_closed():
            try:
                self._run_async(self.async_client.cleanup())
            except Exception:
                # Best effort cleanup
                pass

        # Then close the loop
        if self.loop and not self.loop.is_closed():
            try:
                # Run all pending tasks to completion
                pending = asyncio.all_tasks(self.loop)
                if pending:
                    self.loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
                self.loop.close()
            except Exception:
                # Best effort cleanup
                pass

    def call_tools(self, tool_calls: List[ToolCall]) -> List[CallToolResult]:
        """Call tools synchronously."""
        if not self._connected:
            raise RuntimeError("MCP client is not connected to a server.")
        try:
            return self._run_async(self.async_client.call_tools(tool_calls))
        except Exception as e:
            self.cleanup()
            raise e

    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()
