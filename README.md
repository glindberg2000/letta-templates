# Letta Quickstart for Roblox Development

This project provides a quick-start template for using Letta agents in Roblox development workflows.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment:
Copy `.env.example` to `.env` and fill in your values:
```bash
cp .env.example .env
```

3. Start the Letta server:
```bash
docker run -p 8283:8283 letta/server
```

## Usage

Basic usage:
```python
from letta import create_client
from letta_quickstart import create_roblox_agent, chat_with_agent

client = create_client(base_url="http://localhost:8283")
agent = create_roblox_agent(client, "RobloxHelper")

response = chat_with_agent(client, agent.id, 
    "Can you help me optimize this Lua script?")
print(response)
```

## Features

- Create specialized Roblox development agents
- Update agent personas for different development focuses
- Maintain conversation context
- Clean error handling and resource cleanup

## Configuration

The following environment variables are supported:
- `LETTA_SERVER_PORT` (default: 8283)
- `OPENAI_API_KEY` (required)
- `LETTA_SERVER_HOST` (default: localhost)

## Examples

See `examples/` directory for more usage examples:
- Basic agent creation
- Memory management
- Code optimization workflows 