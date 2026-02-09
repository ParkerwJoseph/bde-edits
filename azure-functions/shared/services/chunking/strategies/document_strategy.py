"""
Document chunking strategy - per-page analysis with accumulated context.
"""
import json
import re
import time
from typing import List, Dict, Any, Optional

from shared.services.chunking.strategies.base_strategy import BaseStrategy
from shared.services.chunking.models import ChunkInput, ChunkOutput, NormalizedInput, SourceType, ProgressCallback
from shared.services.chunking.prompts import PromptManager
from shared.database.models.document import BDEPillar, ChunkType
from shared.utils.logger import get_logger

logger = get_logger(__name__)

# Rate limit management
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 65
INTER_PAGE_DELAY_SECONDS = 2


class DocumentChunkingStrategy(BaseStrategy):
    """
    Strategy for chunking document content (PDF, DOCX, etc.).

    Processes pages sequentially with accumulated context to maintain
    document coherence across chunks.
    """

    def __init__(self, llm_client, prompt_manager: PromptManager):
        super().__init__(llm_client, prompt_manager)

    async def execute(
        self,
        normalized_input: NormalizedInput,
        original_input: ChunkInput,
        progress_callback: Optional[ProgressCallback] = None
    ) -> List[ChunkOutput]:
        """
        Execute document chunking - page by page with context accumulation.

        Args:
            normalized_input: Normalized document pages
            original_input: Original input with document info
            progress_callback: Optional callback for progress updates.
                              Signature: (current_page, total_pages, step_name) -> None

        Returns:
            List of ChunkOutput objects
        """
        self._reset_usage_stats()

        content_units = normalized_input.content_units
        context = normalized_input.context
        total_pages = len(content_units)

        logger.info(f"[DocumentStrategy] Processing {total_pages} pages")

        all_chunks = []
        accumulated_context = ""
        document_summary_parts = []
        chunk_index = 0
        previous_chunk_summary = ""

        # Process each page sequentially
        for unit_idx, unit in enumerate(content_units):
            page_num = unit.get("unit_number", unit_idx + 1)

            logger.info(f"[DocumentStrategy] Processing page {page_num}/{total_pages}")

            # Send progress update before processing each page
            if progress_callback:
                try:
                    progress_callback(page_num, total_pages, f"Processing page {page_num} of {total_pages}")
                except Exception as e:
                    logger.warning(f"[DocumentStrategy] Progress callback failed: {e}")

            # Get prompt with context
            prompt = self.prompt_manager.get_prompt(
                source_type="document",
                context=context
            )

            # Format prompt with page-specific info
            formatted_prompt = prompt.replace("{page_number}", str(page_num))
            formatted_prompt = formatted_prompt.replace(
                "{accumulated_context}",
                accumulated_context if accumulated_context else "This is the first section."
            )

            # Build content for LLM
            content = self._build_llm_content(unit)

            try:
                # Call LLM with retry logic
                response, usage_stats = self._call_with_retry(
                    system_prompt=formatted_prompt,
                    content=content,
                    max_tokens=16000,
                    temperature=0.1
                )

                self._update_usage_stats(usage_stats)

                # Parse response
                result = self._parse_json_response(response)
                page_chunks = result.get("chunks", [])
                page_summary = result.get("page_summary", "")

                logger.info(f"[DocumentStrategy] Page {page_num}: extracted {len(page_chunks)} chunks")

                # Process chunks
                for chunk_data in page_chunks:
                    chunk_summary = chunk_data.get("summary", "")

                    chunk = ChunkOutput(
                        content=chunk_data.get("content", ""),
                        summary=chunk_summary,
                        pillar=self._validate_pillar(chunk_data.get("pillar", "general")),
                        chunk_type=self._validate_chunk_type(chunk_data.get("chunk_type", "text")),
                        confidence_score=min(1.0, max(0.0, chunk_data.get("confidence_score", 0.8))),
                        metadata=chunk_data.get("metadata", {}),
                        source_type=SourceType.DOCUMENT,
                        page_number=page_num,
                        chunk_index=chunk_index,
                        previous_context=previous_chunk_summary if previous_chunk_summary else None,
                    )
                    all_chunks.append(chunk)
                    chunk_index += 1

                    # Update previous chunk summary
                    if chunk_summary:
                        previous_chunk_summary = chunk_summary

                # Update accumulated context
                if page_summary:
                    document_summary_parts.append(f"Page {page_num}: {page_summary}")

                    # Keep last 5 summaries to avoid context overflow
                    if len(document_summary_parts) > 5:
                        accumulated_context = "Previous pages summary:\n" + "\n".join(document_summary_parts[-5:])
                    else:
                        accumulated_context = "Previous pages summary:\n" + "\n".join(document_summary_parts)

            except Exception as e:
                logger.error(f"[DocumentStrategy] Page {page_num} failed: {e}")
                # Create fallback chunk
                all_chunks.append(ChunkOutput(
                    content=f"Failed to extract content from page {page_num}",
                    summary=f"Extraction failed: {str(e)[:100]}",
                    pillar="general",
                    chunk_type="text",
                    confidence_score=0.1,
                    metadata={"error": str(e)},
                    source_type=SourceType.DOCUMENT,
                    page_number=page_num,
                    chunk_index=chunk_index,
                ))
                chunk_index += 1

            # Delay between pages to avoid rate limits
            if unit_idx < len(content_units) - 1:
                logger.debug(f"[DocumentStrategy] Waiting {INTER_PAGE_DELAY_SECONDS}s before next page")
                time.sleep(INTER_PAGE_DELAY_SECONDS)

        logger.info(f"[DocumentStrategy] Complete: {len(all_chunks)} total chunks")
        return all_chunks

    def _build_llm_content(self, unit: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build content list for LLM call"""
        content = []

        if unit.get("image_base64"):
            # Image content (PDF, PPTX)
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{unit['image_base64']}",
                    "detail": "high"
                }
            })
            content.append({
                "type": "text",
                "text": f"[This is Page {unit.get('unit_number', 1)}]"
            })
        elif unit.get("text_content"):
            # Text content (DOCX, XLSX, Audio)
            content.append({
                "type": "text",
                "text": f"[Section {unit.get('unit_number', 1)} Content]:\n{unit['text_content']}"
            })

        return content

    def _call_with_retry(
        self,
        system_prompt: str,
        content: List[Dict[str, Any]],
        max_tokens: int = 8000,
        temperature: float = 0.1
    ) -> tuple:
        """Call LLM API with retry logic for rate limits"""
        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                # Check if content has images
                has_images = any(item.get("type") == "image_url" for item in content)

                if has_images:
                    response, usage_stats = self.llm_client.chat_completion_with_images(
                        system_prompt=system_prompt,
                        content=content,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )
                else:
                    # Text-only request
                    text_content = "\n\n".join(
                        item.get("text", "") for item in content if item.get("type") == "text"
                    )
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text_content}
                    ]
                    response, usage_stats = self.llm_client.chat_completion(
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )

                return response, usage_stats

            except Exception as e:
                last_error = e
                error_str = str(e)

                if "429" in error_str or "RateLimitReached" in error_str or "rate limit" in error_str.lower():
                    if attempt < MAX_RETRIES:
                        logger.warning(f"[DocumentStrategy] Rate limit hit, waiting {RETRY_DELAY_SECONDS}s")
                        time.sleep(RETRY_DELAY_SECONDS)
                        continue

                raise

        raise last_error

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Parse JSON from LLM response"""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        try:
            # Try to extract JSON from markdown code blocks
            json_match = re.search(r'```(?:json)?\s*([\s\S]+?)\s*```', content)
            if json_match:
                return json.loads(json_match.group(1).strip())

            # Try to find JSON object directly
            json_match = re.search(r'(\{[\s\S]*\})', content)
            if json_match:
                return json.loads(json_match.group(1).strip())

            logger.error(f"[DocumentStrategy] No valid JSON found in response")
            return {"chunks": [], "page_summary": "Failed to parse response"}

        except json.JSONDecodeError as e:
            logger.error(f"[DocumentStrategy] JSON parse error: {e}")
            return {"chunks": [], "page_summary": "Failed to parse response"}

    def _validate_pillar(self, pillar: str) -> str:
        """Validate and normalize pillar value"""
        valid_pillars = [p.value for p in BDEPillar]
        pillar_lower = pillar.lower().replace(" ", "_").replace("-", "_")

        if pillar_lower in valid_pillars:
            return pillar_lower

        for valid in valid_pillars:
            if pillar_lower in valid or valid in pillar_lower:
                return valid

        return BDEPillar.GENERAL.value

    def _validate_chunk_type(self, chunk_type: str) -> str:
        """Validate and normalize chunk type value"""
        valid_types = [t.value for t in ChunkType]
        type_lower = chunk_type.lower()

        if type_lower in valid_types:
            return type_lower

        return ChunkType.TEXT.value
