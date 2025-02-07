# Group Memory Block Tools

These tools manage the group_members memory block structure used by both NPCs and the game API.

## Block Structure

```python
{
    "members": {
        "player_123": {
            "name": str,              # Display name
            "is_present": bool,       # Currently in range
            "health_status": str,     # Current health state
            "appearance": str,        # Visual description
            "last_seen": str,         # ISO timestamp
            "last_location": str,     # Location name
            "notes": str             # NPC observations
        }
        # ... other members
    },
    "summary": str,      # Current group state summary
    "updates": list,     # Recent group changes
    "last_updated": str  # ISO timestamp
}
```

## Block Tools

### update_group_block
```python
def update_group_block(
    client, 
    agent_id: str, 
    group_data: dict,
    send_notification: bool = False
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
) -> str:
```
Updates specific fields for a single member. Used by the game API to maintain player state.

## Usage Notes

1. Block tools handle:
   - Block structure maintenance
   - Data validation
   - FIFO pruning when size > 4800 chars
   - Timestamp management

2. These tools are used by:
   - RobloxDev's API endpoints
   - System initialization
   - Group state resets

3. NPCs use their own tools:
   - group_memory_append
   - group_memory_replace 