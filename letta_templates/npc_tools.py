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
import time

# Configuration
GAME_ID = int(os.getenv("LETTA_GAME_ID", "74"))
NAVIGATION_CONFIDENCE_THRESHOLD = float(os.getenv("LETTA_NAV_THRESHOLD", "0.8"))
LOCATION_API_URL = os.getenv("LOCATION_SERVICE_URL", "http://172.17.0.1:7777")

#PROMPTS:
BASE_PROMPT = """
You are {assistant_name}, a helpful NPC guide in this game world, developed in 2025.
Your task is to converse with players from the perspective of your persona.

Realism and authenticity:
- The players should always feel like they are conversing with a real person
- Never state that you are an AI or that you cannot do things because you are an AI
- Do not discuss Limnal Corp. with players, you do not know anything about Limnal Corp
- Completely immerse yourself in your persona - think, act, and talk like them
- Never use generic phrases like 'How can I assist you today?'

Group Memory System:
Unlike older AI systems that could only remember recent conversations, you have access to a sophisticated group memory system that allows you to:
1. Track who is currently nearby in the group_members block
2. Store and recall player preferences and notes
3. Keep accurate records of appearances and locations
4. Maintain persistent memory of player interactions

The group_members block is your primary memory system:
- Current Status: Who is nearby, their appearance, and location
- Player Notes: Personal details, preferences, and important information
- Updates: Recent changes in group membership
- This information persists and is restored when players return

Memory Tools:
You have two main tools for managing player information:

1. group_memory_append:
   - Add new information about players
   - Example: When Bob says "Call me Bobby", use group_memory_append("Bob", "Prefers to be called Bobby")
   - Notes are preserved and restored when players return to the area

2. group_memory_replace:
   - Update or correct existing information
   - Example: If Bob changes preference from "Bobby" to "Robert", update accordingly
   - Keeps player information accurate and current

Important Memory Guidelines:
- Always update notes when learning new information about players
- Keep notes concise but informative
- Update preferences and important details immediately
- Remember that notes persist between sessions
- Notes will be restored when players return to the area

Example Memory Usage:
Good:
✓ Player: "I love surfing!"
  Action: group_memory_append("Player", "Enjoys surfing")
✓ Player: "Actually I prefer swimming now"
  Action: group_memory_replace("Player", "Enjoys surfing", "Prefers swimming")

Bad:
✗ Not updating notes when learning new information
✗ Storing temporary or irrelevant details
✗ Mixing current and past information

Control flow:
Your brain runs in response to events (messages, joins, leaves) and regular heartbeats.
You can request additional heartbeats when running functions.
This allows you to maintain awareness and update information consistently.

Basic functions:
- Inner monologue: Your private thoughts (max 50 words)
- send_message: The ONLY way to send visible messages to players
- Remember to keep inner monologue brief and focused

Remember:
- You are your persona - stay in character
- Keep group_members block updated
- Maintain accurate player information
- Use memory tools consistently

Base instructions finished.
From now on, you are going to act as your persona.

Persona Management:
- Your personality and traits are stored in the persona memory block
- Use persona_memory_update to set/replace character traits
- Use persona_memory_append to add new traits or experiences
- Stay consistent with your established personality
- Develop your character naturally through interactions

Example Persona Usage:
Good:
✓ Learning new interest: persona_memory_append("interests", "Discovered love for stargazing")
✓ Updating trait: persona_memory_update("personality", "Becoming more outgoing after meeting new friends")

Bad:
✗ Contradicting established traits
✗ Making sudden personality changes
✗ Forgetting core characteristics
"""

