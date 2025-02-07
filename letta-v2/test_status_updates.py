import os
from dotenv import load_dotenv
from letta_templates.npc_utils_v2 import (
    update_status_block,
    get_memory_block,
    create_memory_blocks
)
from letta_templates.npc_tools import create_letta_client

def test_status_updates():
    """Test various status update scenarios"""
    
    # Setup
    load_dotenv()
    client = create_letta_client()
    
    # Create test agent with empty status
    blocks = {
        "status": "",
        "locations": {"known_locations": []},
        "group_members": {"members": {}},
        "persona": "Test NPC"
    }
    
    agent = client.agents.create(
        name="test_status_npc",
        description="Testing status updates",
        system="You are a test NPC"
    )
    memory_blocks = create_memory_blocks(client, blocks)
    
    print("\nRunning status update tests...")
    
    # Test 1: Simple text update
    print("\nTest 1: Simple text update")
    result = update_status_block(
        client=client,
        agent_id=agent.id,
        status_text="Location: Shop | Action: Testing"
    )
    print(f"Result: {result}")
    
    # Test 2: Dict update with basic fields
    print("\nTest 2: Dict update with basic fields")
    result = update_status_block(
        client=client,
        agent_id=agent.id,
        status_data={
            "location": "Town Square",
            "action": "Walking",
            "activity": "busy"
        }
    )
    print(f"Result: {result}")
    
    # Test 3: Dict update with custom fields
    print("\nTest 3: Dict update with custom fields")
    result = update_status_block(
        client=client,
        agent_id=agent.id,
        status_data={
            "location": "Shop",
            "action": "Helping",
            "health": 100,
            "mood": "happy"
        }
    )
    print(f"Result: {result}")
    
    # Test 4: Partial update
    print("\nTest 4: Partial update")
    result = update_status_block(
        client=client,
        agent_id=agent.id,
        status_data={
            "action": "Running"  # Should preserve other fields
        }
    )
    print(f"Result: {result}")
    
    # Test 5: Update with numbers
    print("\nTest 5: Update with numbers")
    result = update_status_block(
        client=client,
        agent_id=agent.id,
        status_data={
            "health": 100,
            "current_action": "Idle"
        }
    )
    print(f"Result: {result}")
    
    # Test 6: Read final state
    print("\nTest 6: Verify final state")
    status = get_memory_block(client, agent.id, "status")
    print(f"Final status: {status}")
    
    # Cleanup
    print("\nCleaning up...")
    client.agents.delete(agent.id)
    
if __name__ == "__main__":
    test_status_updates() 