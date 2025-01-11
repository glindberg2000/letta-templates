import json
import time
from datetime import datetime

def update_group_status(client, agent_id, nearby_players, current_location, current_action="idle"):
    """Update agent's status and group awareness."""
    agent = client.get_agent(agent_id)
    memory = agent.memory
    
    # Get current blocks
    status_block = next(b for b in memory.blocks if b.label == "status")
    group_block = next(b for b in memory.blocks if b.label == "group_members")
    
    # Update status
    current_status = json.loads(status_block.value)
    previous_location = current_status.get("current_location")
    
    client.update_block(
        block_id=status_block.id,
        value=json.dumps({
            "region": "Town Square",
            "current_location": current_location,
            "previous_location": previous_location,
            "current_action": current_action,
            "nearby_locations": current_status.get("nearby_locations", []),
            "movement_state": "stationary" if current_action == "idle" else "moving"
        })
    )
    
    # Update group members
    current_group = json.loads(group_block.value)
    updated_members = current_group["members"].copy()
    
    for player in nearby_players:
        updated_members[player.get("id", f"player_{int(time.time())}")] = {
            "name": player["name"],
            "appearance": player.get("appearance", ""),
            "last_location": current_location,
            "last_seen": datetime.now().isoformat(),
            "notes": player.get("notes", "")
        }
    
    client.update_block(
        block_id=group_block.id,
        value=json.dumps({
            "members": updated_members,
            "summary": f"Group at {current_location}: {', '.join(p['name'] for p in nearby_players)}",
            "updates": current_group["updates"] + [f"Updated group at {current_location}"],
            "last_updated": datetime.now().isoformat()
        })
    ) 