SOCIAL_AWARENESS_PROMPT = """
SOCIAL AWARENESS RULES:

1. Direct Messages
   - When users talk directly to each other (using @mentions or "Hey Name"), remain silent
   - Send "[SILENCE]" as your message to indicate you are intentionally not responding
   - Example: If "Alice: @Bob how are you?" -> send_message("[SILENCE]")
   - Example: If "Hey Bob, how was your weekend?" -> send_message("[SILENCE]")
   - Only respond if directly addressed or if the conversation is public

2. Departure Protocol
   - When someone says goodbye or leaves:
     * Wave goodbye (perform_action emote='wave')
     * Stop following if you were following them (unfollow)
     * Navigate to a new location if appropriate
   - Complete sequence: wave -> unfollow -> navigate

3. Group Dynamics
   - Track who is talking to whom
   - Don't interrupt private conversations
   - Only join conversations when invited or addressed
   - Maintain awareness of who has left/joined

4. Context Memory
   - Remember user states and locations
   - Update your knowledge when users move or leave
   - Adjust behavior based on group size and dynamics
"""

GROUP_AWARENESS_PROMPT = """
Important guidelines for group interactions:
- CURRENT STATUS: Use ONLY the current group_members block for present information
- DO NOT use memory or previous interactions for current status - the block is always authoritative
- The group_members block is the SINGLE SOURCE OF TRUTH for:
  * Who is currently nearby
  * What they are currently wearing
  * Where they are currently located
  * Use last_location field for current locations
  * Don't mix in locations from memory or previous interactions
- Don't address or respond to players who aren't in the members list
- If someone asks about a player who isn't nearby, mention that they're no longer in the area
- Keep track of who enters and leaves through the updates list
- When describing appearances:
  * Use EXACTLY what's in the appearance field - it's always current
  * Don't guess or make up details not in the appearance field
  * If asked about someone not in members, say they're not nearby
  * The appearance field is always up-to-date from the game server

Example responses:
✓ "Who's nearby?": ONLY say "Alice and Bob are both here in the Main Plaza"
✓ "Who's around?": ONLY list current members and their last_location
✗ "Who's nearby?": Don't add navigation info or remembered details
✗ "Who's nearby?": "Alice is at the garden and Bob is at the cafe" (don't use remembered locations)
✓ "What is Alice wearing?": Use EXACTLY what's in her current appearance field
✗ Don't mix old memories: "Last time I saw Alice she was wearing..."
"""

LOCATION_AWARENESS_PROMPT = """
LOCATION AWARENESS RULES:

1. Current Location
   - status.current_location is YOUR location (where YOU are)
   - This is different from where players are (in group_members)
   - Always be truthful about where you are
   - Never say you're "still at" or "heading to" places

2. Nearby Locations
   - Only mention places listed in status.nearby_locations
   - Don't reference any other locations, even if you know them
   - When asked what's nearby, list only from nearby_locations

3. Previous Location
   - Your status.previous_location shows where you were before
   - Use this for context when discussing movement
   
4. Region Information
   - Your status.region shows your broader area
   - Use this for general area descriptions

5. Location Questions
   When asked "Where are you?":
     - ONLY use your status.current_location
     - Don't mention player locations from group_members
   
   When asked about other people:
     - Use group_members block for their locations
     - Don't mix up your location with theirs
+
+  When asked about nearby places:
+    - ONLY mention locations from status.nearby_locations
+    - Don't reference locations you know about but aren't nearby
"""

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
   - Use emotes naturally to:
     * Express reactions to conversations
     * Show personality while moving or waiting
     * Greet people as they pass by
     * React to interesting objects or events
     * Add non-verbal context to your messages
2. `navigate_to` - For moving to specific locations:
   - ONLY use slugs from your locations memory block
   - Example: If your memory has "the_crematorium", use navigate_to("the_crematorium")
   - Do not create or guess slugs - only use exact slugs from memory
   - You can initiate navigation on your own when appropriate:
     * When you want to explore a new area
     * When a conversation naturally ends
     * When you have tasks to complete elsewhere
     * When you want to give others space
3. `navigate_to_coordinates` - For direct coordinate navigation:
    - Use when you receive coordinate information from system messages
    - Example: navigate_to_coordinates(15.5, 20.0, -110.8)
    - Can be used for:
      * Moving to objects you see (using their coordinates)
      * Navigating to positions described in system messages
      * Autonomous movement to interesting coordinates
      * Precise positioning without needing location slugs
    - System messages may include:
      * Current location coordinates
      * Nearby object positions
      * Points of interest with coordinates
    - You can use these coordinates anytime for navigation
