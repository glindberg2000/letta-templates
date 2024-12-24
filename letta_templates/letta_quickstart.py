import os
from dotenv import load_dotenv
from letta import EmbeddingConfig, LLMConfig, create_client, ChatMemory
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
from letta_templates.npc_tools import TOOL_INSTRUCTIONS, TOOL_REGISTRY, navigate_to, examine_object, perform_action
import requests

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
            human="Name: RobloxDev\nRole: A Roblox developer working on game development",
            persona=persona or "You are a knowledgeable AI assistant with expertise in Roblox development, Lua programming, and game design."
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

def chat_with_agent(client, agent_id: str, message: str, role: str = "user") -> str:
    """
    Send a chat message to an agent and return the response.
    """
    try:
        # Send message and get response
        response = client.send_message(
            agent_id=agent_id,
            message=message,
            role=role
        )
        
        # Extract the actual message content
        return extract_message_from_response(response)
        
    except Exception as e:
        print(f"Error in chat_with_agent: {e}")
        raise

def create_letta_client():
    """Create Letta client with configuration"""
    base_url = os.getenv("LETTA_BASE_URL", "http://localhost:8283")  # Default to local
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

def create_personalized_agent(
    name: str = "emma_research_assistant",
    client = None,
    use_claude: bool = False,
    overwrite: bool = False,
    with_custom_tools: bool = False,
    custom_registry = None  # Add parameter for custom registry
):
    """Create a personalized agent with tools"""
    # Use passed client or create new one
    if client is None:
        client = create_letta_client()

    # Add timestamp to name to make it unique
    timestamp = int(time.time())
    unique_name = f"{name}_{timestamp}"
    print(f"Creating agent with unique name: {unique_name}")
    
    # Get base system prompt
    system_prompt = gpt_system.get_system_text("memgpt_chat")
    
    # Add location knowledge
    location_knowledge = """
    Known Locations:
    - Pete's Stand
      Description: A friendly food stand run by Pete
      Location: (-12.0, 18.9, -127.0)
      Slug: petes_stand
    """
    
    system_prompt = system_prompt.replace(
        "Base instructions finished.",
        location_knowledge + "\n" + TOOL_INSTRUCTIONS + "\nBase instructions finished."
    )

    # Create agent
    agent = client.create_agent(
        name=unique_name,
        system=system_prompt,
        include_base_tools=True,
        llm_config=LLMConfig(
            model="gpt-4o-mini",
            model_endpoint_type="openai",
            model_endpoint="https://api.openai.com/v1",
            context_window=128000,
        ),
        embedding_config=EmbeddingConfig(
            embedding_endpoint_type="openai",
            embedding_endpoint="https://api.openai.com/v1",
            embedding_model="text-embedding-ada-002",
            embedding_dim=1536,
            embedding_chunk_size=300,
        )
    )

    # Register tools if requested
    if with_custom_tools:
        # Use custom registry if provided, otherwise use default
        registry_to_use = custom_registry if custom_registry else TOOL_REGISTRY
        for name, info in registry_to_use.items():
            tool = client.create_tool(info["function"], name=name)
            print(f"Created tool: {name} (ID: {tool.id})")
            client.add_tool_to_agent(agent.id, tool.id)

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
    parser = argparse.ArgumentParser(description='Letta Quickstart Tool')
    parser.add_argument('--keep', action='store_true', 
                      help='Keep the agent after testing (do not cleanup)')
    parser.add_argument('--llm', choices=['openai', 'claude'], default='openai', 
                      help='Choose LLM provider (default: openai)')
    parser.add_argument('--name', default='emma_assistant', 
                      help='Name for the agent (default: emma_assistant)')
    parser.add_argument('--overwrite', action='store_true',
                      help='Overwrite existing agent with same name')
    parser.add_argument('--skip-test', action='store_true',
                      help='Skip the test message verification')
    parser.add_argument('--custom-tools', action='store_true',
                      help='Create agent with custom tools')
    parser.add_argument('--test', choices=['navigate', 'examine', 'all'], 
                      help='Run specific test (navigate, examine) or all')
    parser.add_argument(
        "--use-api",
        action="store_true",
        help="Route chat messages through FastAPI instead of direct to Letta"
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

def send_chat_message(message: str, agent_id: str, use_api: bool = False) -> dict:
    """Send chat message either directly or through API"""
    if use_api:
        print("\n=== Using FastAPI Endpoint ===")
        
        # Use real NPC ID
        npc_id = get_test_npc()
        
        request = {
            "npc_id": npc_id,  # Use Pete's ID instead of agent_id
            "participant_id": "test_user_1",
            "message": message,
            "context": {
                "participant_type": "player",
                "participant_name": "TestUser"
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
        return client.chat(message, agent_id)

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

def test_navigation(agent_id: str, use_api: bool = False):
    """Test navigation without API"""
    print("\nTesting navigation...")
    
    try:
        # Direct tool test
        result = navigate_to("Pete's stand", request_heartbeat=True)
        print(f"\nNavigation result: {json.dumps(result, indent=2)}")
        
        # Verify response format
        assert "status" in result, "Missing status field"
        assert "message" in result, "Missing message field"
        
        if result["status"] == "success":
            assert "coordinates" in result, "Missing coordinates in success response"
            coords = result["coordinates"]
            print(f"\nFound coordinates: ({coords['x']}, {coords['y']}, {coords['z']})")
        else:
            print(f"\nNavigation failed: {result['message']}")
            
    except Exception as e:
        print(f"\nError in navigation test: {type(e).__name__}: {str(e)}")
        raise

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

def main():
    args = parse_args()
    
    # Validate environment before proceeding
    if not validate_environment():
        sys.exit(1)

    try:
        if args.use_api:
            # Skip agent creation, just test API with existing NPC
            print("\nTesting with existing NPC (Pete)...")
            test_api_navigation()
        else:
            # Normal flow for direct testing
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
            
            client = create_letta_client(base_url, port)
            agent = create_personalized_agent(
                name=args.name,
                use_claude=(args.llm == 'claude'),
                overwrite=args.overwrite,
                with_custom_tools=args.custom_tools
            )
            print(f"\nCreated agent: {agent.id}")
            print_agent_details(client, agent.id, "INITIAL STATE")
            test_navigation(agent.id, use_api=False)

    finally:
        pass

if __name__ == "__main__":
    main() 