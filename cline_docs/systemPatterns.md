# System Patterns

## Architecture

### Core Components
1. Memory System
   - Core Memory: Immediate access blocks
   - Journal: Personal reflections
   - Archival Memory: Long-term storage
   - Group Memory: Social context

2. Tools & Utilities
   - Status management
   - Group tracking
   - Navigation
   - Action performance

3. Response Handling
   - Message processing
   - Tool coordination
   - System messages

### Key Patterns
- Memory block updates with system notifications
- Tool call extraction and processing
- Status and group state management
- Social awareness protocols

1. Memory Blocks
   - group_members
   - status
   - navigation

2. Update Patterns
   - NPCs: append-only notes
   - Game: state updates
   - System: structure maintenance

3. Data Flow
   - NPCs observe and record
   - Game updates state
   - System maintains integrity 

## Status System
1. First-Person Status Format:
```python
{
    "current_location": "location_name",
    "state": "current_state",
    "health": "health_condition",
    "description": "First-person immersive description..."
}
```

2. Health Status Patterns:
- Use descriptive health conditions
- First-person injury descriptions
- Realistic scenarios (car crashes, attacks)
- Appropriate distress levels

3. Status Updates:
```python
update_status_block(
    client=client,
    agent_id=agent_id,
    field_updates={...}
)
```

## Memory Patterns
[Previous memory patterns remain unchanged] 

## Action System
- Core actions: patrol, wander, idle, hide, flee, emote, follow, unfollow
- Each action has specific validation and response format
- Movement style handled by navigate_to function
- Emergency actions require location/threat targets

## Navigation System
- Uses slugs for location identification
- Optional movement styles (walk, run, sneak)
- Provides progress updates via heartbeat

## Role-Based Behaviors
- Each role (waiter, merchant, etc.) has specific action patterns
- Prompts guide appropriate action selection
- Emergency protocols consistent across roles 