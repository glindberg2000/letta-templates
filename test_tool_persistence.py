import os
from dotenv import load_dotenv
from letta_templates.npc_tools import (
    TOOL_REGISTRY,
    perform_action,
    create_letta_client,
    create_personalized_agent_v3
)
from letta_templates.npc_utils_v2 import (
    update_status_block,
    update_group_block,
    upsert_group_member
)
import requests
import json

def test_tool_persistence():
    """Test if tools remain attached after various updates"""
    load_dotenv()
    
    print("\n=== Tool Persistence Test ===")
    
    # 1. Create client and basic agent
    client = create_letta_client()
    
    # Create required memory blocks
    memory_blocks = {
        "status": {
            "current_location": "",
            "state": "idle",
            "health": "healthy",
            "description": ""
        },
        "locations": {},
        "group_members": {"players": {}},
        "persona": {"name": "ToolTestAgent"}
    }
    
    print("\nCreating basic agent...")
    agent = create_personalized_agent_v3(
        name="ToolTestAgent",
        memory_blocks=memory_blocks,
        llm_type="openai",
        with_custom_tools=True,
        prompt_version="FULL"
    )
    agent_id = agent.id
    print(f"Created agent: {agent_id}")
    
    def verify_tools(stage=""):
        """Helper to verify tools are still attached"""
        tools = client.agents.tools.list(agent_id=agent_id)
        print(f"\nTools after {stage}:")
        for tool in tools:
            print(f"- {tool.name}")
        
        # Test perform_action to verify functionality
        print(f"\nTesting perform_action after {stage}...")
        try:
            result = perform_action("jump")
            print(f"Tool test result: {result}")
        except Exception as e:
            print(f"Tool test failed: {e}")
    
    # Initial tool check
    verify_tools("initial setup")
    
    # Test 1: Status Update
    print("\n=== Test 1: Status Update ===")
    status_update = {
        "current_location": "test_room",
        "state": "idle",
        "health": "healthy",
        "description": "Standing in test room"
    }
    update_status_block(client, agent_id, status_update)
    print("Status updated")
    verify_tools("status update")
    
    # Test 2: Group Update
    print("\n=== Test 2: Group Update ===")
    group_update = {
        "players": {
            "test_player_1": {
                "name": "TestPlayer",
                "is_present": True,
                "health": "healthy",
                "appearance": "Default appearance",
                "last_seen": "now"
            }
        }
    }
    update_group_block(client, agent_id, group_update)
    print("Group updated")
    verify_tools("group update")
    
    # Test 3: Multiple Rapid Updates
    print("\n=== Test 3: Multiple Rapid Updates ===")
    for i in range(3):
        status_update["description"] = f"Update test #{i}"
        update_status_block(client, agent_id, status_update)
        print(f"Rapid status update #{i} complete")
    verify_tools("multiple rapid updates")
    
    # Test 4: Group Member Update
    print("\n=== Test 4: Group Member Update ===")
    upsert_group_member(
        client,
        agent_id,
        "test_player_2",
        {
            "name": "TestPlayer2",
            "is_present": True,
            "health": "healthy",
            "appearance": "Test appearance",
            "last_seen": "now"
        }
    )
    print("Group member upserted")
    verify_tools("group member update")

def test_put_vs_patch_tool_retention():
    """Test if PUT requests clear tools while PATCH retains them"""
    load_dotenv()
    
    print("\n=== Testing PUT vs PATCH Tool Retention ===")
    
    # Setup
    client = create_letta_client()
    
    # Create required memory blocks
    memory_blocks = {
        "status": {
            "current_location": "",
            "state": "idle",
            "health": "healthy",
            "description": ""
        },
        "locations": {},
        "group_members": {"players": {}},
        "persona": {"name": "ToolTestAgent"}
    }
    
    # Create test agent
    print("\nCreating test agent...")
    agent = create_personalized_agent_v3(
        name="ToolTestAgent",
        memory_blocks=memory_blocks,
        llm_type="openai",
        with_custom_tools=True,
        prompt_version="FULL"
    )
    agent_id = agent.id
    print(f"Created agent: {agent_id}")
    
    def count_tools():
        tools = client.agents.tools.list(agent_id=agent_id)
        return len(tools)
    
    # Get initial tool count
    initial_tools = count_tools()
    print(f"\nInitial tool count: {initial_tools}")
    
    # Test 1: PUT update
    print("\n=== Test 1: PUT Update ===")
    base_url = os.getenv('LETTA_BASE_URL', 'http://localhost:8283')
    headers = {
        'Authorization': f'Bearer {os.getenv("LETTA_API_KEY")}',
        'Content-Type': 'application/json'
    }
    
    put_response = requests.put(
        f"{base_url}/v1/agents/{agent_id}/core_memory/blocks/status",
        headers=headers,
        json={
            "value": json.dumps({
                "current_location": "test_room",
                "state": "exploring",
                "health": "healthy",
                "description": "Testing PUT update"
            })
        }
    )
    print(f"PUT Response: {put_response.status_code}")
    if put_response.status_code != 200:
        print(f"PUT Error: {put_response.text}")
    
    tools_after_put = count_tools()
    print(f"Tools after PUT: {tools_after_put}")
    
    # Test 2: PATCH update
    print("\n=== Test 2: PATCH Update ===")
    patch_response = requests.patch(
        f"{base_url}/v1/agents/{agent_id}/core_memory/blocks/status",
        headers=headers,
        json={
            "value": json.dumps({
                "current_location": "test_room",
                "state": "exploring",
                "health": "healthy",
                "description": "Testing PATCH update"
            })
        }
    )
    print(f"PATCH Response: {patch_response.status_code}")
    if patch_response.status_code != 200:
        print(f"PATCH Error: {patch_response.text}")
    
    tools_after_patch = count_tools()
    print(f"Tools after PATCH: {tools_after_patch}")
    
    # Summary
    print("\n=== Results ===")
    print(f"Initial tools: {initial_tools}")
    print(f"After PUT: {tools_after_put}")
    print(f"After PATCH: {tools_after_patch}")

def test_client_update_method():
    """Test what HTTP method client.agents.core_memory.modify_block actually uses"""
    load_dotenv()
    
    print("\n=== Testing Client Update Method ===")
    
    # Setup
    client = create_letta_client()
    
    # Create required memory blocks
    memory_blocks = {
        "status": {
            "current_location": "",
            "state": "idle",
            "health": "healthy",
            "description": ""
        },
        "locations": {},
        "group_members": {"players": {}},
        "persona": {"name": "ToolTestAgent"}
    }
    
    # Create test agent
    print("\nCreating test agent...")
    agent = create_personalized_agent_v3(
        name="ToolTestAgent",
        memory_blocks=memory_blocks,
        llm_type="openai",
        with_custom_tools=True,
        prompt_version="FULL"
    )
    agent_id = agent.id
    print(f"Created agent: {agent_id}")
    
    # Enable debug logging to see HTTP method
    import logging
    import http.client
    http.client.HTTPConnection.debuglevel = 1
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True
    
    # Test client.agents.core_memory.modify_block
    print("\nTesting client.agents.core_memory.modify_block...")
    status_update = {
        "current_location": "test_room",
        "state": "exploring",
        "health": "healthy",
        "description": "Testing client update method"
    }
    
    response = client.agents.core_memory.modify_block(
        agent_id=agent_id,
        block_label="status",
        value=json.dumps(status_update)
    )
    print(f"Update response: {response}")

if __name__ == "__main__":
    # test_tool_persistence()  # Comment out original test
    test_put_vs_patch_tool_retention()  # Run new test
    test_client_update_method() 