"""Claude API client implementation."""

import logging

import anthropic

from ..config import config
from .base import LLMClient

logger = logging.getLogger(__name__)


class ClaudeClient(LLMClient):
    """Claude API client for automation generation."""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=config.claude_api_key)
        self.model = config.model

    async def generate_automation(
        self, system_prompt: str, user_prompt: str
    ) -> str:
        """Generate an automation using Claude.

        Args:
            system_prompt: The system prompt with context about HA entities/services.
            user_prompt: The user's natural language request.

        Returns:
            The generated automation YAML with explanation.
        """
        try:
            # Use synchronous client in async context
            # anthropic SDK handles this correctly
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
            )

            # Extract text from response
            response_text = ""
            for block in message.content:
                if block.type == "text":
                    response_text += block.text

            return response_text

        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling Claude: {e}")
            raise


class AsyncClaudeClient(LLMClient):
    """Async Claude API client for automation generation."""

    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=config.claude_api_key)
        self.model = config.model

    async def generate_automation(
        self, system_prompt: str, user_prompt: str
    ) -> str:
        """Generate an automation using Claude.

        Args:
            system_prompt: The system prompt with context about HA entities/services.
            user_prompt: The user's natural language request.

        Returns:
            The generated automation YAML with explanation.
        """
        try:
            message = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
            )

            # Extract text from response
            response_text = ""
            for block in message.content:
                if block.type == "text":
                    response_text += block.text

            return response_text

        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling Claude: {e}")
            raise
