"""OpenRouter API client implementation (future use)."""

import logging

import aiohttp

from .base import LLMClient

logger = logging.getLogger(__name__)


class OpenRouterClient(LLMClient):
    """OpenRouter API client for automation generation.

    This is a placeholder for future OpenRouter integration.
    OpenRouter provides an OpenAI-compatible API for multiple LLM providers.
    """

    def __init__(self, api_key: str, model: str = "anthropic/claude-3.5-sonnet"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1"

    async def generate_automation(
        self, system_prompt: str, user_prompt: str
    ) -> str:
        """Generate an automation using OpenRouter.

        Args:
            system_prompt: The system prompt with context about HA entities/services.
            user_prompt: The user's natural language request.

        Returns:
            The generated automation YAML with explanation.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://home-assistant.io",
            "X-Title": "Home Assistant Automation Assistant",
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": 4096,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return data["choices"][0]["message"]["content"]

        except aiohttp.ClientError as e:
            logger.error(f"OpenRouter API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling OpenRouter: {e}")
            raise
