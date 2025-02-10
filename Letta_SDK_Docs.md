# Letta LocalClient Documentation

## Quick Start

The fastest way to connect to a Letta server is using the `create_client` factory function:

```python
from letta import create_client

# Connect to the server
client = create_client(base_url="http://localhost:8283")

# Example: Send a message to an agent
response = client.send_message(
    agent_id="your-agent-id", 
    role="user", 
    message="Hello!"
)
```

This method automatically handles server configuration and is the recommended way to initialize the client.

## Overview
`LocalClient` is a client class for Letta that corresponds to a single user. It provides methods for managing agents, tools, data sources, and memory.

## Class Definition

### LocalClient
```python
class LocalClient(AbstractClient)
```

#### Attributes
- `auto_save` (bool): Whether to automatically save changes
- `user_id` (str): The user ID
- `debug` (bool): Whether to print debug information
- `interface` (QueuingInterface): The interface for the client
- `server` (SyncServer): The server for the client

## Constructor

### __init__
```python
def __init__(auto_save: bool = False, user_id: Optional[str] = None, debug: bool = False)
```
Initializes a new instance of Client class.

## Agent Management Methods

### agent_exists
```python
def agent_exists(agent_id: Optional[str] = None, agent_name: Optional[str] = None) -> bool
```
Check if an agent exists by ID or name.

### create_agent
```python
def create_agent(
    name: Optional[str] = None,
    embedding_config: Optional[EmbeddingConfig] = None,
    llm_config: Optional[LLMConfig] = None,
    memory: Memory = ChatMemory(
        human=get_human_text(DEFAULT_HUMAN),
        persona=get_persona_text(DEFAULT_PERSONA)
    ),
    system: Optional[str] = None,
    tools: Optional[List[str]] = None,
    include_base_tools: Optional[bool] = True,
    metadata: Optional[Dict] = {
        "human:": DEFAULT_HUMAN,
        "persona": DEFAULT_PERSONA
    },
    description: Optional[str] = None
) -> AgentState
```
Create a new agent with specified configuration.

### update_agent
```python
def update_agent(
    agent_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    system: Optional[str] = None,
    tools: Optional[List[str]] = None,
    metadata: Optional[Dict] = None,
    llm_config: Optional[LLMConfig] = None,
    embedding_config: Optional[EmbeddingConfig] = None,
    message_ids: Optional[List[str]] = None,
    memory: Optional[Memory] = None
)
```
Update an existing agent's configuration.

### rename_agent
```python
def rename_agent(agent_id: str, new_name: str)
```
Rename an existing agent.

### delete_agent
```python
def delete_agent(agent_id: str)
```
Delete an agent by ID.

### get_agent
```python
def get_agent(agent_id: str) -> AgentState
```
Get an agent's state by ID.

### get_agent_id
```python
def get_agent_id(agent_name: str) -> AgentState
```
Get an agent's ID by name.

## Memory Management Methods

### get_in_context_memory
```python
def get_in_context_memory(agent_id: str) -> Memory
```
Get the in-context (core) memory of an agent.

### update_in_context_memory
```python
def update_in_context_memory(agent_id: str, section: str, value: Union[List[str], str]) -> Memory
```
Update the in-context memory of an agent.

### get_archival_memory_summary
```python
def get_archival_memory_summary(agent_id: str) -> ArchivalMemorySummary
```
Get a summary of an agent's archival memory.

### get_recall_memory_summary
```python
def get_recall_memory_summary(agent_id: str) -> RecallMemorySummary
```
Get a summary of an agent's recall memory.

### get_in_context_messages
```python
def get_in_context_messages(agent_id: str) -> List[Message]
```
Get in-context messages of an agent.

## Communication Methods

### send_message
```python
def send_message(
    message: str,
    role: str,
    agent_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    stream_steps: bool = False,
    stream_tokens: bool = False,
    include_full_message: Optional[bool] = False
) -> LettaResponse
```
Send a message to an agent.

### user_message
```python
def user_message(
    agent_id: str,
    message: str,
    include_full_message: Optional[bool] = False
) -> LettaResponse
```
Send a message to an agent as a user.

### run_command
```python
def run_command(agent_id: str, command: str) -> LettaResponse
```
Run a command on the agent.

## Human and Persona Management

### create_human
```python
def create_human(name: str, text: str)
```
Create a human block template.

### create_persona
```python
def create_persona(name: str, text: str)
```
Create a persona block template.

### list_humans
```python
def list_humans()
```
List available human block templates.

### list_personas
```python
def list_personas() -> List[Persona]
```
List available persona block templates.

### update_human
```python
def update_human(human_id: str, text: str)
```
Update a human block template.

### update_persona
```python
def update_persona(persona_id: str, text: str)
```
Update a persona block template.

### get_persona
```python
def get_persona(id: str) -> Persona
```
Get a persona block template.

