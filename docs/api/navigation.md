# Navigation Block Tools

Tools supporting NPC navigation and movement tracking.

## Block Structure

```python
{
    "current_path": {
        "destination": str,      # Target location
        "waypoints": [           # Path points
            {
                "x": float,
                "y": float,
                "z": float
            }
        ],
        "progress": int,        # Current waypoint index
        "status": str          # "active", "completed", "failed"
    },
    "last_updated": str        # ISO timestamp
}
```

## Block Tools

### update_navigation_block
```python
def update_navigation_block(
    client,
    agent_id: str,
    nav_data: dict,
    send_notification: bool = False
) -> None:
```
Updates navigation state and path information.

## Usage Notes

1. Navigation updates from:
   - Pathfinding system
   - Movement commands
   - Location changes

2. Integrates with:
   - Status updates
   - Location tracking
   - Movement animations 