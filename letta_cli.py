import argparse
import os
from dotenv import load_dotenv
from letta import EmbeddingConfig, LLMConfig, create_client as letta_create_client, ChatMemory
from letta.prompts import gpt_system
from letta_local_client import LocalAPIClient
import time

# Load environment variables
load_dotenv()

def list_all_agents(client):
    """
    List all available agents with their details and memory blocks.
    
    Args:
        client: Letta client instance
    
    Returns:
        list: List of agents if successful, empty list on error
        
    Example:
        >>> agents = list_all_agents(client)
        
        All Available Agents:
        ID: agent-123
        Name: TestAgent
        Description: A test agent
        
        Memory Blocks:
          Human:
            Name: Alice
            Role: Developer
          Persona:
            You are an AI assistant...
        --------------------------------------------------
    """
    try:
        agents = client.list_agents()
        print("\nAll Available Agents:")
        for agent in agents:
            print(f"ID: {agent.id}")
            print(f"Name: {agent.name}")
            print(f"Description: {agent.description}")
            
            # Get memory blocks for each agent
            try:
                memory = client.get_in_context_memory(agent.id)
                print("\nMemory Blocks:")
                for block in memory.blocks:
                    if block.label in ['human', 'persona']:
                        print(f"  {block.label.capitalize()}:")
                        # Split and indent the value for better readability
                        value_lines = block.value.split('\n')
                        for line in value_lines:
                            print(f"    {line}")
            except Exception as e:
                print(f"  Unable to fetch memory blocks: {e}")
            
            print("-" * 50)
        return agents
    except Exception as e:
        print(f"Error listing agents: {e}")
        return []

def get_memory_blocks(client, agent_id):
    """
    Retrieve and display memory blocks for a specific agent.
    
    Args:
        client: Letta client instance
        agent_id (str): ID of the agent to query
        
    Returns:
        list: List of memory blocks if successful, empty list on error
        
    Example:
        >>> blocks = get_memory_blocks(client, "agent-123")
        
        Memory Blocks:
        Block ID: block-456
        Label: human
        Value: Name: Alice
              Role: Developer
        --------------------------------------------------
    """
    try:
        memory = client.get_in_context_memory(agent_id)
        print("\nMemory Blocks:")
        for block in memory.blocks:
            print(f"Block ID: {block.id}")
            print(f"Label: {block.label}")
            print(f"Value: {block.value}")
            print("-" * 50)
        return memory.blocks
    except Exception as e:
        print(f"Error getting memory blocks: {e}")
        return []

def create_test_agent(client, name="TestAgent", description="A test agent"):
    """
    Create a new agent with default configuration.
    
    Args:
        client: Letta client instance
        name (str, optional): Name for the new agent. Defaults to "TestAgent"
        description (str, optional): Description of the agent. Defaults to "A test agent"
    
    Returns:
        Agent: Created agent object if successful, None on error
        
    Example:
        >>> agent = create_test_agent(
        ...     client,
        ...     name="RobloxHelper",
        ...     description="A Roblox development assistant"
        ... )
        Created agent with ID: agent-123
    
    Note:
        Creates agent with default embedding and LLM configurations
        Includes default human and persona memory blocks
    """
    try:
        agent = client.create_agent(
            name=name,
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
                human="Name: User\nRole: A helpful user seeking assistance.",
                persona="You are a helpful AI assistant that provides clear and concise answers."
            ),
            system=gpt_system.get_system_text("memgpt_chat"),
            tools=None,
            include_base_tools=True,
            metadata={
                "human": "DEFAULT_HUMAN",
                "persona": "DEFAULT_PERSONA"
            },
            description=description
        )
        print(f"Created agent with ID: {agent.id}")
        return agent
    except Exception as e:
        print(f"Error creating agent: {e}")
        return None

