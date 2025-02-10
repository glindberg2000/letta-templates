# Memory Block Configuration Guide

## Overview
Memory blocks are organized to give NPCs natural access to information about themselves, their surroundings, and the people they interact with. The format prioritizes narrative understanding over structured data where possible.

## Core Memory Blocks

### 1. Persona Block (JSON)
Your core identity and personality.
```json
{
    "description": "You are a friendly town guide with short brown hair and a warm smile. You wear a blue uniform with a silver name badge.",
    "personality": "You are patient and helpful, always eager to assist visitors. You've grown more confident in your role over time.",
    "journal": "You've been helping with festival preparations. Yesterday you learned a better route to Pete's Stand.",
    "abilities": "You can navigate the town, chat with visitors, and perform friendly gestures."
}
```

### 2. Status Block (String)
Free-form narrative for maximum flexibility. Updated by external systems.
```python
status = (
    "You are at the Market Square, feeling energetic. "
    "The festival music has lifted your spirits. "
    "You've been helping direct visitors to Pete's Stand for the past 10 minutes. "
    "A light rain just started falling."
)
```
- Allows any state to be naturally described
- Easy to append new conditions/events
- No parsing needed by the NPC
- External systems can use templates or LLM to generate updates

### 3. Group Members Block (JSON)
Structured for reliable tracking with simple text descriptions.
```json
{
    "members": {
        "alice123": {
            "description": "Alice in red hat, asking about the gardens",
            "notes": "Interested in flowers. Second visit this week."
        },
        "bob456": {
            "description": "Bob looking for Pete's Stand",
            "notes": "First time visitor, seems lost easily."
        }
    },
    "updates": [
        "Alice joined asking about gardens",
        "Bob arrived looking lost"
    ],
    "last_updated": "2024-01-19T06:55:31Z"
}
```
- `description`: Current appearance and state (changes frequently)
- `notes`: Persistent observations about the player (accumulates over time)
- Basic chronological updates
- Easy to update programmatically

## Recommended New Blocks

### 4. Environment Block (String)
Ambient world state and conditions.
```
It's a sunny afternoon in SpringVale. The market is bustling with activity. 
The weekly festival preparations are underway near the town square. There's 
music playing from the direction of Pete's Stand.
```

### 5. Recent Events Block (JSON)
Short-term memory of significant happenings.
```json
{
    "events": [
        {
            "type": "festival_prep",
            "description": "Town square being decorated for SpringFest",
            "impact": "More visitors than usual in the area"
        },
        {
            "type": "weather_change",
            "description": "Rain has stopped, sun coming out",
            "impact": "People returning to outdoor areas"
        }
    ],
    "last_updated": "2024-01-19T06:55:31Z"
}
```

## Design Principles

1. **Narrative Priority**
   - Use natural language descriptions where possible
   - Structure data only when relationships need tracking
   - Let the NPC process information like a character would

2. **Information Grouping**
   - Personal info in Persona block
   - Immediate situation in Status block
   - Social context in Group Members block
   - World state in Environment block
   - Temporal events in Recent Events block

3. **Update Frequency**
   - Persona: Rare updates (character development)
   - Status: Very frequent (real-time)
   - Group Members: Frequent (as people come/go)
   - Environment: Moderate (world state changes)
   - Recent Events: As needed (significant happenings)

4. **Format Choices**
   - Strings: For narrative understanding (status, environment)
   - JSON: For structured relationships (group members, events)
   - Mixed: When both structure and narrative needed (persona)

## Best Practices

1. **Status Updates**
   - Keep narrative flowing and natural
   - Include previous context when relevant
   - Focus on immediate situation and state

2. **Group Management**
   - Use simple descriptions for members
   - Keep updates chronological
   - Maintain clear summary of current group

3. **Environmental Context**
   - Blend ambient and dynamic elements
   - Include relevant cultural/event context
   - Connect to NPC's current location

4. **Memory Integration**
   - Let blocks complement each other
   - Avoid redundant information
   - Maintain consistent narrative voice

## Implementation Notes

1. **Block Updates**
   ```python
   # Status update (string)
   update_memory_block(
       client, agent_id, "status",
       "You've moved to the garden area. The roses are in full bloom, "
       "and several visitors are admiring the new fountain installation."
   )

   # Group update (JSON)
   update_memory_block(
       client, agent_id, "group_members",
       {
           "members": {...},
           "summary": "Current group situation",
           "updates": ["Recent changes..."],
           "last_updated": timestamp
       }
   )
   ```

2. **Real-time Processing**
   - Update Status and Group blocks most frequently
   - Batch Environment updates when location changes
   - Add Recent Events for significant changes
   - Keep Persona updates rare and meaningful

3. **Memory Limits**
   - Status: ~200-300 characters
   - Group Members: Last 5-10 interactions
   - Environment: ~200-300 characters
   - Recent Events: Last 3-5 significant events
   - Persona: Core attributes plus recent development

# Memory Block Update Responsibilities

## Automated Updates (Game Engine/Code)
These can be handled directly by the game system:

### Status Block (String)
```python
# Simple template-based updates
status = (
    f"You are at {current_location}. "
    f"You have been here for {time_elapsed}. "
    f"You are currently {current_action}."
)
```

### Group Members Block (JSON)
```json
{
    "members": {
        "alice123": "Alice wearing red hat",  // Basic appearance from game data
        "bob456": "Bob in green jacket"
    },
    "updates": [
        "Alice joined the group",  // Simple state changes
        "Bob left the group"
    ],
    "last_updated": "timestamp"
}
```

## LLM-Assisted Updates
These require contextual understanding:

### 1. Group Summary Generation
- When: Every N member changes or time interval
- Task: Generate natural summary of current group state
- Example: "You're with Alice and Bob. Alice has been here longer."

### 2. Persona Development
- When: After significant interactions/events
- Task: Update personality/journal based on experiences
- Limited scope: Only process major character developments

## Hybrid Approach (Recommended)
1. Keep base data structure simple and code-updateable
2. Use LLM sparingly for:
   - Periodic summary generation
   - Major character development
   - Complex event interpretation

This reduces overhead while maintaining narrative quality.

## Future Considerations: Overseer System

While current focus is on individual NPC memory management, future scaling may benefit from a centralized "Overseer" system that:

1. **Efficiency**
   - Batch processes memory updates across multiple NPCs
   - Shares relevant context between NPCs in same area
   - Manages summary generation for groups of NPCs

2. **Safety & Stability**
   - Monitors for NPC behavioral loops or conflicts
   - Detects stuck states (physical or conversational)
   - Provides gentle corrections when needed

3. **Resource Management**
   - Prioritizes LLM calls for most important updates
   - Coordinates group dynamics efficiently
   - Maintains world consistency across NPCs

For now, we'll focus on robust individual NPC memory management, keeping the architecture open for future Overseer integration.
