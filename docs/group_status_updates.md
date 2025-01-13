# Group and Status Block Updates Guide

## Overview
The `update_group_status()` function handles updating both group membership and NPC status in one call. It automatically:
- Tracks who joins/leaves the group
- Maintains a history of group changes
- Updates NPC location and action state

## Function Usage
```python
update_group_status(
    client=direct_client,
    agent_id=agent.id,
    nearby_players=[],  # List of player data
    current_location="Location Name",
    current_action="idle"  # or "moving"
)
```

## Example Usage with Game Snapshots
```python
# When processing a game snapshot:
def process_snapshot(snapshot_data):
    # Convert snapshot players to required format
    nearby_players = [
        {
            "id": player.id,          # Required: Unique player ID
            "name": player.name,      # Required: Player name
            "appearance": player.appearance or "",  # Optional
            "notes": player.notes or ""            # Optional
        }
        for player in snapshot_data.players
    ]

    # Update NPC state
    update_group_status(
        client=direct_client,
        agent_id=npc.agent_id,
        nearby_players=nearby_players,
        current_location=snapshot_data.location,
        current_action=snapshot_data.npc_action
    )
```

## Memory Block Results
The function updates two memory blocks:

### 1. group_members Block
```python
{
    "members": {
        "player_123": {
            "name": "Alice",
            "appearance": "Red hat",  # Optional
            "notes": "First visit"    # Optional
        },
        "player_456": {
            "name": "Bob",
            "appearance": "Blue shirt",
            "notes": "Looking for shop"
        }
    },
    "summary": "Current members: Alice, Bob",
    "updates": [
        "Alice, Bob joined the group",
        "Charlie left the group",
        # Keeps last 10 updates
    ],
    "last_updated": "2024-01-12T09:15:23.456Z"
}
```

### 2. status Block
```python
{
    "current_location": "Main Plaza",
    "previous_location": "Market District",
    "current_action": "idle",        # or "moving"
    "movement_state": "stationary",  # Set based on current_action
    # Other existing status fields preserved
}
```

## Key Features
1. **Automatic Update Tracking**
   - Detects who joins/leaves the group
   - Creates readable update messages
   - Maintains last 10 updates

2. **State Management**
   - Updates movement state based on action
   - Preserves previous location
   - Maintains existing status fields

3. **Group Management**
   - Tracks current group members
   - Updates group summary
   - Timestamps all changes

## Common Usage Scenarios

### 1. Player Joins Group
```python
update_group_status(
    client=direct_client,
    agent_id=npc.agent_id,
    nearby_players=[{
        "id": "player_123",
        "name": "Alice",
        "appearance": "Red hat",
        "notes": "First time visitor"
    }],
    current_location="Main Plaza",
    current_action="idle"
)
# Result: Adds Alice to members, creates "Alice joined the group" update
```

### 2. NPC Moving with Group
```python
update_group_status(
    client=direct_client,
    agent_id=npc.agent_id,
    nearby_players=current_players,  # Keep same players
    current_location="Market District",
    current_action="moving"
)
# Result: Updates location and sets movement_state to "moving"
```

### 3. Player Leaves Group
```python
# Update with player removed from nearby_players
update_group_status(
    client=direct_client,
    agent_id=npc.agent_id,
    nearby_players=[],  # Empty when no players nearby
    current_location="Market District",
    current_action="idle"
)
# Result: Removes player from members, adds departure to updates
```

## Best Practices
1. Always include required fields (id, name) for players
2. Call this function when:
   - Processing game snapshots
   - After navigation completes
   - When players enter/leave NPC's area
3. Use consistent location names
4. Set appropriate action states ("idle" vs "moving") 

## Debugging & Verification
You can inspect memory blocks using these built-in functions:

### 1. Get Specific Block Contents
```python
from letta_templates.npc_utils import get_memory_block

# Check if NPC is using [SILENCE] correctly
response = chat_with_agent(
    client=direct_client,
    agent_id=agent.id,
    message="@OtherPlayer how are you?",  # Direct message to another player
    role="user",
    name="Player1"
)
print(f"Response: {response}")  # Should show [SILENCE] for direct messages

# Check group block
group_block = get_memory_block(client, agent_id, "group_members")
print(f"Current group members: {json.dumps(group_block, indent=2)}")

# Check status block
status_block = get_memory_block(client, agent_id, "status")
print(f"Current status: {json.dumps(status_block, indent=2)}")
```

### 2. Print All Agent Details
```python
from letta_templates import print_agent_details

# Print all memory blocks and system prompt
print_agent_details(client, agent_id, stage="After Update")
```

This will show:
- All memory block contents
- System prompt
- Agent configuration
- Block limits and IDs 