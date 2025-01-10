# Roblox NPC Integration Guide

## Quick Start
```python
from letta_templates.roblox_integration import RobloxNPCManager

# Initialize
npc_manager = RobloxNPCManager(letta_client)

# Create NPC with memory blocks
blocks = npc_manager.create_memory_blocks(
    npc_name="Guide Emma",
    home_location="Town Square",
    known_locations=[
        {
            "name": "Town Square",
            "coordinates": [0, 0, 0],
            "slug": "town_square"
        }
    ]
)

# Create agent
agent = letta_client.create_agent(
    name="emma_guide",
    memory=blocks,
    system=system_prompt
)

# Update when players move nearby
nearby_players = [
    {
        "name": "Player1",
        "appearance": "Red shirt, blue hat",
        "notes": "New player"
    }
]
npc_manager.update_group_status(
    agent.id,
    nearby_players=nearby_players,
    current_location="Town Square"
)

# Handle responses in Lua
response = agent.send_message("Hello!")
if response != "[SILENCE]":
    # Send response to player
```

## Critical Integration Points

1. **Memory Block Synchronization**
   - Status block must reflect current Roblox state
   - Group block must match actual nearby players
   - Both blocks should update together using `update_group_status()`

2. **SILENCE Protocol**
   - Check responses for "[SILENCE]"
   - Return None/nil in Lua when SILENCE detected
   - Skip sending response to players

3. **Player Information**
   - Keep appearance descriptions updated
   - Track player locations accurately
   - Maintain notes about interactions

4. **Location Awareness**
   - Update status block when NPC moves
   - Keep nearby_locations list current
   - Track previous locations for context

## Example Lua Integration
```lua
local LettaNPC = require("LettaNPC")

-- Initialize NPC
local emma = LettaNPC.new({
    name = "Guide Emma",
    location = "Town Square"
})

-- Update nearby players
game.Players.PlayerAdded:Connect(function(player)
    local nearby = emma:getNearbyPlayers()
    emma:updateGroupStatus(nearby)
end)

-- Handle chat
emma.onMessage:Connect(function(response)
    if response ~= "[SILENCE]" then
        -- Send response to players
    end
end)
``` 