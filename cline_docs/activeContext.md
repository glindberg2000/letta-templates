# Active Context

## Current Work
- Implemented upsert_group_member for game state
- Added comprehensive documentation
- Updated setup.py and dependencies

## Recent Changes
1. Memory Structure
   - Standardized fields (is_present, last_seen, etc.)
   - FIFO pruning at 4800 chars
   - Timestamp management

2. Tool Separation
   - NPCs: group_memory_append/replace
   - Game: upsert_group_member
   - System: update_group_block

## Next Steps
1. Test with live game cluster
2. Monitor memory usage
3. Add validation for fields 