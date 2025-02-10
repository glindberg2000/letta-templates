# Letta v0.9.8 - Response Handling Guide

## Message Sending - Keep It Simple

1. Send a message - this is all you need
```python
from letta_templates.npc_utils_v2 import extract_agent_response

# 1. Send a message - this is all you need
response = client.agents.messages.create(
    agent_id=agent_id,
    message="Hello!",              # The message text
    role="user",                   # Optional: "user" (default), "system"
    name="Player123"               # Optional: Speaker name
)

# 2. Get the response
result = extract_agent_response(response)
print(result["message"])           # Show the agent's reply
```

That's it! Letta handles everything else internally:
- Message history
- Context tracking
- Tool processing

## Common Use Cases

### 1. Player Chat
```python
# When a player talks to the NPC
response = client.agents.messages.create(
    agent_id=npc_id,
    message=player_message,
    role="user",
    name=player_name
)

# Show the NPC's response
result = extract_agent_response(response)
print(result["message"])
```

### 2. System Updates
```python
# Update the NPC about location changes
response = client.agents.messages.create(
    agent_id=npc_id,
    message="You are now in Town Square",
    role="system"
)
```

### 3. Handling Tool Calls
```python
# Send player message
response = client.agents.messages.create(
    agent_id=npc_id,
    message="Can you show me to the shop?",
    role="user",
    name="Player123"
)

# Check for navigation or other tool calls
result = extract_agent_response(response)

# Handle any tool calls first
for tool_call in result["tool_calls"]:
    if tool_call["tool"] == "navigate_to":
        destination = tool_call["args"]["destination_slug"]
        print(f"NPC is heading to: {destination}")

# Then show the response
print(result["message"])
```

## Response Structure
The `extract_agent_response()` function returns a dict with:
- `message`: Final response to show the user
- `tool_calls`: List of tool calls with name and arguments
- `tool_results`: Results from tool executions
- `reasoning`: Agent's reasoning steps

## Best Practices
1. Always check tool calls before showing the final message
2. Use system messages for location/context updates:
```python
# Update location context
client.agents.messages.create(
    agent_id=agent_id,
    message="You are now in Town Square",
    role="system"
)
```

3. Update memory blocks for persistent state:
```python
from letta_templates.npc_utils_v2 import update_location_status

# Update location with history
status = update_location_status(
    client,
    agent_id,
    current_location="Town Square",
    current_action="greeting"
)
```

## Status and Group Management

### Status Updates
```python
from letta_templates.npc_utils_v2 import update_status

# Update status with narrative
update_status(client, agent_id, 
    "Taking a break by the fountain, watching the pigeons and greeting passersby"
)

# Read current status
status = get_memory_block(client, agent_id, "status")
print(f"Current status: {status}")
```

### Group Management
```python
from letta_templates.npc_utils_v2 import update_group_members_v2

# Update group with new players
nearby_players = [
    {
        "id": "player123",
        "name": "Alice",
        "appearance": "Wearing a red hat",
        "location": "Town Square",
        "notes": "First time visitor"
    },
    {
        "id": "player456",
        "name": "Bob",
        "location": "Town Square"
    }
]

group_state = update_group_members_v2(client, agent_id, nearby_players)

# Read group history
from letta_templates.npc_utils_v2 import get_group_history

history = get_group_history(client, agent_id)
for event in history:
    print(event)  # e.g. "Alice, Bob joined the group at 2024-01-25T10:30:00"
```

### Journal Management
```python
# Read journal entries
journal = get_memory_block(client, agent_id, "journal")

# Journal is typically updated through tool calls
# The agent will use core_memory_append/replace for the journal block

# Example tool call for journal update:
for tool_call in result["tool_calls"]:
    if tool_call["tool"] == "core_memory_append":
        if tool_call["args"]["block_label"] == "journal":
            new_entry = tool_call["args"]["content"]
            print(f"Adding to journal: {new_entry}")
```

## Error Handling
```python
try:
    response = client.agents.messages.create(...)
    result = extract_agent_response(response)
    
    # Check for failed tool calls
    for tool_result in result["tool_results"]:
        if tool_result["status"] == "error":
            print(f"Tool error: {tool_result['result']}")
            
except Exception as e:
    print(f"Error in message handling: {e}")
```

For more examples and detailed API documentation, visit:
https://github.com/glindberg2000/letta-templates 

## Initial Setup

### Creating an Agent with Memory Blocks
```python
from letta_templates.npc_utils_v2 import create_memory_blocks

# Define initial memory blocks
initial_blocks = {
    "locations": {
        "known_locations": ["Town Square", "Shop", "Fountain"],
        "visited_locations": [],
        "favorite_spots": []
    },
    "status": "Just arrived in Town Square, ready to help visitors",
    "group_members": {
        "members": {},
        "updates": [],
        "summary": "No current group members",
        "last_updated": ""
    },
    "journal": {
        "entries": [],
        "last_updated": ""
    }
}

# Create agent with memory blocks
memory_blocks = create_memory_blocks(client, initial_blocks)

agent = client.agents.create(
    name="TownGuide",
    description="A helpful town guide",
    memory_blocks=memory_blocks,
    # ... other agent configuration ...
)
```

### Basic Message Flow
```python
# 1. Send message and get response
response = client.agents.messages.create(
    agent_id=agent.id,
    message="Can you show me around?",
    role="user",
    name="Visitor"
)

# 2. Extract structured response
result = extract_agent_response(response)

# 3. Handle tool calls first
for tool_call in result["tool_calls"]:
    # Handle navigation, actions, etc.
    print(f"Tool: {tool_call['tool']}")
    print(f"Args: {tool_call['args']}")

# 4. Show final message to user
print(result["message"])
```

### Debugging Client Setup
```python
from letta_templates.npc_utils_v2 import print_client_info

# Print API information
print_client_info(client)
```

## Agent Setup

### Production Setup
```python
# App startup - check tools once
client = create_letta_client()
custom_tools = ensure_custom_tools_exist(client)

# Required memory blocks
initial_blocks = {
    "locations": { ... },
    "status": "Ready to help",
    "group_members": { ... },
    "persona": { ... },
    "journal": {           # Don't forget this one!
        "entries": [],
        "last_updated": ""
    }
}

# Create agent with full prompt
agent = create_personalized_agent_v3(
    name="TownGuide",
    memory_blocks=initial_blocks,
    client=client,
    llm_type="openai",     # Default LLM provider
    with_custom_tools=True,  # Include navigation etc.
    prompt_version="FULL"    # Use full NPC prompt
)
```

### Development Setup
```python
# Dev setup - update tools as needed
client = create_letta_client()
update_tools(client)  # Recreates tools with latest code
```

## Player Join/Leave Events

Use optimized system messages to handle player events efficiently:

```python
from letta_templates.npc_prompts import PLAYER_JOIN_MESSAGE, PLAYER_LEAVE_MESSAGE

# When a player joins
# Only searches archival memory if player isn't recognized recently
client.agents.messages.create(
    agent_id=agent_id,
    message=PLAYER_JOIN_MESSAGE.format(
        name="Alice",
        player_id="alice_123"
    ),
    role="system"
)

# When a player leaves
# Only saves to archival memory if meaningful interactions occurred
client.agents.messages.create(
    agent_id=agent_id,
    message=PLAYER_LEAVE_MESSAGE.format(
        name="Alice",
        player_id="alice_123"
    ),
    role="system"
)
```

This ensures:
- Efficient memory usage (only searches/saves when needed)
- History tracking for meaningful interactions
- Optimized for high-traffic scenarios 