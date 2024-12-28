@click.command()
@click.argument('agent_id')
def inspect_memory(agent_id):
    """Show all memory blocks for an agent"""
    client = create_client()
    
    print(f"\n=== Memory Blocks for Agent {agent_id} ===")
    
    # Get memory configuration
    memory = client.get_in_context_memory(agent_id)
    print("\nMemory Blocks:")
    for block in memory.blocks:
        print(f"\nBlock: {block.label}")
        print(f"ID: {block.id}")
        print(f"Value: {block.value}")
        print(f"Limit: {block.limit}")
        print("-" * 50)

# Add to cli group
cli.add_command(inspect_memory) 