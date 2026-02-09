from typing import List, Optional
from openai import AzureOpenAI

from shared.config.settings import (
    AZURE_OPENAI_EMBEDDING_ENDPOINT,
    AZURE_OPENAI_EMBEDDING_API_KEY,
    AZURE_OPENAI_EMBEDDING_API_VERSION,
)


class EmbeddingService:
    """Service for generating embeddings using Azure OpenAI text-embedding-3-large."""

    _instance: Optional["EmbeddingService"] = None

    def __init__(self):
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

        self.dimensions = 3072

    @classmethod
    def get_instance(cls) -> "EmbeddingService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def is_configured(self) -> bool:
        return self.client is not None

    def generate_embedding(self, text: str) -> List[float]:
        if not self.client:
            raise ValueError("Embedding service not configured.")

        max_chars = 30000
        if len(text) > max_chars:
            text = text[:max_chars]

        response = self.client.embeddings.create(
            model=self.deployment_name,
            input=text,
        )

        return response.data[0].embedding

    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 20) -> List[List[float]]:
        if not self.client:
            raise ValueError("Embedding service not configured.")

        all_embeddings = []
        max_chars = 30000

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            truncated_batch = [t[:max_chars] if len(t) > max_chars else t for t in batch]

            response = self.client.embeddings.create(
                model=self.deployment_name,
                input=truncated_batch,
            )

            batch_embeddings = [data.embedding for data in response.data]
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    def create_chunk_embedding_text(self, chunk: dict) -> str:
        parts = []

        if chunk.get("summary"):
            parts.append(f"Summary: {chunk['summary']}")

        if chunk.get("pillar"):
            pillar_name = chunk["pillar"].replace("_", " ").title()
            parts.append(f"Category: {pillar_name}")

        if chunk.get("content"):
            parts.append(f"Content: {chunk['content']}")

        metadata = chunk.get("metadata", {})
        if metadata.get("section_title"):
            parts.append(f"Section: {metadata['section_title']}")
        if metadata.get("key_entities"):
            parts.append(f"Entities: {', '.join(metadata['key_entities'])}")

        return "\n\n".join(parts)


def get_embedding_service() -> EmbeddingService:
    return EmbeddingService.get_instance()
