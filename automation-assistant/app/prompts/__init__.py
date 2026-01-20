"""Prompt templates for automation generation."""

from .automation import build_system_prompt, build_user_prompt
from .conflicts import (
    build_batch_analysis_prompt,
    build_batch_summary_prompt,
    build_conflict_analysis_prompt,
    build_single_diagnosis_summary_prompt,
)
from .debug import build_debug_system_prompt, build_debug_user_prompt

__all__ = [
    "build_system_prompt",
    "build_user_prompt",
    "build_debug_system_prompt",
    "build_debug_user_prompt",
    "build_batch_analysis_prompt",
    "build_batch_summary_prompt",
    "build_conflict_analysis_prompt",
    "build_single_diagnosis_summary_prompt",
]
