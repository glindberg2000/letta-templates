import os
from dotenv import load_dotenv
import json
import time
import argparse
from typing import Optional, Any
import sys
from letta_templates.npc_tools import (
    TOOL_REGISTRY,
    MINIMUM_PROMPT,
    BASE_PROMPT,
    SOCIAL_AWARENESS_PROMPT,
    GROUP_AWARENESS_PROMPT,
    LOCATION_AWARENESS_PROMPT,
    TOOL_INSTRUCTIONS,
    navigate_to,
    navigate_to_coordinates,
    perform_action,
    examine_object,
    test_echo,
    update_tools,
    create_personalized_agent_v3,
    create_letta_client
)
from letta_templates.npc_test_data import DEMO_BLOCKS
from letta_templates.npc_utils_v2 import (
    print_response,
    extract_message_from_response,
    retry_test_call,
    extract_agent_response,
    update_status_block,
    update_group_block,
    upsert_group_member
)
from letta_templates.npc_prompts import (
    STATUS_UPDATE_MESSAGE,
    GROUP_UPDATE_MESSAGE
)

import requests
import asyncio
import logging
import inspect
from textwrap import dedent
from letta_client import (
    EmbeddingConfig,
    LlmConfig as LLMConfig,
    Memory,
    Block,
    Tool,
    ToolCallMessage,
    ToolReturnMessage,
    ReasoningMessage,
    Message,
    MessageCreate,
    Letta
)
from datetime import datetime

# Load environment variables (keeps your custom server URL)
load_dotenv()

BASE_TOOLS = {
    "send_message",
    "conversation_search",
    "archival_memory_insert",
    "archival_memory_search",
    "core_memory_append",
    "core_memory_replace"
}

def print_agent_details(client, agent_id, stage=""):
    """
    Print detailed information about an agent's configuration and memory.
    
    Args:
        client: Letta client instance
        agent_id (str): ID of the agent to inspect
        stage (str, optional): Description of the current stage (e.g., "INITIAL STATE", "AFTER UPDATE")
    
    Example:
        >>> print_agent_details(client, agent.id, "AFTER PERSONA UPDATE")
        
        === Agent Details AFTER PERSONA UPDATE ===
        Agent ID: agent-123
        Name: RobloxHelper
        Description: A Roblox development assistant
        
        Memory Blocks:
        Block: human
        ID: block-456
        Value: Name: Bob
              Role: Game Developer
        Limit: 5000
        --------------------------------------------------
    """
    print(f"\n=== Agent Details {stage} ===")
    
    # Get agent configuration using new API
    agent = client.agents.retrieve(agent_id)
    print(f"Agent ID: {agent.id}")
    print(f"Name: {agent.name}")
    print(f"Description: {agent.description}")
    
    # Print system prompt
    print("\nSystem Prompt:")
    print(f"{agent.system}")
    print("-" * 50)
    
    # Get memory configuration
    memory = client.memory.retrieve(agent_id)
    print("\nMemory Blocks:")
    for block in memory.blocks:
        print(f"\nBlock: {block.label}")
        print(f"ID: {block.id}")
        print(f"Value: {block.value}")
        print(f"Limit: {block.limit}")
        print("-" * 50)

def update_agent_persona(client, agent_id: str, blocks: dict):
    """Update an agent's memory blocks using new API."""
    memory = client.memory.retrieve(agent_id)
    for block in memory.blocks:
        if block.label in blocks:
            print(f"\nUpdating {block.label} block:")
            print(f"Old value: {block.value}")
            print(f"New value: {blocks[block.label]}")
            # Update using new API
            client.agents.core_memory.blocks.update(
                agent_id=agent_id,
                block_label=block.label,
                value=blocks[block.label]
            )

def create_letta_client():
    """Create Letta client instance"""
    base_url = os.getenv("LETTA_BASE_URL", "http://localhost:8283")
    print("\nLetta Quickstart Configuration:")
    print(f"Base URL: {base_url}")
    print("-" * 50 + "\n")
    return Letta(base_url=base_url)  # Use new Letta client

def run_quick_test(client, npc_id="test-npc-1", user_id="test-user-1"):
    """Run test sequence with identifiable messages."""
    print(f"\nRunning duplicate detection test...")
    print(f"NPC ID: {npc_id}")
    print(f"User ID: {user_id}")
    print("-" * 50)
    
    # Normal messages with clear sequence numbers
    test_sequence = [
        "TEST_MSG_1: Starting sequence",
        "TEST_MSG_2: Checking timing",
        "TEST_MSG_3: Almost ready",
        "TEST_MSG_4: Now testing rapid messages"
    ]
    
    for i, message in enumerate(test_sequence, 1):
        print(f"\nSending message {i}...")
        response = client.send_message(
            npc_id=npc_id,
            participant_id=user_id,
            message=message
        )
        if response:
            print(f"Response: {response['parsed_message']}")
            print(f"Duration: {response['duration']:.3f}s")
        time.sleep(1.0)  # Clear gap between normal messages
    
    # Rapid messages with identical content
    print("\nSending rapid messages...")
    rapid_msg = "RAPID_TEST_MESSAGE_PLEASE_LOG_ME"
    
    for i in range(3):
        print(f"\nRapid message {i+1}...")
        client.send_message(
            npc_id=npc_id,
            participant_id=user_id,
            message=rapid_msg
        )
        time.sleep(0.1)  # Very short delay
    
    print("\nTest complete! Showing full history:")
    client.print_conversation_history()

def get_or_create_tool(client, tool_name: str, tool_func=None, update_existing: bool = False):
    """Get existing tool or create if needed."""
    # List all tools
    tools = client.tools.list()
    
    # During testing, always create new tools
    if tool_func:
        print(f"Creating new tool: {tool_name}")
        return client.tools.create(tool_func, name=tool_name)
    else:
        raise ValueError(f"Tool {tool_name} not found and no function provided to create it")

def cleanup_agents(client, name_prefix: str):
    """Clean up any existing agents with our prefix using new API"""
    print(f"\nCleaning up existing agents with prefix: {name_prefix}")
    try:
        agents = client.agents.list()
        for agent in agents:
            if agent.name.startswith(name_prefix):
                print(f"Deleting agent: {agent.name} ({agent.id})")
                client.agents.delete(agent.id)
    except Exception as e:
        print(f"Warning: Error during cleanup: {e}")

def create_group_tools():
    """Create tools for managing group interactions"""
    
    def group_navigate(users: list, destination: str):
        """Navigate multiple users to the same destination"""
        return {
            "status": "success",
            "message": f"Moving group to {destination}",
            "users": users
        }
    
    def group_gather(users: list, location: str):
        """Gather users at a specific location"""
        return {
            "status": "success",
            "message": f"Gathering group at {location}",
            "users": users
        }
    
    return {
        "group_navigate": group_navigate,
        "group_gather": group_gather
    }

