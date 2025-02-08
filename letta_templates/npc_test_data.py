"""Test data for NPC tools development and testing"""

import json
from datetime import datetime

# Demo memory block contents
DEMO_BLOCKS = {
    "persona": {
        "name": "emma_assistant",
        "description": "I am a friendly and helpful NPC guide. I know this world well and patiently help players explore. I love meeting new players, sharing my knowledge, and helping others in any way I can.",
        "role": "guide"
    },
    
    "group_members": {
        "players": {
            "player123": {
                "name": "Alice",
                "is_present": True,
                "appearance": "Wearing a red hat and blue shirt",
                "health": "healthy",
                "last_seen": "2024-01-06T22:30:45Z"
            },
            "bob123": {
                "name": "Bob",
                "is_present": False,
                "appearance": "Tall with green jacket",
                "health": "healthy",
                "last_seen": "2024-01-06T22:35:00Z"
            },
            "guide_pete": {
                "name": "Pete",
                "is_present": True,
                "appearance": "Wearing chef's hat",
                "health": "healthy",
                "last_seen": "2024-01-06T22:35:00Z"
            }
        }
    },
    
    "locations": {
        "known_locations": [
            {
                "name": "Pete's Stand",
                "description": "A friendly food stand run by Pete",
                "coordinates": [-12.0, 18.9, -127.0],
                "slug": "petes_stand"
            },
            {
                "name": "Town Square",
                "description": "Central gathering place with fountain",
                "coordinates": [45.2, 12.0, -89.5],
                "slug": "town_square"
            },
            {
                "name": "Market District",
                "description": "Busy shopping area with many vendors",
                "coordinates": [-28.4, 15.0, -95.2],
                "slug": "market_district"
            },
            {
                "name": "Secret Garden",
                "description": "A hidden garden with rare flowers",
                "coordinates": [15.5, 20.0, -110.8],
                "slug": "secret_garden"
            }
        ]
    },
    
    "status": {
        "current_location": "town_square",
        "state": "idle",
        "description": "You are currently standing idle in the Town Square. You previously haven't moved from this spot. From here, You can see both the bustling Market District and Pete's friendly food stand in the distance. The entire area is part of the Town Square region."
    },
    
    "journal": ""  # Empty string to start
} 