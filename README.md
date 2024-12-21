# Letta Client Projects

A collection of tools and utilities for working with the Letta AI server, including a CLI tool for managing agents.

## Version Compatibility

### Client-Server Version Matching
The Letta client must match the server version to handle tool schemas correctly. If you see validation errors like:
```
ValidationError: validation errors for AgentState
tools.0.return_char_limit
  Extra inputs are not permitted
```
Update your client to match the server:
```bash
# Check current version
pip show letta

# Upgrade to latest
pip install --upgrade letta
```

## Installation

1. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Unix/MacOS
# or
venv\Scripts\activate  # On Windows
```

2. Install requirements:
```bash
pip install -r requirements.txt
pip install --upgrade letta  # Ensure latest client version
```

3. Copy and configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Configuration

The `.env` file supports the following configurations:

```bash
# Choose your Letta server type:
# For Docker: LETTA_BASE_URL=http://localhost:8283
# For pip-installed: LETTA_BASE_URL=memory://

LETTA_BASE_URL=http://localhost:8283

# Optional port override
# LETTA_PORT=8083

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Claude Configuration (optional)
LETTA_LLM_ENDPOINT=https://api.anthropic.com/v1/messages
LETTA_LLM_ENDPOINT_TYPE=anthropic
LETTA_LLM_MODEL=claude-3-haiku-20240307
LETTA_LLM_CONTEXT_WINDOW=200000

# Embedding Configuration for Claude
LETTA_EMBEDDING_ENDPOINT=https://api.anthropic.com/v1/embeddings
LETTA_EMBEDDING_ENDPOINT_TYPE=anthropic
LETTA_EMBEDDING_MODEL=claude-3-haiku-20240307
LETTA_EMBEDDING_DIM=1536
```

## Creating a Personalized Agent

You can create a personalized agent using either OpenAI or Claude as the LLM provider:

### Command Line Usage

```bash
# Create agent with OpenAI (default)
python letta_quickstart.py --name emma_openai --llm openai

# Create agent with Claude 3
python letta_quickstart.py --name emma_claude --llm claude

# Additional options
python letta_quickstart.py --name custom_agent --llm claude --keep  # Keep agent after creation
```

### Programmatic Usage

```python
from letta_quickstart import create_personalized_agent

# Create with OpenAI (default)
agent_openai = create_personalized_agent(name="emma_openai")

# Create with Claude 3
agent_claude = create_personalized_agent(name="emma_claude", use_claude=True)
```

## CLI Usage

The CLI tool provides several commands for managing Letta agents:

### Basic Commands

```bash
# List all agents
python letta_cli.py list

# Create a new agent with specific LLM
python letta_cli.py create --name "MyAgent" --description "My custom agent" --llm openai
python letta_cli.py create --name "ClaudeAgent" --description "Claude-powered assistant" --llm claude

# Delete a specific agent
python letta_cli.py delete <agent_id>

# Delete all agents (with confirmation)
python letta_cli.py delete-all

# View memory blocks for an agent
python letta_cli.py memory <agent_id>

# View agent details (including system prompt)
python letta_cli.py details <agent_id>

# Chat with an agent
python letta_cli.py chat <agent_id> "Your message here"
```

### Port Configuration

You can specify which Letta server to connect to in several ways:

```bash
# Use specific port
python letta_cli.py --port 8283 list

# Use different URL and port
python letta_cli.py --url http://localhost:8283 --port 8083 list

# Use in-memory version
python letta_cli.py --url memory:// list
```

Port resolution priority:
1. Command line `--port` argument
2. `LETTA_PORT` environment variable
3. Port in base URL
4. Default (8283 for Docker version)

## Memory Management

### Viewing Memory Blocks
```bash
# View current memory blocks for an agent
python letta_cli.py memory <agent_id>

# View memory blocks in message history
python letta_cli.py messages <agent_id> --show-human
```

### Updating Memory Blocks
Memory blocks can be updated in two ways:

1. Using the CLI:
```bash
# Update human block
python letta_cli.py update-memory <agent_id> --human "Name: Alice\nRole: Developer"

# Update persona block
python letta_cli.py update-memory <agent_id> --persona "Name: Emma\nRole: AI Assistant"

# Update both blocks
python letta_cli.py update-memory <agent_id> \
    --human "Name: Bob\nRole: Data Scientist" \
    --persona "Name: Emma\nRole: Research Assistant"
```

2. Programmatically using the quickstart functions:
```python
from letta_quickstart import update_agent_persona

