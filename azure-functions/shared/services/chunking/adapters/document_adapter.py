"""
Document adapter for normalizing document page input.
"""
import json
from typing import List, Any

from shared.services.chunking.adapters.base_adapter import BaseAdapter
from shared.services.chunking.models import ChunkInput, ChunkOutput, NormalizedInput, SourceType
from shared.database.models.document import DocumentChunk


class DocumentAdapter(BaseAdapter):
    """
    Adapter for document content (PDF, DOCX, XLSX, PPTX, Audio).

    Normalizes pages/sections into content units for the document
    chunking strategy.
    """

    def normalize(self, input: ChunkInput) -> NormalizedInput:
        """
        Convert document pages to normalized content units.

        Args:
            input: ChunkInput with pages list

        Returns:
            NormalizedInput with page-based content units
        """
        pages = input.pages or []

        content_units = []
        for i, page in enumerate(pages):
            page_num = page.get("page_number", i + 1)

            content_units.append({
                "unit_type": "page",
                "unit_number": page_num,
                "has_image": page.get("image_base64") is not None,
                "image_base64": page.get("image_base64"),
                "text_content": page.get("text_content"),
                # Preserve any additional page metadata
                "width": page.get("width"),
                "height": page.get("height"),
                "char_count": page.get("char_count"),
                "estimated_tokens": page.get("estimated_tokens"),
            })

        return NormalizedInput(
            content_units=content_units,
            context={
                "document_filename": input.document_filename or "Unknown",
                "total_pages": len(pages),
            },
            source_info={
                "document_id": input.document_id,
                "tenant_id": input.tenant_id,
                "company_id": input.company_id,
            }
        )

    def denormalize(self, chunks: List[ChunkOutput], input: ChunkInput) -> List[DocumentChunk]:
        """
        Convert ChunkOutput list to DocumentChunk models.

        Args:
            chunks: List of ChunkOutput from chunking
            input: Original ChunkInput for IDs

        Returns:
            List of DocumentChunk instances ready for database insertion
        """
        return [
            DocumentChunk(
                document_id=input.document_id,
                tenant_id=input.tenant_id,
                company_id=input.company_id,
                content=chunk.content,
                summary=chunk.summary,
                pillar=chunk.pillar,
                chunk_type=chunk.chunk_type,
                page_number=chunk.page_number or 0,
                chunk_index=chunk.chunk_index or 0,
                confidence_score=chunk.confidence_score,
                metadata_json=json.dumps(chunk.metadata) if chunk.metadata else None,
                previous_context=chunk.previous_context,
                embedding=chunk.embedding,
            )
            for chunk in chunks
        ]
