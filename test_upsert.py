from letta_templates.npc_utils_v2 import upsert_group_member, get_memory_block
from letta_client import Letta
from datetime import datetime
import json

# Create client
client = Letta(base_url="http://192.168.2.16:8283")

# Get or create agent (you can get this from the quickstart test output)
agent_id = "agent-a58d1e0f-ce76-4bc2-8ff7-4dfcaca30d82"

# Test 1: Add player as present
print("\nTest 1: Adding present player")
result = upsert_group_member(
    client,
    agent_id,
    "player_1738969730",
    {
        "name": "greggytheegg",
        "is_present": True,
        "health_status": "healthy",
        "last_seen": datetime.now(),
        "last_location": "Main Plaza",
        "notes": "First login."
    }
)

print("\nResult:", result)
print("\nBlock state after adding present player:")
agent = client.agents.retrieve(agent_id)
block = next(b for b in agent.memory.blocks if b.label == "group_members")
print(json.dumps(json.loads(block.value), indent=2)) 