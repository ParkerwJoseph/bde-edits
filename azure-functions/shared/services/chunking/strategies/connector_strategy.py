"""
Connector chunking strategy - aggregation-based insight generation.

Key principle: Create insight chunks, NOT record chunks.
For 10,000 invoices, create ~15 meaningful insight chunks.
"""
import json
import re
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

from shared.services.chunking.strategies.base_strategy import BaseStrategy
from shared.services.chunking.models import (
    ChunkInput,
    ChunkOutput,
    NormalizedInput,
    SourceType,
    ProgressCallback,
    ENTITY_AGGREGATION_CONFIG,
    DEFAULT_AGGREGATION_CONFIG,
)
from shared.services.chunking.prompts import PromptManager
from shared.database.models.document import BDEPillar
from shared.utils.logger import get_logger

logger = get_logger(__name__)

# Rate limit management
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 65


class ConnectorChunkingStrategy(BaseStrategy):
    """
    Strategy for chunking connector data with aggregation.

    Instead of creating 1 chunk per record, this strategy:
    1. Processes grouped/aggregated data
    2. Creates insight chunks (summaries, trends, segments)
    3. Limits total chunks based on entity type config

    Result: 10,000 invoices -> ~15 insight chunks
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
        Execute aggregation-based chunking for connector data.

        Args:
            normalized_input: Normalized and grouped records
            original_input: Original input with entity info
            progress_callback: Optional callback for progress updates (not used for connectors)

        Returns:
            List of ChunkOutput objects (limited by entity config)
        """
        self._reset_usage_stats()

        content_units = normalized_input.content_units
        context = normalized_input.context
        source_info = normalized_input.source_info

        entity_type = context.get("entity_type", "unknown")
        config = context.get("aggregation_config", DEFAULT_AGGREGATION_CONFIG)
        max_chunks = config.get("max_chunks", 10)

        logger.info(f"[ConnectorStrategy] Processing {len(content_units)} groups for {entity_type}")
        logger.info(f"[ConnectorStrategy] Total records: {context.get('total_records', 0)}, max_chunks: {max_chunks}")

        all_chunks = []

        # Get base prompt for this entity type
        base_prompt = self.prompt_manager.get_prompt(
            source_type="connector",
            entity_type=entity_type,
            context=context
        )

        # Process each group (e.g., each month of invoices)
        for unit in content_units:
            group_key = unit.get("group_key", "unknown")
            records = unit.get("records", [])
            record_count = unit.get("record_count", len(records))
            pre_aggregated = unit.get("pre_aggregated", {})
            record_ids = unit.get("record_ids", [])

            logger.info(f"[ConnectorStrategy] Processing group '{group_key}' with {record_count} records")

            # Format prompt with group-specific data
            formatted_prompt = base_prompt.replace("{period_key}", str(group_key))
            formatted_prompt = formatted_prompt.replace("{record_count}", str(record_count))

            # Build user content with pre-aggregated data and samples
            user_content = self._build_user_content(
                entity_type=entity_type,
                group_key=group_key,
                records=records,
                pre_aggregated=pre_aggregated,
                record_count=record_count
            )

            try:
                # Call LLM
                response, usage_stats = self._call_with_retry(
                    system_prompt=formatted_prompt,
                    user_content=user_content,
                    max_tokens=4000,
                    temperature=0.2
                )

                self._update_usage_stats(usage_stats)

                # Parse response
                result = self._parse_json_response(response)
                group_chunks = result.get("chunks", [])

                logger.info(f"[ConnectorStrategy] Group '{group_key}': LLM returned {len(group_chunks)} chunks")

                # Convert to ChunkOutput objects
                for chunk_data in group_chunks:
                    chunk = ChunkOutput(
                        content=chunk_data.get("content", ""),
                        summary=chunk_data.get("summary", ""),
                        pillar=self._validate_pillar(chunk_data.get("pillar", "general")),
                        chunk_type=chunk_data.get("chunk_type", "aggregated_summary"),
                        confidence_score=chunk_data.get("confidence_score", 0.85),
                        metadata=self._build_metadata(chunk_data, pre_aggregated, group_key),
                        source_type=SourceType.CONNECTOR,
                        entity_type=entity_type,
                        entity_name=chunk_data.get("entity_name", f"{entity_type} - {group_key}"),
                        entity_ids=record_ids,  # Track source records
                        aggregation_type=chunk_data.get("aggregation_type", "summary"),
                        data_as_of=self._get_latest_date(records),
                        connector_type=context.get("connector_type"),
                    )
                    all_chunks.append(chunk)

            except Exception as e:
                logger.error(f"[ConnectorStrategy] Group '{group_key}' failed: {e}", exc_info=True)
                # Create fallback chunk
                all_chunks.append(ChunkOutput(
                    content=f"Failed to process {entity_type} data for period {group_key}. {record_count} records available.",
                    summary=f"Processing failed for {group_key}",
                    pillar="general",
                    chunk_type="aggregated_summary",
                    confidence_score=0.1,
                    metadata={"error": str(e), "record_count": record_count},
                    source_type=SourceType.CONNECTOR,
                    entity_type=entity_type,
                    entity_name=f"{entity_type} - {group_key} (error)",
                    entity_ids=record_ids,
                    aggregation_type="summary",
                    connector_type=context.get("connector_type"),
                ))

            # Small delay between groups to avoid rate limits
            time.sleep(1)

        # Ensure we don't exceed max chunks
        if len(all_chunks) > max_chunks:
            logger.info(f"[ConnectorStrategy] Consolidating {len(all_chunks)} chunks to max {max_chunks}")
            all_chunks = self._consolidate_chunks(all_chunks, max_chunks, entity_type)

        logger.info(f"[ConnectorStrategy] Complete: {len(all_chunks)} total chunks")
        return all_chunks

    def _build_user_content(
        self,
        entity_type: str,
        group_key: str,
        records: List[dict],
        pre_aggregated: Dict[str, Any],
        record_count: int
    ) -> str:
        """Build user content for LLM with pre-aggregated data and samples"""

        # Limit sample records to avoid token overflow
        sample_records = records[:5] if len(records) > 5 else records

        # Clean up sample records (remove very long fields)
        cleaned_samples = []
        for record in sample_records:
            cleaned = {}
            for key, value in record.items():
                if isinstance(value, str) and len(value) > 500:
                    cleaned[key] = value[:500] + "..."
                elif isinstance(value, (dict, list)):
                    # Simplify nested structures
                    cleaned[key] = json.dumps(value, default=str)[:300] + "..." if len(json.dumps(value, default=str)) > 300 else value
                else:
                    cleaned[key] = value
            cleaned_samples.append(cleaned)

        content = f"""Analyze this {entity_type} data for period: {group_key}

## Pre-Aggregated Summary (computed values - use these for accuracy):
{json.dumps(pre_aggregated, indent=2, default=str)}

## Record Count: {record_count}

## Sample Records (first {len(cleaned_samples)} of {record_count}):
{json.dumps(cleaned_samples, indent=2, default=str)}

Based on the pre-aggregated data and samples above, create 1-3 insight chunks that would be useful for business due diligence.

IMPORTANT:
- Use the pre-aggregated numbers for accuracy (they are calculated, not estimated)
- Create INSIGHT chunks, not raw data descriptions
- Focus on what matters for evaluating this business
- Each chunk should provide actionable intelligence"""

        return content

    def _call_with_retry(
        self,
        system_prompt: str,
        user_content: str,
        max_tokens: int = 4000,
        temperature: float = 0.2
    ) -> tuple:
        """Call LLM with retry logic"""
        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ]

                response, usage_stats = self.llm_client.chat_completion(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    response_format={"type": "json_object"}
                )

                return response, usage_stats

            except Exception as e:
                last_error = e
                error_str = str(e)

                if "429" in error_str or "RateLimitReached" in error_str or "rate limit" in error_str.lower():
                    if attempt < MAX_RETRIES:
                        logger.warning(f"[ConnectorStrategy] Rate limit hit, waiting {RETRY_DELAY_SECONDS}s")
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

            logger.error(f"[ConnectorStrategy] No valid JSON found in response")
            return {"chunks": []}

        except json.JSONDecodeError as e:
            logger.error(f"[ConnectorStrategy] JSON parse error: {e}")
            return {"chunks": []}

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

    def _build_metadata(
        self,
        chunk_data: Dict[str, Any],
        pre_aggregated: Dict[str, Any],
        group_key: str
    ) -> Dict[str, Any]:
        """Build metadata for chunk, merging LLM output with pre-aggregated data"""
        metadata = chunk_data.get("metadata", {})

        # Add period info
        metadata["period"] = group_key

        # Merge key pre-aggregated values
        if "total_amount" in pre_aggregated:
            metadata["total_amount"] = pre_aggregated["total_amount"]
        if "count" in pre_aggregated:
            metadata["record_count"] = pre_aggregated["count"]
        if "date_range" in pre_aggregated:
            metadata["date_range"] = pre_aggregated["date_range"]

        return metadata

    def _get_latest_date(self, records: List[dict]) -> Optional[datetime]:
        """Get the latest date from records"""
        dates = []
        for r in records:
            date_str = (
                r.get("TxnDate") or
                r.get("Date") or
                r.get("MetaData", {}).get("LastUpdatedTime")
            )
            if date_str:
                dt = self._parse_date(date_str)
                if dt:
                    dates.append(dt)

        return max(dates) if dates else None

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string"""
        if not date_str:
            return None

        formats = [
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S%z",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str[:26].replace("Z", ""), fmt.replace("%z", ""))
            except ValueError:
                continue

        return None

    def _consolidate_chunks(
        self,
        chunks: List[ChunkOutput],
        max_chunks: int,
        entity_type: str
    ) -> List[ChunkOutput]:
        """
        Consolidate chunks if we have too many.

        Strategy: Keep chunks with highest confidence scores and most important periods.
        """
        if len(chunks) <= max_chunks:
            return chunks

        # Sort by confidence score (descending)
        sorted_chunks = sorted(chunks, key=lambda c: c.confidence_score, reverse=True)

        # Keep top chunks
        return sorted_chunks[:max_chunks]
