from letta.memory import BaseMemory, MemoryModule
from typing import Optional, Dict, List
import json

class NPCMemoryV2(BaseMemory):
    """V2 Memory system for NPCs"""
    
    def __init__(
        self,
        npc_id: str,
        npc_details: Dict,
        player_id: str = None
    ):
        # Initialize with all V2 memory blocks
        self.memory = {
            # Core NPC blocks (shared across instances)
            "persona": MemoryModule(
                name="persona",
                value=npc_details["system_prompt"],
                limit=2000
            ),
            "status": MemoryModule(
                name="status",
                value=json.dumps({
                    "position": None,
                    "emotion": "neutral",
                    "energy": 100
                }),
                limit=1000
            ),
            "tasks": MemoryModule(
                name="tasks",
                value=json.dumps({
                    "queue": [],
                    "completed": []
                }),
                limit=2000
            ),
            "shared_social": MemoryModule(
                name="shared_social",
                value=json.dumps({
                    "recent_facts": [],
                    "group_interactions": []
                }),
                limit=2000
            ),
            # Private memory for this player interaction
            "participant": MemoryModule(
                name="participant",
                value=json.dumps({
                    "name": player_id,  # or actual name if provided
                    "description": "",   # physical description, role, etc.
                    "relationship": {
                        "status": "neutral",
                        "trust_level": 0,
                        "notable_interactions": []
                    },
                    "known_facts": [],   # what NPC knows about participant
                    "shared_secrets": [] # secrets specifically shared with this participant
                }),
                limit=2000
            ) if player_id else None
        }
        
        # Add private memory if player_id provided
        if player_id:
            self.memory["private"] = MemoryModule(
                name="private",
                value=json.dumps({
                    "relationship": "neutral",
                    "interactions": [],
                    "secrets": []
                }),
                limit=2000
            ) 
        
    def update_status(self, field: str, value: str) -> Optional[str]:
        """Update a status field"""
        status = json.loads(self.memory["status"].value)
        status[field] = value
        self.memory["status"].value = json.dumps(status)
        return None
        
    def add_task(self, task: str) -> Optional[str]:
        """Add task to queue"""
        tasks = json.loads(self.memory["tasks"].value)
        tasks["queue"].append(task)
        self.memory["tasks"].value = json.dumps(tasks)
        return None
        
    def record_interaction(self, details: str, private: bool = True) -> Optional[str]:
        """Record an interaction"""
        block = "private" if private else "shared_social"
        data = json.loads(self.memory[block].value)
        if private:
            data["interactions"].append(details)
        else:
            data["group_interactions"].append(details)
        self.memory[block].value = json.dumps(data)
        return None 
        
    # Persona editing
    def update_persona(self, old_content: str, new_content: str) -> Optional[str]:
        """Update part of persona memory"""
        return self.core_memory_replace("persona", old_content, new_content)
    
    def append_to_persona(self, content: str) -> Optional[str]:
        """Add new information to persona"""
        return self.core_memory_append("persona", content)
    
    # Private memory editing
    def update_relationship(self, new_status: str) -> Optional[str]:
        """Update relationship status in private memory"""
        data = json.loads(self.memory["private"].value)
        data["relationship"] = new_status
        self.memory["private"].value = json.dumps(data)
        return None
    
    def add_secret(self, secret: str) -> Optional[str]:
        """Add a secret to private memory"""
        data = json.loads(self.memory["private"].value)
        data["secrets"].append(secret)
        self.memory["private"].value = json.dumps(data)
        return None
    
    def get_relationship_status(self) -> str:
        """Get current relationship status"""
        data = json.loads(self.memory["private"].value)
        return data["relationship"]
    
    def get_secrets(self) -> List[str]:
        """Get list of shared secrets"""
        data = json.loads(self.memory["private"].value)
        return data["secrets"] 
        
    # Participant memory methods
    def update_participant_info(self, field: str, value: str) -> Optional[str]:
        """Update participant information"""
        data = json.loads(self.memory["participant"].value)
        if field in ["name", "description"]:
            data[field] = value
        elif field == "relationship":
            data["relationship"]["status"] = value
        elif field == "fact":
            data["known_facts"].append(value)
        self.memory["participant"].value = json.dumps(data)
        return None
    
    def get_participant_info(self) -> Dict:
        """Get all known information about participant"""
        return json.loads(self.memory["participant"].value) 