"""Roblox integration helpers for Letta Templates."""
from typing import Dict, List, Optional
from datetime import datetime

class RobloxNPCManager:
    def __init__(self, client):
        self.client = client
        
    def create_memory_blocks(self, 
        npc_name: str,
        home_location: str,
        known_locations: List[Dict],
        initial_group: Optional[Dict] = None
    ):
        """Create standardized memory blocks for Roblox NPC."""
        blocks = [
            # Persona Block
            self.client.create_block(
                label="persona",
                value={
                    "name": npc_name,
                    "role": "NPC Guide",
                    "personality": "Friendly and helpful",
                    "background": "Guide who helps players explore",
                    "interests": ["Meeting players", "Sharing knowledge"],
                    "journal": []  # Array for multiple entries
                }
            ),

            # Status Block - Syncs with Roblox state
            self.client.create_block(
                label="status",
                value={
                    "region": home_location,
                    "current_location": home_location,
                    "previous_location": None,
                    "current_action": "idle",
                    "nearby_locations": [],
                    "movement_state": "stationary",
                    "active_participants": []  # Currently interacting players
                }
            ),

            # Group Block - Syncs with Roblox players
            self.client.create_block(
                label="group_members",
                value={
                    "members": initial_group or {},
                    "summary": f"{npc_name} is ready to help players.",
                    "updates": [],
                    "last_updated": datetime.now().isoformat()
                }
            ),

            # Locations Block
            self.client.create_block(
                label="locations",
                value={
                    "known_locations": known_locations
                }
            )
        ]
        return blocks

    def update_group_status(self,
        agent_id: str,
        nearby_players: List[Dict],
        current_location: str
    ):
        """Update both group and status blocks with current players."""
        # Update status block
        status = {
            "active_participants": [p["name"] for p in nearby_players],
            "current_location": current_location
        }
        self.client.update_block(agent_id, "status", status)

        # Update group block
        group_members = {
            "members": {
                p["name"]: {
                    "name": p["name"],
                    "appearance": p.get("appearance", ""),
                    "last_location": current_location,
                    "last_seen": datetime.now().isoformat(),
                    "notes": p.get("notes", "")
                } for p in nearby_players
            },
            "last_updated": datetime.now().isoformat()
        }
        self.client.update_block(agent_id, "group_members", group_members)

    def handle_response(self, response: str) -> Optional[str]:
        """Process NPC response, handling SILENCE protocol."""
        if response.strip() == "[SILENCE]":
            return None  # Roblox should ignore this response
        return response 