from typing import Optional
from sqlmodel import Session, select
from datetime import datetime, timedelta

from database.models.prompt_template import PromptTemplate, DEFAULT_RAG_PROMPT
from utils.logger import get_logger

logger = get_logger(__name__)

# Cache for prompt to avoid DB hits on every RAG call
_prompt_cache: Optional[str] = None
_cache_timestamp: Optional[datetime] = None
CACHE_TTL_SECONDS = 300  # 5 minutes


class PromptService:
    """
    Service for retrieving the RAG system prompt.
    Uses in-memory caching to avoid database hits on every request.
    """

    def get_rag_prompt(self, session: Session) -> str:
        """
        Get the active RAG system prompt.
        Returns cached prompt if available and fresh, otherwise fetches from DB.
        Falls back to default if no prompt exists in DB.
        """
        global _prompt_cache, _cache_timestamp

        # Check if cache is valid
        if _prompt_cache is not None and _cache_timestamp is not None:
            if datetime.utcnow() - _cache_timestamp < timedelta(seconds=CACHE_TTL_SECONDS):
                logger.debug("[PromptService] Returning cached prompt")
                return _prompt_cache

        # Fetch from database
        logger.info("[PromptService] Fetching prompt from database")
        prompt = session.exec(
            select(PromptTemplate).where(PromptTemplate.is_active == True)
        ).first()

        if prompt:
            _prompt_cache = prompt.template
            _cache_timestamp = datetime.utcnow()
            logger.info(f"[PromptService] Loaded prompt version {prompt.version}")
            return prompt.template

        # Fallback to default
        logger.info("[PromptService] No prompt in DB, using default")
        _prompt_cache = DEFAULT_RAG_PROMPT
        _cache_timestamp = datetime.utcnow()
        return DEFAULT_RAG_PROMPT

    def invalidate_cache(self):
        """Invalidate the prompt cache. Call this after prompt updates."""
        global _prompt_cache, _cache_timestamp
        _prompt_cache = None
        _cache_timestamp = None
        logger.info("[PromptService] Cache invalidated")


# Singleton instance
_prompt_service: Optional[PromptService] = None


def get_prompt_service() -> PromptService:
    """Get the singleton PromptService instance."""
    global _prompt_service
    if _prompt_service is None:
        _prompt_service = PromptService()
    return _prompt_service