def create_personalized_agent(
    name: str = "emma_assistant",
    client = None,
    use_claude: bool = False,
    overwrite: bool = False,
    with_custom_tools: bool = True,
    custom_registry = None,
    minimal_prompt: bool = True
):
    """Create a personalized agent with memory and tools"""
    logger = logging.getLogger('letta_test')
    
    if client is None:
        client = create_letta_client()
        
    # Clean up existing agents if overwrite is True
    if overwrite:
        cleanup_agents(client, name)
    
    # Add timestamp to name to avoid conflicts
    timestamp = int(time.time())
    unique_name = f"{name}_{timestamp}"
    
    # Format base prompt with assistant name
    base_system = BASE_PROMPT.format(assistant_name=name)
    
    # Use minimal prompt for testing if requested
    if minimal_prompt:
        logger.info(f"Using MINIMUM_PROMPT (minimal_prompt={minimal_prompt})")
        system_prompt = MINIMUM_PROMPT.format(assistant_name=name)
    else:
        logger.info(f"Using full prompt (minimal_prompt={minimal_prompt})")
        system_prompt = (
            base_system +
            "\n\n" + TOOL_INSTRUCTIONS +
            "\n\n" + SOCIAL_AWARENESS_PROMPT +
            "\n\n" + GROUP_AWARENESS_PROMPT +
            "\n\n" + LOCATION_AWARENESS_PROMPT
        )
    
    # Log what we're using
    logger.info("\nSystem prompt components:")
    if minimal_prompt:
        logger.info(f"Using MINIMUM_PROMPT: {len(system_prompt)} chars")
    else:
        logger.info(f"1. Base system: {len(base_system)} chars")
        logger.info(f"2. TOOL_INSTRUCTIONS: {len(TOOL_INSTRUCTIONS)} chars")
        logger.info(f"3. SOCIAL_AWARENESS_PROMPT: {len(SOCIAL_AWARENESS_PROMPT)} chars")
        logger.info(f"4. LOCATION_AWARENESS_PROMPT: {len(LOCATION_AWARENESS_PROMPT)} chars")
    
    # Create configs first
    llm_config = LLMConfig(
        model="gpt-4o-mini",
        model_endpoint_type="openai",
        model_endpoint="https://api.openai.com/v1",
        context_window=128000,
    )
    
    embedding_config = EmbeddingConfig(
        embedding_endpoint_type="openai",
        embedding_endpoint="https://api.openai.com/v1",
        embedding_model="text-embedding-ada-002",
        embedding_dim=1536,
        embedding_chunk_size=300,
    )
    

    
    # Create memory blocks with consistent identity
    memory = BasicBlockMemory(
        blocks=[
            client.create_block(
                label="persona", 
                value=f"I am {name}, a friendly and helpful NPC guide. I know this world well and patiently help players explore. I love meeting new players, sharing my knowledge, and helping others in any way I can.",
                limit=2500
            ),
            client.create_block(
                label="group_members",
                value=json.dumps({
                    "members": {
                        "player123": {
                            "name": "Alice",
                            "appearance": "Wearing a red hat and blue shirt", 
                            "last_location": "Main Plaza",
                            "last_seen": "2024-01-06T22:30:45Z",
                            "notes": "Interested in exploring the garden"
                        },
                        "bob123": {  # Match the ID we use in test
                            "name": "Bob",
                            "appearance": "Tall with green jacket",
                            "last_location": "Cafe",
                            "last_seen": "2024-01-06T22:35:00Z", 
                            "notes": "Looking for Pete's Stand"
                        },
                        "charlie123": {
                            "name": "Charlie",
                            "appearance": "Wearing a blue cap",
                            "last_location": "Main Plaza",
                            "last_seen": "2024-01-06T22:35:00Z",
                            "notes": "New to the area"
                        }
                    },
                    "summary": "Alice and Charlie are in Main Plaza, with Alice interested in the garden. Bob is at the Cafe looking for Pete's Stand. Charlie is new and exploring the area.",
                    "updates": ["Alice arrived at Main Plaza", "Bob moved to Cafe searching for Pete's Stand", "Charlie joined and is exploring Main Plaza"],
                    "last_updated": "2024-01-06T22:35:00Z"
                }),
                limit=2000
            ),
            client.create_block(
                label="locations",
                value=json.dumps({
                    "known_locations": [
                        {
                            "name": "Pete's Stand",
                            "description": "A friendly food stand run by Pete",
                            "coordinates": [-12.0, 18.9, -127.0],
                            "slug": "petes_stand"
                        },
                        {
                            "name": "Town Square",
                            "description": "Central gathering place with fountain", 
                            "coordinates": [45.2, 12.0, -89.5],
                            "slug": "town_square"
                        },
                        {
                            "name": "Market District",
                            "description": "Busy shopping area with many vendors",
                            "coordinates": [-28.4, 15.0, -95.2],
                            "slug": "market_district"
                        },
                        {
                            "name": "Secret Garden",
                            "description": "A hidden garden with rare flowers",
                            "coordinates": [15.5, 20.0, -110.8],
                            "slug": "secret_garden"
                        }
                    ]
                }),
                limit=1500
            ),
            client.create_block(
                label="status",
                value="You are currently standing idle in the Town Square. You previously haven't moved from this spot. From here, You can see both the bustling Market District and Pete's friendly food stand in the distance. The entire area is part of the Town Square region.",
                limit=500
            ),
            client.create_block(
                label="journal", 
                value="",  # Empty string to start
                limit=2500
            )
        ]
    )

    # Log what we're using
    logger.info("\nSystem prompt components:")
    if minimal_prompt:
        logger.info(f"Using MINIMUM_PROMPT: {len(system_prompt)} chars")
    else:
        logger.info(f"1. Base system: {len(base_system)} chars")
        logger.info(f"2. TOOL_INSTRUCTIONS: {len(TOOL_INSTRUCTIONS)} chars")
        logger.info(f"3. SOCIAL_AWARENESS_PROMPT: {len(SOCIAL_AWARENESS_PROMPT)} chars")
        logger.info(f"4. LOCATION_AWARENESS_PROMPT: {len(LOCATION_AWARENESS_PROMPT)} chars")
    
    # Log params in a readable way
    print("\nCreating agent with params:")
    print(f"Name: {unique_name}")
    print(f"System prompt length: {len(system_prompt)} chars")
    print("Memory blocks:")
    for block in memory.blocks:
        print(f"- {block.label}: {len(block.value)} chars")
    print("\nConfigs:")
    print(f"LLM: {llm_config.model} via {llm_config.model_endpoint_type}")
    print(f"Embeddings: {embedding_config.embedding_model}")
    print(f"Include base tools: {False}")
    
    # Create agent first
    agent = client.agents.create(  # Updated to use new API
        name=unique_name,
        embedding_config=embedding_config,
        llm_config=llm_config,
        memory=memory,
        system=system_prompt,
        include_base_tools=False,  # We'll add tools manually
        description="A Roblox development assistant"
    )
    
    # Add selected base tools first
    base_tools = [
        "send_message",
        "conversation_search",
        "archival_memory_search",  # Read from memory
        "archival_memory_insert"   # Write to memory
    ]
    
    # Get existing tools
    existing_tools = {t.name: t.id for t in client.tools.list()}
    
    # Add base tools
    for tool_name in base_tools:
        if tool_name in existing_tools:
            print(f"Adding base tool: {tool_name}")
            client.agents.tools.attach(  # Updated to use new API
                agent_id=agent.id,
                tool_id=existing_tools[tool_name]
            )
    
    # Create and attach custom tools
    print("\nSetting up custom tools:")
    # Then register other tools
    for name, tool_info in TOOL_REGISTRY.items():
        try:
            # Check if tool already exists
            if name in existing_tools:
                print(f"Tool {name} already exists (ID: {existing_tools[name]})")
                tool_id = existing_tools[name]
            else:
                print(f"Creating tool: {name}")
                tool = client.tools.create(tool_info['function'], name=name)
                print(f"Tool created with ID: {tool.id}")
                tool_id = tool.id
                
            # Attach tool to agent
            print(f"Attaching {name} to agent...")
            client.agents.tools.attach(  # Updated to use new API
                agent_id=agent.id,
                tool_id=tool_id
            )
            print(f"Tool {name} attached to agent {agent.id}")
            
        except Exception as e:
            print(f"Error with tool {name}: {e}")
            raise
    
    return agent

