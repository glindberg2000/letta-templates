from letta import EmbeddingConfig, LLMConfig, create_client, ChatMemory
from letta.prompts import gpt_system

def cleanup_agent(client, agent_id):
    try:
        client.delete_agent(agent_id)
        print(f"\nCleaned up agent: {agent_id}")
    except Exception as e:
        print(f"Error cleaning up agent: {e}")

def list_all_agents(client):
    try:
        agents = client.list_agents()
        print("\nAll Available Agents:")
        for agent in agents:
            print(f"ID: {agent.id}")
            print(f"Name: {agent.name}")
            print(f"Description: {agent.description}")
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

def update_memory_blocks(client, agent_id, human_text=None, persona_text=None):
    try:
        memory = client.get_in_context_memory(agent_id)
        for block in memory.blocks:
            if block.label == 'human' and human_text:
                client.update_block(block_id=block.id, value=human_text)
                print(f"Updated human block: {block.id}")
            elif block.label == 'persona' and persona_text:
                client.update_block(block_id=block.id, value=persona_text)
                print(f"Updated persona block: {block.id}")
    except Exception as e:
        print(f"Error updating memory blocks: {e}")

try:
    # Initialize the client using the factory function
    client = create_client(base_url="http://localhost:8283")

    # List existing agents before creating a new one
    print("Existing agents before creation:")
    list_all_agents(client)

    # Create a simple agent with full configuration
    agent = client.create_agent(
        name="TestAgent9",
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
        description="A test agent to verify our setup"
    )

    print(f"Created agent with ID: {agent.id}")

    # Get initial memory state
    initial_memory = client.get_in_context_memory(agent.id)
    print(f"Initial memory configuration:")
    print(initial_memory)

    # Test initial message
    response = client.send_message(
        agent_id=agent.id,
        role="user",
        message="Hello! Who am I and who are you?"
    )

    for msg in response.messages:
        if hasattr(msg, 'function_call'):
            try:
                import json
                args = json.loads(msg.function_call.arguments)
                if 'message' in args:
                    print(f"Response: {args['message']}")
            except:
                pass

    # Let's try updating the blocks directly
    # First, get the current blocks
    memory = client.get_in_context_memory(agent.id)
    for block in memory.blocks:
        if block.label == 'human':
            human_block_id = block.id
            client.update_block(
                block_id=human_block_id,
                value="Name: Alice\nRole: A curious tech enthusiast who loves learning about AI."
            )
        elif block.label == 'persona':
            persona_block_id = block.id
            client.update_block(
                block_id=persona_block_id,
                value="You are Claude, a knowledgeable AI assistant with expertise in technology and programming."
            )

    # Get updated memory state
    updated_memory = client.get_in_context_memory(agent.id)
    print("\nAfter memory update:")
    print(updated_memory)

    # Test after update
    response = client.send_message(
        agent_id=agent.id,
        role="user",
        message="Hello again! Who am I and who are you now?"
    )

    for msg in response.messages:
        if hasattr(msg, 'function_call'):
            try:
                args = json.loads(msg.function_call.arguments)
                if 'message' in args:
                    print(f"Response: {args['message']}")
            except:
                pass

    # Get and display memory blocks
    get_memory_blocks(client, agent.id)

    # Update memory blocks with new values
    new_human = "Name: Alice\nRole: A curious tech enthusiast who loves learning about AI."
    new_persona = "You are Claude, a knowledgeable AI assistant with expertise in technology and programming."
    update_memory_blocks(client, agent.id, new_human, new_persona)

    # Display updated memory blocks
    print("\nAfter updating memory blocks:")
    get_memory_blocks(client, agent.id)

    # Rest of your existing code...

finally:
    # Clean up the agent
    if 'agent' in locals():
        cleanup_agent(client, agent.id)