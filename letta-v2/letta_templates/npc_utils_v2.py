from typing import Dict, Any, Optional
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
        block = client.create_block(
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
    """Extract the actual message content from a LettaResponse object."""
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