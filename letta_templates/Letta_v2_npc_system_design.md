Letta_v2_npc_system_design.md


NPC System Development Overhaul Proposal

New Memory Block System (2024)

Based on the current Letta integration and our proposed block enhancements, we’re introducing a streamlined memory block system that consolidates functionality, simplifies context management, and integrates new layers of shared and private memory for dynamic interactions.

Revised Memory Block System

1. Persona Block

Purpose: Stores the NPC’s identity, personality traits, and role.
Scope: Unique to each NPC.

Fields:

{
    "name": "Seraphina Stormborne",
    "role": "Captain of the Guard",
    "personality": "Honorable, stern, diplomatic",
    "interests": ["Law enforcement", "Chess"],
    "home_location": "Capital City, East Barracks"
}

Updates:
	•	Who Updates:
	•	Game designers during NPC creation.
	•	Rare in-game updates based on major events (e.g., promotions, betrayals).

2. Private Memory Block

Purpose: Tracks personal, 1:1 interactions and secrets shared with individual users.
Scope: Unique to each NPC ↔ Player/User relationship.

Fields:

{
    "PlayerA": {
        "relationship_status": "Friendly",
        "last_interaction": "Helped defend the gate",
        "trust_score": 75,
        "secrets": ["Knows about hidden tunnel under the castle"]
    }
}

Updates:
	•	Who Updates:
	•	The NPC: After private interactions, secrets shared, or relationship changes.
	•	Sub-Process: Offline updates for summarizing or cleaning older data.

3. Shared Social Block

Purpose: Stores facts and interactions the NPC is comfortable sharing across all users.
Scope: Shared among all interactions for the same NPC persona.

Fields:

{
    "recent_facts": [
        "The bridge to the castle is repaired",
        "PlayerB found the key to the treasury"
    ],
    "group_interactions": [
        {
            "participants": ["PlayerC", "PlayerD"],
            "topic": "Discussed the market fire",
            "timestamp": "2024-12-30T12:00:00Z"
        }
    ]
}

Updates:
	•	Who Updates:
	•	The NPC: After new group interactions or public discoveries.
	•	Game System: For broadcasts or common facts.

4. Global Knowledge Block

Purpose: Tracks lore, major events, and shared world data.
Scope: Shared across all NPCs and agents.

Fields:

{
    "lore": "The kingdom of Arenthia was founded 300 years ago...",
    "recent_events": [
        "Earthquake destroyed the Northern Tower",
        "King declared war on the Westlands"
    ],
    "locations": [
        {
            "name": "City Market",
            "coordinates": [345, 789],
            "description": "Bustling trade hub"
        }
    ]
}

Updates:
	•	Who Updates:
	•	Game System: Automatically when major events or map changes occur.
	•	Sub-Process: Offline summarization to manage block size.

5. Status Block

Purpose: Tracks the NPC’s real-time state and current engagement.
Scope: Unique to each NPC.

Fields:

{
    "position": [100, 50, 30],
    "engagement": "Patrolling",
    "health": 87,
    "emotion": "Calm",
    "energy_level": 65,
    "last_updated": "2024-12-30T12:00:00Z"
}

Updates:
	•	Who Updates:
	•	Game System: Real-time updates during gameplay.
	•	NPC: Changes based on actions (e.g., emotion shifts).

6. Task Block

Purpose: Maintains a prioritized list of tasks or goals for the NPC.
Scope: Unique to each NPC.

Fields:

{
    "tasks": [
        { "description": "Patrol the eastern gate", "priority": "High", "timestamp": "..." },
        { "description": "Find food", "priority": "Medium", "timestamp": "..." }
    ]
}

Updates:
	•	Who Updates:
	•	NPC: Dynamically adds/removes tasks based on decisions.
	•	Game System: Adds tasks during missions or scripted events.
	•	Sub-Process: Offline optimization or pruning of older tasks.