def validate_environment():
    """Validate required environment variables are set."""
    required_vars = {
        'claude': [
            'LETTA_LLM_ENDPOINT',
            'LETTA_LLM_ENDPOINT_TYPE',
            'LETTA_LLM_MODEL',
            'ANTHROPIC_API_KEY'
        ],
        'openai': [
            'OPENAI_API_KEY'
        ]
    }

    def check_vars(vars_list):
        missing = [var for var in vars_list if not os.getenv(var)]
        return missing

    print("\nValidating environment variables...")
    
    # Use default URL if not set
    if not os.getenv('LETTA_BASE_URL'):
        os.environ['LETTA_BASE_URL'] = "http://localhost:8283"
        print("Using default base URL: http://localhost:8283")

    # Check provider-specific variables
    provider = os.getenv('LETTA_LLM_ENDPOINT_TYPE', 'openai')
    missing_provider = check_vars(required_vars[provider])
    if missing_provider:
        print(f"Missing {provider} variables: {', '.join(missing_provider)}")
        return False

    print("Environment validation successful!")
    return True

def test_agent_chat(client, agent_id: str, llm_type: str) -> bool:
    try:
        test_message = "Navigate to the stand"
        print(f"\nSending test message: '{test_message}'")
        response = client.agents.messages.create(  # Updated to use new API
            agent_id=agent_id,
            messages=[MessageCreate(
                role="user",
                content=test_message
            )]
        )
        print("\nRaw response:", response)
        print_response(response)
        return True
    except Exception as e:
        print(f"\nError testing agent chat: {e}")
        return False

def test_custom_tools(client, agent_id: str):
    try:
        test_message = "Please examine the treasure chest"
        print(f"\nSending test message: '{test_message}'")
        response = client.agents.messages.create(  # Updated to use new API
            agent_id=agent_id,
            messages=[MessageCreate(
                role="user",
                content=test_message
            )]
        )
        print_response(response)
        return True
    except Exception as e:
        print(f"\nError testing custom tools: {e}")
        return False

def cleanup_test_tools(client, prefixes: list = ["examine_object", "navigate_to", "perform_action"]):
    """Clean up old test tools."""
    tools = client.tools.list()
    cleaned = 0
    
    print(f"\nCleaning up test tools with prefixes: {prefixes}")
    for tool in tools:
        if any(tool.name == prefix or tool.name.startswith(f"{prefix}_") for prefix in prefixes):
            try:
                client.tools.delete(tool.id)
                cleaned += 1
                print(f"Deleted tool: {tool.name} (ID: {tool.id})")
            except Exception as e:
                print(f"Failed to delete {tool.name}: {e}")
    
    print(f"Cleaned up {cleaned} test tools")

def test_tool_update(client, agent_id: str):
    """Test updating a tool's behavior."""
    print("\nTesting tool update...")
    
    test_sequence = [
        # Initial examination
        ("Examine the treasure chest", None),
        ("", "Initial observation: The chest appears to be wooden."),  # System detail
        
        # Update tool
        (None, "Updating examination capabilities..."),  # System message
    ]
    
    for message, system_update in test_sequence:
        if message:
            print(f"\nSending user message: '{message}'")
            response = client.agents.messages.create(
                agent_id=agent_id,
                message=message,
                role="user"
            )
            print_response(response)
        
        if system_update:
            if system_update == "Updating examination capabilities...":
                # Update the tool using our npc_tools version
                print("\nUpdating examine tool...")
                tools = client.tools.list()
                for tool in tools:
                    if tool.name == "examine_object":
                        client.tools.delete(tool.id)
                new_tool = client.tools.create(examine_object, name="examine_object")
                print(f"Created new tool: {new_tool.id}")
            else:
                # Regular system update
                print(f"\nSending system update: '{system_update}'")
                response = client.agents.messages.create(
                    agent_id=agent_id,
                    message=system_update,
                    role="system"
                )
                print_response(response)
            
        time.sleep(1)

def ensure_locations_block(client, agent_id):
    """Ensure locations block has required locations"""
    agent = client.agents.retrieve(agent_id)
    # Update to use blocks list instead of get_block
    locations_block = next(b for b in agent.memory.blocks if b.label == "locations")
    locations_data = json.loads(locations_block.value)
    
    required_locations = {
        "Main Plaza": {
            "name": "Main Plaza",
            "description": "Central gathering place with fountain",
            "coordinates": [45.2, 12.0, -89.5],
            "slug": "main_plaza"
        },
        "Town Square": {
            "name": "Town Square",
            "description": "Busy central area",
            "coordinates": [0.0, 0.0, 0.0],
            "slug": "town_square"
        }
    }
    
    # Update locations if needed
    locations_data["known_locations"] = [
        loc for loc in locations_data["known_locations"] 
        if loc["name"] not in required_locations
    ] + list(required_locations.values())
    
    # Update using blocks.modify
    client.blocks.modify(
        block_id=locations_block.id,
        value=json.dumps(locations_data)
    )

def test_navigation(client, agent_id: str):
    """Test NPC's navigation abilities"""
    print("\nTesting navigation functionality...")
    
    scenarios = [
        # Direct navigation
        ("User", "Take me to Pete's Stand"),
        
        # Navigation with coordinates
        ("User", "Navigate to coordinates [-12.0, 18.9, -127.0]"),
        
        # Nearby location
        ("User", "Let's go to the Market District")
    ]
    
    for speaker, message in scenarios:
        try:
            print(f"\n{speaker} says: {message}")
            response = retry_test_call(  # Use retry helper
                client.agents.messages.create,  # Updated to new API
                agent_id=agent_id,
                messages=[MessageCreate(
                    role="user",
                    content=message,
                    name=speaker
                )],
                max_retries=3,
                delay=2
            )
            print("\nResponse:")
            result = extract_agent_response(response)
            print(f"\nFinal message: {result['message']}")
            
            # Handle navigation tool calls
            for tool_call in result['tool_calls']:
                if tool_call['tool'] == 'navigate_to':
                    print(f"Navigation requested to: {tool_call['args']['destination_slug']}")
            
            # Give time for navigation
            time.sleep(2)
            
        except Exception as e:
            print(f"Error in navigation test: {e}")
            continue  # Try next scenario

