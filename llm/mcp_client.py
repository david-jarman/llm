from typing import List, Optional
from contextlib import AsyncExitStack
from .models import ToolCall

from mcp import ClientSession, StdioServerParameters, Tool
from mcp.client.stdio import stdio_client

class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.tools: List[Tool] = []

    async def connect_to_mcp_server(self): #, server_script_path: str):
        """Connect to an MCP server

        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        #is_python = server_script_path.endswith('.py')
        #is_js = server_script_path.endswith('.js')
        #if not (is_python or is_js):
        #    raise ValueError("Server script must be a .py or .js file")

        #command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command='uvx',
            args=['mcp-server-git'],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        self.tools = response.tools

    def list_tools(self) -> List[Tool]:
        """List available tools"""

        return self.tools
    
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

    async def call_tools(self, tool_calls: List[ToolCall]):
        """Call tools"""
        for tool_call in tool_calls:
            result = await self.session.call_tool(tool_call.name, tool_call.arguments)
            for x in result.content:
                print(x)