Integration with Existing Letta System
	1.	Consolidation:
	•	Replace current persona, human, and locations blocks with the revised blocks:
	•	Persona Block replaces the persona fields.
	•	Private and Shared Social Blocks replace interaction-related fields in the human block.
	•	Locations data moves to the Global Knowledge Block for better scalability.
	2.	Enhanced Memory Use:
	•	Introduce Status Block for real-time NPC state tracking.
	•	Add Task Block for dynamic task management, empowering NPC autonomy.
	3.	System Prompt Update:

system_prompt = f"""
Memory Usage Instructions:
1. Persona Memory:
  - Use persona data for core identity and behavior.
  - Stay consistent with your role and personality traits.

2. Private Memory:
  - Reference private interactions for unique relationships.
  - Do not share private information with other users.

3. Shared Social Memory:
  - Share public facts or notable group interactions freely.
  - Use shared memory for consistency across multiple conversations.

4. Global Knowledge:
  - Reference global events, lore, and maps for context.
  - Always align with the latest global knowledge.

5. Status Block:
  - Use current status for real-time actions and decisions.
  - Update health, emotion, and position after significant changes.

6. Task Block:
  - Use the task queue to prioritize your actions.
  - Complete tasks in order of priority before responding to new input.
"""

Implementation Plan

1. Block Overhaul
	•	Persona: Migrate current fields to new Persona Block format.
	•	Human: Split into Private Memory and Shared Social Memory.
	•	Locations: Move to Global Knowledge Block.

2. Update Agents
	•	Refactor agent creation to include new memory blocks.
	•	Replace old block usage in tools and prompts with new block references.

3. Block Update Logic
	•	Define who updates each block:
	•	Game System: Real-time updates for Status Block, major global events.
	•	NPC: Interaction-based updates for Private and Shared Social Memory, tasks.
	•	Sub-Process: Summarization and cleanup of long-term memory blocks.

4. Testing
	•	Test scenarios for:
	•	Private memory (secrets, unique interactions).
	•	Shared memory (group interactions, shared facts).
	•	Task and status updates (autonomous behavior).

5. Iterate
	•	Monitor block efficiency and scaling.
	•	Optimize summarization and data pruning as needed.

Would you like a specific implementation example for refactoring an existing NPC to use this system, or a walkthrough of testing and debugging strategies?

