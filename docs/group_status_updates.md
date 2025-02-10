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

## Batch Message Processing
The Letta API supports sending multiple messages in a single call, which is useful for group conversations:

```python
from letta import Letta, MessageCreate

# Send multiple messages in one call
response = client.agents.messages.create(
    agent_id="agent_id",
    messages=[
        MessageCreate(
            role="user",
            text="Hey everyone!",
            name="Alice"
        ),
        MessageCreate(
            role="user", 
            text="Hi there!",
            name="Bob"
        )
    ]
)
```

This is particularly useful when:
- Processing group conversations
- Catching up on missed messages
- Providing conversation context

The NPC will receive all messages in order and can respond appropriately to the group context.

### Response Format
```python
{
    "messages": [
        {
            "message_type": "assistant_message",
            "assistant_message": "Hi Alice and Bob! Great to see you both!",
            "date": "2024-01-15T09:30:00Z",
            "id": "msg_123"
        }
    ],
    "usage": {
        "completion_tokens": 12,
        "prompt_tokens": 24,
        "total_tokens": 36,
        "step_count": 1
    }
}
```

Note: This feature requires using the direct Letta API client (`from letta import Letta`) rather than the template functions. 

### Shared Conversation History
NPCs in a group can share a common conversation history using a memory block:

```python
# Structure for conversation_history block
{
    "messages": [
        {
            "id": "msg_123",
            "text": "Hey everyone!",
            "sender": "Alice",
            "timestamp": "2024-01-15T09:30:00Z",
            "type": "user_message"
        },
        {
            "id": "msg_124",
            "text": "Hi there!",
            "sender": "Bob",
            "timestamp": "2024-01-15T09:30:01Z",
            "type": "user_message"
        }
    ],
    "last_processed": "2024-01-15T09:30:01Z",
    "summary": "Alice and Bob greeting the group",
    "participants": ["Alice", "Bob", "TownGuide"],
    "max_messages": 10  # Keep last N messages
}
```

Update the history when processing batches:
```python
def update_conversation_history(client, agent_id, new_messages):
    # Get current history
    history = get_memory_block(client, agent_id, "conversation_history")
    
    # Add new messages
    history["messages"] = (
        history["messages"][-(history["max_messages"]-len(new_messages)):] + 
        new_messages
    )
    
    # Update metadata
    history["last_processed"] = datetime.now().isoformat()
    history["participants"] = list(set(
        [msg["sender"] for msg in history["messages"]]
    ))
    
    # Save back to memory
    update_memory_block(client, agent_id, "conversation_history", history)
```

Benefits:
1. All NPCs in group see same conversation context
2. Easy to catch up after rejoining group
3. Maintains chronological order
4. Automatic cleanup of old messages 

### Managing Conversation Transitions
When NPCs switch groups or leave conversations, we need to handle their conversation memory carefully:

```python
def transition_conversation_context(client, agent_id, new_group_id=None):
    """Handle NPC leaving/joining conversation groups"""
    
    # Get current conversation history
    current_history = get_memory_block(client, agent_id, "conversation_history")
    
    # 1. Archive important context
    if current_history["messages"]:
        archival_memory = {
            "conversation_id": current_history.get("conversation_id"),
            "participants": current_history["participants"],
            "summary": current_history["summary"],
            "key_points": extract_key_points(current_history["messages"]),
            "timestamp": datetime.now().isoformat()
        }
        
        # Store in NPC's long-term memory
        client.archival_memory_insert(
            agent_id=agent_id,
            content=json.dumps(archival_memory)
        )
    
    if new_group_id:
        # 2. Join new conversation
        new_history = get_memory_block(client, new_group_id, "conversation_history")
        update_memory_block(client, agent_id, "conversation_history", new_history)
    else:
        # 3. Reset to empty conversation
        empty_history = {
            "messages": [],
            "last_processed": datetime.now().isoformat(),
            "summary": "",
            "participants": [],
            "max_messages": 10
        }
        update_memory_block(client, agent_id, "conversation_history", empty_history)
```

This ensures:
1. Important context is preserved in archival memory
2. NPCs maintain awareness of past conversations
3. Clean transition to new conversations
4. No context bleeding between different groups

The NPC can still reference past conversations when relevant:
```python
# Example: NPC remembering previous interaction
previous_context = client.archival_memory_search(
    agent_id=agent_id,
    query="conversations with Alice about the garden"
)
``` 

## Debugging Group State Issues

### 0. Required Imports
```python
from letta_templates.npc_utils import (
    get_memory_block,
    update_memory_block,
    update_group_status  # This is the main function you should use!
)
```

### Important Note
Always use `update_group_status()` instead of updating blocks directly. It handles:
- Proper block updates
- State synchronization
- Join/leave tracking

```python
# CORRECT WAY:
update_group_status(
    client=direct_client,
    agent_id=agent_id,
    nearby_players=[{
        "id": player_id,
        "name": player_name,
        "appearance": appearance,
        "notes": notes
    }],
    current_location=location,
    current_action=action
)

# DON'T update blocks directly:
# update_memory_block(client, agent_id, "group_members", new_data)  # Avoid this
```

### For Your Current Error
```python
# Fix the import error:
from letta_templates.npc_utils import update_group_status

def process_cluster(cluster_data):
    """Process a cluster of NPCs and players"""
    # Convert your cluster data to nearby_players format
    nearby_players = [
        {
            "id": member_id,
            "name": member_name,
            "appearance": member.get("appearance", ""),
            "notes": member.get("notes", "")
        }
        for member_id, member_name in cluster_data.members.items()
    ]

    # Update each NPC in the cluster
    for agent_id in cluster_data.agent_ids:
        update_group_status(
            client=direct_client,
            agent_id=agent_id,
            nearby_players=nearby_players,
            current_location=cluster_data.location,
            current_action="idle"
        )
``` 

## Location Management

### 1. Location Block Structure
```python
# status block with both coordinates and named location
{
    "current_location": "12.1, 19.9, -11.5",  # Use any string format you want
    "current_action": "idle",
    "movement_state": "stationary"
}
```

### 2. Updating Status with Location
```python
def process_snapshot(snapshot_data):
    """Process a game snapshot with positions"""
    # Format position however you want
    position = snapshot_data["position"]
    location = f"{position.x}, {position.y}, {position.z}"  # Or any format
    
    # Update group status (no coordinates needed)
    update_group_status(
        client=direct_client,
        agent_id=agent_id,
        nearby_players=snapshot_data["nearby_players"],
        current_location=location,  # Just pass the string
        current_action=snapshot_data.get("action", "idle")
    )
```

### Important Notes:
1. Keep coordinates in status block only
2. Use any string format for location
3. Don't duplicate position data in group block
4. Can use coordinates, named locations, or both in the string
5. No need for special JSON structure 