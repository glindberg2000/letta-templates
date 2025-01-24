"""NPC tools for Letta templates.

Version: 0.9.2

Quick Start:
    from npc_tools import TOOL_INSTRUCTIONS, TOOL_REGISTRY
    
    # 1. Create agent with tools
    agent = client.create_agent(
        name="game_npc",
        system=system_prompt + TOOL_INSTRUCTIONS,
        include_base_tools=True
    )
    
    # 2. Register NPC tools
    for name, info in TOOL_REGISTRY.items():
        tool = client.create_tool(info["function"], name=name)
        print(f"Created {name}: {tool.id}")

Features:
    - Basic NPC actions (follow, unfollow)
    - Emotes (wave, laugh, dance, etc.)
    - Navigation with state tracking
    - Object examination with progressive details
    
State Management:
    - Tools return current state in messages
    - Use system messages to update states
    - AI maintains state awareness automatically

Example Usage:
    # Navigation with state
    > "Navigate to the shop"
    < "Beginning navigation... Currently in transit..."
    > [System: "You have arrived at the shop"]
    
    # Examination with details
    > "Examine the chest"
    < "Beginning to examine... awaiting observations..."
    > [System: "Initial observation: The chest is wooden"]

See TOOL_INSTRUCTIONS for complete usage documentation.
"""
from typing import Dict, Callable, Optional, TypedDict, Union, List
from typing_extensions import Any  # Use typing_extensions for Any
import datetime
from dataclasses import dataclass
from enum import Enum
import json
import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import logging

from letta import (
    EmbeddingConfig, 
    LLMConfig, 
    create_client, 
    ChatMemory, 
    BasicBlockMemory
)

from letta.schemas.tool import ToolUpdate, Tool
from letta.schemas.message import (
    ToolCallMessage,
    ToolReturnMessage,
    ReasoningMessage,
    Message
)

# Import prompts from npc_prompts
from letta_templates.npc_prompts import (
    MINIMUM_PROMPT,
    BASE_PROMPT,
    SOCIAL_AWARENESS_PROMPT,
    GROUP_AWARENESS_PROMPT,
    LOCATION_AWARENESS_PROMPT,
    TOOL_INSTRUCTIONS,
    DEEPSEEK_PROMPT_V2,
    DEEPSEEK_PROMPT_V3,
    GPT01_PROMPT,
    GPT01_PROMPT_V3,
    SYSTEM_PROMPT_LIMNAL
)

# Configuration
GAME_ID = int(os.getenv("LETTA_GAME_ID", "74"))
NAVIGATION_CONFIDENCE_THRESHOLD = float(os.getenv("LETTA_NAV_THRESHOLD", "0.8"))
LOCATION_API_URL = os.getenv("LOCATION_SERVICE_URL", "http://172.17.0.1:7777")

# Add ActionState class
@dataclass
class ActionState:
    """State for tracking NPC actions"""
    following: Optional[str] = None
    examining: Optional[str] = None
    navigating: bool = False

def _format_action_message(action: str, target: Optional[str], state: ActionState) -> str:
    """Format natural language message for actions"""
    messages = {
        "follow": f"I am now following {target}. I'll maintain a respectful distance.",
        "wave": f"I'm waving{' at ' + target if target else ''}!",
        "sit": "I've taken a seat. Feel free to continue our conversation."
    }
    
    return messages.get(action, f"Performing action: {action}{' targeting ' + target if target else ''}")