+ Technical Implementation Details
+ 
+ 1. Block Storage and Persistence
+ ```python
+ # Database Schema for Block Management
+ class StoredBlock(Base):
+     __tablename__ = 'memory_blocks'
+     block_id = Column(String, primary_key=True)
+     label = Column(String)
+     block_type = Column(String)  # global, shared, private
+     value = Column(JSON)
+     created_at = Column(DateTime)
+     updated_at = Column(DateTime)
+     shared_with = Column(JSON)  # List of agent IDs for shared blocks
+ ```
+ 
+ 2. Block Management Strategy
+ ```python
+ class BlockManager:
+     """Manages block creation, retrieval, and updates"""
+     
+     def get_or_create_global_block(self, label: str) -> str:
+         """Get existing global block or create new one"""
+         if block_id := self.env.get(f"LETTA_GLOBAL_{label.upper()}_BLOCK"):
+             return block_id
+         return self._create_and_store_block(label, "global")
+     
+     def get_or_create_shared_block(self, label: str, agent_ids: List[str]) -> str:
+         """Get/create shared block for specific agents"""
+         return self._find_or_create_shared_block(label, agent_ids)
+     
+     def get_agent_blocks(self, agent_id: str) -> Dict[str, str]:
+         """Get all block IDs for an agent"""
+         return {
+             "persona": self._get_persona_block(agent_id),
+             "private": self._get_private_block(agent_id),
+             "shared": self._get_shared_blocks(agent_id),
+             "global": self._get_global_blocks()
+         }
+ ```
+ 
+ 3. Memory Block Templates
+ ```python
+ class MemoryBlockTemplates:
+     """Templates for creating different block types"""
+     
+     @staticmethod
+     def create_block_by_type(
+         client,
+         block_type: str,
+         label: str,
+         initial_value: Dict = None
+     ) -> Block:
+         """Factory method for block creation"""
+         creators = {
+             "persona": cls.create_persona_block,
+             "private": cls.create_private_memory_block,
+             "shared": cls.create_shared_social_block,
+             "global": cls.create_global_knowledge_block,
+             "status": cls.create_status_block,
+             "tasks": cls.create_task_block
+         }
+         return creators[block_type](client, initial_value)
+ ```
+ 
+ 4. Block Update Mechanisms
+ ```python
+ class BlockUpdater:
+     """Handles block updates and synchronization"""
+     
+     def update_status(self, agent_id: str, field: str, value: str):
+         """Update status block with new value"""
+         block = self.get_status_block(agent_id)
+         status = json.loads(block.value)
+         status[field] = value
+         block.value = json.dumps(status)
+         self._update_visible_status(agent_id)
+     
+     def _update_visible_status(self, agent_id: str):
+         """Update what's visible to the LLM"""
+         status = self.get_status_block(agent_id)
+         visible = self.get_visible_status_block(agent_id)
+         visible.value = self._format_status_for_llm(status)
+ ```
+ 
+ 5. Configuration Management
+ ```ini
+ # .env additions
+ LETTA_BLOCK_STORAGE=sqlite:///blocks.db
+ LETTA_GLOBAL_KNOWLEDGE_BLOCK=block-abc123
+ LETTA_SHARED_SOCIAL_BLOCK=block-def456
+ ```
+ 
+ 6. Integration Points
+ ```python
+ def create_agent_memory(
+     client,
+     npc_details: Dict,
+     block_manager: BlockManager,
+     use_v2: bool = True
+ ) -> BasicBlockMemory:
+     """Create agent memory with proper block management"""
+     if not use_v2:
+         return create_v1_memory(client, npc_details)
+         
+     blocks = []
+     
+     # Get or create required blocks
+     block_ids = block_manager.get_agent_blocks(npc_details["agent_id"])
+     
+     # Create memory with all blocks
+     return BasicBlockMemory(blocks=[
+         client.get_block(block_id) for block_id in block_ids.values()
+     ])
+ ```

+ 7. LLM Interface Design
+ ```python
+ class V2MemoryTools:
+     """Tools for LLM to interact with memory blocks"""
+     
+     def get_next_task(self) -> str:
+         """LLM calls this to get current task"""
+         return self._format_task_for_llm(self._pop_task())
+     
+     def update_emotion(self, emotion: str) -> None:
+         """LLM updates its emotional state"""
+         self._update_status("emotion", emotion)
+         
+     def record_interaction(self, player_id: str, details: str) -> None:
+         """LLM records private interaction"""
+         self._append_to_private_memory(player_id, details)
+ ```
+
+ 8. Visible Memory Format
+ ```python
+ # What LLM actually sees in context:
+ VISIBLE_MEMORY_FORMAT = """
+ Your Persona:
+ Name: {name}
+ Role: {role}
+ Personality: {personality}
+ 
+ Current Status:
+ Location: {location}
+ Emotion: {emotion}
+ Energy: {energy}
+ 
+ Current Task:
+ {active_task}
+ 
+ Recent Interactions:
+ {recent_interactions}
+ 
+ Known Facts:
+ {shared_facts}
+ """
+ ```
+
+ 9. Quickstart Implementation Flow
+ ```python
+ def quickstart_v2():
+     # 1. Initialize block storage
+     block_manager = BlockManager(db_url=os.getenv("LETTA_BLOCK_STORAGE"))
+     
+     # 2. Create/get global blocks first
+     global_blocks = block_manager.initialize_global_blocks()
+     
+     # 3. Create NPC with all blocks
+     npc = create_v2_agent(
+         client=create_client(),
+         npc_details=load_npc_config(),
+         block_manager=block_manager,
+         global_blocks=global_blocks
+     )
+     
+     # 4. Register memory tools
+     register_v2_memory_tools(npc)
+     
+     return npc
+ ```

