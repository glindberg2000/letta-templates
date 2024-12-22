"""NPC Tool Definitions for Letta Integration

This module provides the core NPC action tools and system prompt instructions for Letta agents.

Usage:
    1. Import tools and instructions:
        from npc_tools import TOOL_INSTRUCTIONS, TOOL_REGISTRY, get_tool

    2. Create NPC agent with tools:
        def create_npc_agent(client, npc_details):
            # Add tool instructions to system prompt
            system_prompt = npc_details["system_prompt"].replace(
                "Base instructions finished.",
                TOOL_INSTRUCTIONS + "\nBase instructions finished."
            )
            
            return client.create_agent(
                name=npc_details["name"],
                system=system_prompt,
                include_base_tools=True
            )

    3. Register tools with Letta:
        def register_npc_tools(client):
            tool_ids = []
            for name, info in TOOL_REGISTRY.items():
                tool = client.create_tool(info["function"], name=name)
                tool_ids.append(tool.id)
            return tool_ids

Available Tools:
    - perform_action: Basic NPC actions (follow, unfollow, emotes)
    - navigate_to: Movement to locations
    - examine_object: Object interaction

Tool States:
    All tools return rich state information including:
    - Current action and progress
    - Position and target information
    - Interaction capabilities
    - Natural language messages

See TOOL_INSTRUCTIONS for complete usage documentation.
"""
from typing import Dict, Callable, Optional
import datetime
from dataclasses import dataclass
from enum import Enum

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

def perform_action(
    action: str, 
    type: Optional[str] = None, 
    target: Optional[str] = None, 
    request_heartbeat: bool = True
) -> dict:
    """
    Perform a basic NPC action like following, unfollowing, or emoting.
    
    Args:
        action (str): The action to perform ('follow', 'unfollow', 'emote')
        type (str, optional): For emotes, the type ('wave', 'laugh', 'dance', 'cheer', 'point', 'sit')
        target (str, optional): Target of the action (player name or object)
        request_heartbeat (bool): Request heartbeat after execution
        
    Returns:
        dict: Rich action result with state information
    """
    # Define states for different actions
    states = {
        "follow": ActionState(
            current_action="following",
            progress=ActionProgress.IN_PROGRESS.value,
            position="maintaining follow distance",
            can_interact=True,
            interruption_allowed=True
        ),
        "unfollow": ActionState(
            current_action="idle",
            progress=ActionProgress.COMPLETED.value,
            position="stationary",
            can_interact=True,
            interruption_allowed=True
        ),
        "emote": {
            "wave": ActionState(
                current_action="waving",
                progress=ActionProgress.IN_PROGRESS.value,
                position="in place",
                can_interact=False,
                interruption_allowed=True
            ),
            "laugh": ActionState(
                current_action="laughing",
                progress=ActionProgress.IN_PROGRESS.value,
                position="in place",
                can_interact=True,
                interruption_allowed=True
            ),
            "dance": ActionState(
                current_action="dancing",
                progress=ActionProgress.IN_PROGRESS.value,
                position="in place",
                can_interact=False,
                interruption_allowed=True
            ),
            "cheer": ActionState(
                current_action="cheering",
                progress=ActionProgress.IN_PROGRESS.value,
                position="in place",
                can_interact=True,
                interruption_allowed=True
            ),
            "point": ActionState(
                current_action="pointing",
                progress=ActionProgress.IN_PROGRESS.value,
                position="in place",
                can_interact=True,
                interruption_allowed=True
            ),
            "sit": ActionState(
                current_action="sitting",
                progress=ActionProgress.COMPLETED.value,
                position="seated",
                can_interact=True,
                interruption_allowed=True
            )
        }
    }
    
    # Get appropriate state
    if action == 'emote' and type:
        state = states['emote'].get(type, ActionState(
            current_action=type,
            progress=ActionProgress.IN_PROGRESS.value,
            position="in place"
        ))
    else:
        state = states.get(action, ActionState(
            current_action=action,
            progress=ActionProgress.IN_PROGRESS.value,
            position="unknown"
        ))
    
    # Format message based on action type
    if action == 'emote' and type:
        message = {
            "wave": f"I'm waving{' at ' + target if target else ''}!",
            "laugh": f"I'm laughing{' with ' + target if target else ''}!",
            "dance": "I'm dancing!",
            "cheer": f"I'm cheering{' for ' + target if target else ''}!",
            "point": f"I'm pointing{' at ' + target if target else ''}.",
            "sit": "I've taken a seat."
        }.get(type, f"Performing {type}{' at ' + target if target else ''}")
    else:
        message = {
            "follow": f"I am now following {target}. I'll maintain a respectful distance.",
            "unfollow": f"I've stopped following {target}.",
        }.get(action, f"Performing action: {action}{' targeting ' + target if target else ''}")
    
    return {
        "status": "success",
        "action_called": action,
        "state": {
            "current_action": state.current_action,
            "target": target,
            "progress": state.progress,
            "position": state.position,
            "emote_type": type if action == 'emote' else None
        },
        "context": {
            "can_interact": state.can_interact,
            "interruption_allowed": state.interruption_allowed,
            "target_type": "player" if target else None
        },
        "message": message,
        "timestamp": datetime.datetime.now().isoformat()
    }

def navigate_to(destination: str, request_heartbeat: bool = True) -> dict:
    """
    Navigate to a specified location in the game world.
    
    Args:
        destination (str): The destination name or coordinate string
        request_heartbeat (bool): Request heartbeat after execution
        
    Returns:
        dict: Rich navigation result with state information
    """
    state = ActionState(
        current_action="moving",
        progress=ActionProgress.INITIATED.value,
        position="moving towards destination"
    )
    
    return {
        "status": "success",
        "action_called": "navigate",
        "state": {
            "current_action": state.current_action,
            "destination": destination,
            "progress": state.progress,
            "position": state.position
        },
        "context": {
            "can_interact": state.can_interact,
            "interruption_allowed": state.interruption_allowed,
            "estimated_time": "in progress"
        },
        "message": (
            f"I am now moving towards {destination}. "
            "I'll let you know when I arrive. "
            "Feel free to give me other instructions while I'm on my way."
        ),
        "timestamp": datetime.datetime.now().isoformat()
    }

def examine_object(object_name: str, request_heartbeat: bool = True) -> dict:
    """
    Examine an object in the game world.
    
    Args:
        object_name (str): Name of the object to examine
        request_heartbeat (bool): Request heartbeat after execution
        
    Returns:
        dict: Rich examination result with state information
    """
    state = ActionState(
        current_action="examining",
        progress=ActionProgress.IN_PROGRESS.value,
        position="at examination distance"
    )
    
    return {
        "status": "success",
        "action_called": "examine",
        "state": {
            "current_action": state.current_action,
            "target": object_name,
            "progress": state.progress,
            "position": state.position
        },
        "context": {
            "can_interact": state.can_interact,
            "focus": object_name,
            "observation_complete": False,
            "interruption_allowed": state.interruption_allowed
        },
        "message": (
            f"I am examining the {object_name} carefully. "
            "I can describe what I observe or interact with it further."
        ),
        "timestamp": datetime.datetime.now().isoformat()
    }

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