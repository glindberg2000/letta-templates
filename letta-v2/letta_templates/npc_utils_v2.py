from typing import Dict, Any, Optional, List
import json
from datetime import datetime
import time
from letta_client import MessageCreate
from letta_templates.npc_prompts import (
    STATUS_UPDATE_MESSAGE,
    GROUP_UPDATE_MESSAGE
)

"""NPC utility functions for Letta templates.

Version: 0.9.2

Provides core functionality for:
- Memory block management
- Group status updates
- Location tracking
"""

def create_memory_blocks(client, blocks: Dict[str, Any]) -> list:
    """Create memory blocks with consistent identity"""
    required_blocks = ["locations", "status", "group_members", "persona"]
    
    # Validate all required blocks are present
    missing_blocks = [b for b in required_blocks if b not in blocks]
    if missing_blocks:
        raise ValueError(f"Missing required memory blocks: {missing_blocks}")
    
    memory_blocks = []
    
    # Create each block from provided data
    for label, data in blocks.items():
        block = client.blocks.create(
            label=label,
            value=data if isinstance(data, str) else json.dumps(data),
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
    agent = client.agents.retrieve(agent_id)
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
    print(f"Updating block {block_label} with method: {client.blocks.update.__name__}")
    agent = client.agents.retrieve(agent_id)
    block = next(b for b in agent.memory.blocks if b.label == block_label)
    client.blocks.patch(
        block_id=block.id,
        value=json.dumps(data)
    )

def update_group_members(client, agent_id: str, nearby_players: list):
    """Update group members block with current players"""
    # Get current group block
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
    
    # Update group
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
    update_memory_block(client, agent_id, "group_members", group)

def update_status(client, agent_id: str, new_status: str):
    """Update the status block with a new status message
    
    Args:
        client: Letta client
        agent_id: ID of agent to update
        new_status: New status message (e.g. "Taking a break by the fountain")
    """
    update_memory_block(client, agent_id, "status", new_status)

# Remove the old combined function
def update_group_status(client, agent_id: str, nearby_players: list, 
                       current_location: str, current_action: str = "idle"):
    """DEPRECATED: Use update_group_members() and update_status() instead"""
    raise DeprecationWarning(
        "update_group_status is deprecated. Use update_group_members() for group updates "
        "and update_status() for status updates instead."
    )

def extract_agent_response(response) -> dict:
    """Extract structured data from an agent response."""
    tool_calls = []
    tool_results = []
    reasoning = []
    final_message = None

    for msg in response.messages:
        if msg.message_type == "tool_call_message":
            tool_calls.append({
                "tool": msg.tool_call.name,
                "args": json.loads(msg.tool_call.arguments)
            })
            
        elif msg.message_type == "tool_return_message":
            tool_results.append({
                "result": msg.tool_return,
                "status": msg.status
            })
            
        elif msg.message_type == "reasoning_message":
            reasoning.append(msg.reasoning)
            
        elif msg.message_type == "assistant_message":
            final_message = msg.content  # Content is now always a string

    return {
        "message": final_message,
        "tool_calls": tool_calls,
        "tool_results": tool_results,
        "reasoning": reasoning
    }

def print_response(response):
    """Print all messages from a Letta response."""
    print("\nParsing response...")
    if not hasattr(response, 'messages'):
        print("No messages found in response")
        return
        
    print(f"Found {len(response.messages)} messages\n")
    
    for i, message in enumerate(response.messages, 1):
        print(f"Message {i}:")
        
        if message.message_type == "reasoning_message":
            print(f"Reasoning: {message.reasoning}")
            
        elif message.message_type == "tool_call_message":
            print(f"Tool Call: {message.tool_call.name}")
            print(f"Arguments: {message.tool_call.arguments}")
            
        elif message.message_type == "tool_return_message":
            print(f"Tool Return: {message.tool_return}")
            if message.status == "error":
                print(f"Error: {message.stderr}")
            if message.stdout:
                print(f"Output: {message.stdout}")
                
        elif message.message_type == "assistant_message":
            print(f"Assistant: {message.content}")  # Content is now always a string
                
        elif message.message_type == "system_message":
            print(f"System: {message.content}")
            
        else:
            print(f"Unknown message type: {message.message_type}")
            print(f"Content: {message.content}")
            
        print()  # Empty line between messages
    
    if hasattr(response, 'usage'):
        print("\nUsage Statistics:")
        print(f"Completion tokens: {response.usage.completion_tokens}")
        print(f"Prompt tokens: {response.usage.prompt_tokens}")
        print(f"Total tokens: {response.usage.total_tokens}")
        print(f"Steps: {response.usage.step_count}")

def extract_message_from_response(response) -> str:
    """DEPRECATED: Use extract_agent_response() instead for complete response handling."""
    try:
        for message in response.messages:
            if message.message_type == "assistant_message":
                if isinstance(message.content, str):
                    return message.content
                elif isinstance(message.content, list):
                    return message.content[0].text
        return ''
    except Exception as e:
        print(f"Error extracting message: {e}")
        return ''

def retry_test_call(func, *args, max_retries=3, delay=2, **kwargs):
    """Wrapper for test API calls with exponential backoff."""
    last_error = None
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            if attempt == max_retries - 1:
                raise
            print(f"Attempt {attempt + 1} failed, retrying in {delay}s...")
            time.sleep(delay)
            delay *= 2  # Exponential backoff
    raise last_error 

def update_status_block(client, agent_id: str, status_text: str, send_notification: bool = True):
    """Update the agent's status block with new status."""
    agent = client.agents.retrieve(agent_id)
    block = next(b for b in agent.memory.blocks if b.label == "status")
    client.blocks.modify(
        block_id=block.id,
        value=status_text
    )
    
    if send_notification:
        client.agents.messages.create(
            agent_id=agent_id,
            messages=[{
                "role": "system",
                "content": STATUS_UPDATE_MESSAGE
            }]
        )

def update_group_block(client, agent_id: str, group_data: dict, send_notification: bool = False):
    """Update the agent's group_members block with new group data."""
    agent = client.agents.retrieve(agent_id)
    block = next(b for b in agent.memory.blocks if b.label == "group_members")
    client.blocks.modify(
        block_id=block.id,
        value=json.dumps(group_data)
    )
    
    if send_notification:
        client.agents.messages.create(
            agent_id=agent_id,
            messages=[{
                "role": "system",
                "content": GROUP_UPDATE_MESSAGE
            }],
            use_assistant_message=False
        )

def update_group_members_v2(
    client,
    agent_id: str,
    players: List[Dict],
    update_message: str = None
) -> Dict:
    """Full group update for initialization or complete resets.
    
    Args:
        client: Letta client instance
        agent_id: ID of agent to update
        players: List of player dicts with:
            - id: Player ID
            - name: Player name (display name)
            - appearance: (optional) Description
            - notes: (optional) Additional notes, defaults to "Spawned into group"
        update_message: Optional message about this group formation
    """
    try:
        # Create new group state
        new_group = {
            "members": {},
            "summary": "",
            "updates": [update_message] if update_message else [],
            "last_updated": datetime.utcnow().isoformat()
        }
        
        for player in players:
            player_id = player["id"]
            if player_id not in new_group["members"]:
                new_group["members"][player_id] = {
                    "name": player["name"],
                    "appearance": player.get("appearance", ""),
                    "notes": player.get("notes", "Spawned into group"),
                    "last_seen": datetime.utcnow().isoformat()
                }
        
        # Update summary
        new_group["summary"] = f"Current members: {', '.join(p['name'] for p in new_group['members'].values())}"
        
        # Update block without system message
        update_group_block(client, agent_id, new_group, send_notification=False)
        return {"success": True, "group": new_group}
    except Exception as e:
        return {"success": False, "error": str(e)}

def add_group_member(
    client,
    agent_id: str,
    player_id: str,
    player_name: str,
    appearance: str = "",
    notes: str = "Spawned into group",
    update_message: str = None
) -> Dict:
    """Add a single member to group with optional notes."""
    try:
        group = get_memory_block(client, agent_id, "group_members")
        
        # Check for duplicate
        if player_id in group["members"]:
            return {"success": False, "error": "Member already exists"}
        
        # Add new member with all fields
        group["members"][player_id] = {
            "name": player_name,
            "appearance": appearance,
            "notes": notes,
            "last_seen": datetime.utcnow().isoformat()
        }
        
        # Update summary and latest update
        group["summary"] = f"Current members: {', '.join(m['name'] for m in group['members'].values())}"
        if update_message:
            group["updates"] = [update_message]  # Keep only latest update
            
        group["last_updated"] = datetime.utcnow().isoformat()
        
        # Update block without system message
        update_group_block(client, agent_id, group, send_notification=False)
        return {"success": True, "group": group}
    except Exception as e:
        return {"success": False, "error": str(e)}

def remove_group_member(
    client,
    agent_id: str,
    player_id: str,
    update_message: str = None
) -> Dict:
    """Remove member and return their data for potential reuse."""
    try:
        group = get_memory_block(client, agent_id, "group_members")
        
        # Store member data before removal
        removed_member = group["members"].pop(player_id, None)
        
        if removed_member:
            # Update summary
            group["summary"] = f"Current members: {', '.join(m['name'] for m in group['members'].values())}"
            if update_message:
                group["updates"] = [update_message]  # Keep only latest update
                
            group["last_updated"] = datetime.utcnow().isoformat()
            
            # Update block without system message
            update_group_block(client, agent_id, group, send_notification=False)
            return {
                "success": True,
                "removed_member": removed_member,
                "group": group
            }
        return {
            "success": False,
            "error": "Member not found"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_location_history(client, agent_id: str) -> List[str]:
    """Get agent's location history."""
    status = get_memory_block(client, agent_id, "status")
    return status.get("location_history", [])

def get_group_history(client, agent_id: str) -> List[str]:
    """Get recent group membership changes."""
    group = get_memory_block(client, agent_id, "group_members")
    return group.get("updates", [])

def print_client_info(client):
    """Print debug info about the client's message API."""
    try:
        import inspect
        from importlib.metadata import version
        
        print("\nLetta Client API Debug Info:")
        print("-" * 50)
        
        # Print version info
        try:
            letta_client_version = version('letta-client')
            letta_templates_version = version('letta_templates')
            print(f"letta-client version: {letta_client_version}")
            print(f"letta_templates version: {letta_templates_version}")
        except Exception as e:
            print(f"Error getting package versions: {e}")
        
        print(f"\nClient instance version: {getattr(client, '__version__', 'unknown')}")
        
        # Print message create signature
        if hasattr(client.agents.messages, 'create'):
            sig = inspect.signature(client.agents.messages.create)
            print("\nMessage create signature:")
            print(f"client.agents.messages.create{sig}")
            
            # Print parameter details
            for name, param in sig.parameters.items():
                print(f"\n{name}:")
                print(f"  type: {param.annotation}")
                print(f"  default: {param.default if param.default != param.empty else 'required'}")
        
        # Print full client structure
        print("\nClient structure:")
        print("client.agents methods:", dir(client.agents))
        print("client.agents.messages methods:", dir(client.agents.messages))
        
        # Try to get source
        try:
            import inspect
            source = inspect.getsource(client.agents.messages.create)
            print("\nMessage create source:")
            print(source)
        except Exception as e:
            print(f"\nCould not get source: {e}")
        
    except Exception as e:
        print(f"Error inspecting client: {e}") 

def upsert_group_member(
    client, 
    agent_id: str, 
    entity_id: str,
    update_data: dict,
    request_heartbeat: bool = True
) -> str:
    """Upsert (create or update) an entity in group memory.
    
    Args:
        client: Letta client instance
        agent_id: ID of the agent to update
        entity_id: ID of player/NPC to upsert
        update_data: Dict containing fields to update:
            {
                "name": str,              # Display name
                "is_present": bool,       # Currently in range
                "health_status": str,     # "healthy", "injured", "critical", "dead"
                "appearance": str,        # Physical description
                "notes": str,            # NPC's observations/notes about entity
                "type": str,              # "player" or "npc"
                "last_seen": str,         # Timestamp (only when is_present=False)
            }
        request_heartbeat: Whether to request heartbeat
        
    Returns:
        str: Status message
        
    Example:
        >>> # NPC first sees player and adds notes
        >>> upsert_group_member(
        ...     client, 
        ...     "agent-123",
        ...     "player_456",
        ...     {
        ...         "name": "greggytheegg",
        ...         "is_present": True,
        ...         "type": "player",
        ...         "notes": "Asked about directions to the garden"
        ...     }
        ... )
        
        >>> # Backend updates with appearance
        >>> upsert_group_member(
        ...     client,
        ...     "agent-123", 
        ...     "player_456",
        ...     {
        ...         "appearance": "Wearing a hamburger hat",
        ...         "health_status": "healthy"
        ...     }
        ... )
    """
    try:
        # Get current group memory
        agent = client.agents.retrieve(agent_id)
        block = next((b for b in agent.memory.blocks if b.label == "group_members"), None)
        
        if not block:
            # Create new block if it doesn't exist
            group_data = {
                "members": {},
                "last_updated": datetime.datetime.now().isoformat(),
                "summary": "0 members"
            }
        else:
            group_data = json.loads(block.value)
            
        # Update or create member entry
        if entity_id not in group_data["members"]:
            group_data["members"][entity_id] = {}
            
        member = group_data["members"][entity_id]
        
        # Handle presence state changes
        if "is_present" in update_data:
            if update_data["is_present"]:
                # Member arrives - clear last_seen
                member.pop("last_seen", None)
            else:
                # Member leaves - set last_seen if not provided
                if "last_seen" not in update_data:
                    update_data["last_seen"] = datetime.datetime.now().isoformat()
                    
        # Update fields
        member.update(update_data)
        
        # Update summary
        present_count = sum(1 for m in group_data["members"].values() if m.get("is_present", False))
        total_count = len(group_data["members"])
        group_data["summary"] = f"{total_count} members: {present_count} present, {total_count - present_count} absent"
        
        # Update timestamp
        group_data["last_updated"] = datetime.datetime.now().isoformat()
        
        # FIFO pruning if needed (remove oldest absent members)
        if len(json.dumps(group_data)) > 4800:  # Leave buffer for new updates
            absent_members = [
                (id, data) for id, data in group_data["members"].items() 
                if not data.get("is_present", True)
            ]
            if absent_members:
                # Sort by last_seen and remove oldest
                oldest_id = sorted(
                    absent_members,
                    key=lambda x: x[1].get("last_seen", "")
                )[0][0]
                del group_data["members"][oldest_id]
        
        # Update block
        if block:
            client.update_block(block.id, json.dumps(group_data))
        else:
            client.create_block(
                agent_id=agent_id,
                label="group_members",
                value=json.dumps(group_data),
                limit=5000
            )
            
        return f"Updated {update_data.get('name', entity_id)} in group memory"
        
    except Exception as e:
        return f"Error updating group memory: {e}" 