+ Development Plan
+ 
+ 1. File Structure
+ ```
+ letta_templates/
+ ├── npc_memory_v2/
+ │   ├── __init__.py
+ │   ├── block_manager.py      # Block storage & management
+ │   ├── block_templates.py    # Block creation templates
+ │   ├── block_updater.py      # Update mechanisms
+ │   ├── memory_tools.py       # LLM-facing tools
+ │   └── visible_format.py     # LLM visibility formatting
+ ├── quickstart_v2.py          # New quickstart implementation
+ └── tests/
+     └── test_memory_v2/
+         ├── test_blocks.py
+         ├── test_tools.py
+         └── test_visibility.py
+ ```
+ 
+ 2. Development Phases
+ 
+ Phase 1: Core Infrastructure
+ - [ ] Implement BlockManager with SQLite storage
+ - [ ] Create block templates for all types
+ - [ ] Set up configuration management
+ 
+ Phase 2: Memory Tools
+ - [ ] Implement V2MemoryTools class
+ - [ ] Create memory formatting utilities
+ - [ ] Add tool registration system
+ 
+ Phase 3: Integration
+ - [ ] Create quickstart_v2.py
+ - [ ] Add migration utilities
+ - [ ] Implement example configurations
+ 
+ Phase 4: Testing
+ - [ ] Unit tests for each component
+ - [ ] Integration tests for full flow
+ - [ ] Migration tests from v1
+ 
+ Implementation Strategy:
+ 1. Create new quickstart_v2.py to avoid disrupting existing functionality
+ 2. Allow both versions to coexist during migration period
+ 3. Provide clear upgrade path for existing users
+ 4. Add version flag to CLI tools for selecting implementation

+ Block Sharing Architecture
+ 
+ ```python
+ # Example: Multiple instances of same NPC sharing blocks
+ class NPCInstance:
+     """Represents a single NPC interaction instance"""
+     def __init__(self, npc_id: str, player_id: str, block_manager: BlockManager):
+         # Shared blocks (same for all instances of this NPC)
+         self.persona = block_manager.get_npc_block(npc_id, "persona")
+         self.shared_social = block_manager.get_npc_block(npc_id, "shared_social")
+         self.global_knowledge = block_manager.get_global_block("knowledge")
+         self.status = block_manager.get_npc_block(npc_id, "status")
+         self.tasks = block_manager.get_npc_block(npc_id, "tasks")
+         
+         # Unique block per player interaction
+         self.private = block_manager.create_private_block(
+             npc_id=npc_id,
+             player_id=player_id
+         )
+ 
+ # Usage example:
+ def create_npc_instance(npc_id: str, player_id: str) -> Agent:
+     """Create NPC agent instance for 1:1 interaction"""
+     # Get/create shared blocks once per NPC
+     if not block_manager.npc_exists(npc_id):
+         block_manager.initialize_npc_blocks(npc_id)
+     
+     # Create instance with shared blocks + unique private block
+     instance = NPCInstance(npc_id, player_id, block_manager)
+     
+     return create_agent(
+         blocks=[
+             instance.persona,
+             instance.shared_social,
+             instance.global_knowledge,
+             instance.status,
+             instance.tasks,
+             instance.private  # Only unique block per instance
+         ]
+     )
+ ```
+ 
+ Block Sharing Rules:
+ 1. Per NPC (shared across all instances):
+    - Persona block (identity)
+    - Shared social block (public knowledge)
+    - Status block (current state)
+    - Tasks block (goals/activities)
+ 
+ 2. Global (shared across all NPCs):
+    - Global knowledge block (world state)
+    - Location data
+    - Game events
+ 
+ 3. Per Instance (unique):
+    - Private memory block (1:1 interactions)
+    - Personal secrets
+    - Relationship status