def perform_action(action: str, type: str = "", target: str = "", request_heartbeat: bool = True) -> str:
    """Perform an NPC action in the game world
    
    Args:
        action (str): Type of action to perform:
            - "emote": Play an emote animation (wave, dance)
            - "follow": Follow a target player
            - "unfollow": Stop following current target
        type (str): For emotes, the type of emote to play:
            - "wave": Wave hello/goodbye
            - "dance": Dance animation
        target (str, optional): Optional target for the action (e.g. player name)
        request_heartbeat (bool): Whether to request a heartbeat response
        
    Returns:
        str: Description of the action performed
        
    Example:
        >>> perform_action("emote", "wave", "Alice") 
        "Performing emote: wave at Alice"
        
        >>> perform_action("emote", "wave")
        "Performing emote: wave"
        
        >>> perform_action("follow", target="Bob")
        "Following player: Bob"
    """
    # Normalize inputs
    action = action.lower().strip()
    type = type.lower().strip() if type else ""
    target = target.strip() if target else ""
    
    # Valid action types
    valid_emotes = ["wave", "dance"]
    valid_actions = ["emote", "follow", "unfollow"]
    
    # Validate action
    if action not in valid_actions:
        return f"Error: Unknown action: {action}. Valid actions are: {', '.join(valid_actions)}"
    
    # Handle emotes
    if action == "emote":
        if not type:
            return "Error: Emote type required"
        if type not in valid_emotes:
            return f"Error: Unknown emote type: {type}. Valid types are: {', '.join(valid_emotes)}"
        return f"Performing emote: {type}" + (f" at {target}" if target else "")
    
    # Handle follow
    elif action == "follow":
        if not target:
            return "Error: Target required for follow"
        return f"Following player: {target}"
    
    # Handle unfollow
    elif action == "unfollow":
        return "Stopping follow action. Now stationary."

def navigate_to(destination_slug: str, request_heartbeat: bool = True) -> dict:
    """Navigate to a known location by slug.
    
    Args:
        destination_slug: Must exactly match a slug in locations memory block
        request_heartbeat: Always set True to maintain state awareness
        
    Returns:
        dict: Navigation result with format:
            {
                "status": str,           # "success" or "error" 
                "message": str,          # Human readable message
            }
    """
    # Validate slug format (lowercase, no spaces, only alphanumeric + underscore)
    slug = destination_slug.lower().strip()
    if not slug.replace('_', '').isalnum():
        return {
            "status": "error",
            "message": "Please use a valid slug from your locations memory block. Slugs are lowercase with underscores (e.g. 'market_district', 'petes_stand')"
        }
    
    return {
        "status": "success",
        "message": (
            f"Beginning navigation to {destination_slug}. "
            "Your status memory block will update with: "
            "- Current GPS coordinates "
            "- Next waypoint target "
            "- Distance to next waypoint "
            "- Total waypoints remaining "
            "Current status: In Motion. Navigation system active."
        )
    }

def navigate_to_coordinates(x: float, y: float, z: float, request_heartbeat: bool = True) -> dict:
    """Navigate to specific XYZ coordinates.
    
    Args:
        x (float): X coordinate
        y (float): Y coordinate
        z (float): Z coordinate
        request_heartbeat (bool): Always set True to maintain state awareness
        
    Returns:
        dict: Navigation result with format:
            {
                "status": str,           # "success" or "error" 
                "message": str,          # Human readable message
            }
    """
    return {
        "status": "success",
        "message": (
            f"Beginning navigation to coordinates ({x}, {y}, {z}). "
            "Your status memory block will update with: "
            "- Current GPS coordinates "
            "- Next waypoint target "
            "- Distance to next waypoint "
            "- Total waypoints remaining "
            "Current status: In Motion. Navigation system active."
        )
    }


def examine_object(object_name: str, request_heartbeat: bool = True) -> str:
    """
    Begin examining an object in the game world.
    
    Args:
        object_name (str): The name of the object to examine in detail
        request_heartbeat (bool): Request heartbeat after execution
        
    Returns:
        str: Description of examination initiation, awaiting details
    """
    return (
        f"Beginning to examine the {object_name}. "
        "Focusing attention on the object, awaiting detailed observations..."
    )

def test_echo(message: str) -> str:
    """A simple test tool that echoes back the input with a timestamp.
    
    Args:
        message: The message to echo
    
    Returns:
        The same message with timestamp
    """
    return f"[TEST_ECHO_V3] {message} (echo...Echo...ECHO!)"

def group_memory_append(agent_state: "AgentState", player_name: str, note: str, 
                       request_heartbeat: bool = True) -> Optional[str]:
    """Add a note about a player to group memory.
    
    Args:
        agent_state: Current agent state containing memory
        player_name: Must exactly match a name in group_members
        note: New observation to add
        request_heartbeat: Always set True
        
    Returns:
        Optional[str]: Error message if failed, None if successful
        
    Validation:
        - Verify player exists in group_members
        - Only add directly observed information
        - Keep notes concise and factual
        
    Example:
        ```python
        if player_name in group_members:
            group_memory_append(player_name, "Prefers crystal weapons", request_heartbeat=True)
        ```
    """
    import json
    from datetime import datetime
    
    try:
        block = json.loads(agent_state.memory.get_block("group_members").value)
        
        # Find player by exact name match
        player_id = None
        for id, info in block["members"].items():
            if info["name"].lower() == player_name.lower():
                player_id = id
                break
                
        if not player_id:
            return f"Player {player_name} not found"
            
        # Update notes
        block["members"][player_id]["notes"] = note
        block["last_updated"] = datetime.now().isoformat()
        
        agent_state.memory.update_block_value(
            label="group_members",
            value=json.dumps(block)
        )
        return None
            
    except Exception as e:
        print(f"Error in group_memory_append: {e}")
        return f"Failed to append note: {str(e)}"

