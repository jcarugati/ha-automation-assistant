"""Shared prompt helpers."""


def build_toon_section(toon_context: str) -> str:
    """Build the TOON context section for prompts."""
    return (
        "## Available Context (TOON format)\n"
        "The following data is encoded in TOON (a compact JSON-like format). "
        "Decode it to access areas, devices, entities, and services.\n"
        "```toon\n"
        f"{toon_context}\n"
        "```\n\n"
    )
