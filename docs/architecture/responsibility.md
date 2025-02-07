# Group Memory Responsibility Model

## Tool Responsibilities

### NPC Tools (via LLM)
- `group_memory_append`: Add observations and interactions
- `group_memory_replace`: Update NPC's notes about a player
- Purpose: Record NPC's observations and interactions with players

### Game Cluster API (via Backend)
- `upsert_group_member`: Update player state and metadata
- Fields managed:
  - `is_present`: Player in range
  - `last_seen`: Timestamp of last presence
  - `last_location`: Current/last known location
  - `appearance`: Visual description
  - `health_status`: Current health state
- Purpose: Keep accurate game state synchronized

### System Tools (via Module)
- `update_group_block`: Initialize and reset block structure
- `update_group_members_v2`: Full group state resets
- Purpose: Maintain memory block structure and integrity

## Example Usage

```python
# NPC observing player behavior
group_memory_append(
    player_name="greggytheegg",
    note="Asked about trading rare items"
)

# Game cluster updating player state
upsert_group_member(
    client, agent_id,
    entity_id="player_123",
    update_data={
        "is_present": True,
        "last_location": "Market Square",
        "appearance": "Wearing new armor"
    }
)

# System initializing memory structure
update_group_block(
    client, agent_id,
    {
        "members": {},
        "summary": "No members present",
        "updates": [],
        "last_updated": datetime.now().isoformat()
    }
)
``` 