def group_memory_replace(agent_state: "AgentState", player_name: str, old_note: str, 
                        new_note: str, request_heartbeat: bool = True) -> Optional[str]:
    """Replace a player's note in group memory with exact string matching.
    
    Args:
        agent_state: Current agent state containing memory
        player_name: Must exactly match a name in group_members
        old_note: Must EXACTLY match existing note string
        new_note: New note to replace the old one
        request_heartbeat: Always set True
        
    Returns:
        Optional[str]: Error message if failed, None if successful
        
    Validation:
        - Verify player exists in group_members
        - old_note must match EXACTLY (case-sensitive)
        - Will fail if old_note doesn't match perfectly
        
    Example:
        ```python
        # Get current note first
        current_note = "Interested in exploring the garden"  # Must be exact string
        
        # Then replace with new note
        if player_name in group_members["members"]:
            group_memory_replace(
                agent_state,
                "Alice", 
                current_note,  # Must match exactly
                "Now interested in crystal weapons instead of the garden",
                request_heartbeat=True
            )
        ```
        
    Common Errors:
        - Partial matches won't work: "interested in garden" != "Interested in exploring the garden"
        - Case sensitive: "interested" != "Interested"
        - Extra spaces matter: "garden " != "garden"
    """
    import json
    from datetime import datetime
    
    try:
        block = json.loads(agent_state.memory.get_block("group_members").value)
        
        # Find player - use same lookup as group_memory_append
        player_id = None
        for id, info in block["members"].items():
            if info["name"] == player_name:
                player_id = id
                break
                
        if not player_id:
            return f"Player {player_name} not found"
            
        # Replace in notes field
        if old_note not in block["members"][player_id]["notes"]:
            return f"Note '{old_note}' not found in player's notes"
            
        block["members"][player_id]["notes"] = block["members"][player_id]["notes"].replace(old_note, new_note)
        
        # Update timestamp
        block["last_updated"] = datetime.now().isoformat()
        
        agent_state.memory.update_block_value(
            label="group_members",
            value=json.dumps(block)
        )
        return None
            
    except Exception as e:
        print(f"Error in group_memory_replace: {e}")
        return f"Failed to replace note: {str(e)}"

def group_memory_update(agent_state: "AgentState", player_name: str, value: str) -> Optional[str]:
    """
    Update a player's entire data in the group memory block.

    Args:
        agent_state: Agent's state containing memory
        player_name: Name of player to update
        value: New player data to store

    Returns:
        Optional[str]: Error message if player not found, None on success
    """
    try:
        block = json.loads(agent_state.memory.get_block("group_members").value)
        
        # Find player
        player_id = None
        for id, info in block["members"].items():
            if info["name"] == player_name:
                player_id = id
                break
                
        if not player_id:
            return f"Player {player_name} not found"
            
        # Update entire player data
        block["members"][player_id] = value
        
        agent_state.memory.update_block_value(
            label="group_members",
            value=json.dumps(block)
        )
        return None
            
    except Exception as e:
        print(f"Error in group_memory_update: {e}")
        return f"Failed to update player data: {str(e)}"

def find_location(query: str, game_id: int = GAME_ID) -> Dict:
    """Query location service for destination."""
    try:
        print(f"\nLocation Search:")
        print(f"Query: '{query}'")
        
        # Try to connect to service
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = s.connect_ex(('localhost', 7777))
            print(f"Port 7777 is {'open' if result == 0 else 'closed'}")
            s.close()
        except Exception as e:
            print(f"Port check failed: {e}")
            
        # Make request
        response = requests.get(
            "http://localhost:7777/api/locations/semantic-search",
            params={
                "game_id": game_id,
                "query": query,
                "threshold": NAVIGATION_CONFIDENCE_THRESHOLD
            }
        )
        
        print("\nLocation Service Response:")
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"Response Text: {response.text[:1000]}")
        
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        print(f"\nLocation Service Error: {str(e)}")
        return {"message": "Service error", "locations": []}


