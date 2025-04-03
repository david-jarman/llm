# Model Context Protocol

## Considerations

- Updating the plugin interface to be able to pass tools to models that support them
- Response model should be able to include tool call responses
- Convert tool call response to then execute MCP servers that match
    - What about concurrent tools?
- Does the SQLite database schema need to be updated to include tool calls?
- Option to show intermediate responses? (debug mode?)
- Should print statuses of tool calls

## Links

### Examples

MCP simple chat with Python client SDK: [GitHub](https://github.com/modelcontextprotocol/python-sdk/blob/main/examples/clients/simple-chatbot/mcp_simple_chatbot/main.py)

OpenAI agents SDK with MCP: [GitHub](https://github.com/openai/openai-agents-python/blob/main/examples/mcp/git_example/main.py)

### Documentation

Model Context Protocol: [Docs](https://modelcontextprotocol.io/introduction)
OpenAI chat mode function calling: [Docs](https://platform.openai.com/docs/guides/function-calling?api-mode=chat)


## Desired Usage

-t/--tools option: run with mcp tools, if model supports tools

### Run llm and include mcp servers as tools

llm -t "Summarize the last commit in this git repo"

### List MCP servers

llm mcp list

### Add MCP server

llm mcp add