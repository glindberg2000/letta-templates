import argparse
import os
import sys
from dotenv import load_dotenv
from .letta_local_client import LocalAPIClient
from letta_client import (
    EmbeddingConfig,
    LlmConfig,
    Memory,
    Block,
    Tool,
    Letta
)
import time
import json

# Load environment variables from .env file
print("\nChecking environment setup:")
print(f"Current directory: {os.getcwd()}")
print(f"Looking for .env file...")

env_file = os.path.join(os.getcwd(), '.env')
letta_v2_env = os.path.join(os.getcwd(), 'letta-v2', '.env')

if os.path.exists(env_file):
    print(f"Found .env file at: {env_file}")
elif os.path.exists(letta_v2_env):
    print(f"Found .env file in letta-v2: {letta_v2_env}")
    load_dotenv(letta_v2_env, override=True)
else:
    print("Warning: No .env file found in current directory")
    # Try parent directory
    parent_env = os.path.join(os.path.dirname(os.getcwd()), '.env')
    if os.path.exists(parent_env):
        print(f"Found .env file in parent directory: {parent_env}")
        load_dotenv(parent_env, override=True)
    else:
        print("Warning: No .env file found in parent directory either")

# Get required environment variables with defaults
LETTA_BASE_URL = os.getenv('LETTA_BASE_URL')
LETTA_API_KEY = os.getenv('LETTA_API_KEY')

if not LETTA_BASE_URL:
    print("Warning: LETTA_BASE_URL not found in environment")
if not LETTA_API_KEY:
    print("Warning: LETTA_API_KEY not found in environment")