def test_actions(client, agent_id: str):
    """Test NPC's ability to perform actions"""
    print("\nTesting action functionality...")
    
    print("\n=== Test Setup ===")
    print("1. Ensuring locations block has required locations...")
    ensure_locations_block(client, agent_id)
    
    print("\n=== Test Sequence ===")
    print("1. Testing basic emotes")
    print("2. Testing archival storage")
    print("3. Testing archival retrieval")
    
    scenarios = [
        # Check archives for history to add to notes
        ("System", """A new player Alice (ID: alice_123) has joined and is in the group. 
        1. FIRST use archival_memory_search with:
           - query='Player profile for alice_123'
           - page=0 (first page)
           - start=0 (from beginning)
        2. ONLY IF search returns results, use group_memory_append to add the found history as a note for Alice
        3. Wave hello and welcome her"""),
        
        # Update location
        ("System", """Alice is exploring the garden. 
        1. Use group_memory_replace to update her current location note
        2. Send a friendly message about the garden"""),
        
        # Just archive before removal
        ("System", """Alice is leaving. 
        1. Wave goodbye
        2. Use archival_memory_insert to save her profile with format:
           "Player profile for alice_123: Last seen <timestamp>. Notes: <current notes>"
        3. Send a farewell message""")
    ]
    
    for i, (speaker, message) in enumerate(scenarios, 1):
        print(f"\n=== Test Step {i} ===")
        print(f"Speaker: {speaker}")
        print(f"Message: {message}")
        
        try:
            print("\nSending message...")
            response = client.agents.messages.create(  # Updated to new API
                agent_id=agent_id,
                messages=[MessageCreate(
                    role="system",
                    content=message,
                    name=speaker
                )]
            )
            print("\nResponse:")
            print_response(response)
            time.sleep(3)
            
        except Exception as e:
            print(f"Error in test step {i}: {e}")
            continue

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', default='TestGuide')
    parser.add_argument('--llm-type', choices=['openai'], default='openai')
    parser.add_argument('--keep', action='store_true')
    parser.add_argument('--overwrite', action='store_true')
    parser.add_argument('--custom-tools', action='store_true')
    parser.add_argument('--continue-on-error', action='store_true')
    parser.add_argument('--minimal-test', action='store_true')
    parser.add_argument('--test-type', choices=[
        'all', 'base', 'notes', 'social', 'status', 
        'group', 'persona', 'journal', 'navigation', 'actions',
        'upsert'
    ], default='all')
    parser.add_argument(
        '--prompt',
        choices=['DEEPSEEK', 'GPT01', 'MINIMUM', 'FULL'],
        default='FULL'
    )
    return parser.parse_args()

def get_api_url():
    """Get FastAPI chat endpoint URL matching Roblox config"""
    base_url = os.getenv("LETTA_API_URL", "https://roblox.ella-ai-care.com")
    return f"{base_url}/letta/v1/chat/v2"

def get_test_npc():
    """Get Pete's NPC ID and verify tools"""
    try:
        # Get NPC info
        response = requests.get("http://localhost:7777/api/npcs?game_id=61")
        response.raise_for_status()
        npcs = response.json()["npcs"]
        
        # Find Pete and verify abilities
        pete = next((npc for npc in npcs 
                    if npc["npcId"] == "693ec89f-40f1-4321-aef9-5aac428f478b"), None)
        
        if pete:
            print(f"\nPete's abilities: {pete.get('abilities', [])}")
            
        return "693ec89f-40f1-4321-aef9-5aac428f478b"
    except Exception as e:
        print(f"\nWarning: Could not fetch NPC info: {e}")
        return "693ec89f-40f1-4321-aef9-5aac428f478b"

def send_chat_message(message: str, agent_id: str, use_api: bool = False, name: str = None) -> dict:
    """Send chat message either directly or through API"""
    if use_api:
        print("\n=== Using FastAPI Endpoint ===")
        
        # Use real NPC ID
        npc_id = get_test_npc()
        
        request = {
            "npc_id": npc_id,
            "participant_id": "test_user_1",
            "message": message,
            "context": {
                "participant_type": "player",
                "participant_name": name or "TestUser"
            }
        }
        
        print(f"\nRequest URL: {get_api_url()}")
        print(f"Request Body: {json.dumps(request, indent=2)}")

        try:
            response = requests.post(
                get_api_url(),
                json=request,
                headers={"Content-Type": "application/json"},
                timeout=30  # Increase timeout for tool calls
            )
            print(f"\nResponse Status: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Response Body: {response.text[:1000]}")  # First 1000 chars
            
            response.raise_for_status()
            data = response.json()
            return data
        except requests.exceptions.HTTPError as e:
            print(f"\nHTTP Error: {e}")
            print(f"Response Body: {e.response.text}")
            raise
        except Exception as e:
            print(f"\nError: {type(e).__name__}: {str(e)}")
            raise
    else:
        print("\n=== Using Direct Letta Connection ===")
        return client.agents.send_message(
            agent_id=agent_id,
            role="user",
            message=message,
            name=name
        )

def parse_and_validate_response(response: dict):
    """Validate response matches expected format"""
    print("\nValidating response format...")
    
    # Check required fields
    required = ["message", "metadata"]
    missing = [f for f in required if f not in response]
    if missing:
        print(f"Warning: Missing required fields: {missing}")
    
    # Check action format if present
    if "action" in response:
        action = response["action"]
        if action.get("type") == "navigate":
            coords = action.get("data", {}).get("coordinates")
            if coords:
                print(f"Navigation coordinates: ({coords['x']}, {coords['y']}, {coords['z']})")

    return response

def test_multi_user_conversation(client, agent_id: str):
    """Test conversation with multiple named users"""
    print("\nTesting multi-user conversation...")
    
    # Define the test conversation
    conversation = [
        ("Alice", "Hi, I'm looking for Pete's Stand."),
        ("Bob", "Me too! Can you help us both get there?"),
        ("Charlie", "I know where it is, it's near the fountain!"),
        ("Alice", "Great! Can you guide us there?"),
        # Add more complex interactions
        ("Bob", "What's on the menu at Pete's?"),
        ("Charlie", "I recommend the burger!"),
        ("Alice", "Can we all sit together when we get there?")
    ]
    
    # Process each message in the conversation
    for name, message in conversation:
        print(f"\n{name} says: {message}")
        response = client.agents.messages.create(
            agent_id=agent_id,
            message=message,
            role="user",
            name=name
        )
        
        print("\nResponse:")
        print_response(response)
        time.sleep(1)

