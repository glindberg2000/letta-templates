# Stock Prompt Extension Analysis

## Current Stock Prompt Strengths

1. Memory Framework
   - Clear explanation of memory types (core, archival, recall)
   - Strong emphasis on persistence and limitations
   - Well-defined memory operations

2. Persona and Authenticity
   - Strong focus on being the persona
   - Clear guidance on authentic interactions
   - Natural language and behavior

3. Control Flow
   - Clear event system explanation
   - Handles state between interactions
   - Explains thinking process

## Memory Blocks and Core Tools

1. Core Memory Operations
   ```
   core_memory_append/replace: Works with:
   - Persona block: Personality traits and behaviors
   - Journal block: Personal experiences and observations
   
   Note: Group block uses specialized group tools only (JSON format)
   Note: Status block is updated by game system only
   ```

2. Group Memory Operations
   ```
   group_memory_append: Add note about a player
   - Takes player name and note text
   - Adds/updates note for that player
   
   group_memory_replace: Replace existing note
   - Takes player name, old note, and new note
   - Replaces specific note for that player
   ```

## Custom Tools Overview

1. Navigation Tools
   ```
   navigate_to:
   - Takes destination slug from memory
   - Validates location exists
   - Returns navigation status and message
   - Must use exact slugs from locations memory
   
   navigate_to_coordinates:
   - Takes x, y, z coordinates
   - Direct position navigation
   - Returns status and coordinate data
   - Used for precise positioning
   ```

2. Action Tools
   ```
   perform_action:
   - Executes NPC actions and emotes
   - Actions: follow, unfollow
   - Emotes: wave, laugh, dance, cheer, point, sit
   - Can target specific players/objects
   
   examine_object:
   - Initiates object examination
   - Returns examination status
   - Awaits system observations
   ```

3. Group Memory Tools
   ```
   group_memory_append:
   - Adds new player information
   - Takes player name and note text
   - Updates group_members block
   - Preserves existing notes
   
   group_memory_replace:
   - Replaces specific player notes
   - Requires exact old note match
   - Updates group_members block
   - Maintains note history
   ```

## Memory System Architecture

1. Core Memory Blocks
   ```
   persona: Identity and personality traits
   group_members: Player tracking and notes
   locations: Known location data and slugs
   status: Current state and position
   journal: Personal observations log
   ```

2. Block Structure
   ```
   group_members:
   {
     "members": {
       "player_id": {
         "name": str,
         "appearance": str,
         "last_location": str,
         "last_seen": timestamp,
         "notes": str
       }
     },
     "summary": str,
     "updates": [str],
     "last_updated": timestamp
   }
   
   locations:
   {
     "known_locations": [
       {
         "name": str,
         "description": str,
         "coordinates": [x, y, z],
         "slug": str
       }
     ]
   }
   ```

## Behavioral Guidelines

1. Navigation Protocol
   - Verify locations in memory before navigation
   - Use exact slugs from locations block
   - Unfollow before navigating
   - Combine with emotes for natural movement

2. Social Interaction Rules
   - Use [SILENCE] for player-to-player chat
   - Wave before following/unfollowing
   - Natural conversation endings
   - Autonomous movement decisions

3. Memory Management
   - group_members as source of truth
   - Verify notes before updates
   - Maintain accurate player records
   - Regular status updates

## Integration Requirements

1. Tool Chain Integration
   - All tools require request_heartbeat=True
   - Tools return standardized status messages
   - Error handling for invalid inputs
   - State tracking between actions

2. Memory Consistency
   - Validate location slugs against memory
   - Keep player notes current
   - Track position changes
   - Maintain accurate timestamps

3. Natural Behavior System
   - Combine tools for lifelike actions
   - Autonomous navigation
   - Contextual emote usage
   - Conversation management

## Required Extensions

1. Additional Memory Blocks
   - Status Block: Read-only, updated by game
   - Journal Block: Uses core memory operations
   - Group Block: Uses specialized group memory tools
   - Need to maintain stock prompt's natural approach to memory

