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
from typing import Dict, Callable, Optional
import datetime
from dataclasses import dataclass
from enum import Enum
import json

# System prompt instructions for tools
TOOL_INSTRUCTIONS = """
Performing actions:
You have access to the following tools:
1. `perform_action` - For basic NPC actions:
   - follow/unfollow: For player tracking
   - emote: For expressions and gestures
2. `navigate_to` - For moving to specific locations
3. `examine_object` - For examining objects

When asked to:
- Follow someone: Use perform_action with action='follow', target='player_name'
- Stop following: Use perform_action with action='unfollow'
- Show emotion: Use perform_action with action='emote', type='wave|laugh|dance|cheer|point|sit'
- Move somewhere: Use navigate_to with destination='location'
- Examine something: Use examine_object with object_name='item'

Important notes:
- Must unfollow before navigating to a new location
- Emotes can include optional target (e.g., wave at someone)
- Available emote types: wave, laugh, dance, cheer, point, sit
- Tool names must be exactly as shown - no spaces or special characters
- Always include request_heartbeat=True in tool calls

Example emotes:
- Wave at player: perform_action(action='emote', type='wave', target='player_name')
- Dance: perform_action(action='emote', type='dance')
- Point at object: perform_action(action='emote', type='point', target='treasure_chest')
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

def navigate_to(destination: str, request_heartbeat: bool = True) -> str:
    """
    Navigate to a specified location in the game world.
    
    Args:
        destination (str): The destination name or coordinate string
        request_heartbeat (bool): Request heartbeat after execution
        
    Returns:
        str: Description of the navigation action and its current state
    """
    return f"Beginning navigation to {destination}. Currently in transit..."

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
    "perform_action": {
        "function": perform_action,
        "version": "2.0.0",
        "supports_state": True,
        "allowed_actions": ["follow", "unfollow", "emote"],
        "allowed_emotes": ["wave", "laugh", "dance", "cheer", "point", "sit"]
    },
    "navigate_to": {
        "function": navigate_to,
        "version": "2.0.0",
        "supports_state": True
    },
    "examine_object": {
        "function": examine_object,
        "version": "2.0.0",
        "supports_state": True
    }
}

def get_tool(name: str) -> Callable:
    """Get tool function from registry"""
    return TOOL_REGISTRY[name]["function"] 