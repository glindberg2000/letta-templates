from letta import EmbeddingConfig, LLMConfig, create_client, ChatMemory
from letta.prompts import gpt_system
import json

def print_agent_details(client, agent_id, stage=""):
    """
    Print detailed information about an agent's configuration and memory
    """
    print(f"\n=== Agent Details {stage} ===")
    
    # Get agent configuration
    agent = client.get_agent(agent_id)
    print(f"Agent ID: {agent.id}")
    print(f"Name: {agent.name}")
    print(f"Description: {agent.description}")
    
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
    Create a Letta agent configured for Roblox development assistance
    """
    return client.create_agent(
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
            human="Name: RobloxDev\nRole: A Roblox developer working on game development",
            persona=persona or "You are a knowledgeable AI assistant with expertise in Roblox development, Lua programming, and game design."
        ),
        system=gpt_system.get_system_text("memgpt_chat"),
        include_base_tools=True,
        description="A Roblox development assistant"
    )

def update_agent_persona(client, agent_id: str, blocks):
    """
    Update an agent's memory blocks (human/persona configuration)
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
    Send a message to an agent and return the response
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

def main():
    try:
        # Initialize client
        client = create_client(base_url="http://localhost:8283")
        
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

    finally:
        # Cleanup
        if 'agent' in locals():
            client.delete_agent(agent.id)
            print(f"\nCleaned up agent: {agent.id}")

if __name__ == "__main__":
    main() 