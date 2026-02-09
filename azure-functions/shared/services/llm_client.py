from typing import List, Optional, Dict, Any
from openai import AzureOpenAI

from shared.config.settings import (
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION,
)
from shared.utils.logger import get_logger

logger = get_logger(__name__)


class LLMClient:
    """
    Reusable Azure OpenAI client wrapper for GPT-4o-mini.
    """

    _instance: Optional["LLMClient"] = None

    def __init__(self):
        logger.info("=" * 60)
        logger.info("Initializing LLMClient...")

        if AZURE_OPENAI_ENDPOINT:
            endpoint_parts = AZURE_OPENAI_ENDPOINT.split("/openai/deployments/")
            self.azure_endpoint = endpoint_parts[0]

            if len(endpoint_parts) > 1:
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

        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_requests = 0

        if self.client:
            logger.info(f"LLMClient initialized successfully")
            logger.info(f"  Endpoint: {self.azure_endpoint}")
            logger.info(f"  Model: {self.deployment_name}")
        else:
            logger.warning("LLMClient NOT configured - Azure OpenAI endpoint not set")
        logger.info("=" * 60)

    @classmethod
    def get_instance(cls) -> "LLMClient":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def is_configured(self) -> bool:
        return self.client is not None

    def get_token_stats(self) -> Dict[str, int]:
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

        usage = response.usage
        usage_stats = {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
        }

        self.total_prompt_tokens += usage.prompt_tokens
        self.total_completion_tokens += usage.completion_tokens
        self.total_requests += 1

        logger.info(f"[LLM] Response received: {usage.total_tokens:,} tokens")

        return response.choices[0].message.content, usage_stats

    def chat_completion_with_images(
        self,
        system_prompt: str,
        content: List[dict],
        max_tokens: int = 16000,
        temperature: float = 0.1,
        **kwargs
    ) -> tuple[str, Dict[str, Any]]:
        if not self.client:
            raise ValueError("Azure OpenAI client not configured. Check environment variables.")

        image_count = sum(1 for item in content if item.get("type") == "image_url")
        logger.info(f"[LLM] Sending vision request with {image_count} image(s)")

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

        usage = response.usage
        usage_stats = {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "image_count": image_count,
        }

        self.total_prompt_tokens += usage.prompt_tokens
        self.total_completion_tokens += usage.completion_tokens
        self.total_requests += 1

        logger.info(f"[LLM] Vision response received: {usage.total_tokens:,} tokens")

        return response.choices[0].message.content, usage_stats


def get_llm_client() -> LLMClient:
    return LLMClient.get_instance()