def delete_agent(client, agent_id):
    """
    Delete a specific agent by ID.
    
    Args:
        client: Letta client instance
        agent_id (str): ID of the agent to delete
        
    Example:
        >>> delete_agent(client, "agent-123")
        Successfully deleted agent: agent-123
    """
    try:
        client.delete_agent(agent_id)
        print(f"Successfully deleted agent: {agent_id}")
    except Exception as e:
        print(f"Error deleting agent: {e}")

def chat_with_agent(client, agent_id, message):
    """
    Send a message to an agent and display the response.
    
    Args:
        client: Letta client instance
        agent_id (str): ID of the agent to chat with
        message (str): Message to send to the agent
        
    Example:
        >>> chat_with_agent(
        ...     client,
        ...     "agent-123",
        ...     "Hello! Can you help me with Python?"
        ... )
        Response: Hi! I'd be happy to help you with Python...
    
    Note:
        Handles function call responses and extracts message content
    """
    try:
        response = client.send_message(
            agent_id=agent_id,
            role="user",
            message=message
        )
        
        for msg in response.messages:
            if hasattr(msg, 'function_call'):
                try:
                    import json
                    args = json.loads(msg.function_call.arguments)
                    if 'message' in args:
                        print(f"Response: {args['message']}")
                except:
                    print(f"Raw response: {msg}")
    except Exception as e:
        print(f"Error chatting with agent: {e}")

def create_letta_client(base_url=None, port=None):
    """Create a client for direct Letta server communication."""
    if base_url == "memory://":
        print("Using in-memory Letta server")
        return letta_create_client()  # Use renamed import
    else:
        if port:
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(base_url)
            base_url = urlunparse(parsed._replace(netloc=f"{parsed.hostname}:{port}"))
        print(f"Connecting to Letta server at: {base_url}")
        return letta_create_client(base_url=base_url)  # Use renamed import

def delete_all_agents(client):
    """
    Delete all agents after user confirmation.
    
    Args:
        client: Letta client instance
        
    Example:
        >>> delete_all_agents(client)
        
        Found the following agents:
        - TestAgent (ID: agent-123)
        - RobloxHelper (ID: agent-456)
        
        Are you sure you want to delete ALL agents? (yes/no): yes
        Deleted agent: TestAgent (ID: agent-123)
        Deleted agent: RobloxHelper (ID: agent-456)
        
        All agents have been deleted.
    
    Note:
        Requires explicit 'yes' confirmation
        Continues with remaining deletions if one fails
    """
    try:
        agents = client.list_agents()
        if not agents:
            print("No agents to delete.")
            return

        print("\nFound the following agents:")
        for agent in agents:
            print(f"- {agent.name} (ID: {agent.id})")
        
        confirm = input("\nAre you sure you want to delete ALL agents? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Operation cancelled.")
            return

        for agent in agents:
            try:
                client.delete_agent(agent.id)
                print(f"Deleted agent: {agent.name} (ID: {agent.id})")
            except Exception as e:
                print(f"Error deleting agent {agent.id}: {e}")
        
        print("\nAll agents have been deleted.")
    except Exception as e:
        print(f"Error deleting agents: {e}")

