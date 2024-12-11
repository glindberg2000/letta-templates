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
```

## CLI Usage

The CLI tool provides several commands for managing Letta agents:

### Basic Commands

```bash
# List all agents
python letta_cli.py list

# Create a new agent
python letta_cli.py create --name "MyAgent" --description "My custom agent"

# Delete a specific agent
python letta_cli.py delete <agent_id>

# Delete all agents (with confirmation)
python letta_cli.py delete-all

# View memory blocks for an agent
python letta_cli.py memory <agent_id>

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

## Testing

The repository includes a test script (`letta_test.py`) that demonstrates various Letta client operations:

```bash
python letta_test.py
```

The test script supports the same port and URL configurations as the CLI tool.

## Server Options

### Docker Version
The Docker version of Letta runs on port 8283 by default:
```bash
# Check if Docker container is running
docker ps | grep letta
```

### Pip-installed Version
The pip-installed version can run:
- As a service (configured via systemd)
- In-memory (using `memory://` URL)
- On any specified port

## Features

- Comprehensive CLI tool for agent management
- Flexible port configuration
- Support for both Docker and pip-installed versions
- Memory block management
- Interactive chat capabilities
- Batch operations (e.g., delete-all)

## Contributing

Feel free to submit issues and enhancement requests!

# Memory Management

## Viewing Memory Blocks
```bash
# View current memory blocks for an agent
python letta_cli.py memory <agent_id>

# View memory blocks in message history
python letta_cli.py messages <agent_id> --show-human
```

## Updating Memory Blocks
Memory blocks can be updated in two ways:

1. Using the CLI:
```bash
# Update human block
python letta_cli.py update-memory <agent_id> --human "Name: Alice\nRole: Developer\nAge: 25"

# Update persona block
python letta_cli.py update-memory <agent_id> --persona "You are a coding expert..."

# Update both blocks
python letta_cli.py update-memory <agent_id> \
    --human "Name: Bob\nRole: Game Developer" \
    --persona "You are a Roblox expert..."
```

2. Programmatically using the quickstart functions:
```python
from letta_quickstart import update_agent_persona

# Update memory blocks
update_agent_persona(client, agent_id, {
    'human': 'Name: Bob\nRole: Game Developer\nExpertise: Roblox',
    'persona': 'You are a Roblox development expert...'
})
```

## Memory Block Structure

### Human Block
Contains information about the user:
```
Name: [user's name]
Role: [user's role]
[Additional attributes...]
```

### Persona Block
Contains the agent's personality and behavior configuration:
```
You are [description of the agent's role and expertise...]
```

Memory blocks are automatically used by the agent to maintain context and personalize interactions.

# Local API Testing

## Overview
The CLI includes a local testing mode for debugging FastAPI endpoints, particularly useful for tracking message timing and duplicates.

## Usage

1. Basic Test:
```bash
# Test single message
python letta_cli.py --mode local --endpoint "http://localhost:7777/letta/v1/chat/v2" \
    test --npc-id "test-npc-1" --user-id "test-user-1" \
    "Hello! How are you?"

# View conversation history with timing
python letta_cli.py --mode local --endpoint "http://localhost:7777/letta/v1/chat/v2" \
    history
```

2. Quick Test Sequence:
```bash
# Run a quick test sequence
python letta_cli.py --mode local --endpoint "http://localhost:7777/letta/v1/chat/v2" \
    quick-test
```

## Features
- Tracks message timing and detects potential duplicates
- Shows full request/response details
- Alerts on rapid messages (< 1s apart)
- Logs timing between messages

## Example Output
```
Message 1:
Time: 15:30:45
Request: {
  "npc_id": "test-npc-1",
  "participant_id": "test-user-1",
  "message": "Hello!"
}
Response: {
  "message": "Hi there! How can I help?"
}
Duration: 0.234s

Message 2:
Time: 15:30:46
Request: {
  "npc_id": "test-npc-1",
  "participant_id": "test-user-1",
  "message": "How are you?"
}
Response: {
  "message": "I'm doing well, thank you!"
}
Duration: 0.156s
Time since previous: 1.234s
```
```
  </rewritten_file>