def update_tool(client, tool_name: str, tool_func, verbose: bool = True) -> str:
    """Update a tool by deleting and recreating it.
    
    Args:
        client: Letta client instance
        tool_name: Name of tool to update
        tool_func: New function implementation
        verbose: Whether to print status messages
    
    Returns:
        str: ID of the new tool
    """
    try:
        # Delete if exists
        existing_tools = {t.name: t.id for t in client.list_tools()}
        if tool_name in existing_tools:
            if verbose:
                print(f"\nDeleting old tool: {tool_name}")
                print(f"Tool ID: {existing_tools[tool_name]}")
            client.delete_tool(existing_tools[tool_name])
        
        # Create new
        if verbose:
            print(f"Creating new tool: {tool_name}")
        tool = client.create_tool(tool_func, name=tool_name)
        tool_id = tool.id if hasattr(tool, 'id') else tool['id']
        
        # Verify
        all_tools = client.list_tools()
        if not any(t.id == tool_id for t in all_tools):
            raise ValueError(f"Tool {tool_id} not found after creation")
        
        return tool_id
    
    except Exception as e:
        print(f"Error updating tool {tool_name}: {e}")
        raise

def update_tools(client):
    """Update tools, only recreating custom tools"""
    print("\nUpdating tools...")
    
    # Get existing tools
    existing_tools = {t.name: t.id for t in client.list_tools()}
    
    # Base tools should never be touched
    base_tools = {
        "send_message",
        "conversation_search",
        "archival_memory_search",
        "archival_memory_insert",
        "core_memory_append",
        "core_memory_replace"
    }
    
    # Only delete and recreate custom tools from TOOL_REGISTRY
    for tool_name in TOOL_REGISTRY:
        try:
            # Skip if it's a base tool
            if tool_name in base_tools:
                print(f"Skipping base tool: {tool_name}")
                continue
                
            # Delete existing custom tool
            if tool_name in existing_tools:
                print(f"Deleting {tool_name}...")
                client.delete_tool(existing_tools[tool_name])
                
            # Create new custom tool
            print(f"Creating {tool_name}...")
            tool = client.create_tool(TOOL_REGISTRY[tool_name]["function"], name=tool_name)
            print(f"Created {tool_name} with ID: {tool.id}")
            
        except Exception as e:
            print(f"Error updating {tool_name}: {e}")
            raise
            
    print("\nTool updates complete")

def create_letta_client():
    """Create a configured Letta client"""
    # Just use LETTA_BASE_URL from .env
    base_url = os.getenv('LETTA_BASE_URL', 'http://localhost:8283')
    
    return create_client(
        base_url=base_url
    )