# Update memory blocks
update_agent_persona(client, agent_id, {
    'human': 'Name: Bob\nRole: Data Scientist',
    'persona': 'Name: Emma\nRole: Research Assistant'
})
```

## Contributing

Feel free to submit issues and enhancement requests!

## LLM Provider Configuration

### OpenAI Configuration
- Uses GPT-4 model
- Context window: 8000 tokens
- Default embedding model: text-embedding-ada-002

### Claude Configuration
- Uses Claude 3 Haiku model
- Context window: 200,000 tokens
- Supports both chat and embedding capabilities

You can switch between providers using either:
1. Command-line arguments (`--llm claude` or `--llm openai`)
2. Environment variables in `.env`
3. Programmatic configuration via `create_personalized_agent(use_claude=True/False)`

## Custom Tools and Action Handling

### Message Types in 0.6.6+
The latest version uses specific message types for tool interactions:

```python
# Response contains a sequence of messages:
response.messages = [
    ToolCallMessage,      # Tool being called
    ToolReturnMessage,    # Result of the tool call
    ReasoningMessage,     # AI's thought process
]
```

### Handling Tool Responses
The new format requires different handling for each message type:

```python
def chat_with_agent(client, agent_id, message):
    response = client.send_message(
        agent_id=agent_id,
        message=message,
        role="user"
    )
    
    if hasattr(response, 'messages'):
        for msg in response.messages:
            # Handle ToolCallMessage
            if type(msg).__name__ == 'ToolCallMessage':
                if hasattr(msg, 'tool_call'):
                    print(f"Tool Call: {msg.tool_call.name}")
                    args = json.loads(msg.tool_call.arguments)
                    print(f"Arguments: {json.dumps(args, indent=2)}")
            
            # Handle ToolReturnMessage
            elif type(msg).__name__ == 'ToolReturnMessage':
                if hasattr(msg, 'tool_return'):
                    result = json.loads(msg.tool_return)
                    if 'message' in result:
                        inner_result = json.loads(result['message'])
                        print(json.dumps(inner_result, indent=2))
            
            # Handle ReasoningMessage
            elif type(msg).__name__ == 'ReasoningMessage':
                if hasattr(msg, 'reasoning'):
                    print(f"Reasoning: {msg.reasoning}")
```

### Example Response Structure
A navigation command response looks like:

```python
# Tool Call Message
{
    'tool_call': {
        'name': 'navigate_to',
        'arguments': '{"destination": "stand", "request_heartbeat": true}'
    }
}

# Tool Return Message
{
    'tool_return': {
        'status': 'OK',
        'message': {
            'status': 'success',
            'action_called': 'navigate',
            'message': 'Navigating to the named location "stand".',
            'timestamp': '2024-12-20T23:33:19.934349'
        }
    },
    'status': 'success'
}

# Reasoning Message
{
    'reasoning': "We're now set to navigate to the stand..."
}
```

### Helper for Roblox Integration
Extract relevant information from the response:

```python
def extract_tool_result(response):
    """
    Extract tool calls, results, and messages for Roblox.
    
    Returns:
        dict: {
            'tool_calls': List of tool calls and their results
            'reasoning': AI's thought process
            'final_message': Final response text
        }
    """
    result = {
        'tool_calls': [],
        'reasoning': None,
        'final_message': None
    }
    
    if hasattr(response, 'messages'):
        for msg in response.messages:
            # Extract Tool Calls
            if type(msg).__name__ == 'ToolCallMessage':
                if hasattr(msg, 'tool_call'):
                    tool_call = {
                        'name': msg.tool_call.name,
                        'arguments': json.loads(msg.tool_call.arguments),
                        'result': None
                    }
                    result['tool_calls'].append(tool_call)
            
            # Extract Tool Results
            elif type(msg).__name__ == 'ToolReturnMessage':
                if result['tool_calls'] and hasattr(msg, 'tool_return'):
                    try:
                        return_data = json.loads(msg.tool_return)
                        if 'message' in return_data:
                            result['tool_calls'][-1]['result'] = json.loads(return_data['message'])
                    except:
                        result['tool_calls'][-1]['result'] = msg.tool_return
            
            # Extract Reasoning
            elif type(msg).__name__ == 'ReasoningMessage':
                if hasattr(msg, 'reasoning'):
                    result['reasoning'] = msg.reasoning
            
            # Extract Final Message
            elif hasattr(msg, 'text') and msg.text:
                result['final_message'] = msg.text
    
    return result

# Usage Example
response = client.send_message(
    agent_id=agent_id,
    message="Navigate to the stand",
    role="user"
)

result = extract_tool_result(response)
print("Tool Calls:", result['tool_calls'])
print("Reasoning:", result['reasoning'])
print("Final Message:", result['final_message'])
```

### Key Differences from Previous Versions
1. Messages are now typed (ToolCallMessage, ToolReturnMessage, etc.)
2. Tool results have a nested structure
3. Reasoning/thought process is included
4. Each message type has specific attributes
5. Results need to be parsed from nested JSON structures

### Integration Tips
1. Always check message types before accessing attributes
2. Parse nested JSON in tool returns
3. Keep track of tool call/return pairs
4. Use the helper function to extract relevant data
5. Handle both success and error states in tool returns

## Debugging and Logging

### Docker Container Logs
To view logs from the Letta Docker container:

```bash
# View logs in real-time
docker logs -f letta-source-letta_server-1

