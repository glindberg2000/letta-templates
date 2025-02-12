# Technical Context

## Technologies
- Python 3.8+
- letta-client 0.1.26+
- pydantic 2.10.6+

## Development Setup
1. Installation:
```bash
pip install git+https://github.com/glindberg2000/letta-templates.git@v3.1.0
```

2. Dependencies:
   - httpx
   - anyio
   - python-dotenv
   - requests

## Constraints
- Memory block size < 5000 chars
- Real-time updates needed
- Backward compatibility 

## Action System Implementation
- perform_action handles core NPC behaviors
- navigate_to handles all point-to-point movement
- Heartbeat system maintains state awareness
- Validation ensures proper action/target usage

## Key Functions
- perform_action: Core NPC behaviors
- navigate_to: Movement with style options
- Both support heartbeat for state tracking 