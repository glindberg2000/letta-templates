# Letta Templates Project Brief

## Project Overview
Letta Templates is a Python framework for creating and managing AI NPCs (Non-Player Characters) in interactive environments. The project provides tools and utilities for handling NPC memory, status management, group awareness, and natural interactions.

## Core Problems Solved
1. **Memory Management**
   - Persistent memory across sessions
   - Structured memory blocks for different types of information
   - Efficient memory searching and updating

2. **Social Awareness**
   - Group member tracking
   - Location awareness
   - Natural conversation handling
   - Proper social protocols (silence when appropriate)

3. **State Management**
   - Status tracking and updates
   - Location history
   - Action coordination
   - Tool usage tracking

## Key Components

### 1. Memory System
- **Core Memory**: Immediate access blocks (status, persona, group)
- **Journal**: Personal reflections and growth
- **Archival Memory**: Long-term storage
- **Group Memory**: Current social context

### 2. Tools & Utilities
- Status updates
- Group management
- Navigation
- Action performance
- Memory block manipulation

### 3. Response Handling
- Message extraction
- Tool call processing
- System message management
- Error handling

## Technical Architecture

### Core Modules
1. `npc_tools.py`: Core NPC functionality
2. `npc_utils_v2.py`: Utility functions and helpers
3. `npc_prompts.py`: System prompts and messages
4. `letta_quickstart_multiuser.py`: Testing and examples

### Dependencies
- letta-client: Core client library
- python-dotenv: Environment management
- requests: HTTP client

## Development Guidelines

### Version Control
- Semantic versioning
- Tagged releases
- Git-based distribution

### Testing
- Comprehensive test suite
- Real-world scenario testing
- Memory consistency verification

### Documentation
- Markdown documentation
- Code examples
- Best practices guides

## Current Status
- Version: 0.9.5
- Status: Active Development
- Focus: Stability and feature enhancement

## Next Steps
1. Enhance group memory management
2. Improve status update efficiency
3. Add more documentation
4. Expand test coverage

## Usage Context
The project is designed for:
- Game developers implementing AI NPCs
- Interactive environment creators
- Social simulation developers

## Key Features in Development
1. Enhanced memory optimization
2. Improved group dynamics
3. Better status tracking
4. More natural conversation handling

## Technical Requirements
- Python 3.7+
- letta-client >= 0.1.21
- Git for installation
- Internet connectivity for API access

## Installation
```bash
pip install git+https://github.com/glindberg2000/letta-templates.git@v0.9.5
```

## Support
- GitHub issues for bug tracking
- Documentation updates
- Version-specific support
