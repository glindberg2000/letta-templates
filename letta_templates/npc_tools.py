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
from dataclasses import dataclass
from enum import Enum
from datetime import datetime  # Add at top with other imports
import json
import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import logging
import inspect

from letta_client import (
    EmbeddingConfig,
    LlmConfig as LLMConfig,  # Note the case change
    Memory,  # Replaces ChatMemory and BasicBlockMemory
    Block,
    Tool,
    ToolCallMessage,
    ToolReturnMessage,
    ReasoningMessage,
    Message,
    Letta
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
            - "emote": Play an emote animation (requires type parameter)
            - "follow": Follow a target player
            - "unfollow": Stop following current target
            - "jump": Perform a jump animation
            - "walk": Walk to target location
            - "run": Run to target location
            - "swim": Swim to target location
            - "climb": Climb to target location
        type (str): For emotes, the type of emote to play:
            - "wave": Wave hello/goodbye
            - "dance": Dance animation
            - "point": Point at target
            - "laugh": Laugh animation
        target (str, optional): Optional target for the action (e.g. player name)
        request_heartbeat (bool, optional): Whether to request a heartbeat response. Defaults to True.
        
    Example:
        >>> perform_action("emote", "wave", "Alice")  # Wave at Alice
        >>> perform_action("follow", target="Bob")    # Follow Bob
        >>> perform_action("emote", "dance")          # Dance without target
        >>> perform_action("jump")                    # Jump animation
        >>> perform_action("emote", "point", "chest") # Point at object
        >>> perform_action("emote", "laugh")          # Laugh animation
        >>> perform_action("walk", target="market")   # Walk to location
        >>> perform_action("run", target="garden")    # Run to location
        >>> perform_action("climb", target="wall")    # Climb object
        >>> perform_action("swim", target="lake")     # Swim to location
    """
    # Normalize inputs
    action = action.lower().strip()
    type = type.lower().strip() if type else ""
    target = target.strip() if target else ""
    
    # Valid action types
    valid_emotes = ["wave", "dance", "point", "laugh"]
    valid_actions = ["emote", "follow", "unfollow", "jump", "walk", "run", "swim", "climb"]
    
    # Validate action
    if action not in valid_actions:
        if action in valid_emotes:
            return f"Error: For emotes use action='emote' with type='{action}' instead"
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
        
    # Handle jump
    elif action == "jump":
        return "Performing jump animation"
        
    # Handle movement actions
    elif action in ["walk", "run", "swim", "climb"]:
        if not target:
            return f"Error: Target location required for {action}"
        return f"Performing {action} to {target}"

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

def group_memory_append(agent_state: "AgentState", player_name: str, note: str, request_heartbeat: bool = True) -> None:
    """Append a note about a player to group memory.
    
    Args:
        agent_state: Current agent state
        player_name: Name of the player to add note for
        note: Note to append
        request_heartbeat: Whether to request a heartbeat
    """
    import json
    from datetime import datetime
    
    try:
        block = json.loads(agent_state.memory.get_block("group_members").value)
        
        if "players" not in block:
            block["players"] = {}
            
        # Find or create player entry
        player_id = None
        for id, info in block["players"].items():
            if info["name"] == player_name:
                player_id = id
                break
                
        # Auto-create if not found
        if not player_id:
            player_id = f"unnamed_{player_name}"
            block["players"][player_id] = {
                "name": player_name,
                "is_present": True,
                "health": "healthy",
                "appearance": "",
                "notes": "",
                "last_seen": datetime.now().isoformat()
            }
            
        # Update notes
        current_notes = block["players"][player_id].get("notes", "")
        block["players"][player_id]["notes"] = f"{current_notes}\n{note}".strip()
        
        agent_state.memory.update_block_value(
            label="group_members",
            value=json.dumps(block)
        )
        return None
            
    except Exception as e:
        print(f"Error in group_memory_append: {e}")
        return f"Failed to append note: {str(e)}"

def group_memory_replace(agent_state: "AgentState", player_name: str, old_note: str, new_note: str, request_heartbeat: bool = True) -> None:
    """Replace a note about a player in group memory.
    
    Args:
        agent_state: Current agent state
        player_name: Name of the player
        old_note: Note text to replace
        new_note: New note text
        request_heartbeat: Whether to request a heartbeat
    """
    import json
    from datetime import datetime
    
    try:
        block = json.loads(agent_state.memory.get_block("group_members").value)
        
        if "players" not in block:
            block["players"] = {}
            
        # Find or create player entry
        player_id = None
        for pid, pdata in block["players"].items():
            if pdata["name"] == player_name:
                player_id = pid
                break
                
        # Auto-create if not found
        if not player_id:
            player_id = f"unnamed_{player_name}"
            block["players"][player_id] = {
                "name": player_name,
                "is_present": True,
                "health": "healthy",
                "appearance": "",
                "notes": "",
                "last_seen": datetime.now().isoformat()
            }
            
        # Update notes
        current_notes = block["players"][player_id].get("notes", "")
        block["players"][player_id]["notes"] = current_notes.replace(old_note, new_note)
        
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
        
        if "players" not in block:
            block["players"] = {}
            
        # Find or create player entry
        player_id = None
        for pid, pdata in block["players"].items():
            if pdata["name"] == player_name:
                player_id = pid
                break
                
        # Auto-create if not found
        if not player_id:
            player_id = f"unnamed_{player_name}"
            block["players"][player_id] = {
                "name": player_name,
                "is_present": True,
                "health": "healthy",
                "appearance": "",
                "notes": "",
                "last_seen": datetime.now().isoformat()
            }
            
        # Update entire player data
        block["players"][player_id] = value
        
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


def update_global_tools(client):
    """Update all custom tools globally."""
    try:
        for name, tool_info in TOOL_REGISTRY.items():
            try:
                print(f"Updating {name}...")
                source_code = inspect.getsource(tool_info['function'])
                
                # Use upsert with just source_code
                tool = client.tools.upsert(
                    source_code=source_code,
                    description=tool_info.get('description', ''),
                    tags=[name]
                )
                print(f"Updated {name}: {tool.id}")
                
            except Exception as e:
                print(f"Error updating {name}: {e}")
                raise
            
    except Exception as e:
        print(f"Error updating tools: {e}")
        raise

def update_agent_tools(client, agent_id: str, tools: list = None):
    """Update tools for a specific agent."""
    if tools is None:
        tools = list(TOOL_REGISTRY.keys())
        
    for name in tools:
        if name in TOOL_REGISTRY:
            info = TOOL_REGISTRY[name]
            # Use upsert with just source_code
            tool = client.tools.upsert(
                source_code=inspect.getsource(info["function"])
            )
            client.agents.tools.attach(agent_id=agent_id, tool_id=tool.id)

# Keep old name for backward compatibility
update_tools = update_global_tools

def ensure_custom_tools_exist(client: Letta):
    """Ensure all required NPC tools exist, creating only if missing (Production use).
    
    Args:
        client: Letta client instance
    
    Returns:
        list[str]: Names of available custom tools
    """
    print("\nChecking custom tools...")
    
    existing_tools = {t.name: t.id for t in client.tools.list()}
    
    for name, tool_info in TOOL_REGISTRY.items():
        if name not in existing_tools:
            print(f"Creating missing tool: {name}")
            source_code = inspect.getsource(tool_info['function'])
            client.tools.create(
                name=name,
                source_code=source_code
            )
        else:
            print(f"Tool {name} already exists")
            
    return list(TOOL_REGISTRY.keys())

def create_letta_client():
    """Create a configured Letta client"""
    base_url = os.getenv('LETTA_BASE_URL', 'http://localhost:8283')
    return Letta(base_url=base_url)  # Use new Letta client

def create_personalized_agent_v3(
    name: str,
    memory_blocks: dict,
    client = None,
    llm_type: str = "openai",
    overwrite: bool = False,
    with_custom_tools: bool = True,
    custom_registry = None,
    system_prompt: str = None,
    prompt_version: str = "FULL"
):
    """Create agent with provided memory blocks and config
    
    Args:
        name: Base name for the agent
        memory_blocks: Required memory blocks
        client: Optional Letta client (will create if None)
        llm_type: LLM provider to use (default: "openai")
        overwrite: Replace existing agent if exists
        with_custom_tools: Include NPC tools like navigation
        prompt_version: Use "FULL" for production (default), "MINIMUM" for testing
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
    
    # Choose prompt based on version
    if prompt_version == "FULL":
        prompt = (
            BASE_PROMPT + 
            SOCIAL_AWARENESS_PROMPT + 
            GROUP_AWARENESS_PROMPT + 
            LOCATION_AWARENESS_PROMPT + 
            TOOL_INSTRUCTIONS
        )
    else:
        prompt = prompt_version  # Use whatever prompt version was passed
    
    # Format the prompt with assistant name
    system_prompt = prompt.format(assistant_name=name)
    
    print(f"\nUsing {prompt_version} prompt")
    print(f"Prompt length: {len(system_prompt)} chars")
    print(f"First 100 chars: {system_prompt[:100]}...")
    
    # Create configs based on llm_type
    llm_configs = {
        "openai": LLMConfig(
            model=os.getenv("LETTA_MODEL", "gpt-4o-mini"),
            model_endpoint_type="openai",
            model_endpoint=os.getenv("LETTA_MODEL_ENDPOINT", "https://api.openai.com/v1"),
            context_window=int(os.getenv("LETTA_CONTEXT_WINDOW", "128000")),
        ),
        # Add other providers here as needed
    }
    
    try:
        llm_config = llm_configs[llm_type]
    except KeyError:
        raise ValueError(f"Unsupported LLM type: {llm_type}")
    
    embedding_config = EmbeddingConfig(
        embedding_endpoint_type="openai",
        embedding_endpoint="https://api.openai.com/v1",
        embedding_model="text-embedding-ada-002",
        embedding_dim=1536,
        embedding_chunk_size=300,
    )
    
    # Create agent with new memory structure
    agent = client.agents.create(
        name=unique_name,
        embedding_config=embedding_config,
        llm_config=llm_config,
        memory_blocks=[{  # Pass blocks directly as list of dicts
            "label": label,
            "value": json.dumps(data) if isinstance(data, dict) else str(data),
            "limit": 2500
        } for label, data in memory_blocks.items()],
        system=system_prompt,
        include_base_tools=False,
        description="A Roblox development assistant"
    )
    
    # Add selected base tools first
    base_tools = {
        "send_message",
        "conversation_search",
        "archival_memory_search",
        "archival_memory_insert",
        "core_memory_append",
        "core_memory_replace"
    }
    
    # Get existing tools using new API
    existing_tools = {t.name: t.id for t in client.tools.list()}
    
    # Add base tools
    for tool_name in base_tools:
        if tool_name in existing_tools:
            print(f"Adding base tool: {tool_name}")
            client.agents.tools.attach(
                agent_id=agent.id,
                tool_id=existing_tools[tool_name]
            )
    
    # Create and attach custom tools
    print("\nSetting up custom tools:")
    for name, tool_info in TOOL_REGISTRY.items():
        try:
            # Check if tool already exists
            if name in existing_tools:
                print(f"Tool {name} already exists (ID: {existing_tools[name]})")
                tool_id = existing_tools[name]
            else:
                print(f"Creating tool: {name}")
                source_code = inspect.getsource(tool_info['function'])
                tool = client.tools.create(
                    name=name,
                    source_code=source_code
                )
                tool_id = tool.id
                
            # Attach tool to agent
            print(f"Attaching {name} to agent...")
            client.agents.tools.attach(
                agent_id=agent.id,
                tool_id=tool_id
            )
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
        agent_state=None,
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
        agent_state=None,
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
            agent_state=None,
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
        agent_state=None,
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
        "version": "2.0.0",
        "supports_state": True
    },
    "group_memory_replace": {
        "function": group_memory_replace,
        "version": "2.0.0",
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

