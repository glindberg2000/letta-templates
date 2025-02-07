# Tool Usage Examples

## Group Memory Management

### NPC Recording Observations
```python
# Player asks for help
group_memory_append(
    player_name="greggytheegg",
    note="Asked about trading rare items"
)

# Player appearance changes
group_memory_append(
    player_name="greggytheegg",
    note="Changed outfit to red armor set"
)
```

### Game API Updating State
```python
# Player enters range
upsert_group_member(
    client, agent_id,
    entity_id="player_123",
    update_data={
        "name": "greggytheegg",
        "is_present": True,
        "last_location": "Market Square",
        "appearance": "Wearing red armor"
    }
)

# Player leaves range
upsert_group_member(
    client, agent_id,
    entity_id="player_123",
    update_data={
        "is_present": False,
        "last_seen": datetime.now()
    }
)
```

### System Initialization
```python
# Initialize empty group
update_group_block(
    client, agent_id,
    {
        "members": {},
        "summary": "No members present",
        "updates": [],
        "last_updated": datetime.now().isoformat()
    }
)

# Full group reset
update_group_members_v2(
    client,
    agent_id,
    players=[
        {
            "id": "player_123",
            "name": "greggytheegg",
            "appearance": "Red armor"
        }
    ],
    update_message="Group reformed in Market Square"
)
```

## Status Management

### Location Updates
```python
update_status_block(
    client,
    agent_id,
    "Location: Market Square | Action: Trading | Target: greggytheegg"
)
```

## Best Practices

1. Use appropriate tool for the task:
   - NPC tools for observations
   - API for game state
   - System tools for maintenance

2. Maintain clean separation:
   - NPCs don't modify game state
   - API doesn't add observations
   - System tools handle structure

3. Handle errors gracefully:
   - Check return values
   - Log issues
   - Maintain fallbacks 