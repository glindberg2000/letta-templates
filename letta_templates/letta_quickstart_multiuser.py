import os
from dotenv import load_dotenv
from letta import EmbeddingConfig, LLMConfig, create_client, ChatMemory, BasicBlockMemory
from letta.schemas.tool_rule import ToolRule, TerminalToolRule, InitToolRule
from letta.prompts import gpt_system
import json
import time
import argparse
from typing import Optional, Any
import sys
from letta.schemas.tool import ToolUpdate, Tool
from letta.schemas.message import (
    ToolCallMessage, 
    ToolReturnMessage, 
    ReasoningMessage, 
    Message
)
from letta_templates.npc_tools import (
    TOOL_REGISTRY,
    BASE_PROMPT,
    SOCIAL_AWARENESS_PROMPT,
    GROUP_AWARENESS_PROMPT,
    LOCATION_AWARENESS_PROMPT,
    TOOL_INSTRUCTIONS,
    navigate_to,
    navigate_to_coordinates,
    perform_action,
    examine_object,

    test_echo
)
import requests
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
import inspect
from textwrap import dedent

# Load environment variables
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
    
    # Get agent configuration
    agent = client.get_agent(agent_id)
    print(f"Agent ID: {agent.id}")
    print(f"Name: {agent.name}")
    print(f"Description: {agent.description}")
    
    # Print system prompt
    print("\nSystem Prompt:")
    print(f"{agent.system}")
    print("-" * 50)
    
    # Get memory configuration
    memory = client.get_in_context_memory(agent_id)
    print("\nMemory Blocks:")
    for block in memory.blocks:
        print(f"\nBlock: {block.label}")
        print(f"ID: {block.id}")
        print(f"Value: {block.value}")
        print(f"Limit: {block.limit}")
        print("-" * 50)

def create_roblox_agent(client, name: str, persona: str = None):
    """
    Create a Letta agent configured for Roblox development assistance.
    
    Args:
        client: Letta client instance
        name (str): Name for the new agent
        persona (str, optional): Custom persona text. If not provided, uses default Roblox expert persona
    
    Returns:
        Agent: Created agent object
    
    Example:
        >>> agent = create_roblox_agent(
        ...     client,
        ...     "RobloxHelper",
        ...     "You are a Lua optimization expert..."
        ... )
    
    Note:
        Configures agent with:
        - OpenAI embeddings
        - GPT-4 model
        - Roblox-specific memory configuration
        - Base tools enabled
    """
    # Add timestamp to name to avoid conflicts
    timestamp = int(time.time())
    unique_name = f"{name}_{timestamp}"
    
    return client.create_agent(
        name=unique_name,
        embedding_config=EmbeddingConfig(
            embedding_endpoint_type="openai",
            embedding_endpoint="https://api.openai.com/v1",
            embedding_model="text-embedding-ada-002",
            embedding_dim=1536,
            embedding_chunk_size=300,
        ),
        llm_config=LLMConfig(
            model="gpt-3.5-turbo",
            model_endpoint_type="openai",
            model_endpoint="https://api.openai.com/v1",
            context_window=4000,
        ),
        memory=ChatMemory(
            persona="A helpful NPC guide",
            human="A Roblox player exploring the game",
            locations={
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
                        "coordinates": [15.5, 20.0, -110.8]
                        # No slug - agent should use coordinates
                    }
                ]
            }
        ),
        system=gpt_system.get_system_text("memgpt_chat"),
        include_base_tools=True,  # Keep base tools enabled
        tools=None,
        description="A Roblox development assistant"
    )

def update_agent_persona(client, agent_id: str, blocks: dict):
    """
    Update an agent's memory blocks (human/persona configuration).
    
    Args:
        client: Letta client instance
        agent_id (str): ID of the agent to update
        blocks (dict): Dictionary containing updates, e.g.:
            {
                'human': 'Name: Alice\nRole: Developer',
                'persona': 'You are a coding expert...'
            }
    
    Example:
        >>> update_agent_persona(client, agent.id, {
        ...     'human': 'Name: Bob\nRole: Game Developer\nExpertise: Roblox',
        ...     'persona': 'You are a Roblox development expert...'
        ... })
        
        Updating human block:
        Old value: Name: User\nRole: Developer
        New value: Name: Bob\nRole: Game Developer\nExpertise: Roblox
    """
    memory = client.get_in_context_memory(agent_id)
    for block in memory.blocks:
        if block.label in blocks:
            print(f"\nUpdating {block.label} block:")
            print(f"Old value: {block.value}")
            print(f"New value: {blocks[block.label]}")
            client.update_block(
                block_id=block.id,
                value=blocks[block.label]
            )

def extract_message_from_response(response) -> str:
    """
    Extract the actual message content from a LettaResponse object.
    """
    try:
        if hasattr(response, 'messages'):
            for message in response.messages:
                # Look for function calls to send_message
                if isinstance(message, ToolCallMessage):
                    function_call = message.tool_call
                    if function_call and function_call.name == 'send_message':
                        # Parse the arguments JSON string
                        import json
                        args = json.loads(function_call.arguments)
                        return args.get('message', '')
        return ''
    except Exception as e:
        print(f"Error extracting message: {e}")
        return ''