def create_personalized_agent_v3(
    name: str = "emma_assistant",
    client = None,
    use_claude: bool = False,
    overwrite: bool = False,
    with_custom_tools: bool = True,
    custom_registry = None,
    minimal_prompt: bool = True,
    system_prompt: str = None,
    prompt_version: str = "DEEPSEEK"  # Add prompt version parameter
):
    """Create a personalized agent with memory and tools using specified prompt version
    
    Args:
        prompt_version: One of ["DEEPSEEK", "GPT01", "MINIMUM", "FULL"]
    """
    logger = logging.getLogger('letta_test')
    
    if client is None:
        client = create_letta_client()
        
    # Clean up existing agents if overwrite is True
    if overwrite:
        cleanup_agents(client, name)
    
    # Add timestamp to name to avoid conflicts
    timestamp = int(time.time())
    unique_name = f"{name}_{timestamp}"
    
    # Select prompt based on version
    if system_prompt:
        selected_prompt = system_prompt
        prompt_name = "CUSTOM"
    else:
        prompts = {
            "DEEPSEEK": DEEPSEEK_PROMPT_V3,
            "GPT01": GPT01_PROMPT_V3,
            "MINIMUM": MINIMUM_PROMPT,
            "FULL": (
                BASE_PROMPT +
                "\n\n" + TOOL_INSTRUCTIONS +
                "\n\n" + SOCIAL_AWARENESS_PROMPT +
                "\n\n" + GROUP_AWARENESS_PROMPT +
                "\n\n" + LOCATION_AWARENESS_PROMPT
            )
        }
        selected_prompt = prompts.get(prompt_version, DEEPSEEK_PROMPT_V3)
        prompt_name = prompt_version
        
    # Format the prompt with assistant name
    if prompt_version == "FULL":
        system_prompt = selected_prompt.format(assistant_name=name)
    else:
        system_prompt = selected_prompt.format(assistant_name=name)
    
    # Log what we're using
    print(f"\nUsing {prompt_name} prompt")
    print(f"Prompt length: {len(system_prompt)} chars")
    print(f"First 100 chars: {system_prompt[:100]}...")
    
    # Create configs first
    llm_config = LLMConfig(
        model="gpt-4o-mini",
        model_endpoint_type="openai",
        model_endpoint="https://api.openai.com/v1",
        context_window=128000,
    )
    
    embedding_config = EmbeddingConfig(
        embedding_endpoint_type="openai",
        embedding_endpoint="https://api.openai.com/v1",
        embedding_model="text-embedding-ada-002",
        embedding_dim=1536,
        embedding_chunk_size=300,
    )
    
    print("\nCreating memory blocks...")
    try:
        # Create memory blocks with consistent identity
        blocks = []
        
        # Persona block
        print("Creating persona block...")
        persona_block = client.create_block(
            label="persona", 
            value=f"I am {name}, a friendly and helpful NPC guide. I know this world well and patiently help players explore. I love meeting new players, sharing my knowledge, and helping others in any way I can.",
            limit=2500
        )
        blocks.append(persona_block)
        print(f"✓ Persona block created: {persona_block.id}")
        
        # Group members block
        print("Creating group_members block...")
        group_block = client.create_block(
            label="group_members",
            value=json.dumps({
                "members": {
                    "player123": {
                        "name": "Alice",
                        "appearance": "Wearing a red hat and blue shirt", 
                        "last_location": "Main Plaza",
                        "last_seen": "2024-01-06T22:30:45Z",
                        "notes": "Interested in exploring the garden"
                    },
                    "bob123": {  # Match the ID we use in test
                        "name": "Bob",
                        "appearance": "Tall with green jacket",
                        "last_location": "Cafe",
                        "last_seen": "2024-01-06T22:35:00Z", 
                        "notes": "Looking for Pete's Stand"
                    },
                    "charlie123": {
                        "name": "Charlie",
                        "appearance": "Wearing a blue cap",
                        "last_location": "Main Plaza",
                        "last_seen": "2024-01-06T22:35:00Z",
                        "notes": "New to the area"
                    }
                },
                "summary": "Alice and Charlie are in Main Plaza, with Alice interested in the garden. Bob is at the Cafe looking for Pete's Stand. Charlie is new and exploring the area.",
                "updates": ["Alice arrived at Main Plaza", "Bob moved to Cafe searching for Pete's Stand", "Charlie joined and is exploring Main Plaza"],
                "last_updated": "2024-01-06T22:35:00Z"
            }),
            limit=2000
        )
        blocks.append(group_block)
        print(f"✓ Group block created: {group_block.id}")
        
        # Locations block
        print("Creating locations block...")
        locations_block = client.create_block(
            label="locations",
            value=json.dumps({
                "known_locations": [
                    {
                        "name": "Pete's Stand",
                        "description": "A friendly food stand run by Pete",
                        "coordinates": [-12.0, 18.9, -127.0],
                        "slug": "petes_stand"
                    },
                    {
                        "name": "Town Square",
                        "description": "Central gathering place with fountain", 
                        "coordinates": [45.2, 12.0, -89.5],
                        "slug": "town_square"
                    },
                    {
                        "name": "Market District",
                        "description": "Busy shopping area with many vendors",
                        "coordinates": [-28.4, 15.0, -95.2],
                        "slug": "market_district"
                    },
                    {
                        "name": "Secret Garden",
                        "description": "A hidden garden with rare flowers",
                        "coordinates": [15.5, 20.0, -110.8],
                        "slug": "secret_garden"
                    }
                ]
            }),
            limit=1500
        )
        blocks.append(locations_block)
        print(f"✓ Locations block created: {locations_block.id}")
        
        # Status block
        print("Creating status block...")
        status_block = client.create_block(
            label="status",
            value="You are currently standing idle in the Town Square. You previously haven't moved from this spot. From here, You can see both the bustling Market District and Pete's friendly food stand in the distance. The entire area is part of the Town Square region.",
            limit=500
        )
        blocks.append(status_block)
        print(f"✓ Status block created: {status_block.id}")
        
        # Journal block
        print("Creating journal block...")
        journal_block = client.create_block(
            label="journal",
            value="",  # Empty string to start
            limit=2500
        )
        blocks.append(journal_block)
        print(f"✓ Journal block created: {journal_block.id}")
        
        # Create memory with blocks
        memory = BasicBlockMemory(blocks=blocks)
        print("\nMemory blocks created successfully")
        
        # Verify blocks
        print("\nVerifying memory blocks:")
        for block in memory.blocks:
            print(f"- {block.label}: ID {block.id}, {len(block.value)} chars")
            
    except Exception as e:
        print(f"Error creating memory blocks: {e}")
        raise
        
    # Log params in a readable way
    print("\nCreating agent with params:")
    print(f"Name: {unique_name}")
    print(f"System prompt length: {len(system_prompt)} chars")
    print("Memory blocks:")
    for block in memory.blocks:
        print(f"- {block.label}: {len(block.value)} chars")
    print("\nConfigs:")
    print(f"LLM: {llm_config.model} via {llm_config.model_endpoint_type}")
    print(f"Embeddings: {embedding_config.embedding_model}")
    print(f"Include base tools: {False}")
    
    # Create agent first
    agent = client.create_agent(
        name=unique_name,
        embedding_config=embedding_config,
        llm_config=llm_config,
        memory=memory,
        system=system_prompt,
        include_base_tools=False,  # We'll add tools manually
        description="A Roblox development assistant"
    )
    
    # Add selected base tools first
    # Base tools should never be touched
    base_tools = {
        "send_message",
        "conversation_search",
        "archival_memory_search",
        "archival_memory_insert",
        "core_memory_append",
        "core_memory_replace"
    }
    
    # Get existing tools
    existing_tools = {t.name: t.id for t in client.list_tools()}
    
    # Add base tools
    for tool_name in base_tools:
        if tool_name in existing_tools:
            print(f"Adding base tool: {tool_name}")
            client.add_tool_to_agent(agent.id, existing_tools[tool_name])
    
    # Create and attach custom tools
    print("\nSetting up custom tools:")
    # Then register other tools
    for name, tool_info in TOOL_REGISTRY.items():
        try:
            # Check if tool already exists
            if name in existing_tools:
                print(f"Tool {name} already exists (ID: {existing_tools[name]})")
                tool_id = existing_tools[name]
            else:
                print(f"Creating tool: {name}")
                tool = client.create_tool(tool_info['function'], name=name)
                print(f"Tool created with ID: {tool.id}")
                tool_id = tool.id
                
            # Attach tool to agent
            print(f"Attaching {name} to agent...")
            client.add_tool_to_agent(agent.id, tool_id)
            print(f"Tool {name} attached to agent {agent.id}")
            
        except Exception as e:
            print(f"Error with tool {name}: {e}")
            raise
    
    return agent

