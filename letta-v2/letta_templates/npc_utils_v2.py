from typing import Dict, Any, Optional, List
import json
from datetime import datetime
import time

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
    agent = client.agents.retrieve(agent_id)
    block = next(b for b in agent.memory.blocks if b.label == block_label)
    client.blocks.update(
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
    """Extract structured data from an agent response.
    
    Args:
        response: Response from client.agents.messages.create()
        
    Returns:
        dict with:
            message (str): Final response to user
            tool_calls (list): List of tool calls with name and arguments
            tool_results (list): Results from tool executions
            reasoning (list): Agent's reasoning steps
            
    Example:
        >>> response = client.agents.messages.create(agent_id, message="Go to the shop")
        >>> result = extract_agent_response(response)
        >>> print(f"Tool calls: {result['tool_calls']}")  # [{tool: 'navigate_to', args: {'destination': 'shop'}}]
        >>> print(f"Final message: {result['message']}")  # "I'll head to the shop now!"
    """
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
            final_message = msg.content if isinstance(msg.content, str) else msg.content[0].text

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
            if isinstance(message.content, str):
                print(f"Assistant: {message.content}")
            elif isinstance(message.content, list):
                print(f"Assistant: {message.content[0].text}")
                
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

def update_location_status(
    client,
    agent_id: str,
    current_location: str,
    current_action: str = "idle",
    max_history: int = 5
) -> Dict:
    """Update agent's location status with history tracking.
    
    Args:
        client: Letta client instance
        agent_id: ID of agent to update
        current_location: Name/slug of current location
        current_action: Current action (default: "idle")
        max_history: Max number of previous locations to track
    """
    # Get current status
    status_block = get_memory_block(client, agent_id, "status")
    
    # Create new status with history
    new_status = {
        "current_location": current_location,
        "previous_location": status_block.get("current_location"),
        "current_action": current_action,
        "movement_state": "stationary" if current_action == "idle" else "moving",
        "location_history": (
            [status_block.get("current_location")] + 
            status_block.get("location_history", [])
        )[:max_history]
    }
    
    # Update status block
    update_memory_block(client, agent_id, "status", new_status)
    return new_status

def update_group_members_v2(
    client,
    agent_id: str,
    players: List[Dict],
    max_updates: int = 10
) -> Dict:
    """Enhanced group member tracking with history.
    
    Args:
        client: Letta client instance
        agent_id: ID of agent to update
        players: List of player dicts with:
            - id: Player ID
            - name: Player name
            - appearance: (optional) Description
            - location: (optional) Current location
            - notes: (optional) Additional notes
        max_updates: Max number of group changes to track
    """
    # Get current group data
    group = get_memory_block(client, agent_id, "group_members")
    current_members = set(group.get("members", {}).keys())
    new_members = set(p["id"] for p in players)
    
    # Track changes
    joined = new_members - current_members
    left = current_members - new_members
    
    # Build updates list
    timestamp = datetime.utcnow().isoformat()
    updates = group.get("updates", [])
    
    if joined:
        updates.insert(0, f"{', '.join(sorted(joined))} joined the group at {timestamp}")
    if left:
        updates.insert(0, f"{', '.join(sorted(left))} left the group at {timestamp}")
    
    # Update group data
    new_group = {
        "members": {
            p["id"]: {
                "name": p["name"],
                "appearance": p.get("appearance", ""),
                "last_location": p.get("location", "unknown"),
                "last_seen": timestamp,
                "notes": p.get("notes", "")
            } for p in players
        },
        "summary": f"Current members: {', '.join(p['name'] for p in players)}",
        "updates": updates[:max_updates],
        "last_updated": timestamp
    }
    
    update_memory_block(client, agent_id, "group_members", new_group)
    return new_group

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