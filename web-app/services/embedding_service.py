from typing import List, Optional
from openai import AzureOpenAI

from config.settings import (
    AZURE_OPENAI_EMBEDDING_ENDPOINT,
    AZURE_OPENAI_EMBEDDING_API_KEY,
    AZURE_OPENAI_EMBEDDING_API_VERSION,
)


class EmbeddingService:
    """
    Service for generating embeddings using Azure OpenAI text-embedding-3-large.
    Used for creating vector representations of document chunks for RAG.
    """

    _instance: Optional["EmbeddingService"] = None

    def __init__(self):
        # Extract the base endpoint and deployment name from the full URL
        # Expected format: https://{resource}.openai.azure.com/openai/deployments/{deployment}/embeddings?api-version=...
        if AZURE_OPENAI_EMBEDDING_ENDPOINT:
            endpoint_parts = AZURE_OPENAI_EMBEDDING_ENDPOINT.split("/openai/deployments/")
            self.azure_endpoint = endpoint_parts[0]

            if len(endpoint_parts) > 1:
                deployment_part = endpoint_parts[1].split("/")[0]
                self.deployment_name = deployment_part
            else:
                self.deployment_name = "text-embedding-3-large"
        else:
            self.azure_endpoint = None
            self.deployment_name = "text-embedding-3-large"

        self.client = AzureOpenAI(
            azure_endpoint=self.azure_endpoint,
            api_key=AZURE_OPENAI_EMBEDDING_API_KEY,
            api_version=AZURE_OPENAI_EMBEDDING_API_VERSION,
        ) if self.azure_endpoint else None

        # Embedding dimensions for text-embedding-3-large
        self.dimensions = 3072

    @classmethod
    def get_instance(cls) -> "EmbeddingService":
        """Get singleton instance of EmbeddingService."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def is_configured(self) -> bool:
        """Check if the service is properly configured."""
        return self.client is not None

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector
        """
        if not self.client:
            raise ValueError("Embedding service not configured. Check environment variables.")

        # Truncate text if too long (max ~8000 tokens for embedding models)
        max_chars = 30000  # Approximate safe limit
        if len(text) > max_chars:
            text = text[:max_chars]

        response = self.client.embeddings.create(
            model=self.deployment_name,
            input=text,
        )

        return response.data[0].embedding

    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 20) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts per API call (max 2048 for Azure)

        Returns:
            List of embedding vectors
        """
        if not self.client:
            raise ValueError("Embedding service not configured. Check environment variables.")

        all_embeddings = []

        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            # Truncate each text
            max_chars = 30000
            truncated_batch = [t[:max_chars] if len(t) > max_chars else t for t in batch]

            response = self.client.embeddings.create(
                model=self.deployment_name,
                input=truncated_batch,
            )

            # Extract embeddings in order
            batch_embeddings = [data.embedding for data in response.data]
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    def create_chunk_embedding_text(self, chunk: dict) -> str:
        """
        Create optimized text for embedding from a chunk.
        Combines summary, content, and metadata for better retrieval.

        Args:
            chunk: Chunk dict with content, summary, pillar, etc.

        Returns:
            Combined text optimized for embedding
        """
        parts = []

        # Add summary first (most important for retrieval)
        if chunk.get("summary"):
            parts.append(f"Summary: {chunk['summary']}")

        # Add pillar classification
        if chunk.get("pillar"):
            pillar_name = chunk["pillar"].replace("_", " ").title()
            parts.append(f"Category: {pillar_name}")

        # Add main content
        if chunk.get("content"):
            parts.append(f"Content: {chunk['content']}")

        # Add key metadata if present
        metadata = chunk.get("metadata", {})
        if metadata.get("section_title"):
            parts.append(f"Section: {metadata['section_title']}")
        if metadata.get("key_entities"):
            parts.append(f"Entities: {', '.join(metadata['key_entities'])}")

        return "\n\n".join(parts)


# Convenience function
def get_embedding_service() -> EmbeddingService:
    """Get the singleton embedding service instance."""
    return EmbeddingService.get_instance()
