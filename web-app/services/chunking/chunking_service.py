"""
Unified ChunkingService for documents and connectors.

This service provides a single interface for chunking content from any source
with consistent quality and output format.
"""
import json
from typing import List, Dict, Any, Optional, TYPE_CHECKING

from services.llm_client import get_llm_client
from services.embedding_service import get_embedding_service
from services.chunking.models import (
    SourceType,
    ChunkInput,
    ChunkOutput,
    ChunkingResult,
)
from services.chunking.prompts import get_prompt_manager
from utils.logger import get_logger

if TYPE_CHECKING:
    from services.chunking.adapters.base_adapter import BaseAdapter
    from services.chunking.strategies.base_strategy import BaseStrategy

logger = get_logger(__name__)


class ChunkingService:
    """
    Unified chunking service for both documents and connectors.

    Responsibilities:
    - Route inputs to appropriate chunking strategy
    - Manage LLM calls with consistent retry logic
    - Generate embeddings for all chunks
    - Return consistent chunk format

    Usage:
        service = get_chunking_service()
        result = await service.process(ChunkInput(...))
    """

    _instance: Optional["ChunkingService"] = None

    def __init__(self):
        self.llm_client = get_llm_client()
        self.embedding_service = get_embedding_service()
        self.prompt_manager = get_prompt_manager()

        # Lazy-loaded strategies and adapters
        self._strategies: Dict[SourceType, "BaseStrategy"] = {}
        self._adapters: Dict[SourceType, "BaseAdapter"] = {}

        logger.info("[ChunkingService] Initialized")

    @classmethod
    def get_instance(cls) -> "ChunkingService":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_strategy(self, source_type: SourceType) -> "BaseStrategy":
        """Get or create strategy for source type"""
        if source_type not in self._strategies:
            if source_type == SourceType.DOCUMENT:
                from services.chunking.strategies.document_strategy import DocumentChunkingStrategy
                self._strategies[source_type] = DocumentChunkingStrategy(
                    llm_client=self.llm_client,
                    prompt_manager=self.prompt_manager
                )
            elif source_type == SourceType.CONNECTOR:
                from services.chunking.strategies.connector_strategy import ConnectorChunkingStrategy
                self._strategies[source_type] = ConnectorChunkingStrategy(
                    llm_client=self.llm_client,
                    prompt_manager=self.prompt_manager
                )
            else:
                raise ValueError(f"Unknown source type: {source_type}")

        return self._strategies[source_type]

    def _get_adapter(self, source_type: SourceType) -> "BaseAdapter":
        """Get or create adapter for source type"""
        if source_type not in self._adapters:
            if source_type == SourceType.DOCUMENT:
                from services.chunking.adapters.document_adapter import DocumentAdapter
                self._adapters[source_type] = DocumentAdapter()
            elif source_type == SourceType.CONNECTOR:
                from services.chunking.adapters.connector_adapter import ConnectorAdapter
                self._adapters[source_type] = ConnectorAdapter()
            else:
                raise ValueError(f"Unknown source type: {source_type}")

        return self._adapters[source_type]

    async def process(self, input: ChunkInput) -> ChunkingResult:
        """
        Main entry point for all chunking operations.

        Args:
            input: ChunkInput with source-specific data

        Returns:
            ChunkingResult with chunks, overview, and usage stats
        """
        logger.info(f"[ChunkingService] Processing {input.source_type.value} input")
        logger.info(f"[ChunkingService] tenant={input.tenant_id}, company={input.company_id}")

        # Get adapter and strategy
        adapter = self._get_adapter(input.source_type)
        strategy = self._get_strategy(input.source_type)

        # Normalize input
        normalized = adapter.normalize(input)
        logger.info(f"[ChunkingService] Normalized to {len(normalized.content_units)} content units")

        # Execute chunking strategy
        chunks = await strategy.execute(normalized, input)
        logger.info(f"[ChunkingService] Strategy produced {len(chunks)} chunks")

        # Generate embeddings
        chunks = await self._generate_embeddings(chunks)
        logger.info(f"[ChunkingService] Embeddings generated for {len(chunks)} chunks")

        # Build result
        return ChunkingResult(
            chunks=chunks,
            overview=self._build_overview(chunks, input),
            usage_stats=strategy.get_usage_stats()
        )

    async def _generate_embeddings(self, chunks: List[ChunkOutput]) -> List[ChunkOutput]:
        """Generate embeddings for all chunks"""
        if not self.embedding_service.is_configured():
            logger.warning("[ChunkingService] Embedding service not configured, skipping")
            return chunks

        for i, chunk in enumerate(chunks):
            try:
                embedding_text = self._create_embedding_text(chunk)
                chunk.embedding = self.embedding_service.generate_embedding(embedding_text)
            except Exception as e:
                logger.error(f"[ChunkingService] Failed to generate embedding for chunk {i}: {e}")
                chunk.embedding = None

        return chunks

    def _create_embedding_text(self, chunk: ChunkOutput) -> str:
        """Create optimized text for embedding - consistent across all sources"""
        parts = []

        # Summary first (most important for retrieval)
        if chunk.summary:
            parts.append(f"Summary: {chunk.summary}")

        # Category/pillar
        if chunk.pillar:
            pillar_name = chunk.pillar.replace("_", " ").title()
            parts.append(f"Category: {pillar_name}")

        # Content
        if chunk.content:
            parts.append(f"Content: {chunk.content}")

        # Entity info for connectors
        if chunk.entity_type:
            parts.append(f"Data Type: {chunk.entity_type}")
        if chunk.entity_name:
            parts.append(f"Name: {chunk.entity_name}")

        return "\n\n".join(parts)

    def _build_overview(self, chunks: List[ChunkOutput], input: ChunkInput) -> Dict[str, Any]:
        """Build overview from processed chunks"""
        # Count chunks by pillar
        pillar_counts = {}
        for chunk in chunks:
            pillar = chunk.pillar or "general"
            pillar_counts[pillar] = pillar_counts.get(pillar, 0) + 1

        # Get top themes (pillars with most chunks)
        sorted_pillars = sorted(pillar_counts.items(), key=lambda x: x[1], reverse=True)
        top_themes = [p[0] for p in sorted_pillars[:3] if p[0] != "general"]

        overview = {
            "source_type": input.source_type.value,
            "total_chunks": len(chunks),
            "pillar_distribution": pillar_counts,
            "key_themes": top_themes,
        }

        # Add source-specific info
        if input.source_type == SourceType.DOCUMENT:
            overview["document_id"] = input.document_id
            overview["document_filename"] = input.document_filename
            overview["total_pages"] = len(input.pages) if input.pages else 0
        else:
            overview["connector_type"] = input.connector_type
            overview["entity_type"] = input.entity_type
            overview["total_records"] = len(input.raw_records) if input.raw_records else 0

        return overview


# Singleton factory
def get_chunking_service() -> ChunkingService:
    """Get singleton ChunkingService instance"""
    return ChunkingService.get_instance()
