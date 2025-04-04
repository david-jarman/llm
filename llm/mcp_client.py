from typing import List, Optional, Any
from contextlib import AsyncExitStack
import asyncio
import concurrent.futures
from abc import ABC, abstractmethod
from .models import ToolCall

from mcp import ClientSession, StdioServerParameters, Tool
from mcp.types import CallToolResult
from mcp.client.stdio import stdio_client

class BaseMCPClient(ABC):
    """Abstract base class for MCP clients."""

    @abstractmethod
    def connect_to_mcp_server(self) -> Any:
        """Connect to an MCP server."""
        pass

    @abstractmethod
    def list_tools(self) -> Any:
        """List available tools."""
        pass

    @abstractmethod
    def cleanup(self) -> Any:
        """Clean up resources."""
        pass

    @abstractmethod
    def call_tools(self, tool_calls: List[ToolCall]) -> Any:
        """Call tools."""
        pass

class AsyncMCPClient(BaseMCPClient):
    """Asynchronous implementation of MCP client."""

    def __init__(self, command: str = 'uvx', args: List[str] = ["mcp-server-git"]):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.command = command
        self.args = args if args is not None else ['mcp-server-git']

    async def connect_to_mcp_server(self):
        """Connect to an MCP server asynchronously."""
        server_params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

    async def list_tools(self) -> List[Tool]:
        """List available tools."""
        if self.session is None:
            raise RuntimeError("MCP client is not connected to a server.")
        
        response = await self.session.list_tools()
        return response.tools

    async def cleanup(self):
        """Clean up resources asynchronously."""
        await self.exit_stack.aclose()

    async def call_tools(self, tool_calls: List[ToolCall]) -> List[CallToolResult]:
        """Call tools asynchronously."""
        if self.session is None:
            raise RuntimeError("MCP client is not connected to a server.")

        results = []
        for tool_call in tool_calls:
            result = await self.session.call_tool(tool_call.name, tool_call.arguments)
            results.append(result)
        return results

class MCPClient(BaseMCPClient):
    """Synchronous implementation of MCP client."""
    
    def __init__(self):
        self.async_client = AsyncMCPClient()
        self.executor = concurrent.futures.ThreadPoolExecutor()
        self.loop = asyncio.new_event_loop()
    
    def _run_async(self, coro):
        """Run async coroutine in a separate event loop."""
        return self.loop.run_until_complete(coro)
    
    def connect_to_mcp_server(self):
        """Connect to an MCP server synchronously."""
        return self._run_async(self.async_client.connect_to_mcp_server())
    
    def list_tools(self) -> List[Tool]:
        """List available tools."""
        return self._run_async(self.async_client.list_tools())
    
    def cleanup(self):
        """Clean up resources synchronously."""
        result = self._run_async(self.async_client.cleanup())
        self.executor.shutdown()
        self.loop.close()
        return result

    def call_tools(self, tool_calls: List[ToolCall]) -> List[CallToolResult]:
        """Call tools synchronously."""
        return self._run_async(self.async_client.call_tools(tool_calls))