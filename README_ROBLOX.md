# Roblox NPC Integration Guide

## Quick Start

1. Install latest version with NPC support:
```bash
pip install git+https://github.com/yourusername/letta-templates.git@v0.8.0
```

2. Basic usage:
```python
from letta_templates import create_personalized_agent, update_group_status

# Create NPC agent with required memory blocks
agent = create_personalized_agent(
    name="town_guide",
    client=letta_client,
    memory_blocks={
        "persona": {
            "name": "town_guide",
            "role": "Tutorial Guide",
            "personality": "Patient and friendly",
            "background": "Helps new players explore",
            "interests": ["Teaching", "Exploring"],
            "journal": []  # Optional
        },
        "status": {
            "region": "Tutorial",
            "current_location": "Town Square",
            "current_action": "idle",
            "movement_state": "stationary",
            "nearby_locations": ["Market", "Garden"]
        },
        "group_members": {
            "members": {},
            "summary": "No players nearby",
            "updates": [],
            "last_updated": "2024-01-12T00:00:00Z"
        },
        "locations": {
            "known_locations": [
                {
                    "name": "Market District",
                    "description": "Busy shopping area",
                    "coordinates": [-28.4, 15.0, -95.2],
                    "slug": "market_district"
                }
            ]
        }
    }
)

# Update when players are nearby
update_group_status(
    client=letta_client,
    agent_id=agent.id,
    nearby_players=[{
        "id": "player_123",
        "name": "Alex",
        "appearance": "Wearing a blue hat",
        "notes": "First time visitor"
    }],
    current_location="Town Square",
    current_action="idle"
)
```

## Memory System

### Required Memory Blocks
All blocks must be provided during creation:

1. **Persona Block**
   - Basic identity and personality
   - Optional journal for experiences
   - Customizable fields for character depth

2. **Status Block**
   - NPC's current state
   - Location and movement tracking
   - Action status

3. **Group Members Block**
   - Current group members
   - Last 10 group updates (joins/leaves)
   - Member appearance and notes

4. **Locations Block**
   - Known navigation points
   - Coordinates and descriptions
   - Navigation slugs

### Group Updates
The system maintains a history of group changes:
```python
{
    "members": {
        "player_123": {
            "name": "Alex",
            "appearance": "Blue hat",
            "notes": "First time visitor"
        }
    },
    "summary": "Current members: Alex",
    "updates": [
        "Emma left the group",
        "Alex joined the group"
    ],
    "last_updated": "2024-01-12T00:00:00Z"
}
```

## Example Implementation
See `examples/roblox_npc_example.py` for a complete working example showing:
- NPC creation with custom memory blocks
- Group formation and dissolution
- Location updates and navigation
- Status tracking
- Memory management

## Critical Integration Points

1. **Status Updates**
   - Update status when NPC moves:
     ```python
     update_group_status(
         client=client,
         agent_id=agent.id,
         current_location="Market District",
         current_action="moving"
     )
     ```

2. **Group Management**
   - Track nearby players:
     ```python
     update_group_status(
         client=client,
         agent_id=agent.id,
         nearby_players=[
             {
                 "id": "player_1",
                 "name": "Alice",
                 "appearance": "Red shirt",
                 "notes": "Looking for garden"
             },
             # ... more players
         ]
     )
     ```

3. **Tool Usage**
   - NPC will automatically use:
     - `navigate_to` for movement
     - `perform_action` for emotes
     - `examine_object` for surroundings

4. **SILENCE Protocol**
   - Check responses for "[SILENCE]":
     ```python
     response = client.send_message(
         agent_id=agent.id,
         message="@Bob hey where are you?",  # Player-to-player chat
         role="user",
         name="Alice"
     )
     if response.messages[-1].content == "[SILENCE]":
         # Skip sending response to players
         pass
     ```
   - In Lua, return nil when SILENCE detected
   - Skip sending response to players for private chats

5. **Memory System**
   - Status block: Current state
   - Group block: Player tracking
   - Locations block: Navigation points
   - Persona block: NPC personality

## Example Lua Integration
```lua
local LettaNPC = require("LettaNPC")

-- Initialize NPC with minimal prompt
local guide = LettaNPC.new({
    name = "town_guide",
    minimal_prompt = true  -- Uses simpler prompt
})

-- Update on player proximity
game.Players.PlayerAdded:Connect(function(player)
    local nearby = guide:getNearbyPlayers()
    guide:updateGroupStatus(nearby)
end)

-- Handle movement
guide.onLocationChanged:Connect(function(newLocation)
    guide:updateStatus({
        location = newLocation,
        action = "moving"
    })
end)
```

## Testing
Use the example file as a reference:
```bash
python examples/roblox_npc_example.py
```

This demonstrates:
1. NPC creation and setup
2. Player interactions
3. Group formation
4. Navigation
5. Status updates
6. Memory management 