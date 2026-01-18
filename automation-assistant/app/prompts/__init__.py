"""Prompt templates for automation generation."""

from .automation import build_system_prompt, build_user_prompt
from .debug import build_debug_system_prompt, build_debug_user_prompt

__all__ = [
    "build_system_prompt",
    "build_user_prompt",
    "build_debug_system_prompt",
    "build_debug_user_prompt",
]