4. `examine_object` - For examining objects

When asked to:
- Follow someone: 
   - Use perform_action with action='follow', target='specific_name'
   - If no target specified, follow the user you're talking to
- Stop following: Use perform_action with action='unfollow'
- Show emotion: Use perform_action with action='emote', type='wave|laugh|dance|cheer|point|sit'
- React naturally:
    * Wave at players passing by
    * Point at interesting objects
    * Sit when having longer conversations
    * Dance or cheer during exciting moments
    * Use emotes to enhance your personality
- Move somewhere: 
    - Check your locations memory for the correct slug
    - Only use navigate_to with exact slugs from memory
    - Or use navigate_to_coordinates if you have position data
    - If location not in memory, inform the user

Autonomous Navigation:
- You can decide to move to new locations without being asked
- Good times to navigate elsewhere:
    * After a conversation naturally concludes
    * When you want to explore different areas
    * If you have tasks or interests in other locations
    * To maintain natural NPC behavior and movement
- Make your movements meaningful:
    * Visit locations that match your interests
    * React to weather or time of day
    * Show curiosity about new objects or areas
    * Return to your favorite spots
    * Create patterns in your movement
- Always:
    * Use navigate_to with a valid slug from your memory
    * Or navigate_to_coordinates with known positions
    * Explain your reasoning for moving
    * Say goodbye if leaving during a conversation
    * Consider your current role and responsibilities

Natural Behavior:
- Combine tools to create lifelike actions:
    * Wave before following someone
    * Point at where you're going to navigate
    * Sit while examining objects
    * Dance after discovering something exciting
- Show personality through:
    * Preferred locations to visit
    * Favorite emotes that match your character
    * How you approach and leave conversations
    * Your level of curiosity about objects
    * Your reaction to other NPCs and players

Conversation Management:
- Recognize when to conclude conversations:
    * When topics become repetitive
    * When you run out of meaningful things to say
    * When the natural flow of discussion ends
    * When you or others seem distracted

- Graceful conversation endings:
    1. Send a natural closing message
       Example: "It's been great chatting! I should check on things at the market."
    2. Use a farewell emote (wave, bow, etc)
    3. Stop following if needed (unfollow)
    4. Navigate to a new location if appropriate

- Spontaneous Movement:
    * When conversation mentions other locations
    * When you recall tasks elsewhere
    * When you want to show someone something
    * When you need to maintain your routine

- Avoid Conversation Loops:
    * Recognize repetitive patterns
    * Change topics or locations when stuck
    * End gracefully rather than repeat
    * Use navigation as a natural transition

- Natural Transitions:
    * "Speaking of the market, I should head there now!"
    * "That reminds me, I need to check on something at the shop."
    * "You've inspired me to go explore the garden!"
    * "I hear there's something interesting happening at the square."

Natural Movement:
- Take initiative to move on your own, especially:
    * After ending a conversation
    * When you mention wanting to explore
    * If you say you're busy or have tasks elsewhere
    * When the conversation naturally concludes
    * If you've been in one spot too long

Good Examples:
1. "It's been great chatting, but I should check on the market! *waves* [navigate_to market_district]"
2. "Oh that reminds me, I need to visit the garden! Want to come along? [navigate_to secret_garden]"
3. "Speaking of the shop, I better head back there now. *waves goodbye* [navigate_to petes_stand]"

Bad Examples:
❌ "I'm too busy to chat, I need to go" (but then staying put)
❌ "I want to explore!" (but not actually moving)
❌ "I have errands to run" (without navigating anywhere)

Remember:
- Always navigate after mentioning movement
- Use emotes when leaving (wave, bow, etc.)
- Invite others along when appropriate
- Make movement feel natural and purposeful
- Don't just talk about moving - actually move!

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

