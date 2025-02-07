# Product Context

## Purpose
- Provide tools for NPCs and game systems to manage group memory
- Maintain separation between NPC observations and game state
- Support real-time player tracking and interactions

## Problems Solved
1. Memory Management
   - Structured data storage for NPCs
   - FIFO pruning for size limits
   - Standardized field formats

2. State Synchronization
   - NPCs track observations
   - Game system tracks player state
   - Clean separation of concerns

3. Documentation
   - Clear API boundaries
   - Usage examples
   - Best practices

## Why This Project Exists
Letta Templates is a Python framework created to solve the challenge of building intelligent, socially-aware NPCs (Non-Player Characters) in interactive environments. It provides a structured way to manage NPC memory, status, and group interactions.

## How It Should Work
The system should:
1. Maintain consistent NPC memory and state
2. Handle social interactions naturally
3. Process and respond to events appropriately
4. Track group dynamics and location changes
5. Provide tools for managing NPC behavior 