### get_human
```python
def get_human(id: str) -> Human
```
Get a human block template.

### get_persona_id
```python
def get_persona_id(name: str) -> str
```
Get the ID of a persona block template.

### get_human_id
```python
def get_human_id(name: str) -> str
```
Get the ID of a human block template.

### delete_persona
```python
def delete_persona(id: str)
```
Delete a persona block template.

### delete_human
```python
def delete_human(id: str)
```
Delete a human block template.

## Tool Management

### add_tool
```python
def add_tool(tool: Tool, update: Optional[bool] = True) -> Tool
```
Add a tool directly.

### create_tool
```python
def create_tool(
    func,
    name: Optional[str] = None,
    update: Optional[bool] = True,
    tags: Optional[List[str]] = None
) -> Tool
```
Create a tool from a function.

### update_tool
```python
def update_tool(
    id: str,
    name: Optional[str] = None,
    func: Optional[callable] = None,
    tags: Optional[List[str]] = None
) -> Tool
```
Update a tool.

### list_tools
```python
def list_tools()
```
List available tools.

### get_tool
```python
def get_tool(id: str) -> Optional[Tool]
```
Get a tool by ID.

### delete_tool
```python
def delete_tool(id: str)
```
Delete a tool.

### get_tool_id
```python
def get_tool_id(name: str) -> Optional[str]
```
Get a tool's ID by name.

## Data Source Management

### load_data
```python
def load_data(connector: DataConnector, source_name: str)
```
Load data into a source.

### load_file_into_source
```python
def load_file_into_source(filename: str, source_id: str, blocking=True)
```
Load a file into a source.

### create_source
```python
def create_source(name: str) -> Source
```
Create a new source.

### delete_source
```python
def delete_source(source_id: str)
```
Delete a source.

### get_source
```python
def get_source(source_id: str) -> Source
```
Get a source by ID.

### get_source_id
```python
def get_source_id(source_name: str) -> str
```
Get a source's ID by name.

### attach_source_to_agent
```python
def attach_source_to_agent(
    agent_id: str,
    source_id: Optional[str] = None,
    source_name: Optional[str] = None
)
```
Attach a source to an agent.

### detach_source_from_agent
```python
def detach_source_from_agent(
    agent_id: str,
    source_id: Optional[str] = None,
    source_name: Optional[str] = None
)
```
Detach a source from an agent.

### list_sources
```python
def list_sources() -> List[Source]
```
List available sources.

### list_attached_sources
```python
def list_attached_sources(agent_id: str) -> List[Source]
```
List sources attached to an agent.

### update_source
```python
def update_source(source_id: str, name: Optional[str] = None) -> Source
```
Update a source.

## Archival Memory Management

### insert_archival_memory
```python
def insert_archival_memory(agent_id: str, memory: str) -> List[Passage]
```
Insert archival memory into an agent.

### delete_archival_memory
```python
def delete_archival_memory(agent_id: str, memory_id: str)
```
Delete archival memory from an agent.

### get_archival_memory
```python
def get_archival_memory(
    agent_id: str,
    before: Optional[str] = None,
    after: Optional[str] = None,
    limit: Optional[int] = 1000
) -> List[Passage]
```
Get archival memory from an agent with pagination.

### get_messages
```python
def get_messages(
    agent_id: str,
    before: Optional[str] = None,
    after: Optional[str] = None,
    limit: Optional[int] = 1000
) -> List[Message]
```
Get messages from an agent with pagination.

## Model Management

### list_models
```python
def list_models() -> List[LLMConfig]
```
List available LLM models.

### list_embedding_models
```python
def list_embedding_models() -> List[EmbeddingConfig]
```
List available embedding models.

## Block Management

### list_blocks
```python
def list_blocks(
    label: Optional[str] = None,
    templates_only: Optional[bool] = True
) -> List[Block]
```
List available blocks.

### create_block
```python
def create_block(name: str, text: str, label: Optional[str] = None) -> Block
```
Create a block.

### update_block
```python
def update_block(
    block_id: str,
    value: str,
    name: Optional[str] = None
) -> Block
```
Updates a block's content.

Arguments:
- `block_id` (str): The ID of the block to update
- `value` (str): The new content for the block
- `name` (Optional[str]): Optional new name for the block

Returns:
- `Block`: The updated block

Example:
```python
# Update a block's content
client.update_block(
    block_id="block-123",
    value="New block content"
)
```

### get_block
```python
def get_block(block_id: str) -> Block
```
Get a block by ID.

### delete_block
```python
def delete_block(id: str) -> Block
```
Delete a block.



[Previous documentation content remains the same...]

# Data Models

## AgentState
```python
class AgentState(BaseAgent)
```

Representation of an agent's state at a given time, persisted in the DB backend.