def get_agent_messages(client, agent_id, limit=None, role=None, include_system=False, show_human=False):
    """
    Retrieve and display message history for an agent with various filtering options.
    
    Args:
        client: Letta client instance
        agent_id (str): ID of the agent
        limit (int, optional): Number of recent messages to show
        role (str, optional): Filter by message role ('user', 'assistant', 'system', 'tool')
        include_system (bool): Whether to include system messages (default: False)
        show_human (bool): Whether to display the human memory block (default: False)
    
    Example:
        >>> get_agent_messages(
        ...     client,
        ...     "agent-123",
        ...     limit=5,
        ...     role="user",
        ...     show_human=True
        ... )
        
        Messages for agent: TestAgent (ID: agent-123)
        
        Human Memory Block:
        ID: block-456
        Value: Name: Alice
              Role: Developer
        --------------------------------------------------
        Time: 2024-12-07 22:42:30
        Role: user
        Text: Hello! What can you help me with?
        --------------------------------------------------
    """
    try:
        # Get agent info first
        agent = client.get_agent(agent_id)
        print(f"\nMessages for agent: {agent.name} (ID: {agent.id})")
        
        # Show human block if requested
        if show_human:
            memory = client.get_in_context_memory(agent_id)
            print("\nHuman Memory Block:")
            for block in memory.blocks:
                if block.label == 'human':
                    print(f"ID: {block.id}")
                    print(f"Value: {block.value}")
            print("-" * 50)
        
        # Get messages
        messages = client.get_messages(agent_id)
        if not messages:
            print("No messages found.")
            return
        
        # Filter out system messages by default unless specifically requested
        if not include_system and role != 'system':
            messages = [msg for msg in messages if msg.role != 'system']
        
        # If limit is specified, only show last X messages
        if limit:
            messages = messages[-limit:]
        
        # Filter by role if specified
        if role:
            messages = [msg for msg in messages if msg.role == role]
        
        for msg in messages:
            print(f"\nTime: {msg.created_at}")
            print(f"Role: {msg.role}")
            
            # Display text content if available
            if msg.text:
                print(f"Text: {msg.text}")
            
            # Display tool calls if available
            if msg.tool_calls:
                for tool_call in msg.tool_calls:
                    print(f"Tool: {tool_call.function.name}")
                    try:
                        args = json.loads(tool_call.function.arguments)
                        if 'message' in args:
                            print(f"Message: {args['message']}")
                        else:
                            print(f"Arguments: {tool_call.function.arguments}")
                    except:
                        print(f"Raw arguments: {tool_call.function.arguments}")
            
            print("-" * 50)
            
    except Exception as e:
        print(f"Error getting messages: {e}")

def update_memory_blocks(client, agent_id, human, persona):
    """
    Update the human and/or persona memory blocks for an agent.
    
    Args:
        client: Letta client instance
        agent_id (str): ID of the agent to update
        human (str, optional): New content for human block
        persona (str, optional): New content for persona block
        
    Example:
        >>> update_memory_blocks(
        ...     client,
        ...     "agent-123",
        ...     human="Name: Bob\\nRole: Developer\\nExpertise: Python",
        ...     persona="You are a Python expert..."
        ... )
        Updated human block: block-456
        Updated persona block: block-789
        Memory blocks updated successfully.
    
    Note:
        Use \\n for newlines in the content strings.
        Both human and persona are optional - only specified blocks will be updated.
    """
    try:
        memory = client.get_in_context_memory(agent_id)
        for block in memory.blocks:
            if block.label == 'human' and human:
                client.update_block(block_id=block.id, value=human)
                print(f"Updated human block: {block.id}")
            elif block.label == 'persona' and persona:
                client.update_block(block_id=block.id, value=persona)
                print(f"Updated persona block: {block.id}")
        print("Memory blocks updated successfully.")
    except Exception as e:
        print(f"Error updating memory blocks: {e}")

def create_client(mode: str, endpoint: str = None, **kwargs):
    """Factory function to create appropriate client based on mode."""
    if mode == 'local':
        if not endpoint:
            raise ValueError("Endpoint required for local mode")
        return LocalAPIClient(endpoint)
    else:
        # Remove mode from kwargs since create_letta_client doesn't expect it
        kwargs.pop('mode', None)
        return create_letta_client(**kwargs)

