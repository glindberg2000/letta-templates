"""Letta Templates - Tools and utilities for Letta AI server

This package provides reusable components for Letta AI:
- NPC tools and actions
- State management
- System prompts
"""

from .npc_tools import (
    TOOL_INSTRUCTIONS,
    TOOL_REGISTRY,
    NAVIGATION_TOOLS,
    navigate_to,
    perform_action
)

__version__ = "0.2.11"
__all__ = [
    "TOOL_INSTRUCTIONS",
    "TOOL_REGISTRY",
    "perform_action",
    "navigate_to",
    "examine_object"
]