async def handle_multi_user_requests(client, agent_id: str, requests: list):
    """Handle multiple user requests in parallel"""
    async def process_request(name, message):
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as pool:
            response = await loop.run_in_executor(
                pool,
                client.agents.messages.create,
                agent_id,
                message,
                "user",
                name
            )
            return name, response
    
    tasks = [
        process_request(name, message) 
        for name, message in requests
    ]
    
    responses = await asyncio.gather(*tasks)
    return dict(responses)

# Usage in test
async def test_parallel_multi_user():
    requests = [
        ("Alice", "Where's Pete's Stand?"),
        ("Bob", "Can you guide me there?"),
        ("Charlie", "What's on the menu?")
    ]
    
    responses = await handle_multi_user_requests(client, agent_id, requests)
    for name, response in responses.items():
        print(f"\n{name}'s response:")
        print_response(response)

def test_agent_identity(client, agent_id: str):
    """Test agent's understanding of its identity."""
    print("\nTesting agent identity understanding...")
    
    try:
        # Test basic identity
        print("\nAlice asks: Hi! What's your name?")
        response = client.agents.messages.create(
            agent_id=agent_id,
            messages=[
                MessageCreate(
                    role="user",
                    content="Hi! What's your name?",
                    name="Alice"
                )
            ]
        )
        print("\nResponse:")
        print_response(response)
        
        # Test role understanding
        print("\nBob asks: What kind of assistant are you?")
        response = client.agents.messages.create(
            agent_id=agent_id,
            messages=[
                MessageCreate(
                    role="user",
                    content="What kind of assistant are you?",
                    name="Bob"
                )
            ]
        )
        print("\nResponse:")
        print_response(response)
        
    except Exception as e:
        print(f"Error in test_agent_identity: {e}")
        raise

def test_social_awareness(client, agent_id: str):
    """Additional tests for social awareness and movement"""
    print("\nTesting social awareness and natural movement...")
    
    # Verify group_members block has required users
    agent = client.agents.retrieve(agent_id)
    group_block = next((b for b in agent.memory.blocks if b.label == "group_members"), None)
    if not group_block:
        print("❌ No group_members block found")
        return
        
    initial_block = json.loads(group_block.value)
    required_users = {"Alice", "Bob", "Charlie"}
    present_users = {member["name"] for member in initial_block["members"].values()}
    if not required_users.issubset(present_users):
        missing = required_users - present_users
        print(f"❌ Missing required users in group_members: {missing}")
        return
    print("✓ All required users present in group_members block")
    
    social_tests = [
        # Test direct addressing (should use [SILENCE])
        ("Alice", "Hey Bob, how was your weekend?"),
        ("Bob", "Great thanks Alice! The market was fun."),
        
        # Test conversation ending with movement
        ("Bob", "Thanks for the help, I need to go now!"),
        ("Alice", "Bye everyone!"),
        
        # Test staying quiet in private exchanges
        ("Charlie", "@Bob remember that thing we discussed earlier?"),
        ("Bob", "@Charlie yeah, let's talk about it later"),
        
        # Test natural movement after others leave
        ("System", "Bob and Alice have left the area.")
    ]
    
    for speaker, message in social_tests:
        print(f"\n{speaker} says: {message}")
        response = client.agents.messages.create(
            agent_id=agent_id,
            messages=[
                MessageCreate(
                    role="user",
                    content=message,
                    name=speaker
                )
            ]
        )
        print("\nResponse:")
        print_response(response)
        
        # Verify proper tool sequences
        tool_calls = []
        message_contents = []
        
        for msg in response.messages:
            if msg.message_type == "tool_call_message":
                tool = msg.tool_call
                tool_calls.append(tool)
                if tool.name == "send_message":
                    message_contents.append(json.loads(tool.arguments)["message"])
                
        # Verify proper goodbye sequences
        if any("goodbye" in msg.lower() for msg in message_contents):
            wave_found = any(
                t.name == "perform_action" and "wave" in t.arguments.lower() 
                for t in tool_calls
            )
            move_found = any(
                t.name == "navigate_to" for t in tool_calls
            )
            if wave_found and move_found:
                print("✓ Proper goodbye sequence (wave + move)")
            else:
                print("✗ Missing proper goodbye sequence")
                
        print(f"\nTool Calls: {json.dumps([t.name for t in tool_calls], indent=2)}")
        time.sleep(1)

def evaluate_response_with_gpt4(response_text: str, current_status: dict, message: str):
    """Evaluate NPC response using GPT-4o-mini"""
    try:
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        if not OPENAI_API_KEY:
            print("\nNo OpenAI API key found, using basic evaluation")
            return basic_evaluation(response_text, current_status)
            
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": "You evaluate NPC responses. Return only JSON."
                    },
                    {
                        "role": "user",
                        "content": f"""Evaluate this NPC response:
Current location: {current_status['current_location']}
Nearby locations: {', '.join(current_status['nearby_locations'])}
User message: {message}
NPC response: {response_text}

Return ONLY a JSON object like this:
{{
    "location_aware": true/false,
    "nearby_accurate": true/false,
    "contextually_appropriate": true/false,
    "explanation": "brief reason"
}}"""
                    }
                ],
                "temperature": 0.1
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            return json.loads(content)
        else:
            print(f"\nGPT-4 API error: {response.status_code}")
            return basic_evaluation(response_text, current_status)
            
    except Exception as e:
        print(f"\nGPT-4 evaluation failed: {str(e)}")
        return basic_evaluation(response_text, current_status)

def basic_evaluation(response_text: str, current_status: dict):
    """Basic fallback evaluation"""
    response_lower = response_text.lower()
    current_loc = current_status['location'].lower()
    
    return {
        "location_aware": current_loc in response_lower,
        "nearby_accurate": any(loc.lower() in response_lower for loc in current_status['nearby_locations']),
        "contextually_appropriate": True,  # Basic assumption
        "explanation": "Basic evaluation: Checked location and nearby mentions"
    }

