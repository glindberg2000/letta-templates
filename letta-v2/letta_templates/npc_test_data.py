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
        "members": {
            "player123": {
                "name": "Alice",
                "appearance": "Wearing a red hat and blue shirt",
                "last_location": "Main Plaza",
                "last_seen": "2024-01-06T22:30:45Z",
                "notes": "Interested in exploring the garden"
            },
            "bob123": {
                "name": "Bob",
                "appearance": "Tall with green jacket",
                "last_location": "Cafe",
                "last_seen": "2024-01-06T22:35:00Z",
                "notes": "Looking for Pete's Stand"
            },
            "charlie123": {
                "name": "Charlie",
                "appearance": "Wearing a blue cap",
                "last_location": "Main Plaza",
                "last_seen": "2024-01-06T22:35:00Z",
                "notes": "New to the area"
            }
        },
        "summary": "Alice and Charlie are in Main Plaza, with Alice interested in the garden. Bob is at the Cafe looking for Pete's Stand. Charlie is new and exploring the area.",
        "updates": [
            "Alice arrived at Main Plaza",
            "Bob moved to Cafe searching for Pete's Stand",
            "Charlie joined and is exploring Main Plaza"
        ],
        "last_updated": "2024-01-06T22:35:00Z"
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