### Arguments
- `id` (str): Unique identifier of the agent
- `name` (str): Name of the agent (unique to the user)
- `created_at` (datetime): Creation datetime
- `message_ids` (List[str]): IDs of messages in agent's in-context memory
- `memory` (Memory): In-context memory of the agent
- `tools` (List[str]): Tools used by the agent
- `system` (str): System prompt
- `llm_config` (LLMConfig): LLM configuration
- `embedding_config` (EmbeddingConfig): Embedding configuration

## Block
```python
class Block(BaseBlock)
```

Represents a reserved section of the LLM's context window.

### Arguments
- `name` (str): Block name
- `value` (str): Block value represented in context window
- `limit` (int): Character limit
- `template` (bool): Whether block is a template
- `label` (str): Block category label
- `description` (str): Block description
- `metadata_` (Dict): Block metadata
- `user_id` (str): Associated user ID

## Tool
```python
class Tool(BaseTool)
```

Represents a callable function for the agent.

### Arguments
- `id` (str): Unique tool identifier
- `name` (str): Function name
- `tags` (List[str]): Metadata tags
- `source_code` (str): Function source code
- `json_schema` (Dict): Function JSON schema

### Methods

#### to_dict
```python
def to_dict()
```
Convert tool to OpenAI representation.

#### from_langchain
```python
@classmethod
def from_langchain(cls, langchain_tool) -> "Tool"
```
Create Tool instance from Langchain tool.

#### from_crewai
```python
@classmethod
def from_crewai(cls, crewai_tool) -> "Tool"
```
Create Tool instance from crewAI BaseTool.

## Memory
```python
class Memory(BaseModel)
```

Represents agent's in-context memory.

### Attributes
- `memory` (Dict[str, Block]): Memory block mapping

### Methods

#### get_prompt_template
```python
def get_prompt_template() -> str
```
Returns current Jinja2 template string.

[Additional Memory methods documented...]

### Derived Classes

#### BasicBlockMemory
```python
class BasicBlockMemory(Memory)
```
Basic Memory implementation with editable blocks.

#### ChatMemory
```python
class ChatMemory(BasicBlockMemory)
```
Initializes memory with default human and persona blocks.

## LLMConfig
```python
class LLMConfig(BaseModel)
```

Configuration for Language Model.

### Attributes
- `model` (str): LLM model name
- `model_endpoint_type` (str): Endpoint type
- `model_endpoint` (str): Model endpoint
- `model_wrapper` (str): Model wrapper
- `context_window` (int): Context window size

## EmbeddingConfig
```python
class EmbeddingConfig(BaseModel)
```

Embedding model configuration.

### Attributes
- `embedding_endpoint_type` (str): Endpoint type
- `embedding_endpoint` (str): Model endpoint
- `embedding_model` (str): Model name
- `embedding_dim` (int): Embedding dimension
- `embedding_chunk_size` (int): Chunk size
- `azure_endpoint` (str, optional): Azure endpoint
- `azure_version` (str): Azure version
- `azure_deployment` (str): Azure deployment

## User
```python
class User(UserBase)
```

Represents a user.

### Arguments
- `id` (str): Unique user identifier
- `name` (str): User name
- `created_at` (datetime): Creation date

# Response Models

## LettaResponse
```python
class LettaResponse(BaseModel)
```

Response from agent interaction.

### Attributes
- `messages` (List[Union[Message, LettaMessage]]): Agent response messages
- `usage` (LettaUsageStatistics): Usage statistics

## LettaUsageStatistics
```python
class LettaUsageStatistics(BaseModel)
```

Usage statistics for agent interaction.

### Attributes
- `completion_tokens` (int): Generated tokens count
- `prompt_tokens` (int): Prompt tokens count
- `total_tokens` (int): Total processed tokens
- `step_count` (int): Agent steps count

# Message Types

## Message
```python
class Message(BaseMessage)
```

Internal message representation.

### Attributes
- `id` (str): Message identifier
- `role` (MessageRole): Participant role
- `text` (str): Message text
- `user_id` (str): User identifier
- `agent_id` (str): Agent identifier
- `model` (str): Model used
- `name` (str): Participant name
- `created_at` (datetime): Creation time
- `tool_calls` (List[ToolCall]): Tool calls
- `tool_call_id` (str): Tool call ID

[Additional Message methods documented...]

## LettaMessage
```python
class LettaMessage(BaseModel)
```

Simplified message response type.

### Attributes
- `id` (str): Message ID
- `date` (datetime): Creation date

### Derived Classes

#### InternalMonologue
```python
class InternalMonologue(LettaMessage)
```
Agent's internal monologue.

#### FunctionCallMessage
```python
class FunctionCallMessage(LettaMessage)
```
Function call request message.

#### FunctionReturn
```python
class FunctionReturn(LettaMessage)
```
Function return value message.
