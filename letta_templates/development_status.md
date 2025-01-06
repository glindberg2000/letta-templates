# NPC System Development Status (December 2024)

## Letta Integration (Updated)

### Agent System
1. **Core Integration**
   - Letta 0.6.6 server integration
   - Custom memory blocks:
     * persona (NPC personality)
     * human (interaction context)
     * locations (navigation data)
   - Tool registration system
   - Autonomous behavior support
   - System prompt integration

2. **Memory System**
   ```python
   # Complete Memory Block Structure
   memory = BasicBlockMemory(
       blocks=[
           # Persona Block - NPC's core identity and behavior
           client.create_block(
               label="persona",
               value=f"""
               Name: {npc_details['display_name']}
               Role: {npc_details.get('role', 'Friendly NPC')}
               Personality: {npc_details['system_prompt']}
               Interests: {npc_details.get('interests', [])}
               Home Location: {npc_details.get('home_location', 'Unknown')}
               """.strip(),
               limit=2000
           ),
           
           # Human Block - Current interaction context
           client.create_block(
               label="human",
               value=json.dumps({
                   "name": interaction_context['participant_name'],
                   "type": interaction_context['participant_type'],
                   "description": human_description,
                   "last_interaction": None,
                   "relationship_status": "neutral",
                   "notable_interactions": []
               }),
               limit=2000
           ),
           
           # Locations Block - Navigation and spatial awareness
           client.create_block(
               label="locations",
               value=json.dumps({
                   "known_locations": [
                       {
                           "name": "Pete's Merch Stand",
                           "description": "A friendly food stand run by Pete",
                           "coordinates": [-12.0, 18.9, -127.0],
                           "slug": "petes_stand",
                           "category": "shop",
                           "connected_to": ["town_square", "market_district"],
                           "typical_visitors": ["shoppers", "merchants"]
                       },
                       # Additional locations...
                   ],
                   "current_location": {
                       "name": "Unknown",
                       "coordinates": None
                   },
                   "favorite_spots": [],
                   "restricted_areas": []
               }),
               limit=5000
           )
       ]
   )
   ```

   **Memory Block Testing Guidelines:**
   1. Persona Block Tests:
      - Verify all required fields present
      - Test character limit handling
      - Validate prompt injection prevention
      - Sample size: 10-15 diverse NPC types

   2. Human Block Tests:
      - Test JSON serialization/deserialization
      - Verify interaction history updates
      - Check relationship status changes
      - Sample size: 20-30 interaction scenarios

   3. Locations Block Tests:
      - Validate coordinate formats
      - Test slug generation/validation
      - Verify location relationships
      - Sample size: 50-100 location combinations

   **Memory Integration Points:**
   1. Tool Integration:
      - Tools read from relevant memory blocks
      - Tools update memory after actions
      - Memory influences tool behavior

   2. State Management:
      - Current location tracking
      - Relationship status updates
      - Interaction history maintenance

   3. Decision Making:
      - Location preferences from persona
      - Relationship-based responses
      - Context-aware navigation

3. **Tool System**
   - Navigation Tools:
     * navigate_to(slug) - Location-based movement
     * navigate_to_coordinates(x,y,z) - Direct coordinate movement
   - Action Tools:
     * perform_action("follow", target="player")
     * perform_action("emote", type="wave|dance|sit")
     * perform_action("unfollow")
   - Autonomous Behaviors:
     * Self-initiated navigation
     * Natural conversation endings
     * Dynamic emote usage
     * Location-based decisions

4. **Current Capabilities**
   ```python
   # Available tools
   TOOL_REGISTRY = {
       "navigate_to": navigate_to,
       "navigate_to_coordinates": navigate_to_coordinates,
       "perform_action": perform_action,
       "examine_object": examine_object
   }
   ```

### Recent Improvements
1. **Navigation System**
   - Slug-based location system
   - Coordinate support
   - Autonomous movement
   - Natural transitions

2. **Conversation Management**
   - Graceful endings
   - Loop prevention
   - Natural transitions
   - Context awareness

3. **Behavior System**
   - Emote integration
   - Follow/unfollow actions
   - Location awareness
   - Personality expression

### Next Steps
1. **Tool Enhancements**
   - [ ] Add emote cancellation
   - [ ] Improve group chat handling
   - [ ] Add more complex actions
   - [ ] Enhance location awareness

2. **Memory Improvements**
   - [ ] Add relationship tracking
   - [ ] Improve location memory
   - [ ] Add event memory
   - [ ] Better context retention

3. **Behavior Refinements**
   - [ ] More natural transitions
   - [ ] Better group dynamics
   - [ ] Enhanced personality traits
   - [ ] Improved decision making

### System Prompt Design
```python
# System prompt must instruct the NPC how to:
system_prompt = f"""
Memory Usage Instructions:
1. Persona Memory:
  - Access your identity from persona block
  - Use interests to guide decisions
  - Reference home location for context
  - Stay in character based on role

2. Human Interaction Memory:
  - Track relationship status
  - Reference past interactions
  - Adapt tone based on relationship
  - Update notable_interactions after significant events

3. Location Memory:
  - Use known_locations for navigation
  - Consider connected_to for natural movement
  - Update current_location after movement
  - Build favorite_spots based on experiences

Memory Integration Rules:
- Always check relevant memory before making decisions
- Update memory blocks after significant events
- Use memory context to guide tool usage
- Maintain consistent personality across interactions

{TOOL_INSTRUCTIONS}  # Tool usage instructions
"""
```

**Memory-Prompt Integration Testing:**
1. Verify NPC:
  - References correct memory blocks
  - Updates memory appropriately
  - Maintains consistent behavior
  - Uses tools as instructed

2. Test Scenarios:
  - New player interactions
  - Returning player recognition
  - Location-based decisions
  - Memory-guided responses
