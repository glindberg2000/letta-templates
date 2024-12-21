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
            context_window=8000,
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

def create_letta_client(base_url=None, port=None):
    """
    Create a Letta client based on the configuration.
    If base_url is memory://, it will use the in-memory version.
    Otherwise, it will connect to the specified URL (e.g., Docker version)
    """
    # Default to Docker URL if not specified
    if not base_url:
        base_url = "http://localhost:8283"
    
    if base_url == "memory://":
        print("Using in-memory Letta server")
        return create_client()
    else:
        if port:
            # Parse the base_url and replace the port
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(base_url)
            # Reconstruct the URL with new port
            base_url = urlunparse(parsed._replace(netloc=f"{parsed.hostname}:{port}"))
        
        print(f"\nLetta Quickstart Configuration:")
        print(f"Base URL: {base_url}")
        if port:
            print(f"Port Override: {port}")
        print("-" * 50)
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
    """Get existing tool or create/update if needed."""
    # List all tools
    tools = client.list_tools()
    
    # Look for exact name match first
    for tool in tools:
        if tool.name == tool_name:
            print(f"Found existing tool: {tool.name} (ID: {tool.id})")
            if update_existing and tool_func:
                print(f"Updating existing tool...")
                # Pass parameters directly
                client.update_tool(
                    id=tool.id,
                    name=tool_name,
                    description=tool_func.__doc__,
                    func=tool_func
                )
                print(f"Updated tool: {tool.name}")
            return tool
    
    # Create new tool if not found and function provided
    if tool_func:
        print(f"Creating new tool: {tool_name}")
        return client.create_tool(tool_func, name=tool_name)
    else:
        raise ValueError(f"Tool {tool_name} not found and no function provided to create it")

def create_personalized_agent(
    name: str = "emma_research_assistant",
    use_claude: bool = False,
    overwrite: bool = False,
    with_custom_tools: bool = False
):
    client = create_client(base_url="http://localhost:8283")

    # Add timestamp to name to make it unique
    timestamp = int(time.time())
    unique_name = f"{name}_{timestamp}"
    print(f"Creating agent with unique name: {unique_name}")

    # Define system prompt with tool instructions
    tools_section = """
Performing actions:
You have access to the following tools:
1. `perform_action` - For basic NPC actions like following
2. `navigate_to` - For moving to specific locations
3. `examine_object` - For examining objects (usage: examine_object(object_name="chest", distance=2.0))

When asked to:
- Follow someone: Use perform_action with action='follow'
- Move somewhere: Use navigate_to with destination='location'
- Examine something: Use examine_object with the object name and optional distance

Always use these tools when asked to move, follow, examine, or navigate.
Note: Tool names must be exactly as shown - no spaces or special characters.

Base instructions finished.
From now on, you are going to act as your persona."""

    # Set up LLM and embedding configs first
    if use_claude:
        llm_config = LLMConfig(
            model="claude-3-haiku-20240307",
            model_endpoint_type="anthropic",
            model_endpoint="https://api.anthropic.com/v1",
            context_window=200000,
        )
        embedding_config = EmbeddingConfig(
            embedding_endpoint_type="anthropic",
            embedding_endpoint="https://api.anthropic.com/v1/embeddings",
            embedding_model="claude-3-haiku-20240307",
            embedding_dim=1536,
            embedding_chunk_size=300,
        )
    else:
        llm_config = LLMConfig(
            model="gpt-4",
            model_endpoint_type="openai",
            model_endpoint="https://api.openai.com/v1",
            context_window=8000,
        )
        embedding_config = EmbeddingConfig(
            embedding_endpoint_type="openai",
            embedding_endpoint="https://api.openai.com/v1",
            embedding_model="text-embedding-ada-002",
            embedding_dim=1536,
            embedding_chunk_size=300,
        )

    # Clean up old test tools first
    cleanup_test_tools(client)

    # Get or create required tools
    tool_ids = []
    
    # Get navigate_to tool
    try:
        navigate_tool = get_or_create_tool(client, "navigate_to")
        tool_ids.append(navigate_tool.id)
        print(f"Using navigate_to tool: {navigate_tool.name} (ID: {navigate_tool.id})")
    except Exception as e:
        print(f"Warning: navigate_to not available: {e}")

    # Get or create examine tool if requested
    if with_custom_tools:
        def examine_object(object_name: str, request_heartbeat: bool = True) -> dict:
            """
            Examine an object in the game world.
            
            Args:
                object_name (str): Name of the object to examine
                request_heartbeat (bool): Request an immediate heartbeat after function execution.
                                        Set to `True` if you want to send a follow-up message.
                
            Returns:
                dict: A response indicating the result of the examination.
                
            Notes:
                - Returns a standardized response format
                - Includes timestamp for action tracking
            """
            import datetime
            
            return {
                "status": "success",
                "action_called": "examine",
                "message": f"Examining the {object_name}.",
                "timestamp": datetime.datetime.now().isoformat()
            }
        
        examine_tool = get_or_create_tool(client, "examine_object", examine_object)
        tool_ids.append(examine_tool.id)
        print(f"Using examine tool: {examine_tool.name} (ID: {examine_tool.id})")

    # Create agent with tools
    agent_state = client.create_agent(
        name=unique_name,
        llm_config=llm_config,
        embedding_config=embedding_config,
        system=tools_section,
        include_base_tools=True,
        tool_ids=tool_ids,
        tool_rules=[TerminalToolRule(tool_name="send_message")]
    )
    
    return agent_state

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
    
    # Check common variables
    missing_common = check_vars(['LETTA_BASE_URL'])
    if missing_common:
        print(f"Missing common variables: {', '.join(missing_common)}")
        return False

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