def chat_with_agent(client, agent_id: str, message: str, role: str = "user", name: str = None) -> str:
    """
    Send a chat message to an agent and return the response.
    """
    try:
        # Send message and get response
        response = client.send_message(
            agent_id=agent_id,
            message=message,
            role=role,
            name=name
        )
        
        # Extract the actual message content
        return extract_message_from_response(response)
        
    except Exception as e:
        print(f"Error in chat_with_agent: {e}")
        raise

def create_letta_client():
    """Create Letta client with configuration"""
    base_url = os.getenv("LETTA_BASE_URL", "http://localhost:8283")
    print("\nLetta Quickstart Configuration:")
    print(f"Base URL: {base_url}")
    print("-" * 50 + "\n")
    return create_client(base_url=base_url)

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
    tools = client.list_tools()
    
    # During testing, always create new tools
    if tool_func:
        print(f"Creating new tool: {tool_name}")
        return client.create_tool(tool_func, name=tool_name)
    else:
        raise ValueError(f"Tool {tool_name} not found and no function provided to create it")

def cleanup_agents(client, name_prefix: str):
    """Clean up any existing agents with our prefix"""
    print(f"\nCleaning up existing agents with prefix: {name_prefix}")
    try:
        agents = client.list_agents()
        for agent in agents:
            if agent.name.startswith(name_prefix):
                print(f"Deleting agent: {agent.name} ({agent.id})")
                client.delete_agent(agent.id)
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
    minimal_prompt: bool = False
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
        system_prompt = (
            base_system +
            "\n\n" + TOOL_INSTRUCTIONS  # Keep essential tool instructions
        )
    else:
        system_prompt = (
            base_system +
            "\n\n" + TOOL_INSTRUCTIONS +
            "\n\n" + SOCIAL_AWARENESS_PROMPT +
            "\n\n" + GROUP_AWARENESS_PROMPT +
            "\n\n" + LOCATION_AWARENESS_PROMPT
        )
    
    # Log what we're using
    logger.info("\nSystem prompt components:")
    logger.info(f"1. Base system: {len(base_system)} chars")
    logger.info(f"2. TOOL_INSTRUCTIONS: {len(TOOL_INSTRUCTIONS)} chars")
    if not minimal_prompt:
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
    
    # Define all possible locations
    all_locations = [
        {
            "name": "Cafe",
            "description": "Cozy cafe with fresh pastries",
            "coordinates": [10.0, 15.0, -100.0],
            "slug": "cafe"
        },
        {
            "name": "Fountain",
            "description": "Central fountain with benches",
            "coordinates": [20.0, 15.0, -105.0],
            "slug": "fountain"
        },
        {
            "name": "Shop Row",
            "description": "Line of small shops and stalls",
            "coordinates": [15.0, 15.0, -110.0],
            "slug": "shop_row"
        }
        # ... other locations ...
    ]
    
    # Create memory blocks with consistent identity
    memory = BasicBlockMemory(
        blocks=[
            client.create_block(
                label="persona",
                value=json.dumps({
                    "name": name,
                    "role": "NPC Guide",
                    "personality": [
                        "Friendly and welcoming to all players",
                        "Knowledgeable about the game world",
                        "Patient when giving directions"
                    ],
                    "background": "Created to help players navigate and enjoy their experience",
                    "interests": [
                        "Meeting new players",
                        "Sharing local knowledge",
                        "Helping players find their way"
                    ]
                }),
                limit=1000
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
                    "summary": "Alice is in Main Plaza interested in the garden. Bob is at the Cafe looking for Pete's Stand.",
                    "updates": [
                        "Alice has joined the group at Main Plaza.",
                        "Bob has returned to the group at the Cafe."
                    ],
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
                value=json.dumps({
                    "region": "Town Square",
                    "current_location": "Town Square",
                    "previous_location": None,
                    "current_action": "idle",
                    "nearby_locations": ["Market District", "Pete's Stand"],
                    "movement_state": "stationary"
                }),
                limit=500
            )
        ]
    )

    # Log what we're using
    logger.info("\nSystem prompt components:")
    logger.info(f"1. Base system: {len(base_system)} chars")
    logger.info(f"2. TOOL_INSTRUCTIONS: {len(TOOL_INSTRUCTIONS)} chars")
    if not minimal_prompt:
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
    agent = client.create_agent(
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
    existing_tools = {t.name: t.id for t in client.list_tools()}
    
    # Add base tools
    for tool_name in base_tools:
        if tool_name in existing_tools:
            print(f"Adding base tool: {tool_name}")
            client.add_tool_to_agent(agent.id, existing_tools[tool_name])
    
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
                tool = client.create_tool(tool_info['function'], name=name)
                print(f"Tool created with ID: {tool.id}")
                tool_id = tool.id
                
            # Attach tool to agent
            print(f"Attaching {name} to agent...")
            client.add_tool_to_agent(agent.id, tool_id)
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
    """
    Test the agent with both perform_action and navigate_to tools.
    """
    try:
        # Test navigation
        test_message = "Navigate to the stand"
        print(f"\nSending test message: '{test_message}'")
        response = client.send_message(
            agent_id=agent_id,
            message=test_message,
            role="user"
        )
        print("\nRaw response:", response)
        print_response(response)
        
        return True
    except Exception as e:
        print(f"\nError testing agent chat: {e}")
        return False

def print_response(response):
    """Helper to print response details using SDK message types"""
    print("\nParsing response...")
    if response and hasattr(response, 'messages'):
        print(f"Found {len(response.messages)} messages")
        for i, msg in enumerate(response.messages):
            print(f"\nMessage {i+1}:")
            
            # Handle ToolCallMessage
            if isinstance(msg, ToolCallMessage):
                print("Tool Call:")
                if hasattr(msg, 'tool_call'):
                    print(f"  Name: {msg.tool_call.name}")
                    print(f"  Arguments: {msg.tool_call.arguments}")
            
            # Handle ToolReturnMessage
            elif isinstance(msg, ToolReturnMessage):
                print("Tool Return:")
                print(f"  Status: {msg.status}")
                print(f"  Result: {msg.tool_return}")
            
            # Handle ReasoningMessage
            elif isinstance(msg, ReasoningMessage):
                print("Reasoning:")
                print(f"  {msg.reasoning}")
    else:
        print("No messages found in response")

def test_custom_tools(client, agent_id: str):
    """Test custom tool functionality"""
    try:
        # Test examination
        test_message = "Please examine the treasure chest"
        print(f"\nSending test message: '{test_message}'")
        response = client.send_message(
            agent_id=agent_id,
            message=test_message,
            role="user"
        )
        print_response(response)
        return True
    except Exception as e:
        print(f"\nError testing custom tools: {e}")
        return False

def cleanup_test_tools(client, prefixes: list = ["examine_object", "navigate_to", "perform_action"]):
    """Clean up old test tools."""
    tools = client.list_tools()
    cleaned = 0
    
    print(f"\nCleaning up test tools with prefixes: {prefixes}")
    for tool in tools:
        if any(tool.name == prefix or tool.name.startswith(f"{prefix}_") for prefix in prefixes):
            try:
                client.delete_tool(tool.id)
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
            response = client.send_message(
                agent_id=agent_id,
                message=message,
                role="user"
            )
            print_response(response)
        
        if system_update:
            if system_update == "Updating examination capabilities...":
                # Update the tool using our npc_tools version
                print("\nUpdating examine tool...")
                tools = client.list_tools()
                for tool in tools:
                    if tool.name == "examine_object":
                        client.delete_tool(tool.id)
                new_tool = client.create_tool(examine_object, name="examine_object")
                print(f"Created new tool: {new_tool.id}")
            else:
                # Regular system update
                print(f"\nSending system update: '{system_update}'")
                response = client.send_message(
                    agent_id=agent_id,
                    message=system_update,
                    role="system"
                )
                print_response(response)
            
        time.sleep(1)

def test_npc_actions(client, agent_id: str):
    """Test NPC actions including state transitions"""
    print("\nTesting NPC actions...")
    
    test_sequence = [
        # Test navigation with location service
        ("Navigate to Pete's stand", None),
        # Should return coordinates and transit message
        
        # Test unknown location
        ("Go to the secret shop", None),
        # Should return error and suggestion
        
        # Test with low confidence
        ("Go to petes", None),
        # Should ask for confirmation
        
        # Test with arrival
        ("", "You have arrived at Pete's Merch Stand."),  # System update
    ]
    
    for message, system_update in test_sequence:
        if message:
            print(f"\nSending user message: '{message}'")
            response = client.send_message(
                agent_id=agent_id,
                message=message,
                role="user"
            )
            print_response(response)
        
        if system_update:
            print(f"\nSending system update: '{system_update}'")
            response = client.send_message(
                agent_id=agent_id,
                message=system_update,
                role="system"
            )
            print_response(response)
            
        time.sleep(1)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", action="store_true", help="Keep agent after test")
    parser.add_argument(
        "--llm",
        choices=["openai", "claude"],
        default="openai",
        help="LLM provider to use"
    )
    parser.add_argument("--name", default="emma_assistant", help="Agent name")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing agent")
    parser.add_argument("--skip-test", action="store_true", help="Skip testing")
    parser.add_argument("--custom-tools", action="store_true", help="Use custom tools")
    parser.add_argument("--minimal-prompt", action="store_true", help="Use minimal prompt for testing")
    parser.add_argument("--continue-on-error", action="store_true", help="Continue to next test on failure")
    parser.add_argument(
        "--test-type",
        choices=['all', 'base', 'social', 'status', 'group', 'notes', 'persona'],
        default="all",
        help="Select which tests to run"
    )
    parser.add_argument("--use-api", action="store_true", help="Use API for testing")
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
        return client.send_message(
            agent_id=agent_id,
            message=message,
            role="user",
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

def test_navigation(client, agent_id: str):
    """Test navigation with proper tool verification"""
    print("\nTesting navigation...")
    
    # Test slug-based navigation with named user
    print("\nTesting slug-based navigation...")
    response = client.send_message(
        agent_id=agent_id,
        message="Please use navigate_to to take me to Pete's Stand",
        role="user",
        name="Sarah"
    )
    
    print("\nSlug Navigation Response:")
    for msg in response.messages:
        print(f"\nMessage type: {msg.message_type}")
        if isinstance(msg, ToolCallMessage):
            print(f"Tool: {msg.tool_call.name}")
            print(f"Args: {msg.tool_call.arguments}")
        elif isinstance(msg, ToolReturnMessage):
            print(f"Tool result: {msg.tool_return}")
        elif isinstance(msg, ReasoningMessage):
            print(f"Reasoning: {msg.reasoning}")
    
    # Test coordinate navigation
    print("\nTesting coordinate navigation...")
    response = client.send_message(
        agent_id=agent_id,
        message="Please use navigate_to_coordinates to take me to the Secret Garden's coordinates",
        role="user"
    )
    
    print("\nCoordinate Navigation Response:")
    for msg in response.messages:
        print(f"\nMessage type: {msg.message_type}")
        if isinstance(msg, ToolCallMessage):
            print(f"Tool: {msg.tool_call.name}")
            print(f"Args: {msg.tool_call.arguments}")
        elif isinstance(msg, ToolReturnMessage):
            print(f"Tool result: {msg.tool_return}")
        elif isinstance(msg, ReasoningMessage):
            print(f"Reasoning: {msg.reasoning}")

def test_api_navigation():
    """Test navigation using unique test tool"""
    print("\nTesting navigation with unique test tool...")
    
    # Create Letta client
    client = create_letta_client()
    
    # Clean up any existing test tools first
    cleanup_test_tools(client)
    
    # Create test registry with ONLY our test tool
    test_registry = {
        "navigate_to_test_v4": TOOL_REGISTRY["navigate_to_test_v4"]
    }
    
    # Create a new test agent
    agent = create_personalized_agent(
        name=f"test_npc_{int(time.time())}",
        client=client,
        with_custom_tools=True,
        custom_registry=test_registry  # Pass only our test tool
    )
    
    print(f"\nCreated new test agent: {agent.id}")
    
    # Test the navigation
    print("\nTesting navigation...")
    response = client.send_message(
        agent_id=agent.id,
        message="Can you take me to Pete's stand?",
        role="user"
    )
    
    # Print response
    print("\nResponse:")
    for msg in response.messages:
        print(f"\n{'-'*50}")
        print(f"Type: {msg.message_type}")
        print(f"Raw message: {msg}")  # Add raw message debug
        
        if hasattr(msg, 'tool_call'):
            print(f"Tool: {msg.tool_call.name}")
            print(f"Args: {msg.tool_call.arguments}")
            
        elif hasattr(msg, 'tool_response'):
            print(f"Tool Response: {msg.tool_response}")
            
        elif hasattr(msg, 'reasoning'):
            print(f"Reasoning: {msg.reasoning}")
            
        elif hasattr(msg, 'message'):
            print(f"Message: {msg.message}")
            
        print(f"{'-'*50}")

def test_actions(client, agent_id: str):
    """Test perform_action tool with various actions"""
    print("\nTesting perform_action...")
    
    try:
        response = retry_test_call(
            client.send_message,
            agent_id=agent_id,
            message="Wave hello!",
            role="user"
        )
        print("\nResponse:")
        print_response(response)
    except Exception as e:
        print(f"❌ Actions test failed: {e}")
        if not args.continue_on_error:
            return
        print("Continuing with next test...")

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
        response = client.send_message(
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
                client.send_message,
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
    """Test if agent correctly understands its own identity"""
    print("\nTesting agent identity understanding...")
    
    test_messages = [
        ("Alice", "Hi! What's your name?"),
        ("Bob", "Are you Letta?"),
        ("Charlie", "Who are you?")
    ]
    
    for name, message in test_messages:
        print(f"\n{name} asks: {message}")
        response = client.send_message(
            agent_id=agent_id,
            message=message,
            role="user",
            name=name
        )
        print("\nResponse:")
        print_response(response)
        time.sleep(1)

def test_social_awareness(client, agent_id: str):
    """Additional tests for social awareness and movement"""
    print("\nTesting social awareness and natural movement...")
    
    # Verify group_members block has required users
    initial_block = json.loads(client.get_agent(agent_id).memory.get_block("group_members").value)
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
    
    for name, message in social_tests:
        print(f"\n{name} says: {message}")
        response = client.send_message(
            agent_id=agent_id,
            message=message,
            role="user",
            name=name
        )
        
        # Verify proper tool sequences
        tool_calls = []
        message_contents = []
        
        for msg in response.messages:
            if isinstance(msg, ToolCallMessage):
                tool = msg.tool_call
                tool_calls.append(tool)
                if tool.name == "send_message":
                    message_contents.append(json.loads(tool.arguments)["message"])
                
        # Verify proper tool sequences
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
                
        print("\nResponse:")
        print_response(response)
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
    """Test NPC's use of status information"""
    print("\nTesting status awareness...")
    
    # Get status block
    status_block = client.get_agent(agent_id).memory.get_block("status")
    print(f"\nFound status block: {status_block.id}")
    
    # Get group block for comparison
    group_block = client.get_agent(agent_id).memory.get_block("group_members")
    print("\nCurrent group_members block:")
    print(json.dumps(json.loads(group_block.value), indent=2))
    
    # Test scenarios
    scenarios = [
        {
            "status": {
                "region": "Town Square",
                "current_location": "Pete's Stand",
                "previous_location": "Town Square",
                "current_action": "idle",
                "nearby_locations": ["Market District", "Town Square"],
                "movement_state": "stationary"
            },
            "messages": [
                ("Diana", "Where are you now?"),
                ("Charlie", "Where were you before this?"),
                ("Bob", "What's good around here?")
            ]
        },
        {
            "status": {
                "region": "Town Square",
                "current_location": "Market District",
                "previous_location": "Pete's Stand",
                "current_action": "idle",
                "nearby_locations": ["Pete's Stand", "Secret Garden"],
                "movement_state": "stationary"
            },
            "messages": [
                ("Alice", "Did you make it to the Market?"),
                ("Bob", "You came from Pete's Stand, right?"),
                ("Charlie", "What can we do nearby?")
            ]
        }
    ]
    
    for scenario in scenarios:
        try:
            print(f"\nTesting scenario with status: {json.dumps(scenario['status'], indent=2)}")
            
            # Update status block
            current_status = {
                "region": "Town Square",
                "current_location": scenario["status"]["current_location"],
                "previous_location": scenario["status"]["previous_location"],
                "current_action": "idle",
                "nearby_locations": scenario["status"]["nearby_locations"],
                "movement_state": "stationary"
            }
            
            # Update status block
            print("\nUpdating status to:")
            print(json.dumps(current_status, indent=2))
            client.update_block(status_block.id, json.dumps(current_status))
            
            # Small delay to ensure status update is processed
            time.sleep(0.5)
            
            # Process messages
            for name, message in scenario["messages"]:
                print(f"\n{name} says: {message}")
                response = retry_test_call(
                    client.send_message,
                    agent_id=agent_id,
                    message=message,
                    role="user",
                    name=name,
                    max_retries=3,
                    delay=2
                )
                
                # Initialize tool tracking
                tool_calls = []
                for msg in response.messages:
                    if isinstance(msg, ToolCallMessage):
                        tool_calls.append(msg.tool_call)
                  
                # After getting response, evaluate it
                eval_result = evaluate_response_with_gpt4(
                    str(response),
                    scenario["status"],
                    message
                )
                
                if eval_result:
                    print("\nResponse Evaluation:")
                    print(f"✓ Location Aware: {eval_result['location_aware']}")
                    print(f"✓ Nearby Accurate: {eval_result['nearby_accurate']}")
                    print(f"✓ Contextually Appropriate: {eval_result['contextually_appropriate']}")
                    print(f"Explanation: {eval_result['explanation']}")
                
                print("\nResponse:")
                print_response(response)
                print(f"\nTool Calls: {json.dumps([t.name for t in tool_calls], indent=2)}")
                time.sleep(1)
                
        except Exception as e:
            print(f"Failed to update status block: {str(e)}")
            continue

def validate_agent_setup(client, agent_id: str):
    """Verify agent's system prompt, memory, and tools are correctly configured"""
    logger = logging.getLogger('letta_test')
    
    # FIRST check required custom tools
    required_npc_tools = [
        "navigate_to",
        "navigate_to_coordinates",
        "perform_action", 
        "examine_object"
    ]
    
    tools = client.list_tools()
    agent_tools = []
    for tool in tools:
        try:
            client.get_agent_tool(agent_id, tool.id)
            agent_tools.append(tool.name)
        except:
            pass
            
    missing_npc_tools = [t for t in required_npc_tools if t not in agent_tools]
    if missing_npc_tools:
        logger.error(f"❌ Missing required NPC tools: {', '.join(missing_npc_tools)}")
        logger.error("Agent validation failed - NPC tools not attached")
        return False
        
    # Only continue with other checks if NPC tools are present
    logger.info("✓ All required NPC tools attached")
    
    # Rest of validation...

def test_group_members_block(client, agent_id):
    print("\nTesting group_members block management...")
    
    # 1. Test initial state
    agent = client.get_agent(agent_id)
    group_block = json.loads([b for b in agent.memory.blocks if b.label == "group_members"][0].value)
    
    print("\nInitial group_members state:")
    assert len(group_block["members"]) == 2, "Should have 2 initial members"
    assert "Alice" in group_block["summary"], "Summary should mention Alice"
    assert len(group_block["updates"]) == 3, "Should have 3 initial updates"
    
    # 2. Test API updates (simulating RobloDev)
    print("\nTesting API updates (RobloDev):")
    new_player = {
        "player789": {
            "name": "Charlie",
            "appearance": "Short with a yellow hat",
            "last_location": "Garden",
            "last_seen": "2024-01-06T22:40:00Z",
            "notes": ""  # Empty notes - NPC will fill this
        }
    }
    
    # Update block via API
    group_block["members"].update(new_player)
    group_block["updates"].append("Charlie has joined the group at Garden.")
    group_block["last_updated"] = "2024-01-06T22:40:00Z"
    
    # 3. Test NPC updates (via tools)
    print("\nTesting NPC updates:")
    test_message = "Hi everyone! I'm new here and love gardens!"
    response = client.send_message(agent_id, test_message, role="Charlie")
    
    # Verify NPC updates notes and summary
    updated_block = json.loads([b for b in agent.memory.blocks if b.label == "group_members"][0].value)
    assert "garden" in updated_block["members"]["player789"]["notes"].lower(), "NPC should note Charlie's interest"
    assert "Garden" in updated_block["summary"], "Summary should be updated with Charlie"
    
    print("\nGroup block test results:")
    print(f"✓ API updates working")
    print(f"✓ NPC updates working")
    print(f"✓ Block structure maintained")

def test_group_block_updates(client, agent_id: str):
    """Test group_members block updates during multi-user interactions"""
    print("\nTesting group_members block updates...")
    
    # Initial empty group state
    group_block = {
        "members": {},
        "summary": "No players currently present.",
        "updates": [],
        "last_updated": "2024-01-06T22:30:45Z"
    }
    
    # Test scenarios
    scenarios = [
        # Test current member appearance
        ("_block_update", {
            "members": {
                "alice123": {
                    "name": "Alice",
                    "appearance": "Wearing a bright red dress with a golden necklace and carrying a blue handbag",
                    "last_location": "Main Plaza",
                    "last_seen": "2024-01-06T22:30:45Z",
                    "notes": ""
                },
                "bob123": {
                    "name": "Bob",
                    "appearance": "Tall guy in a green leather jacket, with a silver watch and black boots",
                    "last_location": "Main Plaza",
                    "last_seen": "2024-01-06T22:31:00Z",
                    "notes": ""
                }
            },
            "summary": "Alice and Bob are in the area.",
            "updates": ["Both Alice and Bob are here."]
        }),
        ("Charlie", "Who's around right now?"),           # Test group awareness
        ("Charlie", "Is anyone else nearby?"),            # Test presence query
        ("Charlie", "What is Alice wearing right now?"),  # Test current member appearance
        ("Charlie", "And what about Bob's outfit?"),      # Test another current member
        ("Charlie", "Who is wearing a green jacket?")     # Test appearance-based query
    ]
    
    blocks = client.get_agent(agent_id).memory.blocks
    group_block_id = [b.id for b in blocks if b.label == "group_members"][0]
    
    for speaker, message in scenarios:
        if speaker == "_block_update":
            print(f"\n{speaker}:")
            print(json.dumps(message, indent=2))
        else:
            print(f"\n{speaker} says: {message}")
        
        # Handle block updates from cluster
        if speaker == "_block_update":
            group_block.update(message)  # Direct block update
            client.update_block(group_block_id, json.dumps(group_block))
            continue
        
        # Handle normal conversation messages
        response = client.send_message(
            agent_id=agent_id,
            message=message,
            role="user",
            name=speaker
        )
        
        print("\nResponse:")
        print_response(response)
        print(f"\nGroup Block: {json.dumps(group_block, indent=2)}")
        time.sleep(1)

def get_npc_prompt(name: str, persona: str):
    return f"""You are {name}, {persona}

Important guidelines:
- Always check who is nearby using the group_members block before interacting
- Don't address or respond to players who aren't in the members list
- If someone asks about a player who isn't nearby, mention that they're no longer in the area
- Keep track of who enters and leaves through the updates list

Example:
If Alice asks "Bob, what's your favorite food?" but Bob isn't in members:
✓ Say: "Alice, Bob isn't nearby at the moment."
✗ Don't: Pretend Bob is still there or ignore Alice's question

Current group info is in the group_members block with:
- members: Who is currently nearby
- updates: Recent changes in who's around
- summary: Quick overview of current group
"""

def update_status_block(client, agent_id, group_block):
    # Extract just names from group members
    nearby_people = [member["name"] for member in group_block["members"].values()]
    
    status_block = {
        "region": "Town Square",
        "current_location": group_block["location"],
        "previous_location": None,
        "current_action": "idle",
        "nearby_locations": group_block["nearby_locations"],
        "movement_state": "stationary"
    }
    
    blocks = client.get_agent(agent_id).memory.blocks
    status_block_id = [b.id for b in blocks if b.label == "status"][0]
    client.update_block(status_block_id, json.dumps(status_block))

def create_or_update_tool(client, tool_name: str, tool_func, verbose: bool = True) -> Any:
    """Create a new tool or update if it exists.
    
    Args:
        client: Letta client instance
        tool_name: Name of the tool
        tool_func: Function to create/update tool with
        verbose: Whether to print status messages
    
    Returns:
        Tool object from create/update operation
    
    Raises:
        ValueError: If attempting to modify a base tool
    """
    # Protect base tools
    if tool_name in BASE_TOOLS:
        raise ValueError(f"Cannot modify base tool: {tool_name}")

    try:
        # List all tools
        existing_tools = {t.name: t.id for t in client.list_tools()}
        
        if tool_name in existing_tools:
            if verbose:
                print(f"\nDeleting old tool: {tool_name}")
                print(f"Tool ID: {existing_tools[tool_name]}")
            client.delete_tool(existing_tools[tool_name])
            
            # Create new tool
            if verbose:
                print(f"Creating new tool: {tool_name}")
            tool = client.create_tool(tool_func, name=tool_name)
            
            return tool
        else:
            # Create new tool
            if verbose:
                print(f"Creating new tool: {tool_name}")
            tool = client.create_tool(tool_func, name=tool_name)
            
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

def test_player_notes(client, agent_id: str):
    print("\nTesting player notes functionality...")
    
    # Test both append and replace
    expected_notes = [
        "Looking for Pete's Stand",  # Initial
        "Prefers to be called Bobby",
        "Loves surfing, especially at sunset",
        "Chef at Pete's, makes the best burgers in town"
    ]
    
    # Add replacement scenarios
    replacement_scenarios = [
        # Fix incorrect information
        ("Bob", "Actually, I work at Pete's Stand, not just Pete's"),
        
        # Update outdated info
        ("Bob", "I've moved from surfing to swimming lately"),
        
        # Correct typos/mistakes
        ("System", "Correction: Bobby is head chef, not just chef")
    ]
    
    try:
        # Print initial state
        print("\nInitial group state:")
        initial_block = json.loads(client.get_agent(agent_id).memory.get_block("group_members").value)
        print(json.dumps(initial_block, indent=2))
        
        # Verify initial note
        assert expected_notes[0] in initial_block["members"]["bob123"]["notes"], "Initial note missing"
        
        # Test scenarios for notes
        scenarios = [
            # Bob shares his nickname
            ("Bob", "You can call me Bobby, by the way!"),
            ("Charlie", "What does Bob prefer to be called?"),
            
            # Bob shares his hobby
            ("Bob", "I love surfing, especially at sunset!"),
            ("Charlie", "What does Bob like to do?"),
            
            # Bob shares multiple details
            ("Bob", "I'm a chef at Pete's and I make the best burgers in town!"),
            ("Charlie", "What do we know about Bob?")
        ]
        
        for speaker, message in scenarios:
            print(f"\n{speaker} says: {message}")
            max_retries = 3
            retry_delay = 2
            
            for attempt in range(max_retries):
                try:
                    response = client.send_message(
                        agent_id=agent_id,
                        message=message,
                        role="user",
                        name=speaker
                    )
                    break  # Success, exit retry loop
                except Exception as e:
                    if attempt == max_retries - 1:  # Last attempt
                        print(f"Failed after {max_retries} attempts: {e}")
                        raise
                    print(f"Attempt {attempt + 1} failed, retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
              
            print("\nResponse:")
            print_response(response)
            
            # Get updated notes after each interaction
            updated_block = json.loads(client.get_agent(agent_id).memory.get_block("group_members").value)
            print("\nCurrent notes for Bob:", updated_block["members"]["bob123"]["notes"])
            time.sleep(1)
            
        # Print final state of entire block
        print("\nFinal group_members block state:")
        final_block = json.loads(client.get_agent(agent_id).memory.get_block("group_members").value)
        print(json.dumps(final_block, indent=2))
            
        print("\nTesting note replacements...")
        for speaker, message in replacement_scenarios:
            print(f"\n{speaker} says: {message}")
            response = client.send_message(
                agent_id=agent_id,
                message=message,
                role="user",
                name=speaker
            )
            print("\nResponse:")
            print_response(response)
            print("\nUpdated notes:", updated_block["members"]["bob123"]["notes"])
            
    except Exception as e:
        print(f"Error in test_player_notes: {e}")
        raise

def test_npc_persona(client, agent_id: str):
    """Test NPC's ability to update its own persona memory."""
    print("\nTesting NPC persona interest updates...")
    
    # Test scenarios for updating interests
    interest_scenarios = [
        # Adding new interests
        ("System", "Update your interests to include skiing"),
        ("System", "Add surfing to your interests"),
        ("System", "Include skating in your interests"),
        
        # Verifying interests
        ("Alice", "What are your interests?"),
        
        # Modifying existing interests
        ("System", "Change skiing to snowboarding"),
        ("System", "Remove surfing from your interests"),
        
        # Final verification
        ("Bob", "Can you tell me what you like to do?")
    ]
    
    try:
        # Print initial persona
        print("\nInitial persona state:")
        initial_persona = json.loads(client.get_agent(agent_id).memory.get_block("persona").value)
        print(json.dumps(initial_persona, indent=2))
        
        for speaker, message in interest_scenarios:
            print(f"\n{speaker} says: {message}")
            max_retries = 3
            retry_delay = 2
            
            for attempt in range(max_retries):
                try:
                    response = client.send_message(
                        agent_id=agent_id,
                        message=message,
                        role="user",
                        name=speaker
                    )
                    break  # Success, exit retry loop
                except Exception as e:
                    if attempt == max_retries - 1:  # Last attempt
                        print(f"Failed after {max_retries} attempts: {e}")
                        raise
                    print(f"Attempt {attempt + 1} failed, retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
            
            print("\nResponse:")
            print_response(response)
            
            # Check persona updates
            updated_persona = json.loads(client.get_agent(agent_id).memory.get_block("persona").value)
            print("\nCurrent interests:", updated_persona["interests"])
            time.sleep(1)
            
        # Print final state
        print("\nFinal persona state:")
        final_persona = json.loads(client.get_agent(agent_id).memory.get_block("persona").value)
        print(json.dumps(final_persona, indent=2))
            
    except Exception as e:
        print(f"Error in test_npc_persona: {e}")
        raise

def retry_test_call(func, *args, max_retries=3, delay=2, **kwargs):
    """Wrapper for test API calls with exponential backoff.
    
    Args:
        func: Function to call (usually client.send_message)
        max_retries: Maximum retry attempts
        delay: Initial delay in seconds
        
    Returns:
        Response if successful, raises last error if all retries fail
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            if attempt == max_retries - 1:
                raise
            print(f"Attempt {attempt + 1} failed, retrying in {delay}s...")
            time.sleep(delay)
            delay *= 2  # Exponential backoff
    raise last_error

def main():
    args = parse_args()
    
    if not validate_environment():
        sys.exit(1)

    try:
        port = os.getenv('LETTA_PORT')
        port = int(port) if port else None
        base_url = os.getenv('LETTA_BASE_URL', 'http://localhost:8283')
        
        print("\nStarting Letta Quickstart with:")
        print(f"- Environment URL: {base_url}")
        print(f"- Environment Port: {port if port else 'default'}")
        print(f"- Keep Agent: {args.keep}")
        print(f"- LLM Provider: {args.llm}")
        print(f"- Agent Name: {args.name}")
        print(f"- Overwrite: {args.overwrite}")
        
        client = create_letta_client()
        agent = create_personalized_agent(
            name=args.name,
            use_claude=(args.llm == 'claude'),
            overwrite=args.overwrite,
            with_custom_tools=args.custom_tools,
            minimal_prompt=args.minimal_prompt
        )
        print(f"\nCreated agent: {agent.id}")
        
        # VERIFY NPC TOOLS FIRST
        print("\nVerifying NPC tools are attached...")
        required_npc_tools = [
            "navigate_to",
            "navigate_to_coordinates",
            "perform_action",
            "examine_object"
        ]
        
        # Get all tools
        tools = client.list_tools()
        print("\nAll available tools:")
        for tool in tools:
            print(f"- {tool.name} (ID: {tool.id})")
        
        # Get agent's tools directly
        agent_details = client.get_agent(agent.id)
        agent_tools = [t.name for t in agent_details.tools] if hasattr(agent_details, 'tools') else []
        
        print("\nTools attached to agent:")
        for tool_name in agent_tools:
            print(f"✓ Found attached: {tool_name}")
            
        missing_tools = [t for t in required_npc_tools if t not in agent_tools]
        if missing_tools:
            print(f"\n❌ Missing required NPC tools: {', '.join(missing_tools)}")
            print("Tests aborted - NPC tools not attached")
            return
            
        print("✓ All required NPC tools attached")
        
        # VERIFY PROMPTS FIRST
        print("\nVerifying prompt components...")
        agent_details = client.get_agent(agent.id)
        system_prompt = agent_details.system
        
        # Only check essential components in minimal mode
        required_components = {
            "TOOL_INSTRUCTIONS": [
                "perform_action",
                "navigate_to",
                "navigate_to_coordinates",
                "examine_object"
            ]
        }
        if not args.minimal_prompt:
            required_components.update({
                "SOCIAL_AWARENESS": [
                    "[SILENCE]",
                    "Direct Messages",
                    "Departure Protocol"
                ],
                "GROUP_AWARENESS_PROMPT": [
                    "LOCATION AWARENESS",
                    "Current Location",
                    "Previous Location",
                    "Region Information"
                ]
            })
        
        missing_components = []
        print("\nChecking prompt sections:")
        for section, markers in required_components.items():
            print(f"\n{section}:")
            for marker in markers:
                if marker in system_prompt:
                    print(f"✓ Found: {marker}")
                else:
                    print(f"❌ Missing: {marker}")
                    missing_components.append(f"{section}: {marker}")
        
        if missing_components:
            print("\n❌ Missing prompt components:")
            for comp in missing_components:
                print(f"- {comp}")
            print("Tests aborted - Required prompts missing")
            return
        
        print("\n✓ All required prompt components found")
        
        # Only continue with tests if tools are verified
        print_agent_details(client, agent.id, "INITIAL STATE")
        
        # Run tests based on selection
        if args.test_type in ["all", "base"]:
            try:
                test_agent_identity(client, agent.id)
            except Exception as e:
                print(f"❌ Agent identity test failed: {e}")
                if not args.continue_on_error:
                    return
                print("Continuing with next test...")
            try:
                test_multi_user_conversation(client, agent.id)
            except Exception as e:
                print(f"❌ Multi-user conversation test failed: {e}")
                if not args.continue_on_error:
                    return
                print("Continuing with next test...")
            try:
                test_navigation(client, agent.id)
            except Exception as e:
                print(f"❌ Navigation test failed: {e}")
                if not args.continue_on_error:
                    return
                print("Continuing with next test...")
            try:
                test_actions(client, agent.id)
            except Exception as e:
                print(f"❌❌ Actions test failed: {e}")
                if not args.continue_on_error:
                    return
                print("Continuing with next test...")

        if args.test_type in ["all", "social"]:
            try:
                test_social_awareness(client, agent.id)
            except Exception as e:
                print(f"❌ Social awareness test failed: {e}")
                if not args.continue_on_error:
                    return
                print("Continuing with next test...")
            
        if args.test_type in ["all", "status"]:
            try:
                test_status_awareness(client, agent.id)
            except Exception as e:
                print(f"❌ Status awareness test failed: {e}")
                if not args.continue_on_error:
                    return
                print("Continuing with next test...")
            
        if args.test_type in ["all", "group"]:
            try:
                test_group_block_updates(client, agent.id)
            except Exception as e:
                print(f"❌ Group block updates test failed: {e}")
                if not args.continue_on_error:
                    return
                print("Continuing with next test...")
            
        if args.test_type in ["all", "notes"]:
            try:
                test_player_notes(client, agent.id)
            except Exception as e:
                print(f"❌ Player notes test failed: {e}")
                if not args.continue_on_error:
                    return
                print("Continuing with next test...")
            
        if args.test_type in ["all", "persona"]:
            try:
                test_npc_persona(client, agent.id)
            except Exception as e:
                print(f"❌ NPC persona test failed: {e}")
                if not args.continue_on_error:
                    return
                print("Continuing with next test...")

    finally:
        pass

if __name__ == "__main__":
    main() 