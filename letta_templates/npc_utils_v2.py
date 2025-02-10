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
    print(f"Updating block {block_label}")
    
    # Get current block to verify it exists
    agent = client.agents.retrieve(agent_id)
    block = next(b for b in agent.memory.blocks if b.label == block_label)
    
    # Update using core memory API
    client.agents.core_memory.modify_block(
        agent_id=agent_id,
        block_label=block_label,
        value=json.dumps(data) if isinstance(data, dict) else data
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
    """Extract structured data from an agent response.
    
    Tracks tool calls and their corresponding returns by ID to ensure
    proper message construction. Returns a dict with:
    - message: Final assistant message
    - tool_calls: List of tool calls with their args
    - tool_results: List of tool returns linked to their calls
    - reasoning: List of reasoning steps
    """
    tool_calls = {}  # Track by ID
    tool_results = {}
    reasoning = []
    final_message = None

    for msg in response.messages:
        if msg.message_type == "tool_call_message":
            tool_calls[msg.tool_call.tool_call_id] = {
                "id": msg.tool_call.tool_call_id,
                "tool": msg.tool_call.name,
                "args": json.loads(msg.tool_call.arguments),
                "message_id": msg.id  # Track parent message
            }
            
        elif msg.message_type == "tool_return_message":
            tool_results[msg.tool_call_id] = {
                "id": msg.tool_call_id,
                "result": msg.tool_return,
                "status": msg.status,
                "stdout": getattr(msg, 'stdout', None),
                "stderr": getattr(msg, 'stderr', None),
                "tool_call": tool_calls.get(msg.tool_call_id),  # Link to original call
                "message_id": msg.id
            }
            
        elif msg.message_type == "reasoning_message":
            reasoning.append({
                "text": msg.reasoning,
                "message_id": msg.id
            })
            
        elif msg.message_type == "assistant_message":
            final_message = msg.content

    # Convert to lists but maintain order
    ordered_calls = [
        tool_calls[call_id] 
        for call_id in tool_calls.keys()
    ]
    
    ordered_results = [
        tool_results[call_id] 
        for call_id in tool_calls.keys() 
        if call_id in tool_results
    ]

    return {
        "message": final_message,
        "tool_calls": ordered_calls,
        "tool_results": ordered_results,
        "reasoning": reasoning,
        "complete": bool(final_message)  # Did we get a final message?
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

def update_status_block(client, agent_id: str, field_updates: dict, send_notification: bool = False):
    """Update status fields dynamically."""
    client.agents.core_memory.modify_block(
        agent_id=agent_id,
        block_label="status",
        value=json.dumps(field_updates)
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

def upsert_group_member(client, agent_id: str, entity_id: str, update_data: dict) -> dict:
    """Update or insert a group member.
    
    If a player with matching name exists under a temporary ID (unnamed_*),
    will migrate their data to the real ID.
    """
    try:
        # Get current block
        agent = client.agents.retrieve(agent_id)
        block = next(b for b in agent.memory.blocks if b.label == "group_members")
        data = json.loads(block.value)
        
        if "players" not in data:
            data["players"] = {}
            
        # Check for temp ID with same name
        temp_id = None
        for pid, pdata in data["players"].items():
            if (pid.startswith("unnamed_") and 
                pdata["name"] == update_data["name"]):
                temp_id = pid
                break
                
        if temp_id:
            # Migrate data from temp ID to real ID
            existing_data = data["players"].pop(temp_id)  # Remove temp entry
            # Keep existing notes and other data
            update_data.setdefault("notes", "")  # Ensure notes field exists
            update_data["notes"] = existing_data.get("notes", "")  # Preserve notes
            data["players"][entity_id] = update_data
        else:
            # Normal update/insert
            if entity_id not in data["players"]:
                update_data.setdefault("notes", "")  # Initialize empty notes
            else:
                # Keep existing notes if updating
                update_data["notes"] = data["players"][entity_id].get("notes", "")
            data["players"][entity_id] = update_data
            
        # Convert to JSON string before updating
        client.agents.core_memory.modify_block(
            agent_id=agent_id,
            block_label="group_members",
            value=json.dumps(data)
        )
        return {"status": "success", "message": f"Successfully updated {entity_id}"}
            
    except Exception as e:
        return {"status": "error", "message": str(e)} 