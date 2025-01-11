"""Letta Templates - Tools and utilities for Letta AI server

This package provides reusable components for Letta AI:
- NPC tools and actions
- State management
- System prompts
"""

from letta_templates.letta_quickstart_multiuser import (
    create_personalized_agent,
    chat_with_agent,
    print_agent_details
)

from letta_templates.npc_utils import (
    update_group_status
)

__version__ = "0.7.0"
__all__ = [
    'create_personalized_agent',
    'chat_with_agent',
    'print_agent_details',
    'update_group_status'
]
