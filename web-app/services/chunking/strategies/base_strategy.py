"""
Base strategy interface for chunking operations.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any

from services.chunking.models import ChunkInput, ChunkOutput, NormalizedInput
from services.chunking.prompts import PromptManager


class BaseStrategy(ABC):
    """
    Abstract base class for chunking strategies.

    Strategies implement the actual chunking logic for different source types.
    They use the LLM client to process content and return ChunkOutput objects.
    """

    def __init__(self, llm_client, prompt_manager: PromptManager):
        """
        Initialize strategy with shared services.

        Args:
            llm_client: LLM client for API calls
            prompt_manager: Prompt manager for getting prompts
        """
        self.llm_client = llm_client
        self.prompt_manager = prompt_manager
        self._usage_stats = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "llm_calls": 0,
        }

    @abstractmethod
    async def execute(
        self,
        normalized_input: NormalizedInput,
        original_input: ChunkInput
    ) -> List[ChunkOutput]:
        """
        Execute the chunking strategy.

        Args:
            normalized_input: Normalized input from adapter
            original_input: Original ChunkInput for reference

        Returns:
            List of ChunkOutput objects
        """
        pass

    def get_usage_stats(self) -> Dict[str, int]:
        """Get token usage statistics"""
        return self._usage_stats.copy()

    def _update_usage_stats(self, usage: Dict[str, Any]) -> None:
        """Update usage statistics from LLM response"""
        self._usage_stats["prompt_tokens"] += usage.get("prompt_tokens", 0)
        self._usage_stats["completion_tokens"] += usage.get("completion_tokens", 0)
        self._usage_stats["total_tokens"] += usage.get("total_tokens", 0)
        self._usage_stats["llm_calls"] += 1

    def _reset_usage_stats(self) -> None:
        """Reset usage statistics for new operation"""
        self._usage_stats = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "llm_calls": 0,
        }
