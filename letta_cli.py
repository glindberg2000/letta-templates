import argparse
import os
from dotenv import load_dotenv
from letta import EmbeddingConfig, LLMConfig, create_client, ChatMemory
from letta.prompts import gpt_system

# Load environment variables
load_dotenv()

def list_all_agents(client):
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
    try:
        client.delete_agent(agent_id)
        print(f"Successfully deleted agent: {agent_id}")
    except Exception as e:
        print(f"Error deleting agent: {e}")

def chat_with_agent(client, agent_id, message):
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
    """
    Create a Letta client based on the configuration.
    If base_url is memory://, it will use the in-memory version.
    Otherwise, it will connect to the specified URL (e.g., Docker version)
    
    Args:
        base_url: The base URL for the Letta service
        port: Optional port override. If provided, will override the port in base_url
    """
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
        
        print(f"Connecting to Letta server at: {base_url}")
        return create_client(base_url=base_url)

def delete_all_agents(client):
    """Delete all agents after confirmation"""
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

def main():
    parser = argparse.ArgumentParser(description='Letta CLI Tool')
    parser.add_argument('--url', 
                       default=os.getenv('LETTA_BASE_URL', 'memory://'), 
                       help='Base URL for the Letta service (use memory:// for in-memory version)')
    parser.add_argument('--port',
                       type=int,
                       help='Override the port number (e.g., 8283, 8083)')
    
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
    memory_parser = subparsers.add_parser('memory', help='Get memory blocks for an agent')
    memory_parser.add_argument('agent_id', help='ID of the agent')
    
    # Chat command
    chat_parser = subparsers.add_parser('chat', help='Chat with an agent')
    chat_parser.add_argument('agent_id', help='ID of the agent')
    chat_parser.add_argument('message', help='Message to send to the agent')
    
    # Add delete-all command
    subparsers.add_parser('delete-all', help='Delete all agents (with confirmation)')

    args = parser.parse_args()
    
    # Initialize client with optional port override
    client = create_letta_client(args.url, args.port)
    
    if args.command == 'delete-all':
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
    else:
        parser.print_help()

if __name__ == '__main__':
    main() 