import os
from dotenv import load_dotenv
from letta import EmbeddingConfig, LLMConfig, create_client, ChatMemory
from letta.prompts import gpt_system
import json
import time
import argparse

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

def chat_with_agent(client, agent_id: str, message: str):
    """
    Send a message to an agent and return the response.
    
    Args:
        client: Letta client instance
        agent_id (str): ID of the agent to chat with
        message (str): Message to send to the agent
    
    Returns:
        str: Agent's response message or None if no valid response
    
    Example:
        >>> response = chat_with_agent(
        ...     client,
        ...     agent.id,
        ...     "Can you help optimize this Lua code?"
        ... )
        
        Sending message: Can you help optimize this Lua code?
        Response: I'd be happy to help optimize your Lua code...
    """
    print(f"\nSending message: {message}")
    response = client.send_message(
        agent_id=agent_id,
        role="user",
        message=message
    )
    
    # Extract actual response message
    for msg in response.messages:
        if hasattr(msg, 'function_call'):
            try:
                args = json.loads(msg.function_call.arguments)
                if 'message' in args:
                    return args['message']
            except:
                pass
    return None

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

def main():
    # Add argument parsing
    parser = argparse.ArgumentParser(description='Letta Quickstart Tool')
    parser.add_argument('--keep', action='store_true', help='Keep the agent after testing (do not cleanup)')
    args = parser.parse_args()

    # Initialize the client using environment variable or default to Docker version
    port = os.getenv('LETTA_PORT')  # Get port from environment if set
    port = int(port) if port else None  # Convert to int if exists
    base_url = os.getenv('LETTA_BASE_URL', 'http://localhost:8283')
    
    print("\nStarting Letta Quickstart with:")
    print(f"- Environment URL: {base_url}")
    print(f"- Environment Port: {port if port else 'default'}")
    print(f"- Keep Agent: {args.keep}")
    
    client = create_letta_client(base_url, port)

    try:
        # Create a Roblox development agent
        agent = create_roblox_agent(client, "RobloxHelper")
        print(f"\nCreated agent: {agent.id}")
        
        # Print initial configuration
        print_agent_details(client, agent.id, "INITIAL STATE")

        # Example chat
        response = chat_with_agent(client, agent.id, 
            "Can you help me optimize a Lua script for my Roblox game?")
        print(f"Response: {response}")

        # Example updating persona
        new_blocks = {
            "human": "Name: RobloxDev\nRole: A senior Roblox developer focusing on performance optimization",
            "persona": "You are an AI expert in Roblox development, specializing in performance optimization and best practices."
        }
        update_agent_persona(client, agent.id, new_blocks)
        print("\nUpdated agent persona")
        
        # Print updated configuration
        print_agent_details(client, agent.id, "AFTER UPDATE")

        # Test the updated persona
        response = chat_with_agent(client, agent.id, 
            "Now that you're focused on optimization, what's your approach to performance tuning?")
        print(f"Response: {response}")

        if args.keep:
            print(f"\nKeeping agent for examination: {agent.id}")
        else:
            client.delete_agent(agent.id)
            print(f"\nCleaned up agent: {agent.id}")

    finally:
        pass

if __name__ == "__main__":
    main() 