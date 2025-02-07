from letta_client import Letta
from letta_templates.npc_utils_v2 import upsert_group_member
import json

def test_upsert():
    client = Letta()
    agent_id = "test_agent_id"  # Replace with real agent ID
    
    # Test 1: First interaction
    print("\nTest 1: First interaction")
    result = upsert_group_member(
        client,
        agent_id,
        "player_123",
        {
            "name": "greggytheegg",
            "is_present": True,
            "notes": "Asked about directions"
        }
    )
    print(f"Result: {result}")
    
    # Test 2: Backend updates appearance
    print("\nTest 2: Backend updates appearance")
    result = upsert_group_member(
        client,
        agent_id,
        "player_123",
        {
            "appearance": "Wearing a hamburger hat",
            "health_status": "healthy"
        }
    )
    print(f"Result: {result}")
    
    # Test 3: Player leaves
    print("\nTest 3: Player leaves")
    result = upsert_group_member(
        client,
        agent_id,
        "player_123",
        {
            "is_present": False
        }
    )
    print(f"Result: {result}")
    
    # Print final state
    agent = client.agents.retrieve(agent_id)
    block = next(b for b in agent.memory.blocks if b.label == "group_members")
    print("\nFinal state:")
    print(json.dumps(json.loads(block.value), indent=2))

if __name__ == "__main__":
    test_upsert() 