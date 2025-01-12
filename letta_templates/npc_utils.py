from typing import Dict, Any, Optional
import json
from datetime import datetime

def create_memory_blocks(client, blocks: Dict[str, Any]) -> list:
    """Create memory blocks from provided data
    
    Args:
        client: Letta client
        blocks: Dict of block data containing required blocks:
            - locations
            - status
            - group_members
            - persona
    """
    required_blocks = ["locations", "status", "group_members", "persona"]
    
    # Validate all required blocks are present
    missing_blocks = [b for b in required_blocks if b not in blocks]
    if missing_blocks:
        raise ValueError(f"Missing required memory blocks: {missing_blocks}")
    
    memory_blocks = []
    
    # Create each block from provided data
    for label, data in blocks.items():
        block = client.create_block(
            label=label,
            value=json.dumps(data),
            limit=5000
        )
        memory_blocks.append(block)
        
    return memory_blocks

def get_memory_block(client, agent_id: str, block_label: str) -> dict:
    """Get contents of a memory block
    
    Args:
        client: Letta client
        agent_id: ID of agent
        block_label: Label of block to get
    """
    agent = client.get_agent(agent_id)
    block = next(b for b in agent.memory.blocks if b.label == block_label)
    return json.loads(block.value)

def update_memory_block(client, agent_id: str, block_label: str, data: dict):
    """Update contents of a memory block
    
    Args:
        client: Letta client
        agent_id: ID of agent
        block_label: Label of block to update
        data: New data for block
    """
    agent = client.get_agent(agent_id)
    block = next(b for b in agent.memory.blocks if b.label == block_label)
    client.update_block(
        block_id=block.id,
        value=json.dumps(data)
    )

def update_group_status(client, agent_id: str, nearby_players: list, 
                       current_location: str, current_action: str = "idle"):
    """Update group and status blocks together"""
    # Get current blocks
    status = get_memory_block(client, agent_id, "status")
    group = get_memory_block(client, agent_id, "group_members")
    
    # Track group changes
    current_members = set(group.get("members", {}).keys())
    new_members = set(p["id"] for p in nearby_players)
    
    # Calculate who joined and left
    joined = new_members - current_members
    left = current_members - new_members
    
    updates = []
    if joined:
        joined_names = [p["name"] for p in nearby_players if p["id"] in joined]
        updates.append(f"{', '.join(joined_names)} joined the group")
    if left:
        left_names = [group["members"][pid]["name"] for pid in left]
        updates.append(f"{', '.join(left_names)} left the group")
    
    # Update status (preserve existing fields)
    status.update({
        "current_location": current_location,
        "previous_location": status.get("current_location"),
        "current_action": current_action,
        "movement_state": "stationary" if current_action == "idle" else "moving"
    })
    
    # Update group (simplified structure)
    members = {}
    for player in nearby_players:
        members[player.get("id")] = {
            "name": player["name"],
            "appearance": player.get("appearance", ""),
            "notes": player.get("notes", "")
        }
    
    # Keep last 10 group change updates
    MAX_UPDATES = 10
    existing_updates = group.get("updates", [])
    new_updates = updates + existing_updates
    if len(new_updates) > MAX_UPDATES:
        new_updates = new_updates[:MAX_UPDATES]
    
    group.update({
        "members": members,
        "summary": f"Current members: {', '.join(p['name'] for p in nearby_players)}",
        "updates": new_updates,
        "last_updated": datetime.now().isoformat()
    })
    
    # Save updates
    update_memory_block(client, agent_id, "status", status)
    update_memory_block(client, agent_id, "group_members", group) 