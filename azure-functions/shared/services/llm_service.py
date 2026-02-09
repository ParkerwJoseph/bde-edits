import json
import re
import time
from typing import List, Dict, Any

from shared.services.llm_client import get_llm_client
from shared.database.models.document import BDEPillar, ChunkType, PILLAR_DESCRIPTIONS
from shared.utils.logger import get_logger

logger = get_logger(__name__)

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 65
INTER_PAGE_DELAY_SECONDS = 2


class LLMService:
    """Sequential page-by-page document analysis service."""

    def __init__(self):
        logger.info("[LLMService] Initializing...")
        self.client = get_llm_client()
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        logger.info("[LLMService] Initialized successfully")

    def analyze_document(
        self,
        pages: List[dict],
        document_filename: str = ""
    ) -> dict:
        if not self.client.is_configured():
            raise ValueError("Azure OpenAI client not configured. Check environment variables.")

        logger.info("=" * 70)
        logger.info(f"[LLMService] Starting SEQUENTIAL page-by-page analysis")
        logger.info(f"  Document: {document_filename}")
        logger.info(f"  Total pages: {len(pages)}")
        logger.info("=" * 70)

        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0

        all_chunks = []
        accumulated_context = ""
        document_summary_parts = []
        chunk_index = 0
        previous_chunk_summary = ""

        pillar_list = "\n".join([
            f"- {pillar.value}: {desc}"
            for pillar, desc in PILLAR_DESCRIPTIONS.items()
        ])

        for page_idx, page in enumerate(pages):
            page_num = page.get("page_number", page_idx + 1)

            logger.info(f"[LLMService] Processing page {page_num}/{len(pages)}")

            is_image_content = page.get("image_base64") is not None
            content_type_desc = "page image" if is_image_content else "text section"

            system_prompt = f"""You are a document analysis expert specializing in Business Due Diligence Evaluation (BDE).

                ## Document: {document_filename}
                ## Current Section: {page_num} of {len(pages)}

                ## Context from Previous Sections:
                {accumulated_context if accumulated_context else "This is the first section."}

                ## BDE Pillars for Classification:
                {pillar_list}

                ## Your Task:
                1. Analyze this {content_type_desc} in detail
                2. Extract all meaningful chunks of information
                3. Classify each chunk by its relevant BDE pillar
                4. Provide a brief summary of this section for context continuity

                ## Output Format:
                You MUST respond with ONLY a raw JSON object. Do NOT wrap it in markdown code blocks.

                Required JSON structure:
                {{
                "chunks": [
                    {{
                    "content": "Full extracted text or detailed description",
                    "summary": "1-2 sentence summary",
                    "pillar": "financial_health|gtm_engine|customer_health|product_technical|operational_maturity|leadership_transition|ecosystem_dependency|service_software_ratio|general",
                    "chunk_type": "text|table|chart|image|mixed",
                    "confidence_score": 0.95,
                    "metadata": {{
                        "section_title": "Section title if visible",
                        "has_numbers": true,
                        "has_dates": false,
                        "key_entities": ["Entity1", "Entity2"],
                        "data_type": "financial_statement|narrative|metrics|etc"
                    }}
                    }}
                ],
                "page_summary": "Brief 1-2 sentence summary of what this section contains",
                "page_type": "title|content|financial|chart|table|mixed"
                }}

                CRITICAL RULES:
                - Output ONLY the JSON object, nothing else
                - NO markdown, NO code blocks, NO backticks
                - Extract ALL relevant information from this {content_type_desc}
                - Preserve numerical data accurately (especially financial figures)
                - For tables, preserve complete structure and all values"""

            content = []
            if page.get("image_base64"):
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{page['image_base64']}",
                        "detail": "high"
                    }
                })
                content.append({
                    "type": "text",
                    "text": f"[This is Page {page_num}]"
                })
            elif page.get("text_content"):
                content.append({
                    "type": "text",
                    "text": f"[Section {page_num} Content]:\n{page['text_content']}"
                })

            try:
                response, usage_stats = self._call_with_retry(
                    system_prompt=system_prompt,
                    content=content,
                    max_tokens=16000,
                    temperature=0.1
                )

                self.total_prompt_tokens += usage_stats.get("prompt_tokens", 0)
                self.total_completion_tokens += usage_stats.get("completion_tokens", 0)

                result = self._parse_json_response(response)
                page_chunks = result.get("chunks", [])
                page_summary = result.get("page_summary", "")

                logger.info(f"  Extracted {len(page_chunks)} chunks from page {page_num}")

                for chunk in page_chunks:
                    chunk_summary = chunk.get("summary", "")
                    normalized_chunk = {
                        "content": chunk.get("content", ""),
                        "summary": chunk_summary,
                        "pillar": self._validate_pillar(chunk.get("pillar", "general")),
                        "chunk_type": self._validate_chunk_type(chunk.get("chunk_type", "text")),
                        "page_number": page_num,
                        "chunk_index": chunk_index,
                        "confidence_score": min(1.0, max(0.0, chunk.get("confidence_score", 0.8))),
                        "metadata": chunk.get("metadata", {}),
                        "previous_context": previous_chunk_summary if previous_chunk_summary else None,
                    }
                    all_chunks.append(normalized_chunk)
                    chunk_index += 1

                    if chunk_summary:
                        previous_chunk_summary = chunk_summary

                if page_summary:
                    document_summary_parts.append(f"Page {page_num}: {page_summary}")

                    if len(document_summary_parts) > 5:
                        accumulated_context = "Previous pages summary:\n" + "\n".join(document_summary_parts[-5:])
                    else:
                        accumulated_context = "Previous pages summary:\n" + "\n".join(document_summary_parts)

            except Exception as e:
                logger.error(f"  Page {page_num} processing failed: {e}")
                all_chunks.append({
                    "content": f"Failed to extract content from page {page_num}",
                    "summary": f"Extraction failed: {str(e)[:100]}",
                    "pillar": "general",
                    "chunk_type": "text",
                    "page_number": page_num,
                    "chunk_index": chunk_index,
                    "confidence_score": 0.1,
                    "metadata": {"error": str(e)},
                })
                chunk_index += 1

            if page_idx < len(pages) - 1:
                logger.info(f"  Waiting {INTER_PAGE_DELAY_SECONDS}s before next page...")
                time.sleep(INTER_PAGE_DELAY_SECONDS)

        document_overview = {
            "document_type": self._infer_document_type(document_summary_parts),
            "title": document_filename,
            "summary": " ".join(document_summary_parts[:3]) if document_summary_parts else "No summary available",
            "key_themes": self._extract_themes(all_chunks),
            "total_pages": len(pages),
            "total_chunks": len(all_chunks),
        }

        logger.info("=" * 70)
        logger.info(f"[LLMService] Document analysis complete")
        logger.info(f"  Total chunks extracted: {len(all_chunks)}")
        logger.info(f"  Total tokens: {self.total_prompt_tokens + self.total_completion_tokens:,}")
        logger.info("=" * 70)

        return {
            "chunks": all_chunks,
            "document_overview": document_overview,
            "usage_stats": {
                "prompt_tokens": self.total_prompt_tokens,
                "completion_tokens": self.total_completion_tokens,
                "total_tokens": self.total_prompt_tokens + self.total_completion_tokens
            }
        }

    def _infer_document_type(self, summaries: List[str]) -> str:
        combined = " ".join(summaries).lower()
        if "financial" in combined or "revenue" in combined:
            return "financial_statement"
        elif "slide" in combined or "presentation" in combined:
            return "presentation"
        elif "contract" in combined or "agreement" in combined:
            return "contract"
        elif "report" in combined:
            return "report"
        return "document"

    def _extract_themes(self, chunks: List[dict]) -> List[str]:
        pillar_counts = {}
        for chunk in chunks:
            pillar = chunk.get("pillar", "general")
            pillar_counts[pillar] = pillar_counts.get(pillar, 0) + 1
        sorted_pillars = sorted(pillar_counts.items(), key=lambda x: x[1], reverse=True)
        return [p[0] for p in sorted_pillars[:3] if p[0] != "general"]

    def _call_with_retry(
        self,
        system_prompt: str,
        content: List[dict],
        max_tokens: int = 8000,
        temperature: float = 0.1
    ) -> tuple:
        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"[LLMService] API call attempt {attempt}/{MAX_RETRIES}")

                has_images = any(item.get("type") == "image_url" for item in content)

                if has_images:
                    response, usage_stats = self.client.chat_completion_with_images(
                        system_prompt=system_prompt,
                        content=content,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )
                else:
                    text_content = "\n\n".join(
                        item.get("text", "") for item in content if item.get("type") == "text"
                    )
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text_content}
                    ]
                    response, usage_stats = self.client.chat_completion(
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )

                return response, usage_stats

            except Exception as e:
                last_error = e
                error_str = str(e)

                if "429" in error_str or "rate limit" in error_str.lower():
                    if attempt < MAX_RETRIES:
                        logger.warning(f"[LLMService] Rate limit hit, waiting {RETRY_DELAY_SECONDS}s...")
                        time.sleep(RETRY_DELAY_SECONDS)
                        continue
                raise

        raise last_error

    def _parse_json_response(self, content: str) -> dict:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        try:
            json_match = re.search(r'```(?:json)?\s*([\s\S]+?)\s*```', content)
            if json_match:
                return json.loads(json_match.group(1).strip())

            json_match = re.search(r'(\{[\s\S]*\})', content)
            if json_match:
                return json.loads(json_match.group(1).strip())

            return {"chunks": [], "page_summary": "Failed to parse response"}
        except json.JSONDecodeError:
            return {"chunks": [], "page_summary": "Failed to parse response"}

    def _validate_pillar(self, pillar: str) -> str:
        valid_pillars = [p.value for p in BDEPillar]
        pillar_lower = pillar.lower().replace(" ", "_").replace("-", "_")
        if pillar_lower in valid_pillars:
            return pillar_lower
        for valid in valid_pillars:
            if pillar_lower in valid or valid in pillar_lower:
                return valid
        return BDEPillar.GENERAL.value

    def _validate_chunk_type(self, chunk_type: str) -> str:
        valid_types = [t.value for t in ChunkType]
        type_lower = chunk_type.lower()
        if type_lower in valid_types:
            return type_lower
        return ChunkType.TEXT.value
