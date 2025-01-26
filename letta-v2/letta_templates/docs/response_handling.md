# Letta v0.9.7 - Response Handling Guide

The new version includes a simplified way to handle agent responses. Here's how to use it:

## Basic Usage
```python
from letta_templates.npc_utils_v2 import extract_agent_response

# Send message and handle response
response = client.agents.messages.create(
    agent_id=agent_id,
    message="Go to the shop",
    role="user",
    name="Player123"
)

result = extract_agent_response(response)

# Get final message to show player
print(result["message"])  # "I'll head to the shop right away!"

# Handle any tool calls (e.g. navigation)
for tool_call in result["tool_calls"]:
    if tool_call["tool"] == "navigate_to":
        destination = tool_call["args"]["destination_slug"]
        print(f"NPC is navigating to: {destination}")
```

## Common Tool Call Patterns

1. Navigation:
```python
for tool_call in result["tool_calls"]:
    if tool_call["tool"] == "navigate_to":
        # Handle navigation
        destination = tool_call["args"]["destination_slug"]
        coordinates = tool_call["args"].get("coordinates")
    
    elif tool_call["tool"] == "perform_action":
        # Handle actions like wave, sit, etc.
        action = tool_call["args"]["action"]
        target = tool_call["args"].get("target")
```

2. Group Management:
```python
for tool_call in result["tool_calls"]:
    if tool_call["tool"] == "group_memory_append":
        # Handle group updates
        player = tool_call["args"]["player_name"]
        note = tool_call["args"]["note"]
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