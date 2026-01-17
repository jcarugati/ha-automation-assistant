"""Abstract base class for LLM clients."""

from abc import ABC, abstractmethod


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def generate_automation(
        self, system_prompt: str, user_prompt: str
    ) -> str:
        """Generate an automation from the given prompts.

        Args:
            system_prompt: The system prompt with context about HA entities/services.
            user_prompt: The user's natural language request.

        Returns:
            The generated automation YAML with explanation.
        """
        pass
