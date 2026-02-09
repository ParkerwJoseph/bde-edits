"""
Base adapter interface for content normalization.
"""
from abc import ABC, abstractmethod
from typing import List, Any

from services.chunking.models import ChunkInput, ChunkOutput, NormalizedInput


class BaseAdapter(ABC):
    """
    Abstract base class for content adapters.

    Adapters are responsible for converting source-specific input formats
    into a normalized format that strategies can process consistently.
    """

    @abstractmethod
    def normalize(self, input: ChunkInput) -> NormalizedInput:
        """
        Convert source-specific input to normalized format.

        Args:
            input: Source-specific ChunkInput

        Returns:
            NormalizedInput with content_units, context, and source_info
        """
        pass

    @abstractmethod
    def denormalize(self, chunks: List[ChunkOutput], input: ChunkInput) -> List[Any]:
        """
        Convert chunks back to source-specific model format for storage.

        Args:
            chunks: List of ChunkOutput from chunking
            input: Original ChunkInput for context

        Returns:
            List of source-specific model instances (DocumentChunk or ConnectorChunk)
        """
        pass
