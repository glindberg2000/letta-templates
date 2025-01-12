"""Letta Templates - Tools and utilities for Letta AI server

This package provides reusable components for Letta AI:
- NPC tools and actions
- State management
- System prompts
"""

from letta_templates.letta_quickstart_template import (
    create_personalized_agent,
    chat_with_agent,
    print_agent_details
)

from letta_templates.npc_utils import (
    update_group_status,
    get_memory_block,
    update_memory_block,
    create_memory_blocks
)

__version__ = "0.8.0"
__all__ = [
    'create_personalized_agent',
    'chat_with_agent',
    'print_agent_details',
    'update_group_status',
    'get_memory_block',
    'update_memory_block',
    'create_memory_blocks'
]
