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

### Creating Agents with Custom Tools

You can create agents with custom tools like the `perform_action` tool:

```python
from letta_quickstart import create_personalized_agent

# Create agent with perform_action tool
agent = create_personalized_agent(
    name="action_agent",
    use_claude=False,  # Use OpenAI (default)
    overwrite=True     # Replace if exists
)
```

The agent will have:
- Base tools enabled (`include_base_tools=True`)
- The `perform_action` tool for NPC actions
- Custom system prompt with tool usage instructions

### Handling Tool Responses

When interacting with an agent that uses tools, you'll need to handle different types of responses:

```python
response = client.send_message(
    agent_id=agent_id,
    message="Follow me",
    role="user"
)

if response and hasattr(response, 'messages'):
    for msg in response.messages:
        # Handle direct text responses
        if hasattr(msg, 'text') and msg.text:
            print(f"LLM Response: {msg.text}")
            
        # Handle function calls (e.g., perform_action)
        elif hasattr(msg, 'function_call'):
            if msg.function_call.name == 'perform_action':
                args = json.loads(msg.function_call.arguments)
                action = args.get('action')
                params = args.get('parameters')
                print(f"Action Called: {action}")
                print(f"Parameters: {params}")
                
        # Handle function returns
        elif hasattr(msg, 'function_return'):
            try:
                result = json.loads(msg.function_return)
                status = result.get('status')
                action = result.get('action_called')
                message = result.get('message')
                print(f"Action Result: {action} - {status}")
                print(f"Message: {message}")
            except json.JSONDecodeError:
                print(f"Raw Return: {msg.function_return}")
                
        # Handle internal thoughts
        elif hasattr(msg, 'internal_monologue'):
            print(f"Internal: {msg.internal_monologue}")
```

### Example Response Structure

A typical action response might look like:

```python
{
    'messages': [
        # Internal thought process
        {
            'internal_monologue': 'User wants to be followed...'
        },
        # Tool call
        {
            'function_call': {
                'name': 'perform_action',
                'arguments': '{"action": "follow", "request_heartbeat": true}'
            }
        },
        # Tool result
        {
            'function_return': {
                'status': 'success',
                'action_called': 'follow',
                'message': 'Now following the current target.',
                'timestamp': '2024-12-13T22:42:27.041760'
            }
        },
        # Final LLM response
        {
            'text': "I'm now following you! Let's share some awesome insights together."
        }
    ]
}
```

### Aggregating Responses for Roblox

When sending results back to Roblox, you might want to combine the action result and LLM response:

```python
def extract_action_result(response):
    result = {
        'action_status': None,
        'action_message': None,
        'llm_response': None
    }
    
    if hasattr(response, 'messages'):
        for msg in response.messages:
            # Get function return (action result)
            if hasattr(msg, 'function_return'):
                try:
                    action_result = json.loads(msg.function_return)
                    result['action_status'] = action_result.get('status')
                    result['action_message'] = action_result.get('message')
                except:
                    pass
                    
            # Get final LLM response
            elif hasattr(msg, 'text') and msg.text:
                result['llm_response'] = msg.text
                
    return result

# Usage example:
response = client.send_message(agent_id=agent_id, message="Follow me", role="user")
result = extract_action_result(response)

# Send to Roblox:
{
    'action_status': 'success',
    'action_message': 'Now following the current target.',
    'llm_response': "I'm now following you! Let's share some awesome insights together."
}
```

This structure allows Roblox to:
1. Verify the action was successful
2. Update NPC state based on the action result
3. Display the LLM's conversational response to the user