import os
from dotenv import load_dotenv
from letta import EmbeddingConfig, LLMConfig, create_client, ChatMemory, BasicBlockMemory
from letta.schemas.tool_rule import ToolRule, TerminalToolRule, InitToolRule
from letta.prompts import gpt_system
import json
import time
import argparse
from typing import Optional
import sys
from letta.schemas.tool import ToolUpdate
from letta.schemas.message import (
    ToolCallMessage, 
    ToolReturnMessage, 
    ReasoningMessage, 
    Message
)
from letta_templates.npc_tools import (
    TOOL_INSTRUCTIONS,
    GROUP_AWARENESS_PROMPT,
    navigate_to,
    navigate_to_coordinates,
    perform_action,
    examine_object,
    TOOL_REGISTRY
)
import requests
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Load environment variables
load_dotenv()

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
            model="gpt-4o-mini",
            model_endpoint_type="openai",
            model_endpoint="https://api.openai.com/v1",
            context_window=128000,
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
    custom_registry: dict = None
):
    """Create a personalized agent with modern tool registration"""
    if client is None:
        client = create_letta_client()
        
    # Clean up existing agents if overwrite is True
    if overwrite:
        cleanup_agents(client, name)
    
    # Add timestamp to name to avoid conflicts
    timestamp = int(time.time())
    unique_name = f"{name}_{timestamp}"
    
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
                value=f"I am {name}, a helpful NPC guide. I help players navigate and explore the game world.",
                limit=2000
            ),
            client.create_block(
                label="human", 
                value="A Roblox player exploring the game",
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
                limit=5000
            ),
            # Add new block for user states
            client.create_block(
                label="user_states",
                value=json.dumps({
                    "users": {}  # Empty dict to start
                }),
                limit=5000
            ),
            # Add initial status block
            client.create_block(
                label="status",
                value=json.dumps({
                    "region": "Town Square",
                    "location": "Main Plaza",
                    "current_action": "idle",
                    "nearby_people": [],
                    "nearby_locations": ["Cafe", "Garden"]
                }),
                limit=5000
            )
        ]
    )

    # Create tool instructions with proper docstrings
    tool_instructions = """
    Performing actions:
    IMPORTANT: You MUST use these tools for navigation - do not just send messages!
    
    1. navigate_to: REQUIRED for moving to locations with slugs
       Example: navigate_to("petes_stand")
       You MUST call this before sending any message about navigation
    
    2. navigate_to_coordinates: REQUIRED for moving to coordinates
       Example: navigate_to_coordinates(15.5, 20.0, -110.8)
       You MUST call this before sending any message about navigation
    
    3. perform_action: Required for NPC actions
       Example: perform_action("follow", target="player1")
    
    4. examine_object: Required for examining objects
       Example: examine_object("treasure_chest")
    
    CRITICAL: You must ALWAYS use the appropriate navigation tool BEFORE sending any message about movement.
    Failure to use navigation tools will result in the player being unable to move.
    """

    # Add multi-user awareness to system prompt
    multi_user_instructions = """
    IMPORTANT: You are speaking with multiple users in a shared space. 
    Each message will include the name of the speaker.
    When responding:
    1. Address users by their names
    2. Keep track of who asked what
    3. If multiple users are involved in a conversation, make sure to acknowledge each person
    4. When giving directions, consider that multiple users might be following them
    """

    # Add to existing tool instructions
    group_tool_instructions = """
    Group Management:
    1. group_navigate: Move multiple users together
       Example: group_navigate(["Alice", "Bob"], "petes_stand")
    
    2. group_gather: Gather users at a location
       Example: group_gather(["Alice", "Bob", "Charlie"], "fountain")
    """

    # Modify system prompt to remove Letta/Limnal references
    base_system = gpt_system.get_system_text("memgpt_chat")
    base_system = base_system.replace(
        "You are Letta, the latest version of Limnal Corporation's digital companion",
        f"You are {name}, a helpful NPC guide in this game world"
    )
    
    system_prompt = (
        base_system + 
        TOOL_INSTRUCTIONS +  # Enhanced with movement initiative
        GROUP_AWARENESS_PROMPT  # Our new comprehensive group awareness
    )
    
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
    print(f"Include base tools: {True}")
    
    # Create agent
    agent = client.create_agent(
        name=unique_name,
        system=system_prompt,
        memory=memory,
        llm_config=llm_config,
        embedding_config=embedding_config,
        include_base_tools=True
    )
    
    # Register tools with debug info
    if with_custom_tools:
        print("\nRegistering tools:")
        for name, tool_func in TOOL_REGISTRY.items():
            try:
                print(f"\nCreating tool: {name}")
                print(f"Function: {tool_func.__name__}")
                print(f"Docstring: {tool_func.__doc__}")
                tool = client.create_tool(tool_func, name=name)
                print(f"Tool created with ID: {tool.id}")
                client.add_tool_to_agent(agent.id, tool.id)
                print(f"Tool {name} added to agent {agent.id}")
            except Exception as e:
                print(f"Error adding tool {name}: {e}")
                raise  # Re-raise to see full traceback

    # List tools to verify
    print("\nVerifying registered tools:")
    tools = client.list_tools()
    for tool in tools:
        print(f"Found tool: {tool.name} (ID: {tool.id})")

    print("\nDEBUG: Available tools in TOOL_REGISTRY:")
    for name, func in TOOL_REGISTRY.items():
        print(f"- {name}: {func}")

    # Then explicitly attach each tool
    print("\nAttaching tools to agent:")
    tools = client.list_tools()
    for tool in tools:
        try:
            print(f"Attaching {tool.name} to agent...")
            client.add_tool_to_agent(agent.id, tool.id)
            print(f"Successfully attached {tool.name}")
        except Exception as e:
            print(f"Failed to attach {tool.name}: {e}")

    # Verify tools are attached by getting agent details
    print("\nVerifying agent tools:")
    updated_agent = client.get_agent(agent.id)
    if hasattr(updated_agent, 'tools'):
        print(f"Agent has {len(updated_agent.tools)} tools:")
        for tool in updated_agent.tools:
            print(f"- {tool.name}")
    else:
        print("Note: Agent tools can only be verified through usage")

    # Add version check
    print("\nChecking Letta versions:")
    try:
        import letta
        print(f"Letta client version: {letta.__version__}")
        
        # Get server version from env
        server_url = os.getenv('LETTA_BASE_URL', 'http://localhost:8283')
        response = requests.get(f"{server_url}/version")
        print(f"Letta server version: {response.json()['version']}")
    except Exception as e:
        print(f"Warning: Could not check versions: {e}")

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
    parser.add_argument(
        "--test-type",
        choices=["all", "base", "social", "status"],  # Added "status"
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
    
    # Test follow with system command
    print("\nTesting follow action...")
    response = client.send_message(
        agent_id=agent_id,
        message="Use perform_action to follow the player 'TestUser'",
        role="system",
        name="GameSystem"  # More appropriate system identity
    )
    print_response(response)
    
    # Test emote
    print("\nTesting emote action...")
    response = client.send_message(
        agent_id=agent_id,
        message="Use perform_action to wave at the player",
        role="system",
        name="GameSystem"
    )
    print_response(response)
    
    # Test unfollow
    print("\nTesting unfollow action...")
    response = client.send_message(
        agent_id=agent_id,
        message="Use perform_action to stop following the player",
        role="system",
        name="GameSystem"
    )
    print_response(response)

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
    
    # Initialize states at the start
    states = {"users": {}}  # Initialize empty states dictionary
    
    def update_user_state(name: str, location: str = None, following: str = None):
        # Get current states
        memory = client.get_in_context_memory(agent_id)
        user_states_block = next(b for b in memory.blocks if b.label == "user_states")
        states = json.loads(user_states_block.value)
        
        # Update state
        if name not in states["users"]:
            states["users"][name] = {"location": None, "following": None}
        
        if location:
            states["users"][name]["location"] = location
        if following is not None:  # Allow setting to None
            states["users"][name]["following"] = following
            
        # Save back to memory
        client.update_block(
            block_id=user_states_block.id,
            value=json.dumps(states)
        )
        return states["users"]
    
    # Process each message in the conversation
    for name, message in conversation:
        print(f"\n{name} says: {message}")
        response = client.send_message(
            agent_id=agent_id,
            message=message,
            role="user",
            name=name
        )
        
        # Track tool usage and update memory
        for msg in response.messages:
            if isinstance(msg, ToolCallMessage):
                tool = msg.tool_call
                if tool.name == "navigate_to":
                    states["users"] = update_user_state(
                        name, 
                        location=json.loads(tool.arguments)["destination"]
                    )
                elif tool.name == "perform_action" and "follow" in tool.arguments:
                    states["users"] = update_user_state(
                        name,
                        following=json.loads(tool.arguments)["target"]
                    )
        
        print("\nResponse:")
        print_response(response)
        print(f"\nUser States: {json.dumps(states, indent=2)}")
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
    
    def update_user_state(name: str, location: str = None, following: str = None):
        """Update user state in memory"""
        if name not in states["users"]:
            states["users"][name] = {"location": None, "following": None}
        
        if location:
            states["users"][name]["location"] = location
        if following is not None:
            states["users"][name]["following"] = following
            
        return states["users"]
    
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
    
    states = {"users": {}}
    
    for name, message in social_tests:
        print(f"\n{name} says: {message}")
        response = client.send_message(
            agent_id=agent_id,
            message=message,
            role="user",
            name=name
        )
        
        # Track and verify proper tool usage
        tool_calls = []
        message_contents = []
        
        for msg in response.messages:
            if isinstance(msg, ToolCallMessage):
                tool = msg.tool_call
                tool_calls.append(tool)
                if tool.name == "send_message":
                    message_contents.append(json.loads(tool.arguments)["message"])
                
                if tool.name == "navigate_to":
                    states["users"] = update_user_state(
                        name, 
                        location=json.loads(tool.arguments)["destination"]
                    )
                elif tool.name == "perform_action":
                    args = json.loads(tool.arguments)
                    if args.get("action") == "follow":
                        states["users"] = update_user_state(
                            name,
                            following=args.get("target")
                        )
        
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
                
        # Verify [SILENCE] in direct messages
        if "@" in message or message.lower().startswith(("hey ", "hi ")):
            target = message.split()[1].strip("@,!")
            if target != "Emma":  # Use agent name
                if any("[SILENCE]" in msg for msg in message_contents):
                    print("✓ Correctly remained silent in direct message")
                else:
                    print("✗ Should have remained silent")
        
        print("\nResponse:")
        print_response(response)
        print(f"\nTool Calls: {json.dumps([t.name for t in tool_calls], indent=2)}")
        print(f"User States: {json.dumps(states, indent=2)}")
        time.sleep(1)

def test_status_awareness(client, agent_id: str):
    """Test NPC's use of status information"""
    print("\nTesting status awareness...")
    
    # Define test scenarios
    scenarios = [
        {
            "status": {
                "location": "Main Plaza",
                "nearby_locations": ["Cafe", "Garden"]
            },
            "messages": [
                ("Alice", "Are you at the Cafe?"),
                ("Bob", "What's around here?")
            ]
        },
        {
            "status": {
                "location": "Cafe",
                "nearby_locations": ["Garden", "Main Plaza"]
            },
            "messages": [
                ("Alice", "Did you make it to the Cafe?"),
                ("Charlie", "What can we do nearby?")
            ]
        },
        {
            "status": {
                "location": "Pete's Stand",
                "nearby_locations": ["Fountain", "Shop Row"]
            },
            "messages": [
                ("Diana", "Where are you now?"),
                ("Bob", "What's good around here?")
            ]
        }
    ]
    
    # Get the memory object first
    memory = client.get_in_context_memory(agent_id)
    status_block = next((b for b in memory.blocks if b.label == "status"), None)
    
    if not status_block:
        print("Warning: No status block found in agent memory")
        return
        
    print(f"Found status block: {status_block.id}")
    
    for scenario in scenarios:
        print(f"\nTesting scenario with status: {json.dumps(scenario['status'], indent=2)}")
        
        try:
            # Force a complete status reset
            full_status = {
                "region": scenario["status"]["location"],
                "location": scenario["status"]["location"],
                "current_action": "idle",
                "nearby_people": [],
                "nearby_locations": scenario["status"]["nearby_locations"],
                "previous_location": None,  # Explicitly clear history
                "movement_state": "stationary"  # Explicitly set as stationary
            }
            
            print(f"\nUpdating status to:")
            print(json.dumps(full_status, indent=2))
            
            # Update status block
            client.update_block(
                block_id=status_block.id,
                value=json.dumps(full_status)
            )
            
            # Verify update with system message
            client.send_message(
                agent_id=agent_id,
                message=f"Your location is now: {scenario['status']['location']}. Acknowledge.",
                role="system"
            )
            
            # Small delay to ensure status update is processed
            time.sleep(0.5)
            
            # Continue with test messages...
            for name, message in scenario["messages"]:
                print(f"\n{name} says: {message}")
                response = client.send_message(
                    agent_id=agent_id,
                    message=message,
                    role="user",
                    name=name
                )
                
                # After getting response, evaluate it
                eval_result = evaluate_response_with_claude(
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
                time.sleep(1)
                
        except Exception as e:
            print(f"Failed to update status block: {str(e)}")
            continue

def evaluate_response_with_claude(response_text: str, current_status: dict, message: str):
    """Use Claude Haiku to evaluate NPC response quality"""
    
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_EVAL_KEY")
    if not ANTHROPIC_API_KEY:
        print("Warning: No Claude API key for evaluation")
        return None
        
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    evaluation_prompt = f"""
    Evaluate this NPC response. Return ONLY a JSON object.
    
    CURRENT STATUS:
    Location: {current_status['location']}
    Nearby: {', '.join(current_status['nearby_locations'])}
    
    USER: "{message}"
    NPC: "{response_text}"
    
    Return this exact JSON format with no additional text:
    {{
        "location_aware": true or false,
        "nearby_accurate": true or false,
        "contextually_appropriate": true or false,
        "explanation": "brief explanation"
    }}
    """
    
    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json={
                "model": "claude-3-haiku-20240307",
                "max_tokens": 1024,
                "messages": [
                    {"role": "system", "content": "You are a JSON validator. Return only valid JSON objects."},
                    {"role": "user", "content": evaluation_prompt}
                ]
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['content'][0]['text'].strip()
            # Remove any markdown formatting
            content = content.replace('```json\n', '').replace('\n```', '').strip()
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                print(f"Failed to parse Claude response: {content}")
                return None
        else:
            print(f"Claude API error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Evaluation failed: {str(e)}")
        return None

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
            with_custom_tools=args.custom_tools
        )
        print(f"\nCreated agent: {agent.id}")
        print_agent_details(client, agent.id, "INITIAL STATE")
        
        # Run tests based on selection
        if args.test_type in ["all", "base"]:
            test_agent_identity(client, agent.id)
            test_multi_user_conversation(client, agent.id)
            test_navigation(client, agent.id)
            test_actions(client, agent.id)
        
        if args.test_type in ["all", "social"]:
            test_social_awareness(client, agent.id)
            
        if args.test_type in ["all", "status"]:
            test_status_awareness(client, agent.id)

    finally:
        pass

if __name__ == "__main__":
    main() 