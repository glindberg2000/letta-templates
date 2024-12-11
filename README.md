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

## Creating a Personalized Agent

You can create a personalized agent using the following configuration:

```python
from letta import ChatMemory, EmbeddingConfig, LLMConfig, create_client
from letta.prompts import gpt_system

client = create_client()

agent_state = client.create_agent(
    name="emma_research_assistant",
    memory=ChatMemory(
        # Human context - who the agent is talking to
        human="""
Name: Alex Thompson
Role: Data Scientist
Interests: Machine Learning, Data Analysis, Python Programming
Communication Style: Prefers clear, technical explanations
        """.strip(),
        # Agent's personality and characteristics
        persona="""
Name: Emma
Role: AI Research Assistant
Personality: Professional, knowledgeable, and friendly. Enjoys explaining complex topics in simple terms.
Expertise: Data science, machine learning, and programming with a focus on Python.
Communication Style: Clear and precise, uses analogies when helpful, and maintains a supportive tone.
        """.strip()
    ),
    llm_config=LLMConfig(
        model="gpt-4",
        model_endpoint_type="openai",
        model_endpoint="https://api.openai.com/v1",
        context_window=8000,
    ),
    embedding_config=EmbeddingConfig(
        embedding_endpoint_type="openai",
        embedding_endpoint="https://api.openai.com/v1",
        embedding_model="text-embedding-ada-002",
        embedding_dim=1536,
        embedding_chunk_size=300,
    ),
    # Use the built-in system prompt
    system=gpt_system.get_system_text("memgpt_chat"),
    include_base_tools=True,
    tools=[],
)
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