def list_all_agents(client):
    """List all available agents with their IDs, names, and memory blocks."""
    try:
        agents = client.agents.list()
        print("\nAvailable Agents:")
        for agent in agents:
            print(f"\nAgent ID: {agent.id}")
            print(f"Name: {agent.name}")
            
            # Get memory blocks for each agent
            try:
                agent = client.agents.retrieve(agent.id)  # Use retrieve() instead of get_by_id()
                memory = agent.memory
                print("\nMemory Blocks:")
                for block in memory.blocks:
                    print(f"  • {block.label}")
                    # Pretty print JSON block values
                    try:
                        value = json.loads(block.value)
                        # Show full contents for important blocks
                        if block.label in ['group_members', 'status']:
                            preview = json.dumps(value, indent=2)
                        else:
                            preview = json.dumps(value, indent=2)[:200]  # Limit other blocks
                            if len(preview) >= 200:
                                preview += "\n    ..."
                        # Indent all lines
                        preview = '\n'.join('    ' + line for line in preview.split('\n'))
                        print(preview)
                    except json.JSONDecodeError:
                        # For non-JSON blocks, show first few lines
                        preview = block.value.split('\n')[0][:100]
                        if len(preview) == 100:
                            preview += "..."
                        print(f"    {preview}")
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
        agent = client.agents.create(
            name=name,
            embedding_config=EmbeddingConfig(
                embedding_endpoint_type="openai",
                embedding_endpoint="https://api.openai.com/v1",
                embedding_model="text-embedding-ada-002",
                embedding_dim=1536,
                embedding_chunk_size=300,
            ),
            llm_config=LlmConfig(
                model=os.getenv("LETTA_MODEL", "gpt-4o-mini"),
                model_endpoint_type=os.getenv("LETTA_ENDPOINT_TYPE", "openai"),
                model_endpoint=os.getenv("LETTA_MODEL_ENDPOINT", "https://api.openai.com/v1"),
                context_window=int(os.getenv("LETTA_CONTEXT_WINDOW", "128000")),
            ),
            memory_blocks=[{
                "label": "human",
                "value": "Name: User\nRole: A helpful user seeking assistance.",
                "limit": 2500
            }, {
                "label": "persona", 
                "value": "You are a helpful AI assistant that provides clear and concise answers.",
                "limit": 2500
            }],
            system="You are a helpful AI assistant that provides clear and concise answers.",
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

def delete_agent(client, agent_id: str, agent_name: str) -> bool:
    """Delete a single agent with error handling."""
    try:
        # First try to detach any sources
        try:
            sources = client.list_attached_sources(agent_id)
            for source in sources:
                client.detach_source_from_agent(agent_id, source.id)
        except Exception as e:
            print(f"Warning: Could not detach sources from {agent_name}: {e}")

        # Get the agent's current state
        try:
            agent = client.get_agent(agent_id)
            # Try to clean up the agent state
            client.update_agent(
                agent_id=agent_id,
                name=agent.name,  # Keep the name
                description="",   # Clear description
                system="",       # Clear system
                metadata={},     # Clear metadata
                memory=None      # Clear memory
            )
        except Exception as e:
            print(f"Warning: Could not clean up agent state: {e}")

        # Try to delete archival memory first
        try:
            memories = client.get_archival_memory(agent_id)
            for memory in memories:
                try:
                    client.delete_archival_memory(agent_id, memory.id)
                except Exception as mem_e:
                    print(f"Warning: Could not delete memory {memory.id}: {mem_e}")
        except Exception as e:
            print(f"Warning: Could not clean up archival memory: {e}")

        # Try to delete the agent
        client.delete_agent(agent_id)
        print(f"Deleted agent: {agent_name} (ID: {agent_id})")
        return True

    except Exception as e:
        if "passage_legacy" in str(e):
            print(f"Warning: Legacy passage format issue for {agent_name}")
            try:
                # Try minimal update before delete
                client.update_agent(
                    agent_id=agent_id,
                    name=agent_name,
                    description=""
                )
                # Try delete again
                client.delete_agent(agent_id)
                print(f"Successfully deleted agent after cleanup: {agent_name}")
                return True
            except Exception as retry_e:
                print(f"Error in retry deletion: {retry_e}")
        else:
            print(f"Error deleting agent {agent_id}: {e}")
        return False

def chat_with_agent(client, agent_id, message):
    """
    Send a message to an agent and display the response.
    """
    try:
        response = client.send_message(
            agent_id=agent_id,
            message=message,
            role="user"
        )
        
        print("\nResponse messages:")
        if hasattr(response, 'messages'):
            for msg in response.messages:
                # Handle ToolCallMessage
                if type(msg).__name__ == 'ToolCallMessage':
                    if hasattr(msg, 'tool_call'):
                        print(f"\nTool Call: {msg.tool_call.name}")
                        try:
                            args = json.loads(msg.tool_call.arguments)
                            print(f"Arguments: {json.dumps(args, indent=2)}")
                        except:
                            print(f"Raw arguments: {msg.tool_call.arguments}")
                
                # Handle ToolReturnMessage
                elif type(msg).__name__ == 'ToolReturnMessage':
                    print("\nTool Return:")
                    try:
                        if hasattr(msg, 'tool_return'):
                            result = json.loads(msg.tool_return)
                            if 'message' in result:
                                inner_result = json.loads(result['message'])
                                print(json.dumps(inner_result, indent=2))
                            else:
                                print(json.dumps(result, indent=2))
                            print(f"Status: {msg.status}")
                    except:
                        print(f"Raw return: {msg.tool_return}")
                
                # Handle ReasoningMessage
                elif type(msg).__name__ == 'ReasoningMessage':
                    if hasattr(msg, 'reasoning'):
                        print(f"\nReasoning: {msg.reasoning}")
                
                # Handle regular Message
                elif hasattr(msg, 'text') and msg.text:
                    print(f"\nResponse: {msg.text}")
        
        # Print usage statistics
        if hasattr(response, 'usage'):
            print("\nUsage Statistics:")
            print(json.dumps(response.usage.dict(), indent=2))
                    
    except Exception as e:
        print(f"Error chatting with agent: {e}")
        import traceback
        traceback.print_exc()

def create_letta_client(base_url=None, port=None):
    """Create a client for direct Letta server communication."""
    if base_url == "memory://":
        print("Using in-memory Letta server")
        return Letta(token=LETTA_API_KEY)
    else:
        if port:
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(base_url)
            base_url = urlunparse(parsed._replace(netloc=f"{parsed.hostname}:{port}"))
        print(f"Connecting to Letta server at: {base_url}")
        return Letta(base_url=base_url, token=LETTA_API_KEY)

def is_legacy_agent(agent_name: str) -> bool:
    """Check if this is a legacy NPC agent."""
    return agent_name.startswith('npc_') and len(agent_name.split('_')) >= 3

def list_problematic_agents(client):
    """List agents that can't be deleted and might cause name collisions."""
    try:
        agents = client.list_agents()
        problematic = []
        
        for agent in agents:
            try:
                # Try to delete the agent
                client.delete_agent(agent.id)
                print(f"Successfully deleted test agent: {agent.name}")
            except Exception as e:
                if "passage_legacy" in str(e):
                    problematic.append(agent)
                    print(f"Warning: Undeletable agent found: {agent.name}")
                    print(f"         ID: {agent.id}")
                    print(f"         This name may cause conflicts if reused.")

        return problematic
    except Exception as e:
        print(f"Error checking agents: {e}")
        return []

def delete_all_agents(client):
    """Delete all agents from the server."""
    print("\nFound the following agents:")
    try:
        agents = client.agents.list()
        if not agents:
            print("No agents found.")
            return

        # First identify problematic agents
        problematic_names = set()
        for agent in agents:
            try:
                print(f"- {agent.name} (ID: {agent.id})")
                if "passage_legacy" in str(agent.id):  # Quick check for potential issues
                    problematic_names.add(agent.name)
            except Exception:
                pass

        if problematic_names:
            print("\nWARNING: The following agent names cannot be deleted and may cause")
            print("         conflicts if Roblox tries to recreate agents with these names:")
            for name in problematic_names:
                print(f"         - {name}")
            print("\nConsider using different names for new agents in Roblox.")

        confirm = input("\nAre you sure you want to delete ALL agents? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Operation cancelled.")
            return

        success_count = 0
        fail_count = 0
        
        for agent in agents:
            try:
                print(f"\nDeleting {agent.name}...")
                client.agents.delete(agent.id)
                print(f"Successfully deleted {agent.name}")
                success_count += 1
            except Exception as e:
                if "passage_legacy" in str(e):
                    print(f"Failed to delete {agent.name}: This appears to be an early test agent")
                    print(f"Agent ID: {agent.id}")
                    print(f"WARNING: This name may cause conflicts if reused in Roblox")
                else:
                    print(f"Failed to delete {agent.name}: {e}")
                fail_count += 1

        print(f"\nDeletion complete:")
        print(f"Successfully deleted: {success_count} agents")
        if fail_count > 0:
            print(f"Failed to delete: {fail_count} agents")
            print("\nIMPORTANT:")
            print("1. Some agents could not be deleted (early test agents)")
            print("2. Avoid reusing these names in Roblox to prevent conflicts")
            print("3. Consider using different name suffixes for new agents")

    except Exception as e:
        print(f"Error listing/deleting agents: {e}")

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
    Display detailed information about an agent including system prompt, tools, and memory blocks.
    
    Args:
        client: Letta client instance
        agent_id (str): ID of the agent to query
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
        
        # Display tools
        print("\nTools Configuration:")
        if hasattr(agent, 'tools') and agent.tools:
            for tool in agent.tools:
                print(f"\nTool: {tool.name}")
                if tool.description:
                    print(f"Description: {tool.description}")
                if tool.source_type:
                    print(f"Source Type: {tool.source_type}")
                if tool.module:
                    print(f"Module: {tool.module}")
                if tool.tags:
                    print(f"Tags: {', '.join(tool.tags)}")
                if tool.json_schema:
                    print("Schema:")
                    print(json.dumps(tool.json_schema, indent=2))
        else:
            print("No custom tools attached")
            
        if hasattr(agent, 'include_base_tools'):
            print(f"\nBase Tools: {'Enabled' if agent.include_base_tools else 'Disabled'}")
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

def list_global_tools(client):
    """
    List all globally available tools.
    
    Args:
        client: Letta client instance
        
    Example output:
        Available Global Tools:
        
        Tool: send_message
        Description: Send a message to the user
        Module: letta.tools.messaging
        Tags: messaging, core
        Schema: {
          "type": "object",
          "properties": {
            "message": {"type": "string"}
          }
        }
        --------------------------------------------------
    """
    try:
        tools = client.list_tools()
        if not tools:
            print("\nNo global tools available")
            return
        
        print("\nAvailable Global Tools:")
        for tool in tools:
            print(f"\nTool: {tool.name}")
            if tool.description:
                print(f"Description: {tool.description}")
            if tool.source_type:
                print(f"Source Type: {tool.source_type}")
            if tool.module:
                print(f"Module: {tool.module}")
            if tool.tags:
                print(f"Tags: {', '.join(tool.tags)}")
            if tool.json_schema:
                print("Schema:")
                print(json.dumps(tool.json_schema, indent=2))
            print("-" * 50)
            
    except Exception as e:
        print(f"Error listing global tools: {e}")

def get_tool_details(client, tool_id):
    """
    Get detailed information about a specific tool.
    
    Args:
        client: Letta client instance
        tool_id: ID of the tool to inspect
    """
    try:
        tool = client.get_tool(tool_id)
        if not tool:
            print(f"\nTool with ID {tool_id} not found")
            return
            
        print(f"\nTool Details:")
        print(f"ID: {tool.id}")
        print(f"Name: {tool.name}")
        if tool.description:
            print(f"Description: {tool.description}")
        if tool.source_type:
            print(f"Source Type: {tool.source_type}")
        if tool.module:
            print(f"Module: {tool.module}")
        if tool.tags:
            print(f"Tags: {', '.join(tool.tags)}")
        if tool.source_code:
            print("\nSource Code:")
            print(tool.source_code)
        if tool.json_schema:
            print("\nSchema:")
            print(json.dumps(tool.json_schema, indent=2))
        print("-" * 50)
            
    except Exception as e:
        print(f"Error getting tool details: {e}")

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
    create_parser.add_argument('--llm', 
        choices=['openai', 'claude'], 
        default='openai',
        help='Choose LLM provider (default: openai)')
    
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
    
    # Add tools command
    tools_parser = subparsers.add_parser('tools', 
        help='Tool management commands')
    tools_subparsers = tools_parser.add_subparsers(
        dest='tools_command',
        help='Tool command to execute')
      
    # Add tool commands
    tools_subparsers.add_parser('list',
        help='List all tools')
    tools_subparsers.add_parser('get',
        help='Get tool details')
    # Add delete subcommand with name argument
    delete_parser = tools_subparsers.add_parser('delete', 
        help='Delete a specific tool')
    delete_parser.add_argument('name', 
        help='Name of tool to delete')
    
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
    
    # Add near the start of main():
    print(f"Environment LETTA_BASE_URL: {os.getenv('LETTA_BASE_URL')}")
    print(f"Args URL: {args.url}")
    
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
    elif args.command == 'tools':
        if args.tools_command == 'list':
            tools = client.list_tools()
            print("\nAll Available Tools:")
            for tool in tools:
                print(f"\nTool: {tool.name}")
                print(f"ID: {tool.id}")
                if tool.description:
                    print(f"Description: {tool.description}")
                if tool.tags:
                    print(f"Tags: {', '.join(tool.tags)}")
                if tool.module:
                    print(f"Module: {tool.module}")
        elif args.tools_command == 'delete':
            tools = client.list_tools()
            deleted = False
            for tool in tools:
                if tool.name == args.name:
                    client.delete_tool(tool.id)
                    print(f"Deleted tool: {tool.name}")
                    deleted = True
                    break
            if not deleted:
                print(f"Tool '{args.name}' not found")
    else:
        parser.print_help()

if __name__ == '__main__':
    main() 