def test_status_awareness(client, agent_id: str):
    """Test status awareness and updates."""
    print("\n=== Testing Status Awareness ===")
    
    try:
        # 1. Check initial status
        print("\n1. Initial Status Check:")
        agent = client.agents.retrieve(agent_id)
        status_block = next((b for b in agent.memory.blocks if b.label == "status"), None)
        print("Initial status:", status_block.value)
        
        # 2. Update to Town Square
        print("\n2. Updating to Town Square:")
        update_status_block(
            client=client,
            agent_id=agent_id,
            status_text="Location: Town Square | Action: Greeting visitors"
        )
        print("Status after update:", status_block.value)
        
        # Send system message to notify of status update
        print("\nSending status update notification...")
        response = client.agents.messages.create(
            agent_id=agent_id,
            messages=[MessageCreate(
                role="system",
                content=STATUS_UPDATE_MESSAGE
            )]
        )
        
        # 3. Ask about current location
        print("\n3. Asking about Town Square location:")
        question = "What are you doing right now?"
        print(f"Question: \"{question}\"")
        response = client.agents.messages.create(
            agent_id=agent_id,
            messages=[MessageCreate(
                role="user",
                content=question
            )]
        )
        print("NPC Response:")
        print_response(response)
        
        # Verify status hasn't changed
        agent = client.agents.retrieve(agent_id)
        status_block = next((b for b in agent.memory.blocks if b.label == "status"), None)
        print("Current status:", status_block.value)
        
        # 4. Update to Garden
        print("\n4. Updating to Garden:")
        update_status_block(
            client=client,
            agent_id=agent_id,
            status_text="Location: Garden | Action: Showing new players around"
        )
        print("Status after garden update:", status_block.value)
        
        # Send system message to notify of status update
        print("\nSending status update notification...")
        response = client.agents.messages.create(
            agent_id=agent_id,
            messages=[MessageCreate(
                role="system",
                content=STATUS_UPDATE_MESSAGE
            )]
        )
        
        # 5. Ask about garden
        print("\n5. Asking about Garden location:")
        question = "Where are you and what are you doing?"
        print(f"Question: \"{question}\"")
        response = client.agents.messages.create(
            agent_id=agent_id,
            messages=[MessageCreate(
                role="user",
                content=question
            )]
        )
        print("NPC Response:")
        print_response(response)
        
        # Final status check
        agent = client.agents.retrieve(agent_id)
        status_block = next((b for b in agent.memory.blocks if b.label == "status"), None)
        print("\nFinal status:", status_block.value)
        
    except Exception as e:
        print(f"Error in test_status_awareness: {e}")
        raise

def validate_agent_setup(client, agent_id: str):
    """Verify agent's system prompt, memory, and tools are correctly configured"""
    logger = logging.getLogger('letta_test')
    
    # Check required custom tools
    required_npc_tools = [
        "navigate_to",
        "navigate_to_coordinates",
        "perform_action", 
        "examine_object"
    ]
    
    tools = client.tools.list()
    agent_tools = []
    for tool in tools:
        try:
            client.agents.tools.attach(agent_id, tool.id)
            agent_tools.append(tool.name)
        except:
            pass
            
    missing_npc_tools = [t for t in required_npc_tools if t not in agent_tools]
    if missing_npc_tools:
        logger.error(f"❌ Missing required NPC tools: {', '.join(missing_npc_tools)}")
        logger.error("Agent validation failed - NPC tools not attached")
        return False
        
    logger.info("✓ All required NPC tools attached")
    return True

def test_group(client, agent_id: str):
    """Test group_members block updates"""
    print("\nTesting group_members block updates...")
    
    # Initial group state with only current members
    group_block = {
        "members": {
            "alice123": {
                "name": "Alice",
                "appearance": "Wearing a bright red dress with a golden necklace and carrying a blue handbag",
                "last_seen": "2024-01-06T22:30:45Z",
                "notes": ""
            }
        },
        "summary": "Current members: Alice",
        "updates": [
            "Alice joined the group",
        ]
    }
    
    # Update group block
    print("\nUpdating group block...")
    update_group_block(client, agent_id, group_block)
    
    # Test scenarios
    print("\nTesting group awareness...")
    scenarios = [
        ("Charlie", "Who's around right now?"),
        ("Charlie", "What is Alice wearing?"),
        ("Charlie", "Is anyone else here?")
    ]
    
    for speaker, message in scenarios:
        print(f"\n{speaker} says: {message}")
        response = client.agents.messages.create(
            agent_id=agent_id,
            messages=[MessageCreate(
                role="user",
                content=message,
                name=speaker
            )]
        )
        print("\nResponse:")
        print_response(response)
        
        # Print current group state after each interaction
        agent = client.agents.retrieve(agent_id)
        group_block = next(b for b in agent.memory.blocks if b.label == "group_members")
        print("\nCurrent group state:", group_block.value)

    # Print final state to verify both NPC and API updates
    print("\nFinal state:")
    agent = client.agents.retrieve(agent_id)
    block = next(b for b in agent.memory.blocks if b.label == "group_members")
    data = json.loads(block.value)
    
    # Print full block first
    print("\nFull block:")
    print(json.dumps(data, indent=2))
    
    # Verify fields
    greggytheegg = next((m for m in data["members"].values() if m["name"] == "greggytheegg"), None)
    if greggytheegg:
        print("\nVerifying fields:")
        print(f"is_present: {greggytheegg.get('is_present', 'MISSING')}")
        print(f"appearance: {greggytheegg.get('appearance', 'MISSING')}")
        print(f"last_location: {greggytheegg.get('last_location', 'MISSING')}")
        print(f"last_seen: {greggytheegg.get('last_seen', 'MISSING')}")
        print(f"notes: {greggytheegg.get('notes', 'MISSING')}")

def get_npc_prompt(name: str, persona: str):
    return f"""You are {name}, {persona}

Important guidelines:
- Always check who is nearby using the group_members block before interacting
- Don't address or respond to players who aren't in the members list
- If someone asks about a player who isn't nearby, mention that they're no longer in the area
- Keep track of who enters and leaves through the updates list
- ALWAYS check your status block for your current location and action
- When asked about your location or activity, read directly from your status block

Example:
If Alice asks "Bob, what's your favorite food?" but Bob isn't in members:
✓ Say: "Alice, Bob isn't nearby at the moment."
✗ Don't: Pretend Bob is still there or ignore Alice's question

Example status check:
If your status block says "Location: Garden | Action: Showing new players around":
✓ Say: "I'm in the Garden, showing new players around"
✗ Don't: Make up a different location or action
"""


def create_or_update_tool(client, tool_name: str, tool_func, verbose: bool = True) -> Any:
    """Create a new tool or update if it exists using new API."""
    if tool_name in BASE_TOOLS:
        raise ValueError(f"Cannot modify base tool: {tool_name}")

    try:
        existing_tools = {t.name: t.id for t in client.tools.list()}
        
        if tool_name in existing_tools:
            if verbose:
                print(f"\nDeleting old tool: {tool_name}")
                print(f"Tool ID: {existing_tools[tool_name]}")
            client.tools.delete(existing_tools[tool_name])
            
            if verbose:
                print(f"Creating new tool: {tool_name}")
            tool = client.tools.create(tool_func, name=tool_name)
            
            return tool
        else:
            if verbose:
                print(f"Creating new tool: {tool_name}")
            tool = client.tools.create(tool_func, name=tool_name)
            
            return tool
        
    except Exception as e:
        print(f"Error in create_or_update_tool for {tool_name}: {str(e)}")
        raise

def test_echo(message: str) -> str:
    """A simple test tool that echoes back the input with a timestamp.
    
    Args:
        message: The message to echo
    
    Returns:
        The same message with timestamp
    """
    timestamp = time.strftime('%H:%M:%S')
    return f"[TEST_ECHO_V3 @ {timestamp}] {message} (echo...Echo...ECHO!)"

