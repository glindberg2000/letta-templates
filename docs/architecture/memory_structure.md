# Memory Block Structure

## Overview
NPCs use structured memory blocks to maintain state and context. Each block type serves a specific purpose and follows standard patterns.

## Core Memory Blocks

### group_members
Tracks nearby players and NPCs:
```python
{
    "members": {
        "player_123": {
            "name": str,              # Display name
            "is_present": bool,       # In range
            "health_status": str,     # Health state
            "appearance": str,        # Visual description
            "last_seen": str,         # ISO timestamp
            "last_location": str,     # Location name
            "notes": str             # NPC observations
        }
    },
    "summary": str,      # Group state summary
    "updates": list,     # Recent changes
    "last_updated": str  # ISO timestamp
}
```

### status
Tracks NPC state and actions:
```python
{
    "location": str,     # Current location
    "coordinates": {     # Position
        "x": float,
        "y": float,
        "z": float
    },
    "action": str,      # Current action
    "target": str,      # Interaction target
    "waypoints": list,  # Navigation points
    "last_updated": str # ISO timestamp
}
```

### navigation
Tracks movement and pathfinding:
```python
{
    "current_path": {
        "destination": str,  # Target location
        "waypoints": list,   # Path points
        "progress": int,     # Current waypoint
        "status": str       # Path state
    },
    "last_updated": str
}
```

## Block Management

### Size Limits
- Each block limited to 5000 chars
- FIFO pruning when near limit
- Critical fields preserved

### Update Patterns
1. System Tools
   - Full block updates
   - Structure maintenance
   - Data validation

2. Game API
   - Field-specific updates
   - State synchronization
   - Timestamp management

3. NPC Tools
   - Append-only notes
   - Observation records
   - Memory references

### Notifications
- Optional system messages on updates
- NPCs can react to changes
- Status changes trigger awareness 