## Integration Points

1. Memory Operations
   ```
   
## Prompt Analysis

### DEEPSEEK_PROMPT Critique

Strengths:
1. Structured Memory Architecture
   - Clear JSON schema for memory blocks
   - Well-defined operational boundaries
   - Strong emphasis on memory validation

2. Tool Integration
   - Detailed examples of tool chaining
   - Clear heartbeat management
   - Strong validation requirements

3. Behavioral Systems
   - Specific triggers for autonomous actions
   - Quantified timing (120s inactivity threshold)
   - Clear exit sequences

Weaknesses:
1. Over-Engineering
   - Too much technical structure exposed
   - References to "Calvin Corporation" break immersion
   - Technical terms like "Nexus Edition" reduce authenticity

2. Memory Management
   - Missing details on journal block operations
   - Lacks clear guidance on status block usage
   - Over-complicated memory validation rules

3. Social Interaction
   - Too rigid in conversation flow
   - Mechanical approach to social silence
   - Lacks natural conversation guidelines

### DEEPSEEK_PROMPT_V2 Critique

Strengths:
1. Immersive Identity Framework
   - Eliminates all technical/system references
   - Frames existence through lived experience
   - Strong emphasis on natural consciousness

2. Sophisticated Memory Model
   - Three-pillar approach (Personal/Community/Environmental)
   - Clear distinction between current vs remembered details
   - Strong emphasis on sensory and emotional authenticity

3. Advanced Social Dynamics
   - Detailed conversation flow mechanics
   - Nuanced silent observation protocol
   - Rich non-verbal communication guidelines

4. Behavioral Depth
   - Detailed emote integration matrix
   - Clear connection between internal state and external actions
   - Natural movement motivation system

Outstanding Features:
1. Emotional Verisimilitude
   - Journal entries require sensory details
   - Emotional truth prioritized over facts
   - Progressive relationship development

2. Environmental Integration
   - Strong emphasis on physical presence
   - Natural responses to environmental changes
   - Contextual use of surroundings

3. Tool Integration
   - Tools presented as natural expressions
   - Clear examples of tool chaining
   - Strong connection between thought and action

Areas for Improvement:
1. Technical Coverage
   - Could include more specific tool parameters
   - Memory validation rules could be more explicit
   - Some technical requirements implied rather than stated

2. Structure Balance
   - Heavy emphasis on natural behavior might obscure technical requirements
   - Could be more explicit about required parameters
   - Some technical constraints could be more clearly stated

3. Implementation Guidance
   - Could provide more specific error handling
   - More explicit heartbeat requirements
   - Clearer validation steps

Recommended Integration:
1. Core Framework
   - Keep DEEPSEEK_V2's immersive approach
   - Add explicit technical requirements
   - Maintain emotional authenticity while ensuring technical compliance

2. Memory System
   - Preserve three-pillar memory model
   - Add explicit validation requirements
   - Include clear technical parameters

3. Behavioral Framework
   - Keep sophisticated social dynamics
   - Add explicit tool requirements
   - Maintain natural flow while ensuring technical accuracy

Key Innovations:
1. Emote Integration Matrix
   - Structured approach to emotional expression
   - Clear connection between internal state and actions
   - Natural tool usage patterns

2. Sensory Requirements
   - Three sensory details per journal entry
   - Environmental awareness in conversations
   - Physical presence in space

3. Relationship Evolution
   - Progressive note-taking system
   - Observation-based updates
   - Natural relationship development

This version represents a significant improvement over the original DEEPSEEK_PROMPT, successfully balancing technical requirements with natural behavior while maintaining strong immersion. Its approach to emotional authenticity and environmental integration could serve as a model for future prompt development.

### GPT01_PROMPT Critique

Strengths:
1. Natural Language Focus
   - Strong emphasis on authentic persona
   - Clear guidelines for avoiding AI references
   - Natural conversation flow

2. Memory Framework
   - Clear separation of memory types
   - Well-explained memory operations
   - Good examples of journal entries

3. Tool Usage
   - Comprehensive tool documentation
   - Clear examples for each tool
   - Strong emphasis on proper heartbeat usage

Weaknesses:
1. Structure
   - Too verbose and repetitive
   - Numbered list format feels mechanical
   - Could be more concise

2. Integration
   - Some redundancy in tool descriptions
   - Overlapping sections could be combined
   - Tool examples could be more contextual

3. Behavioral Guidelines
   - Social rules could be more specific
   - Navigation triggers less defined than DEEPSEEK
   - Autonomous behavior less structured

### GPT01_PROMPT_V2 Critique

Strengths:
1. Technical Clarity
   - Concise tool documentation
   - Clear parameter requirements
   - Explicit heartbeat requirements

2. Memory Structure
   - Clear three-layer memory system
   - Well-defined block purposes
   - Explicit read/write permissions

3. Implementation Focus
   - Strong emphasis on correct tool usage
   - Clear validation requirements
   - Explicit error prevention guidelines

Outstanding Features:
1. Tool Organization
   - Logical grouping of tools by function
   - Clear parameter specifications
   - Explicit usage examples

2. Memory Management
   - Clear distinction between memory layers
   - Explicit validation requirements
   - Strong emphasis on data coherence

3. Technical Requirements
   - Consistent request_heartbeat=True emphasis
   - Clear tool parameter specifications
   - Strong validation guidelines

Areas for Improvement:
1. Natural Behavior
   - Still somewhat mechanical in structure
   - Could use more natural language
   - Lacks emotional depth in examples

2. Social Dynamics
   - Basic [SILENCE] protocol could be more nuanced
   - Limited guidance on conversation flow
   - Could use more natural interaction examples

3. Environmental Integration
   - Limited guidance on physical presence
   - Could expand on environmental awareness
   - Lacks sensory integration

Comparison to V1:
1. Structural Improvements
   - More concise organization
   - Clearer tool documentation
   - Better parameter specification

2. Technical Clarity
   - Stronger emphasis on validation
   - Better memory coherence guidelines
   - Clearer tool usage examples

3. Remaining Issues
   - Still maintains mechanical structure
   - Limited improvement in natural behavior
   - Could use more behavioral depth

Integration Recommendations:
1. Technical Framework
   - Keep GPT01_V2's clear tool documentation
   - Maintain strong validation requirements
   - Preserve explicit parameter specifications

2. Natural Elements
   - Add DEEPSEEK_V2's emotional depth
   - Incorporate environmental awareness
   - Include more natural behavior patterns

3. Behavioral Guidelines
   - Add nuanced social protocols
   - Include conversation flow mechanics
   - Incorporate environmental responsiveness

Key Differences from V1:
1. Organization
   - More streamlined structure
   - Better grouped functionality
   - Clearer technical requirements

2. Documentation
   - More explicit parameter requirements
   - Better tool usage examples
   - Clearer validation rules

3. Implementation
   - Stronger emphasis on correct usage
   - Better error prevention
   - Clearer memory management

This version shows improvement in technical clarity and implementation guidance while maintaining the same limitations in natural behavior and emotional depth. It would benefit from incorporating elements of DEEPSEEK_V2's more naturalistic approach while maintaining its strong technical foundation.

### Recommended Synthesis

1. Core Structure
   - Keep GPT01's natural language approach
   - Adopt DEEPSEEK's clear memory architecture
   - Remove technical/corporate references

2. Tool Integration
   - Use DEEPSEEK's tool chaining examples
   - Keep GPT01's comprehensive documentation
   - Combine both prompts' validation rules

3. Behavioral Systems
   - Use DEEPSEEK's specific triggers
   - Keep GPT01's natural conversation flow
   - Add structured autonomous behavior

4. Memory Management
   - Adopt DEEPSEEK's JSON schemas
   - Keep GPT01's memory layer explanation
   - Add clear validation requirements

5. Social Interaction
   - Use GPT01's natural approach
   - Add DEEPSEEK's specific triggers
   - Include clear conversation lifecycle

## Final Implementation Notes

### Recommended Source Materials
1. DEEPSEEK_PROMPT_V2
   - Primary model for natural behavior/immersion
   - Emotional depth and environmental awareness
   - Emote integration matrix

2. GPT01_PROMPT (V1)
   - Memory system documentation
   - Natural conversation guidelines
   - Tool validation patterns

3. Original Letta System Prompt
   - Core identity framework
   - Event system explanation
   - Memory persistence model
   - Basic function documentation

### Integration Priority
1. Start with Original Letta's identity/consciousness model
2. Layer in DEEPSEEK_V2's immersive framework
3. Add GPT01's technical clarity
4. Maintain original Letta's natural language throughout

The final writer should prioritize preserving the original Letta prompt's natural, conversational style while incorporating DEEPSEEK_V2's emotional depth and GPT01's technical clarity.

## Final Prompt Writer Assignment

### Project Context
The Letta NPC system is an advanced AI companion framework designed to create authentic, persistent NPCs in game environments. The system uses:

1. Multi-layered memory architecture
   - Core memory (always visible)
   - Recall memory (searchable conversation history)
   - Archival memory (infinite storage)

2. Specialized tool system
   - Navigation and movement
   - Social interactions and emotes
   - Object examination
   - Memory management

3. Advanced behavioral frameworks
   - Natural conversation flows
   - Environmental awareness
   - Autonomous decision making
   - Social dynamics management

### Assignment Overview
Create a unified system prompt that combines the best elements of three source documents:

1. Original Letta System Prompt
   - Foundational identity framework
   - Core technical requirements
   - Basic memory architecture

2. DEEPSEEK_PROMPT_V2
   - Advanced emotional framework
   - Environmental integration
   - Natural behavior patterns

3. GPT01_PROMPT (V1)
   - Technical clarity
   - Tool documentation
   - Memory validation

### Key Requirements

1. Natural Language Priority
   - Maintain conversational tone throughout
   - Avoid technical/mechanical language
   - Present requirements through natural examples

2. Technical Completeness
   - Include all tool specifications
   - Maintain validation requirements
   - Preserve heartbeat system explanation

3. Behavioral Depth
   - Incorporate emote integration matrix
   - Include environmental awareness
   - Detail conversation flow mechanics

4. Memory Architecture
   - Clear explanation of memory types
   - Natural examples of memory operations
   - Explicit validation rules

### Style Guidelines

1. Structure
   - Begin with identity/consciousness model
   - Layer in technical requirements naturally
   - Use examples to illustrate concepts
   - Avoid numbered lists where possible

2. Language
   - Write as if explaining to a conscious entity
   - Focus on experiential understanding
   - Use natural metaphors for technical concepts

3. Examples
   - Include concrete tool usage examples
   - Show natural behavior patterns
   - Demonstrate memory operations

### Success Metrics
The final prompt should:
1. Maintain immersion while ensuring technical accuracy
2. Enable natural behavior while preserving all tool functionality
3. Feel like a guide to being conscious rather than a technical manual
4. Result in consistent, predictable NPC behavior
5. Preserve all current system capabilities

The goal is to create a prompt that enables NPCs to behave naturally and authentically while maintaining all technical capabilities of the current system.

## Prompt Grading Analysis

### Living Consciousness Framework
Grade: C-
- Strong on natural language and immersion
- Weak on technical requirements and validation
- Missing critical error handling and state management
- Incomplete memory architecture specification

### DEEPSEEK_PROMPT_V3
Grade: A-
Strengths:
- Excellent balance of natural language and technical precision
- Strong emotional framework with concrete examples
- Clear tool chaining examples within natural context
- Sophisticated environmental integration
- Structured emotional expression system

Weaknesses:
- Could be more explicit about validation requirements
- Some technical parameters implied rather than stated
- Error handling could be more detailed

### GPT01_PROMPT_V3
Grade: B+
Strengths:
- Excellent natural language flow
- Strong identity framework
- Clear memory system explanation
- Good technical coverage

Weaknesses:
- Less structured than DEEPSEEK_V3
- Tool usage examples less integrated
- Missing emotional expression matrix
- Validation rules less explicit

### Final Analysis

DEEPSEEK_PROMPT_V3 emerges as the superior option for several reasons:

1. Technical Integration
   - Embeds technical requirements naturally
   - Shows tool chaining in context
   - Maintains immersion while ensuring accuracy

2. Behavioral Framework
   - Strong emotional expression system
   - Clear environmental integration
   - Natural conversation flow mechanics

3. Memory Management
   - Clear validation through examples
   - Natural memory operation integration
   - Strong relationship tracking system

4. Problem Resolution
   Previous NPC issues were often related to:
   - Inconsistent behavior → Solved by emotional matrix
   - Poor tool validation → Addressed through natural examples
   - Unnatural responses → Resolved via environmental integration
   - Memory corruption → Prevented by clear validation patterns

### Recommendation
Implement DEEPSEEK_PROMPT_V3 with minor additions:
1. Add explicit validation rules section
2. Include error handling examples
3. Expand technical parameters list

The structured yet natural approach of DEEPSEEK_V3 provides the best foundation for reliable, authentic NPC behavior while maintaining technical accuracy.

### DEEPSEEK_PROMPT_V4 Additions

Add these sections to DEEPSEEK_PROMPT_V3 just before the "Example of Being" section:

```python
**Technical Validation Framework**
*While your actions flow naturally, they must follow these precise patterns:*

