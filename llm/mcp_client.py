from typing import List, Optional, Any, Coroutine, Protocol, runtime_checkable, AsyncIterator, overload
from contextlib import AsyncExitStack, ExitStack
import asyncio
import concurrent.futures
from abc import ABC, abstractmethod
from .models import ToolCall

from mcp import ClientSession, StdioServerParameters, Tool
from mcp.types import CallToolResult, ListToolsResult
from mcp.client.stdio import stdio_client

@runtime_checkable
class MCPClientProtocol(Protocol):
    """Protocol for MCP clients."""
    
    def connect_to_mcp_server(self) -> None:
        """Connect to an MCP server."""
        ...
        
    def list_tools(self) -> List[Tool]:
        """List available tools."""
        ...
        
    def cleanup(self) -> None:
        """Clean up resources."""
        ...
        
    def call_tools(self, tool_calls: List[ToolCall]) -> List[CallToolResult]:
        """Call tools."""
        ...

class AsyncMCPClientProtocol(Protocol):
    """Protocol for async MCP clients."""
    
    async def connect_to_mcp_server(self) -> None:
        """Connect to an MCP server."""
        ...
        
    async def list_tools(self) -> List[Tool]:
        """List available tools."""
        ...
        
    async def cleanup(self) -> None:
        """Clean up resources."""
        ...
        
    async def call_tools(self, tool_calls: List[ToolCall]) -> List[CallToolResult]:
        """Call tools."""
        ...

class BaseSyncMCPClient(ABC):
    """Abstract base class for synchronous MCP clients."""

    @abstractmethod
    def connect_to_mcp_server(self) -> None:
        """Connect to an MCP server."""
        pass

    @abstractmethod
    def list_tools(self) -> List[Tool]:
        """List available tools."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources."""
        pass

    @abstractmethod
    def call_tools(self, tool_calls: List[ToolCall]) -> List[CallToolResult]:
        """Call tools."""
        pass

class BaseAsyncMCPClient(ABC):
    """Abstract base class for asynchronous MCP clients."""

    @abstractmethod
    async def connect_to_mcp_server(self) -> None:
        """Connect to an MCP server."""
        pass

    @abstractmethod
    async def list_tools(self) -> List[Tool]:
        """List available tools."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources."""
        pass

    @abstractmethod
    async def call_tools(self, tool_calls: List[ToolCall]) -> List[CallToolResult]:
        """Call tools."""
        pass

class AsyncMCPClient(BaseAsyncMCPClient):
    """Asynchronous implementation of MCP client."""

    def __init__(self, command: str = 'uvx', args: List[str] = ["mcp-server-git"]):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.command = command
        self.args = args

    async def connect_to_mcp_server(self) -> None:
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

    async def cleanup(self) -> None:
        """Clean up resources asynchronously."""
        await self.exit_stack.aclose()

    async def call_tools(self, tool_calls: List[ToolCall]) -> List[CallToolResult]:
        """Call tools asynchronously."""
        if self.session is None:
            raise RuntimeError("MCP client is not connected to a server.")

        results = []
        for tool_call in tool_calls:
            result = await self.session.call_tool(tool_call.name, tool_call.arguments or {})
            results.append(result)
        return results

class MCPClient(BaseSyncMCPClient):
    """Synchronous implementation of MCP client."""
    
    def __init__(self, command: str = 'uvx', args: List[str] = ["mcp-server-git"]):
        self.async_client = AsyncMCPClient(command, args)
        self.loop = None
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
            return self.loop.run_until_complete(coro)
        except RuntimeError as e:
            # Handle "Event loop is closed" errors
            if "Event loop is closed" in str(e):
                self._ensure_loop()
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
                    self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
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