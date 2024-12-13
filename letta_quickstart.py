import os
from dotenv import load_dotenv
from letta import EmbeddingConfig, LLMConfig, create_client, ChatMemory
from letta.prompts import gpt_system
import json
import time
import argparse
from typing import Optional
import sys

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
                if getattr(message, 'message_type', '') == 'function_call':
                    function_call = getattr(message, 'function_call', None)
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

def create_personalized_agent(
    name: str = "emma_research_assistant",
    use_claude: bool = False,
    overwrite: bool = False
):
    """
    Create a personalized agent with configurable LLM settings.
    
    Args:
        name (str): Name of the agent
        use_claude (bool): If True, uses Claude 3; if False, uses OpenAI
        overwrite (bool): If True, deletes existing agent with same name before creating new one
    """
    client = create_client(base_url="http://localhost:8283")

    # Check if agent exists and handle accordingly
    try:
        existing_agents = client.list_agents()
        for agent in existing_agents:
            if agent.name == name:
                if overwrite:
                    print(f"Deleting existing agent '{name}'...")
                    client.delete_agent(agent.id)
                else:
                    raise ValueError(f"Agent with name '{name}' already exists. Use --overwrite to replace it.")
    except Exception as e:
        print(f"Error checking existing agents: {e}")
        raise

    if use_claude:
        # Claude 3 Configuration
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
        # Default OpenAI Configuration
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

    # Custom system prompt with tools section
    system_prompt = gpt_system.get_system_text("memgpt_chat").strip()
    tools_section = """
Performing actions:
You have access to the `perform_action` tool. This tool allows you to direct NPC behavior by specifying an action and its parameters. Use it to control NPC actions such as following, unfollowing, examining objects, or navigating to destinations. Ensure actions align with the context of the conversation and the NPC's role.

Base instructions finished.
From now on, you are going to act as your persona."""

    # Replace the default ending with our custom tools section
    system_prompt = system_prompt.replace(
        "Base instructions finished.\nFrom now on, you are going to act as your persona.",
        tools_section
    )

    agent_state = client.create_agent(
        name=name,
        memory=ChatMemory(
            human="""
Name: Alex Thompson
Role: Data Scientist
Interests: Machine Learning, Data Analysis, Python Programming
Communication Style: Prefers clear, technical explanations
            """.strip(),
            persona="""
Name: Emma
Role: AI Research Assistant
Personality: Professional, knowledgeable, and friendly. Enjoys explaining complex topics in simple terms.
Expertise: Data science, machine learning, and programming with a focus on Python.
Communication Style: Clear and precise, uses analogies when helpful, and maintains a supportive tone.
            """.strip()
        ),
        llm_config=LLMConfig(
            model="gpt-4o-mini",  # Using gpt-4o-mini
            model_endpoint_type="openai",
            model_endpoint="https://api.openai.com/v1",
            context_window=8000,
        ),
        embedding_config=embedding_config,
        system=system_prompt,
        include_base_tools=True,
        tools=["perform_action"],
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
    Test the agent with a simple chat message to verify it's working.
    """
    try:
        test_message = "Follow me"  # Simple, direct action request
        print(f"\nSending test message: '{test_message}'")
        
        # Get agent details for debugging
        agent = client.get_agent(agent_id)
        print(f"\nDebug: Agent configuration:")
        print(f"ID: {agent_id}")
        print(f"Model: {getattr(agent, 'model', 'unknown')}")
        
        # Send message and get response
        response = client.send_message(
            agent_id=agent_id,
            message=test_message,
            role="user"
        )
        
        if response and hasattr(response, 'messages'):
            print("\nResponse messages:")
            for msg in response.messages:
                if hasattr(msg, 'text') and msg.text:
                    print(f"Text: {msg.text}")
                elif hasattr(msg, 'function_call'):
                    print(f"Function Call: {msg.function_call.name}")
                    print(f"Arguments: {msg.function_call.arguments}")
                    if msg.function_call.name == 'perform_action':
                        print("Found perform_action call!")
                        try:
                            import json
                            args = json.loads(msg.function_call.arguments)
                            print(f"Action: {args.get('action')}")
                            print(f"Parameters: {args.get('parameters')}")
                        except Exception as e:
                            print(f"Error parsing arguments: {e}")
                elif hasattr(msg, 'function_return'):
                    print(f"Function Return: {msg.function_return}")
                    print(f"Status: {msg.status}")
                    try:
                        import json
                        result = json.loads(msg.function_return)
                        print(f"Action Result: {result}")
                    except:
                        pass
                elif hasattr(msg, 'internal_monologue'):
                    print(f"Internal Monologue: {msg.internal_monologue}")
            
            # Check if perform_action was called with 'follow'
            action_called = any(
                hasattr(msg, 'function_call') and 
                msg.function_call.name == 'perform_action' and
                'follow' in msg.function_call.arguments.lower()
                for msg in response.messages
            )
            
            if not action_called:
                print("Warning: follow action was not called")
            else:
                print("Success: follow action was called!")
                
            return True
        else:
            print("\nWarning: No valid response received from agent")
            return False
            
    except Exception as e:
        print(f"\nError testing agent chat: {e}")
        return False

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
            overwrite=args.overwrite
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

    finally:
        pass

if __name__ == "__main__":
    main() 