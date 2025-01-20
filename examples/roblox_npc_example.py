"""
Roblox NPC Example
Version: 0.9.2

Demonstrates:
- NPC creation with memory blocks
- Group management
- Navigation
- Status updates
"""

from letta import create_client
from letta_templates import (
    create_personalized_agent,
    update_group_status,
    chat_with_agent,
    print_agent_details,
    get_memory_block,
    update_memory_block,
    create_letta_client
)
from dotenv import load_dotenv
import os
import json
from datetime import datetime

def print_response(response):
    """Print detailed response including tool usage"""
    print("\nResponse details:")
    for message in response.messages:
        if hasattr(message, 'tool_call'):
            print(f"Tool Call: {message.tool_call.name}")
            print(f"Arguments: {message.tool_call.arguments}")
        elif hasattr(message, 'tool_return'):
            print(f"Tool Return: {message.tool_return}")
        elif hasattr(message, 'reasoning'):
            print(f"Reasoning: {message.reasoning}")
        else:
            print(f"Message: {message}")

def print_memory_blocks(client, agent_id, blocks=["status", "group_members"]):
    """Print specific memory blocks to verify state"""
    print("\nCurrent Memory State:")
    memory = client.get_in_context_memory(agent_id)
    for block in memory.blocks:
        if block.label in blocks:
            print(f"\n{block.label.upper()} BLOCK:")
            print(json.dumps(json.loads(block.value), indent=2))

