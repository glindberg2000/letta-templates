# Roblox NPC Integration Guide

## Version 0.9.0 Breaking Changes

### Upgrading from 0.8.x
1. Memory blocks are now required during creation:
```python
# Old way (no longer works):
agent = create_personalized_agent(name="guide")

# New way (required):
agent = create_personalized_agent(
    name="guide",
    memory_blocks={
        "persona": { ... },  # Required
        "status": { ... },   # Required
        "group_members": { ... },  # Required
        "locations": { ... }  # Required
    }
)
```

2. Group member structure simplified:
```python
# Old structure had location tracking
members = {
    "player_1": {
        "last_location": "Market",
        "last_seen": timestamp,
        # ...
    }
}

# New structure (location in status block)
members = {
    "player_1": {
        "name": "Alice",
        "appearance": "Red shirt",
        "notes": "Looking for garden"
    }
}
```

3. Group updates now track meaningful events:
```python
# Old updates
"updates": ["Updated group at Market"]

# New updates (limited to 10)
"updates": [
    "Alice joined the group",
    "Bob left the group"
]
```

## Quick Start

1. Install latest version with NPC support:
```bash
# Option 1: From PyPI (recommended)
pip install letta_templates==0.9.1

# Option 2: From GitHub (if needed)
pip install git+https://github.com/glindberg2000/letta-templates.git@v0.9.1
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
   - Extensible personality data:
     ```python
     "persona": {
         # Core fields (recommended but flexible)
         "name": "town_guide",
         "role": "Tutorial Guide",
         
         # Personality (all optional/customizable)
         "personality": {
             "traits": ["friendly", "patient"],
             "mood": "cheerful",
             "speaking_style": "casual",
             "favorite_phrases": ["Welcome!", "Let me show you around"]
         },
         
         # Background (optional/customizable)
         "background": {
             "origin": "Born in Market District",
             "years_as_guide": 5,
             "specialties": ["garden tours", "history"],
             "relationships": {"Pete": "good friend", "Market": "hometown"}
         },
         
         # Optional features
         "interests": ["Teaching", "Exploring"],
         "journal": [],  # For memories/experiences
         
         # Game-specific fields
         "quest_preferences": ["helping_new_players"],
         "daily_schedule": {"morning": "market", "evening": "garden"},
         "dialog_triggers": ["sees_new_player", "at_landmark"],
         
         # Add any fields needed
         "your_custom_field": "any value"
     }
     ```
   - No mandatory structure
   - Tools can access all fields
   - Game defines personality depth

2. **Status Block**
   - NPC's current state
   - Location tracking (flexible format):
     ```python
     # Can use coordinates
     "current_location": "12.5, -45.2, 78.9"
     
     # Or named locations
     "current_location": "Market District"
     
     # Or both
     "current_location": "Market District (12.5, -45.2, 78.9)"
     
     # Or any custom format needed by the game
     "current_location": "zone_4_market_district_coords_12.5_-45.2_78.9"
     ```
   - Action status
   - Extensible for game-specific data:
     ```python
     "status": {
         # Core fields
         "current_location": "Market",
         "current_action": "idle",
         "movement_state": "stationary",
         
         # Game-specific fields
         "vision_range": 50,
         "visible_objects": ["tree_1", "rock_2"],
         "local_events": ["market_sale", "festival"],
         "weather": "rainy",
         "time_of_day": "evening",
         "quest_triggers_nearby": ["help_merchant"],
         
         # Add any fields needed
         "your_custom_field": "any value"
     }
     ```

3. **Group Members Block**
   - Current group members
   - Last 10 group updates (joins/leaves)
   - Member appearance and notes
   - Extensible member data:
     ```python
     "members": {
         "player_123": {
             # Core fields used by tools
             "name": "Emma",
             "appearance": "Purple dress",
             "notes": "Regular visitor",
             
             # Game-specific fields
             "role": "group_leader",
             "permissions": ["can_invite", "can_kick"],
             "friendship_level": 3,
             "shared_quests": ["garden_tour"],
             "favorite_locations": ["Secret Garden"],
             "interaction_history": ["helped_with_quest", "shared_item"],
             
             # Add any fields needed
             "your_custom_field": "any value"
         }
     }
     ```
   - Tools can read/write any fields
   - No validation on extra fields
   - Game can store any player-specific data

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