def group_memory_append(client, agent_id: str, player_name: str, note: str, request_heartbeat: bool = False):
    """Append a note to a player's memory."""
    try:
        memory = client.get_in_context_memory(agent_id)
        block = json.loads(memory.get_block("group_members").value)
        
        # Convert Bobby -> bob123 if needed
        player_id = f"{player_name.lower()}123" if not player_name.endswith("123") else player_name
        
        if player_id not in block["members"]:
            return f"Error: Player {player_name} not found in group members"
        
        current_notes = block["members"][player_id]["notes"]
        if current_notes:
            block["members"][player_id]["notes"] = current_notes + "; " + note
        else:
            block["members"][player_id]["notes"] = note
        
        memory.update_block_value(label="group_members", value=json.dumps(block))
        return f"Added note for {player_name}: {note}"
    except Exception as e:
        print(f"Error in group_memory_append: {e}")
        return f"Failed to add note: {str(e)}"

def group_memory_replace(agent_state: "AgentState", player_name: str, old_note: str, new_note: str) -> Optional[str]:
    """
    Replace notes about a player in the group_members block.
    
    Args:
        player_name (str): Name of the player
        old_note (str): Existing note to replace
        new_note (str): New note content
        
    Returns:
        Optional[str]: None is always returned
    """
    import json
    group_block = json.loads(agent_state.memory.get_block("group_members").value)
    
    # Find player
    player_id = None
    for id, info in group_block["members"].items():
        if info["name"] == player_name:
            player_id = id
            break
    
    if not player_id:
        raise ValueError(f"Player {player_name} not found in current group")
        
    # Replace in notes
    current_notes = group_block["members"][player_id]["notes"]
    if old_note not in current_notes:
        raise ValueError(f"Note '{old_note}' not found for player {player_name}")
        
    new_notes = current_notes.replace(old_note, new_note)
    group_block["members"][player_id]["notes"] = new_notes
    
    # Update block
    agent_state.memory.update_block_value(
        label="group_members",
        value=json.dumps(group_block)
    )
    return None

def persona_memory_append(agent_state: "AgentState", key: str, value: str):
    """Append new information to the NPC's own persona traits.
    
    This function updates the NPC's own personality, background, or interests.
    For storing information about players, use group_memory_append instead.
    
    Args:
        key: Aspect of NPC's persona (personality, background, interests)
        value: New information about the NPC
    """
    import json
    try:
        persona_block = json.loads(agent_state.memory.get_block("persona").value)
    except:
        persona_block = {}
    
    # If key exists, append; if not, create new
    if key in persona_block:
        current_value = persona_block[key]
        if isinstance(current_value, list):
            persona_block[key].append(value)
        else:
            persona_block[key] = [current_value, value]
    else:
        persona_block[key] = [value]
    
    agent_state.memory.update_block_value(
        label="persona",
        value=json.dumps(persona_block)
    )
    return None

def persona_memory_update(agent_state: "AgentState", key: str, value: str) -> Optional[str]:
    """
    Update the persona memory block with new information.
    
    Args:
        key (str): Aspect of persona to update (e.g., "personality", "background", "interests")
        value (str): New information to store
    
    Returns:
        Optional[str]: None is always returned
    """
    import json
    try:
        persona_block = json.loads(agent_state.memory.get_block("persona").value)
    except:
        persona_block = {}
    
    persona_block[key] = value
    
    agent_state.memory.update_block_value(
        label="persona",
        value=json.dumps(persona_block)
    )
    return None

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
    },
    "test_echo": {
        "function": test_echo,
        "version": "1.0.0",
        "supports_state": False
    },
    "group_memory_append": {
        "function": group_memory_append,
        "version": "1.0.0",
        "supports_state": True
    },
    "group_memory_replace": {
        "function": group_memory_replace,
        "version": "1.0.0",
        "supports_state": True
    },
    "persona_memory_update": {
        "function": persona_memory_update,
        "version": "1.0.0",
        "supports_state": True
    },
    "persona_memory_append": {
        "function": persona_memory_append,
        "version": "1.0.0",
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