# View last N lines
docker logs --tail 100 letta-source-letta_server-1

# View logs since specific time
docker logs --since 5m letta-source-letta_server-1  # Last 5 minutes
docker logs --since 2024-01-01T00:00:00Z letta-source-letta_server-1  # Since specific date

# Include timestamps
docker logs -f --timestamps letta-source-letta_server-1
```

### Filtering Logs
```bash
# Filter for specific content
docker logs letta-source-letta_server-1 2>&1 | grep "error"
docker logs letta-source-letta_server-1 2>&1 | grep "tool"

# Save logs to file
docker logs letta-source-letta_server-1 > letta_server.log
```

### Finding Your Container Name
If your container name is different, you can find it using:
```bash
# List all running containers
docker ps | grep letta
```

Look for the container running the `letta/letta:latest` image.

### Common Issues to Check
- Tool registration errors
- Function call validation errors
- Response parsing issues
- Connection timeouts

## Creating Custom Tools

### Tool Implementation Pattern
Custom tools should follow this pattern:

```python
def my_tool(param1: str, request_heartbeat: bool = True) -> dict:
    """
    Tool description.
    
    Args:
        param1 (str): Description of parameter
        request_heartbeat (bool): Request an immediate heartbeat after function execution.
                                Set to `True` if you want to send a follow-up message.
        
    Returns:
        dict: A response indicating the result of the action.
        
    Notes:
        - Returns a standardized response format
        - Includes timestamp for action tracking
    """
    import datetime
    
    return {
        "status": "success",
        "action_called": "action_name",
        "message": f"Action result message for {param1}.",
        "timestamp": datetime.datetime.now().isoformat()
    }
```

### Example: Navigation Tool
```python
def navigate_to(destination: str, request_heartbeat: bool = True) -> dict:
    """
    Navigate to a specified location in the game world.

    Args:
        destination (str): The destination name or coordinate string
        request_heartbeat (bool): Request heartbeat after execution
        
    Returns:
        dict: Navigation result
    """
    import datetime
    
    return {
        "status": "success",
        "action_called": "navigate",
        "message": f"Navigating to the named location '{destination}'.",
        "timestamp": datetime.datetime.now().isoformat()
    }
```

### Example: Examination Tool
```python
def examine_object(object_name: str, request_heartbeat: bool = True) -> dict:
    """
    Examine an object in the game world.
    
    Args:
        object_name (str): Name of the object to examine
        request_heartbeat (bool): Request heartbeat after execution
        
    Returns:
        dict: Examination result
    """
    import datetime
    
    return {
        "status": "success",
        "action_called": "examine",
        "message": f"Examining the {object_name}.",
        "timestamp": datetime.datetime.now().isoformat()
    }
```

### Creating and Using Tools

```python
# Create tools
navigate_tool = client.create_tool(navigate_to)
examine_tool = client.create_tool(examine_object)

# Create agent with tools
agent = client.create_agent(
    name="npc_agent",
    tool_ids=[navigate_tool.id, examine_tool.id],
    tool_rules=[TerminalToolRule(tool_name="send_message")]
)
```

### Tool Response Format
All tools should return a standardized response:

```python
{
    "status": "success",  # or "error"
    "action_called": str, # name of the action
    "message": str,       # human-readable result
    "timestamp": str      # ISO format timestamp
}
```

### Tool Management
Clean up old tools before creating new ones:

```python
def cleanup_test_tools(client, prefix: str = "examine_object"):
    """Clean up old test tools."""
    tools = client.list_tools()
    for tool in tools:
        if tool.name == prefix or tool.name.startswith(f"{prefix}_"):
            client.delete_tool(tool.id)
```

### Example Usage
```python
# Send navigation command
response = client.send_message(
    agent_id=agent.id,
    message="Navigate to the stand",
    role="user"
)

# Response will include:
{
    "messages": [
        {
            "message_type": "tool_call_message",
            "tool_call": {
                "name": "navigate_to",
                "arguments": {"destination": "stand", "request_heartbeat": true}
            }
        },
        {
            "message_type": "tool_return_message",
            "tool_return": {
                "status": "success",
                "action_called": "navigate",
                "message": "Navigating to the named location 'stand'.",
                "timestamp": "2024-12-21T03:59:38.056236"
            }
        }
    ]
}
```

### Key Points
1. Always include `request_heartbeat` parameter
2. Return standardized response format
3. Include timestamps in ISO format
4. Clean up old tools before creating new ones
5. Use tool rules to control execution flow