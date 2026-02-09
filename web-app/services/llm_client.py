from typing import List, Optional, Dict, Any
from openai import AzureOpenAI

from config.settings import (
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION,
)
from utils.logger import get_logger

logger = get_logger(__name__)


class LLMClient:
    """
    Reusable Azure OpenAI client wrapper for GPT-4o-mini.
    Can be used across different services that need LLM capabilities.
    """

    _instance: Optional["LLMClient"] = None

    def __init__(self):
        logger.info("=" * 60)
        logger.info("Initializing LLMClient...")

        # Extract the base endpoint and deployment name from the full URL
        # Expected format: https://{resource}.openai.azure.com/openai/deployments/{deployment}/chat/completions?api-version=...
        if AZURE_OPENAI_ENDPOINT:
            # Parse the endpoint to get base URL
            endpoint_parts = AZURE_OPENAI_ENDPOINT.split("/openai/deployments/")
            self.azure_endpoint = endpoint_parts[0]

            if len(endpoint_parts) > 1:
                # Extract deployment name
                deployment_part = endpoint_parts[1].split("/")[0]
                self.deployment_name = deployment_part
            else:
                self.deployment_name = "gpt-4o-mini"
        else:
            self.azure_endpoint = None
            self.deployment_name = "gpt-4o-mini"

        self.client = AzureOpenAI(
            azure_endpoint=self.azure_endpoint,
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
        ) if self.azure_endpoint else None

        # Track total token usage across all requests
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_requests = 0

        if self.client:
            logger.info(f"LLMClient initialized successfully")
            logger.info(f"  Endpoint: {self.azure_endpoint}")
            logger.info(f"  Model: {self.deployment_name}")
            logger.info(f"  API Version: {AZURE_OPENAI_API_VERSION}")
        else:
            logger.warning("LLMClient NOT configured - Azure OpenAI endpoint not set")
        logger.info("=" * 60)

    @classmethod
    def get_instance(cls) -> "LLMClient":
        """Get singleton instance of LLMClient."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def is_configured(self) -> bool:
        """Check if the client is properly configured."""
        return self.client is not None

    def get_token_stats(self) -> Dict[str, int]:
        """Get cumulative token usage statistics."""
        return {
            "total_requests": self.total_requests,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_prompt_tokens + self.total_completion_tokens,
        }

    def chat_completion(
        self,
        messages: List[dict],
        max_tokens: int = 4000,
        temperature: float = 0.7,
        **kwargs
    ) -> tuple[str, Dict[str, Any]]:
        """
        Send a chat completion request to Azure OpenAI.

        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-2)
            **kwargs: Additional parameters passed to the API

        Returns:
            Tuple of (response content, usage stats dict)
        """
        if not self.client:
            raise ValueError("Azure OpenAI client not configured. Check environment variables.")

        logger.info(f"[LLM] Sending chat completion request (max_tokens={max_tokens}, temp={temperature})")

        response = self.client.chat.completions.create(
            model=self.deployment_name,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )

        # Extract usage stats
        usage = response.usage
        usage_stats = {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
        }

        # Update cumulative stats
        self.total_prompt_tokens += usage.prompt_tokens
        self.total_completion_tokens += usage.completion_tokens
        self.total_requests += 1

        logger.info(f"[LLM] Response received:")
        logger.info(f"  Prompt tokens: {usage.prompt_tokens:,}")
        logger.info(f"  Completion tokens: {usage.completion_tokens:,}")
        logger.info(f"  Total tokens: {usage.total_tokens:,}")

        return response.choices[0].message.content, usage_stats

    def chat_completion_with_images(
        self,
        system_prompt: str,
        content: List[dict],
        max_tokens: int = 16000,
        temperature: float = 0.1,
        **kwargs
    ) -> tuple[str, Dict[str, Any]]:
        """
        Send a chat completion request with images (vision).

        Args:
            system_prompt: System message for the conversation
            content: List of content items (text and images)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            **kwargs: Additional parameters

        Returns:
            Tuple of (response content, usage stats dict)
        """
        if not self.client:
            raise ValueError("Azure OpenAI client not configured. Check environment variables.")

        # Count images in content
        image_count = sum(1 for item in content if item.get("type") == "image_url")
        logger.info(f"[LLM] Sending vision request with {image_count} image(s)")
        logger.info(f"  Max tokens: {max_tokens}, Temperature: {temperature}")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content}
        ]

        response = self.client.chat.completions.create(
            model=self.deployment_name,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )

        # Extract usage stats
        usage = response.usage
        usage_stats = {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "image_count": image_count,
        }

        # Update cumulative stats
        self.total_prompt_tokens += usage.prompt_tokens
        self.total_completion_tokens += usage.completion_tokens
        self.total_requests += 1

        logger.info(f"[LLM] Vision response received:")
        logger.info(f"  Prompt tokens: {usage.prompt_tokens:,}")
        logger.info(f"  Completion tokens: {usage.completion_tokens:,}")
        logger.info(f"  Total tokens: {usage.total_tokens:,}")
        logger.info(f"  Cumulative tokens (all requests): {self.total_prompt_tokens + self.total_completion_tokens:,}")

        return response.choices[0].message.content, usage_stats

    def chat_completion_stream(
        self,
        messages: List[dict],
        max_tokens: int = 4000,
        temperature: float = 0.7,
        **kwargs
    ):
        """
        Send a streaming chat completion request to Azure OpenAI.

        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-2)
            **kwargs: Additional parameters passed to the API

        Yields:
            Chunks of response content as they arrive
        """
        if not self.client:
            raise ValueError("Azure OpenAI client not configured. Check environment variables.")

        logger.info(f"[LLM] Sending streaming chat request (max_tokens={max_tokens}, temp={temperature})")

        stream = self.client.chat.completions.create(
            model=self.deployment_name,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
            **kwargs
        )

        for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content


# Convenience function to get the client
def get_llm_client() -> LLMClient:
    """Get the singleton LLM client instance."""
    return LLMClient.get_instance()
