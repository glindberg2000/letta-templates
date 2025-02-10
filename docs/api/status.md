# Status Block Tools

Tools for managing the status memory block used by NPCs and the game API.

## Block Structure

```python
{
    "location": str,        # Current location name
    "coordinates": {        # Current position
        "x": float,
        "y": float,
        "z": float
    },
    "action": str,         # Current action/state
    "target": str,         # Current interaction target
    "waypoints": list,     # Navigation points
    "last_updated": str    # ISO timestamp
}
```

## Block Tools

### update_status_block
```python
def update_status_block(
    client, 
    agent_id: str, 
    status_text: str,
    send_notification: bool = True
) -> None:
```
Updates the status block with new state information.

## Usage Notes

1. Status updates come from:
   - Navigation system
   - Action system
   - Game events

2. NPCs read status to:
   - Know their location
   - Track current actions
   - Follow navigation 