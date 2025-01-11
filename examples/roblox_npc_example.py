"""
Roblox NPC Example using Letta Templates

Setup Requirements:
1. Docker installed
2. OpenAI API key

Setup Steps:
1. Start Letta server with Docker:
   docker run -d --name letta-server \
     -v ~/.letta/.persist/pgdata:/var/lib/postgresql/data \
     -p 8283:8283 \
     -e OPENAI_API_KEY="your_api_key" \
     letta/letta:latest

2. Set environment variables in .env:
   LETTA_BASE_URL=http://localhost:8283
   OPENAI_API_KEY=your_api_key

3. Install requirements:
   pip install letta_templates python-dotenv
"""

from letta import create_client
from letta_templates import (
    create_personalized_agent,
    update_group_status,
    chat_with_agent,
    print_agent_details
)
from dotenv import load_dotenv
import os
import json

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
    # Load environment variables
    load_dotenv()
    
    # Create client with explicit Docker URL
    client = create_client(
        base_url="http://localhost:8283"
    )
    
    # Create an NPC agent (using minimal prompt by default)
    print("Creating NPC agent...")
    agent = create_personalized_agent(
        name="town_guide",
        client=client
        # minimal_prompt=True is now default
    )
    print(f"Created agent with ID: {agent.id}")
    
    # Print initial agent details
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
        current_location="Town Square",
        current_action="idle"
    )
    print_memory_blocks(client, agent.id)

    # Player initiates conversation
    print("\nPlayer: Hi! Can you take me to Pete's Stand?")
    response = client.send_message(
        agent_id=agent.id,
        message="Hi! Can you take me to Pete's Stand?",
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
        current_location="Town Square",
        current_action="moving"  # Status change: now moving
    )
    print_memory_blocks(client, agent.id)

    # Game event: NPC arrives at destination
    print("\nGame Event: NPC arrives at Pete's Stand")
    update_group_status(
        client=client,
        agent_id=agent.id,
        nearby_players=[{
            "id": "player_123",
            "name": "Alex",
            "appearance": "Wearing a blue hat and red shirt",
            "notes": "First time visitor"
        }],
        current_location="Pete's Stand",
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
        current_location="Pete's Stand",
        current_action="idle"
    )
    print_memory_blocks(client, agent.id)

    # Test group interaction
    print("\nPlayer Emma: Can we all go to the Secret Garden?")
    response = client.send_message(
        agent_id=agent.id,
        message="Can we all go to the Secret Garden?",
        role="user",
        name="Emma"
    )
    print_response(response)

    # Game event: Group starts moving
    print("\nGame Event: Group starts moving to Secret Garden")
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
        current_location="Pete's Stand",
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
        current_location="Secret Garden",
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
        current_location="Secret Garden",
        current_action="idle"
    )
    print_memory_blocks(client, agent.id)

if __name__ == "__main__":
    main() 