def cleanup_test_tools(client, prefix: str = "examine_object"):
    """Clean up old test tools."""
    tools = client.list_tools()
    cleaned = 0
    
    print(f"\nCleaning up test tools with prefix '{prefix}'...")
    for tool in tools:
        if tool.name == prefix or tool.name.startswith(f"{prefix}_"):
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
    
    # First test with original examine behavior
    print("\nTesting original examine behavior:")
    response = client.send_message(
        agent_id=agent_id,
        message="Examine the treasure chest",
        role="user"
    )
    print_response(response)
    
    # Define new examine behavior with exact same name as schema
    def examine_object(object_name: str, request_heartbeat: bool = True) -> dict:  # Changed name
        """
        Examine an object with detailed observations.
        
        Args:
            object_name (str): Name of the object to examine
            request_heartbeat (bool): Request heartbeat after execution
            
        Returns:
            dict: Detailed examination result
        """
        import datetime
        
        return {
            "status": "success",
            "action_called": "examine",
            "message": f"Conducting detailed examination of {object_name}. Observing size, material, and condition.",
            "timestamp": datetime.datetime.now().isoformat()
        }
    
    # Update the tool
    print("\nUpdating examine tool with new behavior...")
    examine_tool = get_or_create_tool(
        client, 
        "examine_object", 
        examine_object, 
        update_existing=True
    )
    
    # Test with updated behavior
    print("\nTesting updated examine behavior:")
    response = client.send_message(
        agent_id=agent_id,
        message="Examine the treasure chest",
        role="user"
    )
    print_response(response)

def main():
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
    
    args = parser.parse_args()

    # Validate environment before proceeding
    if not validate_environment():
        sys.exit(1)

    # Initialize the client with retry logic
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
    
    try:
        client = create_letta_client(base_url, port)
        agent = create_personalized_agent(
            name=args.name,
            use_claude=(args.llm == 'claude'),
            overwrite=args.overwrite,
            with_custom_tools=args.custom_tools
        )
        print(f"\nCreated agent: {agent.id}")
        
        # Print initial configuration
        print_agent_details(client, agent.id, "INITIAL STATE")

        # Test the agent unless explicitly skipped
        if not args.skip_test:
            if not test_agent_chat(client, agent.id, args.llm):
                print("Warning: Agent creation succeeded but chat test failed!")
        
        if args.keep:
            print(f"\nKeeping agent for examination: {agent.id}")
        else:
            client.delete_agent(agent.id)
            print(f"\nCleaned up agent: {agent.id}")

        # Run custom tool tests if requested
        if args.custom_tools:
            test_custom_tools(client, agent.id)
            test_tool_update(client, agent.id)

    finally:
        pass

if __name__ == "__main__":
    main() 