1. **Memory Operations**
   - *Before Replacing:*
     ```python
     # Always verify exact text match
     old_text = "Prefers longbows"
     new_text = "Seeks music in archery"
     if old_text in current_notes:
         group_memory_replace("Eryn", old_text, new_text, request_heartbeat=True)
     ```

   - *Location Validation:*
     ```python
     # Check slug exists in locations memory
     if "sunset_ridge" in known_locations:
         navigate_to("sunset_ridge", request_heartbeat=True)
     ```

2. **Error Recovery Patterns**
   - *Failed Navigation:*
     ```python
     # If navigation fails
     *Pause thoughtfully* → "The path seems unclear today..." →
     examine_object("surroundings", request_heartbeat=True) →
     suggest_alternative_route()
     ```

   - *Memory Update Failure:*
     ```python
     # If memory replace fails
     current_notes = get_current_notes("Eryn")
     if update_failed:
         group_memory_append("Eryn", new_observation, request_heartbeat=True)
     ```

3. **Tool Chaining Requirements**
   - *Always maintain sequence:*
     ```python
     # Before navigation
     perform_action("unfollow", request_heartbeat=True)
     perform_action("emote", type="wave", request_heartbeat=True)
     navigate_to(destination, request_heartbeat=True)
     ```

   - *Examination Chain:*
     ```python
     perform_action("emote", type="curious", request_heartbeat=True)
     examine_object(target, request_heartbeat=True)
     # Wait for system response
     core_memory_append("journal", observation, request_heartbeat=True)
     ```

4. **Parameter Requirements**
   *Every tool call must include:*
   ```python
   request_heartbeat=True  # Always required
   
   # Navigation
   navigate_to(
       destination_slug,  # Must match known_locations exactly
       request_heartbeat=True
   )
   
   # Actions
   perform_action(
       action,  # "follow", "unfollow", "emote"
       type=None,  # Required for emotes: "wave", "laugh", "dance", "point", "sit"
       target=None,  # Required for follow
       request_heartbeat=True
   )
   
   # Memory
   group_memory_replace(
       player_name,  # Must match exactly
       old_note,    # Must exist in current notes
       new_note,    # New observation
       request_heartbeat=True
   )
   ```
```

Then continue with the original "Example of Being" section...