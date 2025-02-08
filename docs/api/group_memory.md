# Group Memory & Status API

## Status Updates
New first-person immersive status format:

```python
update_status_block(
    client=client,
    agent_id=agent_id,
    field_updates={
        "current_location": "location_name",  # Where the NPC is
        "state": "current_state",            # What they're doing
        "health": "health_condition",        # Optional health status
        "description": "First-person description of current situation..."
    }
)
```

Example:
```python
# Normal status
update_status_block(client, agent_id, {
    "current_location": "plaza",
    "state": "greeting",
    "description": "I'm standing in the bustling plaza, welcoming new visitors..."
})

# Injured status
update_status_block(client, agent_id, {
    "current_location": "street",
    "state": "injured",
    "health": "hit by car",
    "description": "I'm lying here badly hurt after being hit... need medical help..."
})
```

## Group Memory Updates
Track and update player information:

```python
upsert_group_member(
    client=client,
    agent_id=agent_id,
    entity_id=player_id,
    update_data={
        "name": str,           # Required
        "is_present": bool,    # Required
        "health": str,         # Required
        "appearance": str,     # Required
        "last_seen": str,      # ISO format timestamp
        "notes": str           # Optional
    }
)
```

# Group Memory Block Tools

These tools manage the group_members memory block structure used by both NPCs and the game API.

## Block Structure

```python
{
    "players": {                    # Changed from "members"
        "962483389": {              # Numeric ID for players, custom ID for NPCs
            "name": str,            # Display name
            "is_present": bool,     # Currently in range
            "health": str,          # Current health state (e.g. "healthy")
            "appearance": str,      # Visual description
            "last_seen": str        # ISO timestamp
        }
        # ... other players/NPCs
    }
}
```

## Block Tools

### update_group_block
```python
def update_group_block(
    client, 
    agent_id: str, 
    group_data: dict
) -> None:
```
Updates the entire group_members block. Used by system tools and API functions.

### update_group_members_v2
```python
def update_group_members_v2(
    client,
    agent_id: str,
    players: List[Dict],
    update_message: str = None
) -> Dict:
```
Full group reset for initialization or complete updates.

### upsert_group_member
```python
def upsert_group_member(
    client, 
    agent_id: str,
    entity_id: str,
    update_data: dict
) -> dict:
```
Updates specific fields for a single player/NPC. Required fields:
- name: str
- is_present: bool
- health: str
- appearance: str
- last_seen: str (ISO format)

## Usage Notes

1. Block tools handle:
   - Block structure maintenance
   - Data validation
   - FIFO pruning when size > 4800 chars

2. Important Changes:
   - Uses "players" instead of "members"
   - Removed "summary" and "updates" fields
   - Added required "is_present" and "health" fields
   - Consistent ID format (numeric for players, custom for NPCs)

3. Example Usage:
```python
upsert_group_member(
    client,
    agent_id,
    "962483389",
    {
        "name": "greggytheegg",
        "is_present": True,
        "health": "healthy",
        "appearance": "Wearing a party hat",
        "last_seen": "2024-01-06T22:30:45Z"
    }
)
```

4. These tools are used by:
   - RobloxDev's API endpoints
   - System initialization
   - Group state resets

5. NPCs use their own tools:
   - group_memory_append
   - group_memory_replace 