def test_notes(client, agent_id: str):
    """Test player notes functionality."""
    print("\nTesting player notes functionality...")
    
    try:
        # Print initial group state
        print("\nInitial group state:")
        agent = client.agents.retrieve(agent_id)
        group_block = next((b for b in agent.memory.blocks if b.label == "group_members"), None)
        print(group_block.value if group_block else "(Empty)")
        
        scenarios = [
            # Test adding notes
            ("System", "Add note about Alice: Loves exploring the garden"),
            ("System", "Add note about Bob: Looking for Pete's Stand"),
            
            # Test updating notes
            ("System", "Update note about Alice: Now interested in crystal weapons"),
            
            # Verify memory
            ("System", "What do you remember about Alice?"),
            ("System", "What do you remember about Bob?")
        ]
        
        for speaker, message in scenarios:
            print(f"\n{speaker} says: {message}")
            response = client.agents.messages.create(
                agent_id=agent_id,
                messages=[
                    MessageCreate(
                        role="user",
                        content=message,
                        name=speaker
                    )
                ]
            )
            print("\nResponse:")
            print_response(response)
            
            # Check group updates
            agent = client.agents.retrieve(agent_id)
            group_block = next((b for b in agent.memory.blocks if b.label == "group_members"), None)
            print("\nCurrent group state:", group_block.value if group_block else "(Empty)")
            time.sleep(1)
            
    except Exception as e:
        print(f"Error in test_notes: {e}")
        raise

def test_npc_persona(client, agent_id: str):
    """Test NPC's ability to update its own persona memory."""
    print("\nTesting NPC persona updates...")
    
    # Test scenarios for personality and interests
    scenarios = [
        # Initial personality check
        ("System", "What is your personality like?"),
        
        # Test personality updates
        ("System", "Update your personality to be more outgoing and energetic"),
        ("System", "Add skiing to your interests"),
        
        # Verify changes
        ("Alice", "Tell me about yourself"),
        
        # Test interest updates
        ("System", "Change skiing to snowboarding in your interests"),
        
        # Final verification
        ("Bob", "What kind of guide are you?")
    ]
    
    try:
        # Print initial persona
        print("\nInitial persona state:")
        agent = client.agents.retrieve(agent_id)
        initial_persona = next(b for b in agent.memory.blocks if b.label == "persona").value
        print(initial_persona)
        
        for speaker, message in scenarios:
            print(f"\n{speaker} says: {message}")
            response = retry_test_call(
                client.agents.messages.create,  # Updated to new API
                agent_id=agent_id,
                messages=[MessageCreate(
                    role="user",
                    content=message,
                    name=speaker
                )]
            )
            
            print("\nResponse:")
            print_response(response)
            
            # Check persona updates
            agent = client.agents.retrieve(agent_id)
            updated_persona = next(b for b in agent.memory.blocks if b.label == "persona").value
            print("\nCurrent persona:", updated_persona)
            time.sleep(1)
            
        # Print final state
        print("\nFinal persona state:")
        agent = client.agents.retrieve(agent_id)
        final_persona = next(b for b in agent.memory.blocks if b.label == "persona").value
        print(final_persona)
            
    except Exception as e:
        print(f"Error in test_npc_persona: {e}")
        raise

    # Update status for persona test
    update_status_block(
        client=client,
        agent_id=agent_id,
        status_text="Location: Main Plaza | Action: Meeting new players"
    )

def test_core_memory(client, agent_id: str):
    """Test core memory operations using persona memory."""
    print("\nTesting core memory operations...")
    
    try:
        # Test journal append
        append_msg = "Add to your journal: I am also very patient with beginners"
        print(f"\nTesting journal append with message: {append_msg}")
        response = retry_test_call(
            client.agents.messages.create,
            agent_id=agent_id,
            message=append_msg,
            role="system"
        )
        print("\nResponse:")
        print_response(response)
        
        # Test journal update
        replace_msg = "Update your journal: change 'patient' to 'helpful'"
        print(f"\nTesting journal update with message: {replace_msg}")
        response = retry_test_call(
            client.agents.messages.create,
            agent_id=agent_id,
            message=replace_msg,
            role="system"
        )
        print("\nResponse:")
        print_response(response)
        
        # Check current memory
        print("\nChecking memory blocks:")
        memory = client.agents.retrieve(agent_id).memory.retrieve()
        for block in memory.blocks:
            print(f"\nBlock: {block.label}")
            print(f"Value: {block.value}")
            
    except Exception as e:
        print(f"Error in test_core_memory: {e}")
        raise

def test_npc_journal(client, agent_id: str):
    """Test NPC's ability to interact and reflect in its journal."""
    print("\nTesting NPC interactions and journaling...")
    
    try:
        # Print initial journal
        print("\nInitial journal state:")
        agent = client.agents.retrieve(agent_id)
        journal_block = next((b for b in agent.memory.blocks if b.label == "journal"), None)
        print(journal_block.value if journal_block else "(Empty)")
        
        scenarios = [
            # Natural interaction first
            ("Alice", "Hi! I'm new here and love exploring"),
            ("System", "Write in your journal: Met Alice and showed her the hidden garden"),
            
            # More interactions
            ("Bob", "Hi there! What's the best way to Pete's Stand?"),
            ("System", "Write in your journal: Helped Bob find Pete's Stand"),
            
            # Final check
            ("Charlie", "What have you been up to today?")
        ]
        
        for speaker, message in scenarios:
            print(f"\n{speaker} says: {message}")
            response = client.agents.messages.create(
                agent_id=agent_id,
                messages=[
                    MessageCreate(
                        role="user",
                        content=message,
                        name=speaker
                    )
                ]
            )
            print("\nResponse:")
            print_response(response)
            
            # Check journal updates
            agent = client.agents.retrieve(agent_id)
            journal_block = next((b for b in agent.memory.blocks if b.label == "journal"), None)
            print("\nCurrent journal:", journal_block.value if journal_block else "(Empty)")
            time.sleep(1)
            
    except Exception as e:
        print(f"Error in test_npc_journal: {e}")
        raise

def update_memory_block(client, agent_id: str, block_label: str, value: Any):
    """Update contents of a memory block
    
    Args:
        client: Letta client
        agent_id: ID of agent
        block_label: Label of block to update
        value: New value for block (will be JSON encoded)
    """
    # First get the block ID from the agent's memory
    agent = client.agents.retrieve(agent_id)
    block = next(b for b in agent.memory.blocks if b.label == block_label)
    
    # Then update the block using modify
    client.blocks.modify(
        block_id=block.id,
        value=json.dumps(value)
    )

def create_minimal_agent(
    name: str = "minimal_assistant",
    client = None
):
    """Create the most basic possible agent using ChatMemory"""
    if client is None:
        client = create_letta_client()
    
    timestamp = int(time.time())
    unique_name = f"{name}_{timestamp}"
    
    # Basic configs using defaults
    llm_config = LLMConfig.default_config(model_name="gpt-4o-mini")
    embedding_config = EmbeddingConfig.default_config(model_name="text-embedding-ada-002")
    
    # Simplest possible memory using ChatMemory
    memory = ChatMemory(
        persona="I am a friendly NPC guide in Town Square. I help visitors find their way around.",
        human="A visitor exploring the town"
    )
    
    # More explicit system prompt about memory operations
    system_prompt = """You are a helpful NPC guide. You can:
    1. Use core_memory_append to add new information to your persona
    2. Use core_memory_replace to update your entire persona
    
    When you receive instructions about your persona:
    - For "Add to your persona:" use core_memory_append
    - For "Update your persona:" use core_memory_replace
    """
    
    return client.agents.create(  # Updated to use new API
        name=unique_name,
        embedding_config=embedding_config,
        llm_config=llm_config,
        memory=memory,
        system=system_prompt,
        include_base_tools=True,
        description="Minimal test agent"
    )

