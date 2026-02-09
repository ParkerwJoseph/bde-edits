"""
Stage 2: Pillar Aggregation Service
Aggregates chunks + metrics per pillar, calculates data coverage.
"""
import json
from typing import List, Dict, Optional, Any
from sqlmodel import Session, select
from database.models.scoring import CompanyMetric, PillarDataCoverageConfig
from database.models.document import DocumentChunk
from database.models.connector import ConnectorChunk
from utils.logger import get_logger

logger = get_logger(__name__)


class PillarAggregationService:
    """
    Thin aggregation layer that:
    1. Fetches chunks for a pillar (filtered by confidence)
    2. Fetches current metrics for a pillar
    3. Calculates data coverage (deterministic)
    4. Returns clean data structure for next stages
    """

    def __init__(self):
        logger.info("[PillarAggregationService] Initialized")

    async def aggregate_pillar_data(
        self,
        db: Session,
        company_id: str,
        pillar: str
    ) -> Dict[str, Any]:
        """
        Aggregate all data for one pillar.

        Returns:
        {
            "chunks": [...],
            "metrics": {...},
            "coverage": {...},
            "metadata": {...}
        }
        """
        logger.info(f"[Stage 2] Aggregating data for pillar: {pillar}")

        # 1. Fetch chunks (with smart filtering)
        chunks = await self._get_filtered_chunks(db, company_id, pillar)

        # 2. Fetch current metrics
        metrics = await self._get_current_metrics(db, company_id, pillar)

        # 3. Calculate data coverage (deterministic)
        coverage = await self._calculate_coverage(db, pillar, metrics, chunks)

        # 4. Build metadata summary
        metadata = self._build_metadata(chunks, metrics)

        result = {
            "pillar": pillar,
            "company_id": company_id,
            "chunks": chunks,
            "metrics": metrics,
            "coverage": coverage,
            "metadata": metadata
        }

        # Log chunk source breakdown
        conn_count = metadata.get("connector_chunks", 0)
        doc_count = metadata.get("document_chunks", 0)
        logger.info(f"[Stage 2] Aggregated {len(chunks)} chunks ({conn_count} connector, {doc_count} document), {len(metrics)} metrics for {pillar}")
        return result

    async def _get_filtered_chunks(
        self,
        db: Session,
        company_id: str,
        pillar: str
    ) -> List:
        """Get chunks for pillar with smart filtering and prioritization.
        Returns both DocumentChunks and ConnectorChunks."""

        all_chunks = []

        # 1. Query document chunks for this pillar
        doc_statement = select(DocumentChunk).where(
            DocumentChunk.company_id == company_id,
            DocumentChunk.pillar == pillar
        ).order_by(
            DocumentChunk.confidence_score.desc(),
            DocumentChunk.page_number.asc()
        )
        doc_chunks = db.exec(doc_statement).all()

        # 2. Query connector chunks for this pillar
        conn_statement = select(ConnectorChunk).where(
            ConnectorChunk.company_id == company_id,
            ConnectorChunk.pillar == pillar
        ).order_by(
            ConnectorChunk.created_at.desc()
        )
        conn_chunks = db.exec(conn_statement).all()

        logger.info(f"[Stage 2] Found {len(doc_chunks)} document chunks, {len(conn_chunks)} connector chunks for {pillar}")

        # Filter document chunks by confidence threshold
        high_confidence_docs = [c for c in doc_chunks if c.confidence_score and c.confidence_score > 0.7]
        medium_confidence_docs = [c for c in doc_chunks if c.confidence_score and 0.4 <= c.confidence_score <= 0.7]

        # Connector chunks are authoritative - add them first (they're pre-computed)
        all_chunks.extend(conn_chunks)

        # Then add high confidence document chunks
        all_chunks.extend(high_confidence_docs)

        # Add medium confidence if we need more context
        if len(all_chunks) < 30:
            all_chunks.extend(medium_confidence_docs)

        logger.info(f"[Stage 2] Filtered {len(all_chunks)} total chunks ({len(conn_chunks)} connector, {len(all_chunks) - len(conn_chunks)} document)")

        return all_chunks

    async def _get_current_metrics(
        self,
        db: Session,
        company_id: str,
        pillar: str
    ) -> Dict[str, CompanyMetric]:
        """Get current metrics for this pillar (including multi-pillar metrics)"""

        # Query metrics where this pillar is primary or in pillars_used_by
        statement = select(CompanyMetric).where(
            CompanyMetric.company_id == company_id,
            CompanyMetric.is_current == True
        )

        all_metrics = db.exec(statement).all()

        # Filter to this pillar
        pillar_metrics = {}
        for metric in all_metrics:
            # Include if primary pillar OR in pillars_used_by
            if metric.primary_pillar == pillar:
                pillar_metrics[metric.metric_name] = metric
            elif metric.pillars_used_by and pillar in metric.pillars_used_by:
                pillar_metrics[metric.metric_name] = metric

        logger.info(f"[Stage 2] Found {len(pillar_metrics)} current metrics for {pillar}")

        return pillar_metrics

    async def _calculate_coverage(
        self,
        db: Session,
        pillar: str,
        metrics: Dict[str, CompanyMetric],
        chunks: List
    ) -> Dict[str, Any]:
        """
        Calculate data coverage percentage (deterministic).
        Uses checklist approach - NO LLM guessing.
        """

        # Get required data points from config
        statement = select(PillarDataCoverageConfig).where(
            PillarDataCoverageConfig.pillar == pillar
        ).order_by(
            PillarDataCoverageConfig.priority.desc()
        )

        required_points = db.exec(statement).all()

        # If no config exists, use metric definitions as checklist
        if not required_points:
            logger.info(f"[Stage 2] No coverage config for {pillar}, using default")
            required_points = self._get_default_required_points(pillar)

        present_points = []
        missing_points = []
        critical_missing = []

        for required in required_points:
            data_point_name = required.required_data_point if hasattr(required, 'required_data_point') else required

            # Check if metric exists
            if data_point_name in metrics:
                present_points.append(data_point_name)
            # OR check if mentioned in chunks
            elif self._data_point_in_chunks(data_point_name, chunks):
                present_points.append(data_point_name)
            else:
                missing_points.append(data_point_name)
                if hasattr(required, 'is_critical') and required.is_critical:
                    critical_missing.append(data_point_name)

        # Calculate percentage
        total_required = len(required_points) if required_points else 1
        coverage_percent = int((len(present_points) / total_required) * 100)

        coverage = {
            "percent": coverage_percent,
            "required_count": total_required,
            "present_count": len(present_points),
            "present_points": present_points,
            "missing_points": missing_points,
            "critical_missing": critical_missing
        }

        logger.info(f"[Stage 2] Coverage for {pillar}: {coverage_percent}% ({len(present_points)}/{total_required})")

        return coverage

    def _get_default_required_points(self, pillar: str) -> List[str]:
        """Get default required metrics if no config exists"""

        # Use the metric definitions from Stage 1
        from services.scoring.metric_extraction_service import MetricExtractionService

        metric_defs = MetricExtractionService.PILLAR_METRIC_DEFINITIONS.get(pillar, [])
        return [m["name"] for m in metric_defs]

    def _data_point_in_chunks(self, data_point: str, chunks: List) -> bool:
        """Check if a data point is mentioned in chunks"""

        # Common variations of data point names
        variations = [
            data_point,
            data_point.replace("Pct", "%"),
            data_point.replace("_", " "),
            data_point.replace("Monthly", ""),
        ]

        for chunk in chunks:
            chunk_text = (chunk.content + " " + (chunk.summary or "")).lower()

            for variation in variations:
                if variation.lower() in chunk_text:
                    return True

        return False

    def _build_metadata(
        self,
        chunks: List,
        metrics: Dict[str, CompanyMetric]
    ) -> Dict[str, Any]:
        """Build summary metadata about the aggregated data"""

        # Count chunks by type and source
        chunk_type_counts = {}
        connector_chunk_count = 0
        document_chunk_count = 0

        for chunk in chunks:
            chunk_type = chunk.chunk_type
            chunk_type_counts[chunk_type] = chunk_type_counts.get(chunk_type, 0) + 1

            # Check if it's a ConnectorChunk (has connector_type attribute)
            if hasattr(chunk, 'connector_type'):
                connector_chunk_count += 1
            else:
                document_chunk_count += 1

        # Count chunks by confidence level
        high_conf = sum(1 for c in chunks if c.confidence_score and c.confidence_score > 0.7)
        medium_conf = sum(1 for c in chunks if c.confidence_score and 0.4 <= c.confidence_score <= 0.7)
        low_conf = sum(1 for c in chunks if c.confidence_score and c.confidence_score < 0.4)

        # Count chunks with data
        chunks_with_numbers = 0
        for chunk in chunks:
            if chunk.metadata_json:
                # Handle both string (DocumentChunk) and dict (ConnectorChunk) formats
                if isinstance(chunk.metadata_json, str):
                    metadata = json.loads(chunk.metadata_json)
                else:
                    metadata = chunk.metadata_json
                if metadata.get("has_numbers"):
                    chunks_with_numbers += 1

        # Metric confidence stats
        metric_confidences = [m.confidence for m in metrics.values() if m.confidence]
        avg_metric_confidence = int(sum(metric_confidences) / len(metric_confidences)) if metric_confidences else 0

        return {
            "total_chunks": len(chunks),
            "connector_chunks": connector_chunk_count,
            "document_chunks": document_chunk_count,
            "chunk_type_counts": chunk_type_counts,
            "high_confidence_chunks": high_conf,
            "medium_confidence_chunks": medium_conf,
            "low_confidence_chunks": low_conf,
            "chunks_with_data": chunks_with_numbers,
            "total_metrics": len(metrics),
            "avg_metric_confidence": avg_metric_confidence
        }
