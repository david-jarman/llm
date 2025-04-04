import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from llm.mcp_client import MCPClient
from llm.models import ToolCall


# Mock the CallToolResult class since we don't have access to its exact structure
class MockCallToolResult:
    def __init__(self, id, result, content="test_content"):
        self.id = id
        self.result = result
        self.content = content


@pytest.mark.asyncio
class TestMCPClient:
    async def test_init(self):
        # Test with valid server name
        client = MCPClient("git")
        assert client.command == "uvx"
        assert client.args == ["mcp-server-git"]
        assert client.session is None

        # Test with invalid server name
        with pytest.raises(ValueError, match="Unknown server: invalid"):
            MCPClient("invalid")

    async def test_connect_to_mcp_server(self):
        with patch("llm.mcp_client.stdio_client") as mock_stdio_client, patch(
            "llm.mcp_client.ClientSession"
        ) as mock_client_session:

            # Setup mocks
            mock_stdio = AsyncMock()
            mock_write = AsyncMock()
            mock_stdio_client.return_value.__aenter__.return_value = (
                mock_stdio,
                mock_write,
            )

            mock_session = AsyncMock()
            mock_client_session.return_value.__aenter__.return_value = mock_session

            # Create client and connect
            client = MCPClient("git")
            await client.connect_to_mcp_server()

            # Verify that the client has connected properly
            assert client.stdio == mock_stdio
            assert client.write == mock_write
            assert client.session == mock_session
            mock_session.initialize.assert_called_once()

    async def test_list_tools(self):
        client = MCPClient("git")
        client.session = AsyncMock()
        mock_response = MagicMock()
        mock_response.tools = ["tool1", "tool2"]
        client.session.list_tools.return_value = mock_response

        tools = await client.list_tools()
        assert tools == ["tool1", "tool2"]
        client.session.list_tools.assert_called_once()

        # Test with no session
        client.session = None
        with pytest.raises(
            RuntimeError, match="MCP client is not connected to a server."
        ):
            await client.list_tools()

    async def test_cleanup(self):
        client = MCPClient("git")
        client.exit_stack = AsyncMock()

        await client.cleanup()
        client.exit_stack.aclose.assert_called_once()

    async def test_call_tool(self):
        client = MCPClient("git")
        client.session = AsyncMock()

        tool_call1 = ToolCall(name="tool1", arguments={"arg1": "value1"})
        tool_call2 = ToolCall(name="tool2", arguments={"arg2": "value2"})

        # Setup return values for call_tool
        result1 = MockCallToolResult(id="1", result="result1")
        result2 = MockCallToolResult(id="2", result="result2")
        client.session.call_tool.side_effect = [result1, result2]

        toolCallResult1 = await client.call_tool(tool_call1)
        assert toolCallResult1 == result1

        toolCallResult2 = await client.call_tool(tool_call2)
        assert toolCallResult2 == result2

        assert client.session.call_tool.call_count == 2
        client.session.call_tool.assert_any_call("tool1", {"arg1": "value1"})
        client.session.call_tool.assert_any_call("tool2", {"arg2": "value2"})

        # Test with no arguments
        client.session.call_tool.reset_mock()
        client.session.call_tool.side_effect = [result1]
        tool_call_no_args = ToolCall(name="tool1")

        await client.call_tool(tool_call_no_args)
        client.session.call_tool.assert_called_once_with("tool1", {})

        # Test with no session
        client.session = None
        with pytest.raises(
            RuntimeError, match="MCP client is not connected to a server."
        ):
            await client.call_tool(tool_call1)