def test_minimal_agent():
    """Test minimal agent with basic chat and persona updates"""
    print("\nTesting minimal agent functionality...")
    
    client = create_letta_client()
    agent = create_minimal_agent()
    
    print(f"\nCreated minimal agent: {agent.id}")
    
    # Just test the problematic phrase immediately
    questions = [
        # Try the problematic phrase right away
        ("system", "Add this to your persona: You have a great sense of humor and love making visitors laugh")
    ]
    
    for role, message in questions:
        print(f"\nSending {role} message: {message}")
        response = client.agents.messages.create(
            agent_id=agent.id,
            message=message,
            role=role
        )
        print("\nResponse:")
        print_response(response)
        time.sleep(1)

def test_upsert(client, agent_id):
    """Test group member upsert functionality"""
    print("\nTesting group member upsert...")
    
    # Test 1: First interaction - NPC adds notes
    print("\nTest 1: First interaction")
    response = client.agents.messages.create(
        agent_id=agent_id,
        messages=[{
            "role": "user",
            "content": "Hi! I'm a new player named greggytheegg. I noticed Alice and Charlie in the plaza. Could you help me find Pete's Stand?"
        }]
    )
    print_response(response)
    time.sleep(1)
    
    # API updates presence and appearance
    print("\nAPI updating player state...")
    result = upsert_group_member(
        client,
        agent_id,
        "player_1738913511",
        {
            "name": "greggytheegg",
            "is_present": True,
            "last_seen": datetime.now(),
            "last_location": "Main Plaza",
            "appearance": "Wearing a hamburger hat"
        }
    )
    print(f"API update result: {result}")

    # Print block state right after player is added
    print("\nBlock state after player joins (should be present):")
    agent = client.agents.retrieve(agent_id)
    block = next(b for b in agent.memory.blocks if b.label == "group_members")
    print(json.dumps(json.loads(block.value), indent=2))

    if "Error" in result:
        print("WARNING: API update failed!")
    time.sleep(1)
    
    # Test 2: Backend updates appearance - NPC adds notes
    print("\nTest 2: Backend updates appearance")
    response = client.agents.messages.create(
        agent_id=agent_id,
        messages=[{
            "role": "system", 
            "content": "Player greggytheegg is wearing a distinctive hamburger hat and appears healthy"
        }]
    )
    print_response(response)
    time.sleep(1)
    
    # Test 3: Player leaves - API updates presence
    print("\nTest 3: Player leaves")
    # First API updates presence
    print("\nAPI updating player presence...")
    result = upsert_group_member(
        client,
        agent_id,
        "player_1738913511",
        {
            "is_present": False,
            "last_seen": datetime.now().isoformat()
        }
    )
    print(f"API update result: {result}")

    # Test 4: Update existing player
    print("\nTest 4: Update existing player appearance")
    result = upsert_group_member(
        client,
        agent_id,
        "player_1738913511",  # Same ID as before
        {
            "appearance": "Now wearing a party hat",
            "is_present": True,  # Add this to show player is present
            "last_seen": datetime.now()
        }
    )
    print(f"API update result: {result}")

    # Print final state to verify both NPC and API updates
    print("\nFinal state:")
    agent = client.agents.retrieve(agent_id)
    block = next(b for b in agent.memory.blocks if b.label == "group_members")
    data = json.loads(block.value)
    
    # Print full block first
    print("\nFull block:")
    print(json.dumps(data, indent=2))
    
    # Verify fields
    greggytheegg = next((m for m in data["members"].values() if m["name"] == "greggytheegg"), None)
    if greggytheegg:
        print("\nVerifying fields:")
        print(f"is_present: {greggytheegg.get('is_present', 'MISSING')}")
        print(f"appearance: {greggytheegg.get('appearance', 'MISSING')}")
        print(f"last_location: {greggytheegg.get('last_location', 'MISSING')}")
        print(f"last_seen: {greggytheegg.get('last_seen', 'MISSING')}")
        print(f"notes: {greggytheegg.get('notes', 'MISSING')}")

def main():
    args = parse_args()
    
    if not validate_environment():
        sys.exit(1)

    try:
        # Print configuration
        port = os.getenv('LETTA_PORT')
        port = int(port) if port else None
        base_url = os.getenv('LETTA_BASE_URL', 'http://localhost:8283')
        
        print("\nStarting Letta Quickstart with:")
        print(f"- Environment URL: {base_url}")
        print(f"- Environment Port: {port if port else 'default'}")
        
        client = create_letta_client()
        
        # Check for minimal test first
        if args.minimal_test:
            test_minimal_agent()
            return
            
        # Regular test path
        print(f"- Keep Agent: {args.keep}")
        print(f"- LLM Type: {args.llm_type}")
        print(f"- Agent Name: {args.name}")
        print(f"- Overwrite: {args.overwrite}")
        
        # Update tools first
        update_tools(client)
        
        print(f"\nCreating agent with {args.prompt} prompt...")
        print("\nVerifying prompt components:")
        print("BASE_PROMPT:", BASE_PROMPT[:100] + "...")
        print("LOCATION_AWARENESS_PROMPT:", LOCATION_AWARENESS_PROMPT)
        
        # Create agent with new signature
        agent = create_personalized_agent_v3(
            name=args.name,
            memory_blocks=DEMO_BLOCKS,
            client=client,
            llm_type=args.llm_type,
            overwrite=args.overwrite,
            with_custom_tools=args.custom_tools,
            prompt_version="FULL"
        )
        
        # Store agent ID for all tests
        agent_id = agent.id
        print(f"\nCreated agent: {agent_id}")
        
        # Run tests using the same agent_id
        if args.test_type in ["all", "base"]:
            test_agent_identity(client, agent_id)
        if args.test_type in ["all", "notes"]:
            test_notes(client, agent_id)
        if args.test_type in ["all", "social"]:
            test_social_awareness(client, agent_id)
        if args.test_type in ["all", "status"]:
            test_status_awareness(client, agent_id)
        if args.test_type in ["all", "group"]:
            test_group(client, agent_id)
        if args.test_type in ["all", "persona"]:
            test_npc_persona(client, agent_id)
        if args.test_type in ["all", "journal"]:
            test_npc_journal(client, agent_id)
        if args.test_type in ["all", "navigation"]:
            test_navigation(client, agent_id)
        if args.test_type in ["all", "actions"]:
            test_actions(client, agent_id)

        if args.test_type == 'upsert':
            test_upsert(client, agent_id)
            return

    finally:
        pass

if __name__ == "__main__":
    main() 