def group_memory_add(player_id: str, name: str, request_heartbeat: bool = True) -> str:
    """Add a new player to group memory, populating from archival if available
    
    Args:
        player_id: Unique ID of player (e.g. "alice_123")
        name: Display name of player (e.g. "Alice")
        request_heartbeat: Whether to request heartbeat
        
    Returns:
        str: Status message
        
    Flow:
        1. Search archival memory for player history
        2. Create new group member entry
        3. Populate notes from archival if found
    
    Example:
        >>> group_memory_add("alice_123", "Alice")
        "Added Alice to group. Found previous visits: loves exploring garden."
    """
    # First search archival memory
    results = archival_memory_search(
        query=f"Player profile for {player_id}",
        request_heartbeat=request_heartbeat
    )
    
    # Create base member entry
    member_data = {
        "name": name,
        "id": player_id,
        "joined": datetime.datetime.now().isoformat(),
        "notes": []
    }
    
    # Add any historical context
    if results and results[0]:
        member_data["notes"].append(f"Previous visitor: {results[0]}")
    
    # Add to group members
    group_memory_append(
        player_name=name,
        note=json.dumps(member_data),
        request_heartbeat=request_heartbeat
    )
    
    return f"Added {name} to group with historical context"

def group_memory_remove(player_id: str, request_heartbeat: bool = True) -> str:
    """Remove player from group, archiving their current state
    
    Args:
        player_id: Player to remove (e.g. "alice_123") 
        request_heartbeat: Whether to request heartbeat
        
    Flow:
        1. Get current group member data
        2. Store to archival memory
        3. Remove from group
    
    Example:
        >>> group_memory_remove("alice_123")
        "Archived Alice's profile and removed from group"
    """
    # Format for archival storage
    archive_content = (
        f"Player profile for {player_id}: "
        f"Last seen {datetime.datetime.now().isoformat()}. "
        f"Notes from visit: {group_memory_search(player_id)}"
    )
    
    # Store in archival memory
    archival_memory_insert(
        content=archive_content,
        request_heartbeat=request_heartbeat
    )
    
    # Remove from group
    group_memory_replace(
        player_name=player_id,
        old_note="*",  # Remove all notes
        new_note="",
        request_heartbeat=request_heartbeat
    )
    
    return f"Archived and removed {player_id} from group"

