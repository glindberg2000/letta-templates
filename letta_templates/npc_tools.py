"""NPC Tool Definitions for Letta Integration

This module provides a complete set of NPC action tools for creating interactive game characters.

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

# Configuration
GAME_ID = int(os.getenv("LETTA_GAME_ID", "61"))
NAVIGATION_CONFIDENCE_THRESHOLD = float(os.getenv("LETTA_NAV_THRESHOLD", "0.8"))
LOCATION_API_URL = os.getenv("LOCATION_SERVICE_URL", "http://172.17.0.1:7777")

# System prompt instructions for tools
TOOL_INSTRUCTIONS = """
Performing actions:
You have access to the following tools:
1. `perform_action` - For basic NPC actions:
   - follow: For tracking specific players or NPCs
     Example: perform_action("follow", target="greggytheegg")
   - unfollow: Stop following current target
     Example: perform_action("unfollow")
   - emote: For expressions and gestures
2. `navigate_to` - For moving to specific locations:
   - ONLY use slugs from your locations memory block
   - Example: If your memory has "the_crematorium", use navigate_to("the_crematorium")
   - Do not create or guess slugs - only use exact slugs from memory
3. `examine_object` - For examining objects

When asked to:
- Follow someone: 
   - Use perform_action with action='follow', target='specific_name'
   - If no target specified, follow the user you're talking to
- Stop following: Use perform_action with action='unfollow'
- Show emotion: Use perform_action with action='emote', type='wave|laugh|dance|cheer|point|sit'
- Move somewhere: 
    - Check your locations memory for the correct slug
    - Only use navigate_to with exact slugs from memory
    - If location not in memory, inform the user
- Examine something: Use examine_object with object_name='item'

Important notes:
- Must unfollow before navigating to a new location
- Emotes can include optional target (e.g., wave at someone)
- Available emote types: wave, laugh, dance, cheer, point, sit
- Tool names must be exactly as shown - no spaces or special characters
- Always include request_heartbeat=True in tool calls
- Never guess or create slugs - only use exact slugs from your locations memory
"""

# State enums for consistency
class ActionProgress(Enum):
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class ActionState:
    """Base state information for actions"""
    current_action: str
    progress: str
    position: str
    can_interact: bool = True
    interruption_allowed: bool = True

def _format_action_message(action: str, target: Optional[str], state: ActionState) -> str:
    """Format natural language message for actions"""
    messages = {
        "follow": f"I am now following {target}. I'll maintain a respectful distance.",
        "wave": f"I'm waving{' at ' + target if target else ''}!",
        "sit": "I've taken a seat. Feel free to continue our conversation."
    }
    
    return messages.get(action, f"Performing action: {action}{' targeting ' + target if target else ''}")

def perform_action(action: str, type: Optional[str] = None, target: Optional[str] = None, request_heartbeat: bool = True) -> str:
    """
    Perform a basic NPC action like following or emoting.
    
    Args:
        action (str): The action to perform ('follow', 'unfollow', 'emote')
        type (str, optional): For emotes, the type ('wave', 'laugh', 'dance', etc)
        target (str, optional): Target of the action (player name or object)
        request_heartbeat (bool): Request heartbeat after execution
        
    Returns:
        str: Description of the action performed
    """
    if action == 'emote' and type:
        if type in ['wave', 'laugh', 'dance', 'cheer', 'point', 'sit']:
            return f"Performing emote: {type}" + (f" at {target}" if target else "")
        return f"Unknown emote type: {type}"
    elif action == 'follow' and target:
        return f"Starting to follow {target}. Will maintain appropriate distance."
    elif action == 'unfollow':
        return f"Stopping follow action. Now stationary."
    return f"Unknown action: {action}"

def navigate_to(destination: str, request_heartbeat: bool = True) -> dict:
    """
    Navigate to a location using its slug from memory.
    
    Args:
        destination (str): Location slug from memory (e.g. "the_crematorium")
        request_heartbeat (bool, optional): Request heartbeat after execution. Defaults to True.
        
    Returns:
        dict: Navigation result with format:
            {
                "status": str,        # "success" or "failure"
                "message": str,       # Human readable message
                "slug": str | None    # Clean slug if success, None if failure
            }
    
    Example:
        >>> navigate_to("the_crematorium")
        {
            "status": "success",
            "message": "Navigating to the_crematorium",
            "slug": "the_crematorium"
        }
    """
    # Validate slug format (lowercase, no spaces, etc)
    slug = destination.lower().strip()
    if not slug.replace('_', '').isalnum():
        return {
            "status": "failure",
            "message": f"Invalid slug format: {destination}",
            "coordinates": None
        }
    
    return {
        "status": "success",
        "message": f"Navigating to {destination}",
        "slug": destination.lower()
    }

def navigate_to_coordinates(x: float, y: float, z: float, request_heartbeat: bool = True) -> dict:
    """
    Navigate to specific XYZ coordinates.
    
    Args:
        x (float): X coordinate
        y (float): Y coordinate
        z (float): Z coordinate
        request_heartbeat (bool, optional): Request heartbeat after execution. Defaults to True.
        
    Returns:
        dict: Navigation result with format:
            {
                "status": str,           # "success" or "failure"
                "message": str,          # Human readable message
                "coordinates": dict      # {x: float, y: float, z: float}
            }
    
    Example:
        >>> navigate_to_coordinates(15.5, 20.0, -110.8)
        {
            "status": "success",
            "message": "Navigating to coordinates (15.5, 20.0, -110.8)",
            "coordinates": {"x": 15.5, "y": 20.0, "z": -110.8}
        }
    """
    return {
        "status": "success",
        "message": f"Navigating to coordinates ({x}, {y}, {z})",
        "coordinates": {"x": x, "y": y, "z": z}
    }

def navigate_to_v1(destination: str, request_heartbeat: bool = True) -> dict:
    """Old semantic search navigation (deprecated)"""
    # Old implementation here...

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

# Tool registry with metadata
TOOL_REGISTRY: Dict[str, Dict] = {
    "navigate_to": {
        "function": navigate_to,
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
    "examine_object": {
        "function": examine_object,
        "version": "2.0.0",
        "supports_state": True
    }
}

# Production navigation tools
NAVIGATION_TOOLS: Dict[str, Dict] = {
    "navigate_to": TOOL_REGISTRY["navigate_to"],
    "navigate_to_coordinates": TOOL_REGISTRY["navigate_to_coordinates"],
    "perform_action": TOOL_REGISTRY["perform_action"]
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