def run_quick_test(client, npc_id="test-npc-1", user_id="test-user-1"):
    """Run test sequence with identifiable messages."""
    print(f"\nRunning duplicate detection test...")
    print(f"NPC ID: {npc_id}")
    print(f"User ID: {user_id}")
    print("-" * 50)
    
    # Normal messages with clear sequence numbers
    test_sequence = [
        "SEQUENCE_1: Starting test pattern",
        "SEQUENCE_2: Measuring response time",
        "SEQUENCE_3: Preparing rapid test",
        "SEQUENCE_4: Ready for rapid messages"
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
    
    # Rapid identical messages
    print("\nSending rapid messages...")
    rapid_msg = "DUPLICATE_TEST_MESSAGE_ABC_123"  # Clear, unique test message
    
    for i in range(3):
        print(f"\nRapid message {i+1}...")
        client.send_message(
            npc_id=npc_id,
            participant_id=user_id,
            message=rapid_msg
        )
        time.sleep(0.1)  # Very short delay

def get_agent_details(client, agent_id):
    """
    Display detailed information about an agent including system prompt and memory blocks.
    
    Args:
        client: Letta client instance
        agent_id (str): ID of the agent to query
        
    Example:
        >>> get_agent_details(client, "agent-123")
        
        Agent Details:
        ID: agent-123
        Name: TestAgent
        Description: A test agent
        
        System Prompt:
        You are a helpful AI assistant...
        --------------------------------------------------
        
        Memory Blocks:
        Block: human
        Value: Name: Alice
              Role: Developer
        --------------------------------------------------
    """
    try:
        # Get agent info
        agent = client.get_agent(agent_id)
        print("\nAgent Details:")
        print(f"ID: {agent.id}")
        print(f"Name: {agent.name}")
        print(f"Description: {agent.description}")
        
        # Display system prompt
        print("\nSystem Prompt:")
        print(agent.system)
        print("-" * 50)
        
        # Get memory blocks
        memory = client.get_in_context_memory(agent_id)
        print("\nMemory Blocks:")
        for block in memory.blocks:
            print(f"\nBlock: {block.label}")
            print(f"Value: {block.value}")
            print("-" * 50)
            
    except Exception as e:
        print(f"Error getting agent details: {e}")

def main():
    """
    Main CLI entry point for the Letta management tool.
    
    Provides commands for:
    - Agent management (create, list, delete)
    - Memory operations (view, update)
    - Chat functionality
    - Server configuration
    
    Environment Variables:
        LETTA_BASE_URL: Base URL for the Letta service
        LETTA_PORT: Optional port override
        
    Example Usage:
        # List all agents
        python letta_cli.py list
        
        # Create new agent
        python letta_cli.py create --name "MyAgent"
        
        # Chat with agent
        python letta_cli.py chat <agent_id> "Hello!"
        
        # Update memory
        python letta_cli.py update-memory <agent_id> --human "Name: Alice"
    """
    parser = argparse.ArgumentParser(description='Letta CLI Tool')
    parser.add_argument('--mode', 
                       choices=['local', 'letta'],
                       default='letta',
                       help='Operating mode (local for FastAPI testing)')
    parser.add_argument('--endpoint',
                       help='Local API endpoint for testing')
    parser.add_argument('--url', 
                       default=os.getenv('LETTA_BASE_URL', 'memory://'), 
                       help='Base URL for the Letta service')
    parser.add_argument('--port',
                       type=int,
                       help='Override the port number')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List agents command
    subparsers.add_parser('list', help='List all agents')
    
    # Create agent command
    create_parser = subparsers.add_parser('create', help='Create a new agent')
    create_parser.add_argument('--name', default='TestAgent', help='Name for the new agent')
    create_parser.add_argument('--description', default='A test agent', help='Description for the new agent')
    
    # Delete agent command
    delete_parser = subparsers.add_parser('delete', help='Delete an agent')
    delete_parser.add_argument('agent_id', help='ID of the agent to delete')
    
    # Get memory command
    memory_parser = subparsers.add_parser('memory', 
        help='Get memory blocks for an agent',
        description='Display the current memory blocks (human and persona) for an agent')
    memory_parser.add_argument('agent_id', help='ID of the agent')
    
    # Chat command
    chat_parser = subparsers.add_parser('chat', help='Chat with an agent')
    chat_parser.add_argument('agent_id', help='ID of the agent')
    chat_parser.add_argument('message', help='Message to send to the agent')
    
    # Add delete-all command
    subparsers.add_parser('delete-all', help='Delete all agents (with confirmation)')
    
    # Add messages command
    messages_parser = subparsers.add_parser('messages', help='View message history for an agent')
    messages_parser.add_argument('agent_id', help='ID of the agent')
    messages_parser.add_argument('--limit', type=int, help='Number of recent messages to show')
    messages_parser.add_argument('--role', choices=['user', 'assistant', 'system', 'tool'], 
                               help='Filter messages by role')
    messages_parser.add_argument('--include-system', action='store_true',
                               help='Include system messages in output')
    messages_parser.add_argument('--show-human', action='store_true',
                               help='Show the human memory block')
    
    # Add update-memory command
    update_parser = subparsers.add_parser('update-memory', 
        help='Update memory blocks for an agent',
        description='''
        Update the human or persona memory blocks for an agent.
        Example:
            Update human block:
            python letta_cli.py update-memory <agent_id> --human "Name: Alice\\nRole: Developer\\nAge: 25"
            
            Update persona block:
            python letta_cli.py update-memory <agent_id> --persona "You are a coding expert..."
        ''')
    update_parser.add_argument('agent_id', help='ID of the agent')
    update_parser.add_argument('--human', help='New content for human block (use \\n for newlines)')
    update_parser.add_argument('--persona', help='New content for persona block (use \\n for newlines)')
    
    # Add local test commands (always available)
    test_parser = subparsers.add_parser('test', help='Run local API tests')
    test_parser.add_argument('--npc-id', default='test-npc-1',
                            help='NPC ID to test with')
    test_parser.add_argument('--user-id', default='test-user-1',
                            help='User ID to test with')
    test_parser.add_argument('message', nargs='+',  # Change: Allow multiple words
                            help='Message to send')
    
    history_parser = subparsers.add_parser('history', 
        help='Show conversation history with timing')
    
    quick_test_parser = subparsers.add_parser('quick-test', 
        help='Run a quick test sequence')
    quick_test_parser.add_argument('--npc-id', default='test-npc-1',
        help='NPC ID to test with')
    quick_test_parser.add_argument('--user-id', default='test-user-1',
        help='User ID to test with')
    
    # Add details command
    details_parser = subparsers.add_parser('details', 
        help='Get detailed information about an agent',
        description='Display agent details including system prompt and memory blocks')
    details_parser.add_argument('agent_id', help='ID of the agent')
    
    args = parser.parse_args()
    
    # Validate mode and endpoint
    if args.mode == 'local' and not args.endpoint:
        parser.error("--endpoint required when using --mode local")
    
    # Create appropriate client
    client = create_client(
        mode=args.mode,
        endpoint=args.endpoint,
        base_url=args.url,
        port=args.port
    )
    
    if args.command == 'messages':
        get_agent_messages(client, args.agent_id, args.limit, args.role, 
                         args.include_system, args.show_human)
    elif args.command == 'delete-all':
        delete_all_agents(client)
    elif args.command == 'list':
        list_all_agents(client)
    elif args.command == 'create':
        create_test_agent(client, args.name, args.description)
    elif args.command == 'delete':
        delete_agent(client, args.agent_id)
    elif args.command == 'memory':
        get_memory_blocks(client, args.agent_id)
    elif args.command == 'chat':
        chat_with_agent(client, args.agent_id, args.message)
    elif args.command == 'update-memory':
        update_memory_blocks(client, args.agent_id, args.human, args.persona)
    elif args.command == 'quick-test':
        run_quick_test(client, args.npc_id, args.user_id)
    elif args.command == 'test':
        # Join multiple words back into a single message
        message = ' '.join(args.message)
        response = client.send_message(
            npc_id=args.npc_id,
            participant_id=args.user_id,
            message=message
        )
        if response:
            print(f"\nMessage sent: {message}")
            print(f"Response: {response['parsed_message']}")
            print(f"Duration: {response['duration']:.3f}s")
    elif args.command == 'details':
        get_agent_details(client, args.agent_id)
    else:
        parser.print_help()

if __name__ == '__main__':
    main() 