def main():
    # Load environment variables first
    load_dotenv()
    
    # Create client using environment config
    client = create_letta_client()  # This will print the Base URL
    
    # Create NPC agent
    agent = create_personalized_agent(
        name="town_guide",
        client=client,
        memory_blocks={
            "persona": {
                "name": "town_guide",
                "role": "Tutorial Guide",
                "personality": {
                    "traits": ["enthusiastic", "knowledgeable"],
                    "speaking_style": "friendly and casual",
                    "favorite_phrases": ["Let me show you around!", "That's a great spot!"]
                },
                "background": {
                    "origin": "Started as a visitor, loved it so much became a guide",
                    "specialties": ["hidden spots", "local history", "best views"]
                },
                "interests": ["discovering new places", "meeting travelers", "sharing stories"],
                "journal": []
            },
            "status": {
                "region": "Tutorial",
                "current_location": "Welcome Center",
                "current_action": "idle",
                "movement_state": "stationary",
                "nearby_locations": ["Visitor Plaza", "Scenic Lookout"],
                "time_of_day": "morning",
                "weather": "sunny",
                "current_visitors": 3
            },
            "group_members": {
                "members": {},
                "summary": "Ready to greet visitors",
                "updates": [],
                "last_updated": datetime.now().isoformat()
            },
            "locations": {
                "known_locations": [
                    {
                        "name": "Visitor Plaza",
                        "description": "Bustling central area with information kiosk",
                        "coordinates": [120.5, 15.0, -85.2],
                        "slug": "visitor_plaza"
                    },
                    {
                        "name": "Scenic Lookout",
                        "description": "Elevated spot with amazing views",
                        "coordinates": [145.2, 35.0, -90.5],
                        "slug": "scenic_lookout"
                    },
                    {
                        "name": "Welcome Center",
                        "description": "Starting point for new visitors",
                        "coordinates": [100.0, 15.0, -80.0],
                        "slug": "welcome_center"
                    }
                ]
            }
        }
    )
    print(f"Created agent with ID: {agent.id}")
    
    # Print initial state
    print_agent_details(client, agent.id, "INITIAL STATE")
    
    # Test 1: Player approaches NPC
    print("\n=== Test 1: Initial Interaction ===")
    
    # Game event: Player approaches NPC
    print("\nGame Event: Player Alex approaches NPC")
    update_group_status(
        client=client,
        agent_id=agent.id,
        nearby_players=[{
            "id": "player_123",
            "name": "Alex",
            "appearance": "Wearing a blue hat and red shirt",
            "notes": "First time visitor"
        }],
        current_location="Welcome Center",
        current_action="idle"
    )
    print_memory_blocks(client, agent.id)

    # Player initiates conversation
    print("\nPlayer: Hi! Can you show me around the Visitor Plaza?")
    response = client.send_message(
        agent_id=agent.id,
        message="Hi! Can you show me around the Visitor Plaza?",
        role="user",
        name="Alex"
    )
    print_response(response)

    # Game event: NPC starts moving
    print("\nGame Event: NPC starts moving")
    update_group_status(
        client=client,
        agent_id=agent.id,
        nearby_players=[{
            "id": "player_123",
            "name": "Alex",
            "appearance": "Wearing a blue hat and red shirt",
            "notes": "First time visitor"
        }],
        current_location="Welcome Center",
        current_action="moving"  # Status change: now moving
    )
    print_memory_blocks(client, agent.id)

    # Game event: NPC arrives at destination
    print("\nGame Event: NPC arrives at Visitor Plaza")
    update_group_status(
        client=client,
        agent_id=agent.id,
        nearby_players=[{
            "id": "player_123",
            "name": "Alex",
            "appearance": "Wearing a blue hat and red shirt",
            "notes": "First time visitor"
        }],
        current_location="Visitor Plaza",
        current_action="idle"  # Back to idle after arriving
    )
    print_memory_blocks(client, agent.id)

    # Test 2: Group Formation
    print("\n=== Test 2: Group Formation ===")
    
    # Game event: Another player joins
    print("\nGame Event: Player Emma joins the group")
    update_group_status(
        client=client,
        agent_id=agent.id,
        nearby_players=[
            {
                "id": "player_123",
                "name": "Alex",
                "appearance": "Wearing a blue hat and red shirt",
                "notes": "First time visitor"
            },
            {
                "id": "player_456",
                "name": "Emma",
                "appearance": "Purple dress with a backpack",
                "notes": "Regular visitor, likes the garden"
            }
        ],
        current_location="Visitor Plaza",
        current_action="idle"
    )
    print_memory_blocks(client, agent.id)

    # Test group interaction
    print("\nPlayer Emma: Can we all go to the Scenic Lookout?")
    response = client.send_message(
        agent_id=agent.id,
        message="Can we all go to the Scenic Lookout?",
        role="user",
        name="Emma"
    )
    print_response(response)

    # Game event: Group starts moving
    print("\nGame Event: Group starts moving to Scenic Lookout")
    update_group_status(
        client=client,
        agent_id=agent.id,
        nearby_players=[
            {
                "id": "player_123",
                "name": "Alex",
                "appearance": "Wearing a blue hat and red shirt",
                "notes": "First time visitor"
            },
            {
                "id": "player_456",
                "name": "Emma",
                "appearance": "Purple dress with a backpack",
                "notes": "Regular visitor, likes the garden"
            }
        ],
        current_location="Visitor Plaza",
        current_action="moving"
    )
    print_memory_blocks(client, agent.id)

    # Test 3: Group Dissolution
    print("\n=== Test 3: Group Dissolution ===")
    
    # Game event: Alex leaves
    print("\nGame Event: Player Alex leaves")
    update_group_status(
        client=client,
        agent_id=agent.id,
        nearby_players=[{
            "id": "player_456",
            "name": "Emma",
            "appearance": "Purple dress with a backpack",
            "notes": "Regular visitor, likes the garden"
        }],
        current_location="Scenic Lookout",
        current_action="idle"
    )
    print_memory_blocks(client, agent.id)

    # Final interaction
    print("\nPlayer Emma: I should go too, thanks for the tour!")
    response = client.send_message(
        agent_id=agent.id,
        message="I should go too, thanks for the tour!",
        role="user",
        name="Emma"
    )
    print_response(response)

    # Game event: Last player leaves
    print("\nGame Event: All players have left")
    update_group_status(
        client=client,
        agent_id=agent.id,
        nearby_players=[],
        current_location="Scenic Lookout",
        current_action="idle"
    )
    print_memory_blocks(client, agent.id)

    # Read any block
    locations = get_memory_block(client, agent.id, "locations")
    
    # Example of reading/writing custom blocks:
    # custom = get_memory_block(client, agent.id, "custom_block")
    # update_memory_block(client, agent.id, "custom_block", {
    #     "my_data": "custom value",
    #     "timestamp": datetime.now().isoformat()
    # })
    
    # Update any block
    update_memory_block(client, agent.id, "locations", {
        "known_locations": [
            # New location data...
        ]
    })

if __name__ == "__main__":
    main() 