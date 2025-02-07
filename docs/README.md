# Letta Templates Documentation

## Overview
Letta Templates provides tools and utilities for creating and managing NPCs in the Letta ecosystem.

## Core Concepts
- **Memory Blocks**: Structured data storage for NPC state
- **Tools**: Functions for NPCs to interact with the world
- **Responsibility Model**: Clear separation between NPC, Game, and System operations

## Quick Start
```python
from letta_templates.npc_tools import group_memory_append
from letta_templates.npc_utils_v2 import upsert_group_member

# NPC observing a player
group_memory_append(
    player_name="greggytheegg",
    note="New player asking for directions"
)

# Game updating player state
upsert_group_member(
    client, agent_id,
    entity_id="player_123",
    update_data={
        "is_present": True,
        "last_location": "Town Square"
    }
)
```

## Documentation Structure
- `/api`: Function and tool documentation
- `/architecture`: System design and patterns
- `/examples`: Usage examples and patterns

## See Also
- [Memory Structure](architecture/memory_structure.md)
- [Group Memory API](api/group_memory.md)
- [Tool Usage Examples](examples/tool_usage.md) 