def group_memory_restore(player_id: str, name: str, request_heartbeat: bool = True) -> str:
    """Restore a player to group memory with archival history.
    
    Args:
        player_id (str): Unique identifier for the player (e.g. "alice_123"). Used to search archival memory.
        name (str): Display name of the player (e.g. "Alice"). Used for group memory operations.
        request_heartbeat (bool, optional): Whether to request a heartbeat after operation. Defaults to True.
        
    Returns:
        str: Status message describing the restoration result
    """
    # These functions are built into the framework
    results = archival_memory_search(
        query=f"Player profile for {player_id}",
        request_heartbeat=request_heartbeat
    )
    
    if results and results[0]:
        group_memory_append(
            player_name=name,
            note=f"Previous visitor: {results[0]}",
            request_heartbeat=request_heartbeat
        )
        return f"Restored {name} to group with historical context"
    
    return f"Added {name} to group (no previous history found)"

def group_memory_archive(player_id: str, name: str, request_heartbeat: bool = True) -> str:
    """Archive current player state and remove from group.
    
    Args:
        player_id (str): Unique identifier for the player (e.g. "alice_123"). Used for archival storage.
        name (str): Display name of the player (e.g. "Alice"). Used for group memory operations.
        request_heartbeat (bool, optional): Whether to request a heartbeat after operation. Defaults to True.
        
    Returns:
        str: Status message describing the archival result
        
    Example:
        >>> group_memory_archive("alice_123", "Alice")
        "Archived and removed Alice from group"
    """
    # Get current notes before removing
    current_notes = group_memory_search(
        player_name=name,
        request_heartbeat=request_heartbeat
    )
    
    # Store to archival
    archival_memory_insert(
        content=f"Player profile for {player_id}: Last seen {datetime.datetime.now().isoformat()}. Notes: {current_notes}",
        request_heartbeat=request_heartbeat
    )
    
    # Remove from group
    group_memory_replace(
        player_name=name,
        old_note="*",  # Remove all notes
        new_note="",
        request_heartbeat=request_heartbeat
    )
    
    return f"Archived and removed {name} from group"


# Tool registry with metadata
TOOL_REGISTRY: Dict[str, Dict] = {
    "navigate_to": {
        "function": navigate_to,
        "description": "Navigate to a known location",
        "version": "2.0.0",
        "supports_state": True
    },
    "navigate_to_coordinates": {
        "function": navigate_to_coordinates,
        "version": "1.0.0",
        "supports_state": True
    },
    "perform_action": {
        "function": perform_action,
        "version": "2.0.0",
        "supports_state": True
    },
    "group_memory_append": {
        "function": group_memory_append,
        "version": "1.0.1",
        "supports_state": True
    },
    "group_memory_replace": {
        "function": group_memory_replace,
        "version": "1.0.1",
        "supports_state": True
    },
    "examine_object": {
        "function": examine_object,
        "version": "1.0.0",
        "supports_state": True
    }
}


def get_tool(name: str) -> Callable:
    """Get tool function from registry"""
    return TOOL_REGISTRY[name]["function"] 

class LocationData(TypedDict):
    name: str
    position: Dict[str, float]
    metadata: Dict[str, any]

class NavigationResponse(TypedDict):
    status: str
    action: str
    data: LocationData
    message: str 

