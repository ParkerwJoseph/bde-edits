"""
API routes for BDE scoring system.
"""
import asyncio
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlmodel import Session, select, func
from typing import Optional
from pydantic import BaseModel

from database.connection import get_session, get_db_session
from database.models import User, Company
from database.models.document import Document, DocumentChunk, DocumentStatus
from database.models.connector import ConnectorChunk, ConnectorSyncLog, ConnectorConfig, SyncStatus
from database.models.scoring import (
    CompanyBDEScore,
    CompanyPillarScore,
    CompanyFlag,
    CompanyMetric,
    AcquisitionRecommendation,
    PillarEvaluationCriteria
)
from az_auth.dependencies import require_permission, get_current_user
from core.permissions import Permissions
from services.scoring.orchestration_service import ScoringOrchestrationService
from api.scoring.websocket_manager import scoring_ws_manager
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


def get_latest_scoring_run_id(session: Session, company_id: str) -> str | None:
    """Get the latest scoring_run_id for a company from the most recent BDE score."""
    statement = select(CompanyBDEScore.scoring_run_id).where(
        CompanyBDEScore.company_id == company_id
    ).order_by(CompanyBDEScore.calculated_at.desc()).limit(1)
    result = session.exec(statement).first()
    return result


# Request/Response Models
class ScoreCompanyRequest(BaseModel):
    recompute: bool = False


class ScoreCompanyResponse(BaseModel):
    status: str
    message: str
    company_id: str
    job_started: bool = True


class BDEScoreResponse(BaseModel):
    company_id: str
    overall_score: int
    weighted_raw_score: float
    valuation_range: str
    confidence: int
    calculated_at: str
    pillar_scores: dict


class PillarDetailResponse(BaseModel):
    pillar: str
    score: float
    health_status: str
    justification: str
    data_coverage_percent: int
    confidence: int
    key_findings: list
    risks: list
    data_gaps: list
    evidence_chunk_ids: list


class MetricsResponse(BaseModel):
    metrics: dict
    conflicts: list


class FlagsResponse(BaseModel):
    red_flags: list
    yellow_flags: list
    green_accelerants: list


class SourceDocumentInfo(BaseModel):
    id: str
    filename: str
    original_filename: str
    file_type: str
    document_type: Optional[str]
    document_title: Optional[str]
    status: str
    total_pages: Optional[int]
    updated_at: str
    metrics_count: int = 0
    chunks_count: int = 0
    confidence: int = 0  # Average confidence of metrics from this document


class DataSourcesResponse(BaseModel):
    documents: list[SourceDocumentInfo]
    total_metrics: int
    total_chunks: int


class MetricSourceInfo(BaseModel):
    """Generic source info - can be document or connector"""
    source_type: str  # "document" or "connector"
    source_id: str  # document_id or connector_chunk_id
    source_name: str  # filename or connector_type/entity_type
    # Document-specific
    page_numbers: Optional[list] = None
    # Connector-specific
    connector_type: Optional[str] = None
    entity_type: Optional[str] = None
    entity_name: Optional[str] = None


class MetricWithSource(BaseModel):
    metric_name: str
    current_value: dict
    pillars_used_by: Optional[list]
    primary_pillar: Optional[str]
    source_documents: list[dict]  # Legacy - kept for backwards compatibility
    sources: list[MetricSourceInfo]  # New unified source info


class MetricsWithSourcesResponse(BaseModel):
    metrics: dict
    conflicts: list
    source_documents: list[SourceDocumentInfo]


# ========================================
# SCORING ENDPOINTS
# ========================================

@router.post("/companies/{company_id}/score", response_model=ScoreCompanyResponse)
async def trigger_company_scoring(
    company_id: str,
    request: ScoreCompanyRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permission(Permissions.SCORING_WRITE)),
):
    """
    Trigger BDE scoring pipeline for a company.
    Runs asynchronously in background with real-time progress via WebSocket.
    """
    logger.info(f"[API] Scoring requested for company {company_id} by user {current_user.id}")

    # Verify company exists
    company = session.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Verify user has access to company (tenant check)
    if company.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Check if already running
    if company_id in scoring_ws_manager._company_tenants:
        raise HTTPException(
            status_code=409,
            detail="Scoring is already running for this company"
        )

    # Get current document count for tracking
    doc_count = session.exec(
        select(func.count(Document.id)).where(
            Document.company_id == company_id,
            Document.status == DocumentStatus.COMPLETED
        )
    ).one()

    # Check for connected connectors with completed syncs
    from database.models.connector import ConnectorStatus as ConnStatus
    connector_count = session.exec(
        select(func.count(ConnectorConfig.id)).where(
            ConnectorConfig.company_id == company_id,
            ConnectorConfig.connector_status == ConnStatus.CONNECTED
        )
    ).one()
    has_connector_data = False
    if connector_count > 0:
        completed_sync_count = session.exec(
            select(func.count(ConnectorSyncLog.id)).where(
                ConnectorSyncLog.company_id == company_id,
                ConnectorSyncLog.sync_status == SyncStatus.COMPLETED
            )
        ).one()
        has_connector_data = completed_sync_count > 0

    if doc_count == 0 and not has_connector_data:
        raise HTTPException(
            status_code=400,
            detail="No data available. Please upload documents or connect and sync integrations first."
        )

    # Register company for WebSocket progress tracking
    scoring_ws_manager.register_company(company_id, current_user.tenant_id, doc_count)

    # Store values needed for background task (session will close after response)
    tenant_id = current_user.tenant_id
    recompute = request.recompute

    # Start scoring in background using asyncio.create_task
    # This ensures proper async execution so WebSocket broadcasts work correctly
    async def run_scoring_task():
        """Run scoring pipeline with a fresh database session."""
        db = get_db_session()
        try:
            orchestration_service = ScoringOrchestrationService()
            await orchestration_service.score_company(
                db=db,
                company_id=company_id,
                tenant_id=tenant_id,
                recompute=recompute
            )
        except Exception as e:
            logger.error(f"[API] Scoring task failed: {e}", exc_info=True)
        finally:
            db.close()

    asyncio.create_task(run_scoring_task())

    return ScoreCompanyResponse(
        status="processing",
        message="Scoring pipeline started. This may take 5-10 minutes.",
        company_id=company_id,
        job_started=True
    )


@router.get("/companies/{company_id}/bde-score", response_model=BDEScoreResponse)
def get_company_bde_score(
    company_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permission(Permissions.SCORING_READ)),
):
    """
    Get the overall BDE score for a company.
    """
    logger.info(f"[API] BDE score requested for company {company_id}")

    # Verify company access
    company = session.get(Company, company_id)
    if not company or company.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Company not found")

    # Get latest scoring run ID
    scoring_run_id = get_latest_scoring_run_id(session, company_id)
    if not scoring_run_id:
        raise HTTPException(
            status_code=404,
            detail="No BDE score found. Run scoring first."
        )

    # Get BDE score for this run
    statement = select(CompanyBDEScore).where(
        CompanyBDEScore.company_id == company_id,
        CompanyBDEScore.scoring_run_id == scoring_run_id
    )
    bde_score = session.exec(statement).first()

    if not bde_score:
        raise HTTPException(
            status_code=404,
            detail="No BDE score found. Run scoring first."
        )

    # Get pillar scores for this run
    pillar_statement = select(CompanyPillarScore).where(
        CompanyPillarScore.company_id == company_id,
        CompanyPillarScore.scoring_run_id == scoring_run_id
    )
    pillar_scores = session.exec(pillar_statement).all()

    # Build dict from existing scores
    existing_scores = {
        score.pillar: {
            "score": score.score,
            "health_status": score.health_status.value,
            "confidence": score.confidence,
            "data_coverage": score.data_coverage_percent
        }
        for score in pillar_scores
    }

    # All 8 BDE pillars - ensure all are returned even if no data
    ALL_PILLARS = [
        "financial_health",
        "gtm_engine",
        "customer_health",
        "product_technical",
        "operational_maturity",
        "leadership_transition",
        "ecosystem_dependency",
        "service_software_ratio",
    ]

    # Return all 8 pillars with defaults for missing ones
    pillar_scores_dict = {}
    for pillar in ALL_PILLARS:
        if pillar in existing_scores:
            pillar_scores_dict[pillar] = existing_scores[pillar]
        else:
            # Default values for pillars with no data
            pillar_scores_dict[pillar] = {
                "score": 0,
                "health_status": "red",
                "confidence": 0,
                "data_coverage": 0
            }

    return BDEScoreResponse(
        company_id=company_id,
        overall_score=bde_score.overall_score,
        weighted_raw_score=bde_score.weighted_raw_score,
        valuation_range=bde_score.valuation_range,
        confidence=bde_score.confidence,
        calculated_at=bde_score.calculated_at.isoformat(),
        pillar_scores=pillar_scores_dict
    )


@router.get("/companies/{company_id}/pillars/{pillar}", response_model=PillarDetailResponse)
def get_pillar_details(
    company_id: str,
    pillar: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permission(Permissions.SCORING_READ)),
):
    """
    Get detailed scoring information for a specific pillar.
    """
    logger.info(f"[API] Pillar details requested: {company_id}/{pillar}")

    # Verify company access
    company = session.get(Company, company_id)
    if not company or company.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Company not found")

    # Get latest scoring run ID
    scoring_run_id = get_latest_scoring_run_id(session, company_id)
    if not scoring_run_id:
        raise HTTPException(status_code=404, detail=f"No score found for pillar {pillar}")

    # Get pillar score for this run
    statement = select(CompanyPillarScore).where(
        CompanyPillarScore.company_id == company_id,
        CompanyPillarScore.pillar == pillar,
        CompanyPillarScore.scoring_run_id == scoring_run_id
    )
    pillar_score = session.exec(statement).first()

    if not pillar_score:
        raise HTTPException(status_code=404, detail=f"No score found for pillar {pillar}")

    # Get evaluation details
    evaluation = session.get(PillarEvaluationCriteria, pillar_score.evaluation_id)

    return PillarDetailResponse(
        pillar=pillar,
        score=pillar_score.score,
        health_status=pillar_score.health_status.value,
        justification=pillar_score.justification or "",
        data_coverage_percent=pillar_score.data_coverage_percent or 0,
        confidence=pillar_score.confidence or 0,
        key_findings=evaluation.key_findings if evaluation else [],
        risks=evaluation.risks if evaluation else [],
        data_gaps=evaluation.data_gaps if evaluation else [],
        evidence_chunk_ids=evaluation.evidence_chunk_ids if evaluation else []
    )


@router.get("/companies/{company_id}/metrics", response_model=MetricsResponse)
def get_company_metrics(
    company_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permission(Permissions.SCORING_READ)),
):
    """
    Get all extracted metrics for a company.
    """
    logger.info(f"[API] Metrics requested for company {company_id}")

    # Verify company access
    company = session.get(Company, company_id)
    if not company or company.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Company not found")

    # Get latest scoring run ID
    scoring_run_id = get_latest_scoring_run_id(session, company_id)
    logger.info(f"[API] Latest scoring_run_id for company {company_id}: {scoring_run_id}")

    # Get ALL current metrics for this company
    # This includes metrics from the latest scoring run AND any other current metrics
    # that might not have been re-extracted (like JSON list metrics)
    statement = select(CompanyMetric).where(
        CompanyMetric.company_id == company_id,
        CompanyMetric.is_current == True
    )
    all_current_metrics = session.exec(statement).all()

    # Build a dict to deduplicate by metric_name, preferring latest scoring run
    metrics_by_name = {}
    for metric in all_current_metrics:
        name = metric.metric_name
        if name not in metrics_by_name:
            metrics_by_name[name] = metric
        elif scoring_run_id and metric.scoring_run_id == scoring_run_id:
            # Prefer metric from latest scoring run
            metrics_by_name[name] = metric

    metrics = list(metrics_by_name.values())

    # Log metric names for debugging
    metric_names = [m.metric_name for m in metrics]
    logger.info(f"[API] Found {len(metrics)} metrics: {metric_names}")

    # Get metrics flagged for review (conflicts) in this run
    if scoring_run_id:
        conflict_statement = select(CompanyMetric).where(
            CompanyMetric.company_id == company_id,
            CompanyMetric.scoring_run_id == scoring_run_id,
            CompanyMetric.needs_analyst_review == True
        )
    else:
        conflict_statement = select(CompanyMetric).where(
            CompanyMetric.company_id == company_id,
            CompanyMetric.needs_analyst_review == True
        )
    conflicted_metrics = session.exec(conflict_statement).all()

    # Format response
    metrics_dict = {}
    for metric in metrics:
        # Parse JSON value - handle various serialization states (including triple-serialized)
        json_value = metric.metric_value_json
        if json_value is not None:
            import json as json_module

            # Keep parsing while it's a string (handles multiple levels of serialization)
            max_iterations = 5  # Safety limit to prevent infinite loops
            iteration = 0
            while isinstance(json_value, str) and iteration < max_iterations:
                iteration += 1
                try:
                    json_value = json_module.loads(json_value)
                except (json_module.JSONDecodeError, TypeError) as e:
                    logger.warning(f"[API] Failed to parse JSON for metric {metric.metric_name} at iteration {iteration}: {e}")
                    json_value = None
                    break

            # Log if we had to parse multiple times (indicates storage issue)
            if iteration > 1:
                logger.info(f"[API] Metric {metric.metric_name} required {iteration} JSON parse iterations")

            # Ensure we have a proper list/dict, not some other type
            if json_value is not None and not isinstance(json_value, (list, dict)):
                logger.warning(f"[API] Unexpected JSON type for metric {metric.metric_name}: {type(json_value)}")
                json_value = None

        metrics_dict[metric.metric_name] = {
            "current_value": {
                "numeric": metric.metric_value_numeric,
                "text": metric.metric_value_text,
                "json": json_value,
                "unit": metric.metric_unit,
                "period": metric.metric_period,
                "as_of_date": metric.metric_as_of_date.isoformat() if metric.metric_as_of_date else None,
                "confidence": metric.confidence,
                "is_current": metric.is_current
            },
            "pillars_used_by": metric.pillars_used_by,
            "primary_pillar": metric.primary_pillar
        }

    conflicts_list = [
        {
            "metric_name": m.metric_name,
            "value": m.metric_value_text,
            "period": m.metric_period,
            "confidence": m.confidence
        }
        for m in conflicted_metrics
    ]

    return MetricsResponse(
        metrics=metrics_dict,
        conflicts=conflicts_list
    )


@router.get("/companies/{company_id}/flags", response_model=FlagsResponse)
def get_company_flags(
    company_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permission(Permissions.SCORING_READ)),
):
    """
    Get all detected flags for a company.
    """
    logger.info(f"[API] Flags requested for company {company_id}")

    # Verify company access
    company = session.get(Company, company_id)
    if not company or company.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Company not found")

    # Get latest scoring run ID
    scoring_run_id = get_latest_scoring_run_id(session, company_id)

    # Get flags for this run
    if scoring_run_id:
        statement = select(CompanyFlag).where(
            CompanyFlag.company_id == company_id,
            CompanyFlag.scoring_run_id == scoring_run_id,
            CompanyFlag.is_active == True
        ).order_by(CompanyFlag.severity.desc())
    else:
        statement = select(CompanyFlag).where(
            CompanyFlag.company_id == company_id,
            CompanyFlag.is_active == True
        ).order_by(CompanyFlag.severity.desc())

    flags = session.exec(statement).all()

    # Group by type
    red_flags = [
        {
            "text": f.flag_text,
            "category": f.flag_category,
            "pillar": f.pillar,
            "severity": f.severity,
            "source": f.flag_source.value,
            "rationale": f.rationale
        }
        for f in flags if f.flag_type.value == "red"
    ]

    yellow_flags = [
        {
            "text": f.flag_text,
            "category": f.flag_category,
            "pillar": f.pillar,
            "severity": f.severity,
            "source": f.flag_source.value,
            "rationale": f.rationale
        }
        for f in flags if f.flag_type.value == "yellow"
    ]

    green_accelerants = [
        {
            "text": f.flag_text,
            "category": f.flag_category,
            "pillar": f.pillar,
            "source": f.flag_source.value,
            "rationale": f.rationale
        }
        for f in flags if f.flag_type.value == "green"
    ]

    return FlagsResponse(
        red_flags=red_flags,
        yellow_flags=yellow_flags,
        green_accelerants=green_accelerants
    )


@router.get("/companies/{company_id}/recommendation")
def get_acquisition_recommendation(
    company_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permission(Permissions.SCORING_READ)),
):
    """
    Get the acquisition recommendation for a company.
    """
    logger.info(f"[API] Recommendation requested for company {company_id}")

    # Verify company access
    company = session.get(Company, company_id)
    if not company or company.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Company not found")

    # Get latest scoring run ID
    scoring_run_id = get_latest_scoring_run_id(session, company_id)
    if not scoring_run_id:
        raise HTTPException(
            status_code=404,
            detail="No recommendation found. Run scoring first."
        )

    # Get recommendation for this run
    statement = select(AcquisitionRecommendation).where(
        AcquisitionRecommendation.company_id == company_id,
        AcquisitionRecommendation.scoring_run_id == scoring_run_id
    )
    recommendation = session.exec(statement).first()

    if not recommendation:
        raise HTTPException(
            status_code=404,
            detail="No recommendation found. Run scoring first."
        )

    return {
        "recommendation": recommendation.recommendation,
        "confidence": recommendation.recommendation_confidence,
        "rationale": recommendation.rationale,
        "value_drivers": recommendation.value_drivers,
        "key_risks": recommendation.key_risks,
        "100_day_plan": recommendation.day_100_plan,
        "suggested_valuation_multiple": recommendation.suggested_valuation_multiple,
        "valuation_adjustments": recommendation.valuation_adjustments,
        "generated_at": recommendation.generated_at.isoformat()
    }


@router.get("/companies/{company_id}/data-sources", response_model=DataSourcesResponse)
def get_company_data_sources(
    company_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permission(Permissions.SCORING_READ)),
):
    """
    Get all source documents used for scoring a company.
    Returns documents with their contribution to metrics and chunks.
    """
    logger.info(f"[API] Data sources requested for company {company_id}")

    # Verify company access
    company = session.get(Company, company_id)
    if not company or company.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Company not found")

    # Get all documents for this company
    doc_statement = select(Document).where(
        Document.company_id == company_id
    ).order_by(Document.updated_at.desc())
    documents = session.exec(doc_statement).all()

    # Get all chunks for this company (to map back to documents)
    chunk_statement = select(DocumentChunk).where(
        DocumentChunk.company_id == company_id
    )
    chunks = session.exec(chunk_statement).all()

    # Get latest scoring run ID
    scoring_run_id = get_latest_scoring_run_id(session, company_id)

    # Get all metrics with their source chunk IDs for this run
    if scoring_run_id:
        metric_statement = select(CompanyMetric).where(
            CompanyMetric.company_id == company_id,
            CompanyMetric.scoring_run_id == scoring_run_id
        )
    else:
        metric_statement = select(CompanyMetric).where(
            CompanyMetric.company_id == company_id,
            CompanyMetric.is_current == True
        )
    metrics = session.exec(metric_statement).all()

    # Build document -> chunks mapping
    doc_chunks_map = {}
    for chunk in chunks:
        if chunk.document_id not in doc_chunks_map:
            doc_chunks_map[chunk.document_id] = []
        doc_chunks_map[chunk.document_id].append(chunk.id)

    # Build chunk -> document mapping
    chunk_to_doc = {chunk.id: chunk.document_id for chunk in chunks}

    # Count metrics per document and calculate confidence
    doc_metrics_count = {}
    doc_confidence_sum = {}
    for metric in metrics:
        if metric.source_chunk_ids:
            for chunk_id in metric.source_chunk_ids:
                doc_id = chunk_to_doc.get(chunk_id)
                if doc_id:
                    doc_metrics_count[doc_id] = doc_metrics_count.get(doc_id, 0) + 1
                    # Add confidence for averaging
                    if doc_id not in doc_confidence_sum:
                        doc_confidence_sum[doc_id] = []
                    doc_confidence_sum[doc_id].append(metric.confidence or 0)

    # Build response
    doc_infos = []
    for doc in documents:
        metrics_count = doc_metrics_count.get(doc.id, 0)
        # Calculate average confidence
        avg_confidence = 0
        if doc.id in doc_confidence_sum and doc_confidence_sum[doc.id]:
            avg_confidence = round(sum(doc_confidence_sum[doc.id]) / len(doc_confidence_sum[doc.id]))

        doc_infos.append(SourceDocumentInfo(
            id=doc.id,
            filename=doc.filename,
            original_filename=doc.original_filename,
            file_type=doc.file_type.value,
            document_type=doc.document_type,
            document_title=doc.document_title,
            status=doc.status.value,
            total_pages=doc.total_pages,
            updated_at=doc.updated_at.isoformat(),
            metrics_count=metrics_count,
            chunks_count=len(doc_chunks_map.get(doc.id, [])),
            confidence=avg_confidence
        ))

    return DataSourcesResponse(
        documents=doc_infos,
        total_metrics=len(metrics),
        total_chunks=len(chunks)
    )


@router.get("/companies/{company_id}/metrics-with-sources", response_model=MetricsWithSourcesResponse)
def get_company_metrics_with_sources(
    company_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permission(Permissions.SCORING_READ)),
):
    """
    Get all extracted metrics with their source document information.
    Provides full data lineage for each metric.
    """
    logger.info(f"[API] Metrics with sources requested for company {company_id}")

    # Verify company access
    company = session.get(Company, company_id)
    if not company or company.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Company not found")

    # Get latest scoring run ID
    scoring_run_id = get_latest_scoring_run_id(session, company_id)

    # Get metrics for this run
    if scoring_run_id:
        metric_statement = select(CompanyMetric).where(
            CompanyMetric.company_id == company_id,
            CompanyMetric.scoring_run_id == scoring_run_id
        )
    else:
        metric_statement = select(CompanyMetric).where(
            CompanyMetric.company_id == company_id,
            CompanyMetric.is_current == True
        )
    metrics = session.exec(metric_statement).all()

    # Get conflicts for this run
    if scoring_run_id:
        conflict_statement = select(CompanyMetric).where(
            CompanyMetric.company_id == company_id,
            CompanyMetric.scoring_run_id == scoring_run_id,
            CompanyMetric.needs_analyst_review == True
        )
    else:
        conflict_statement = select(CompanyMetric).where(
            CompanyMetric.company_id == company_id,
            CompanyMetric.needs_analyst_review == True
        )
    conflicted_metrics = session.exec(conflict_statement).all()

    # Get all document chunks to build lineage
    doc_chunk_statement = select(DocumentChunk).where(
        DocumentChunk.company_id == company_id
    )
    doc_chunks = session.exec(doc_chunk_statement).all()
    doc_chunk_map = {chunk.id: chunk for chunk in doc_chunks}

    # Get all connector chunks to build lineage
    conn_chunk_statement = select(ConnectorChunk).where(
        ConnectorChunk.company_id == company_id
    )
    conn_chunks = session.exec(conn_chunk_statement).all()
    conn_chunk_map = {chunk.id: chunk for chunk in conn_chunks}

    # Get all documents
    doc_statement = select(Document).where(
        Document.company_id == company_id
    )
    documents = session.exec(doc_statement).all()
    doc_map = {doc.id: doc for doc in documents}

    # Track which documents are used
    used_doc_ids = set()

    # Format metrics with source info
    metrics_dict = {}
    for metric in metrics:
        source_docs = []  # Legacy format for backwards compatibility
        sources = []  # New unified format

        if metric.source_chunk_ids:
            # Group document chunks by document
            doc_pages = {}
            for chunk_id in metric.source_chunk_ids:
                # Check if it's a document chunk
                doc_chunk = doc_chunk_map.get(chunk_id)
                if doc_chunk:
                    doc_id = doc_chunk.document_id
                    used_doc_ids.add(doc_id)
                    if doc_id not in doc_pages:
                        doc_pages[doc_id] = {
                            "document_id": doc_id,
                            "filename": doc_map.get(doc_id).original_filename if doc_map.get(doc_id) else "Unknown",
                            "page_numbers": []
                        }
                    if doc_chunk.page_number not in doc_pages[doc_id]["page_numbers"]:
                        doc_pages[doc_id]["page_numbers"].append(doc_chunk.page_number)

                    # Add to unified sources
                    sources.append({
                        "source_type": "document",
                        "source_id": doc_id,
                        "source_name": doc_map.get(doc_id).original_filename if doc_map.get(doc_id) else "Unknown",
                        "page_numbers": [doc_chunk.page_number] if doc_chunk.page_number else [],
                        "connector_type": None,
                        "entity_type": None,
                        "entity_name": None
                    })
                    continue

                # Check if it's a connector chunk
                conn_chunk = conn_chunk_map.get(chunk_id)
                if conn_chunk:
                    connector_type = conn_chunk.connector_type.value if conn_chunk.connector_type else "connector"
                    entity_type = conn_chunk.entity_type or "data"
                    entity_name = conn_chunk.entity_name

                    sources.append({
                        "source_type": "connector",
                        "source_id": chunk_id,
                        "source_name": f"{connector_type.upper()}/{entity_type}",
                        "page_numbers": None,
                        "connector_type": connector_type,
                        "entity_type": entity_type,
                        "entity_name": entity_name
                    })

            source_docs = list(doc_pages.values())
            # Sort page numbers
            for sd in source_docs:
                sd["page_numbers"].sort()

        # Deduplicate sources by source_id
        seen_sources = set()
        unique_sources = []
        for src in sources:
            if src["source_id"] not in seen_sources:
                seen_sources.add(src["source_id"])
                unique_sources.append(src)

        # Parse JSON value if it's a string (may be double-serialized)
        json_value = metric.metric_value_json
        if isinstance(json_value, str):
            try:
                json_value = json.loads(json_value)
                # Handle double-serialized JSON (string containing JSON string)
                if isinstance(json_value, str):
                    json_value = json.loads(json_value)
            except:
                pass

        metrics_dict[metric.metric_name] = {
            "current_value": {
                "numeric": metric.metric_value_numeric,
                "text": metric.metric_value_text,
                "json": json_value,
                "unit": metric.metric_unit,
                "period": metric.metric_period,
                "as_of_date": metric.metric_as_of_date.isoformat() if metric.metric_as_of_date else None,
                "confidence": metric.confidence,
                "is_current": metric.is_current
            },
            "pillars_used_by": metric.pillars_used_by,
            "primary_pillar": metric.primary_pillar,
            "source_documents": source_docs,  # Legacy
            "sources": unique_sources  # New unified format
        }

    conflicts_list = [
        {
            "metric_name": m.metric_name,
            "value": m.metric_value_text,
            "period": m.metric_period,
            "confidence": m.confidence
        }
        for m in conflicted_metrics
    ]

    # Build source documents info (only for used documents)
    source_doc_infos = []
    for doc_id in used_doc_ids:
        doc = doc_map.get(doc_id)
        if doc:
            source_doc_infos.append(SourceDocumentInfo(
                id=doc.id,
                filename=doc.filename,
                original_filename=doc.original_filename,
                file_type=doc.file_type.value,
                document_type=doc.document_type,
                document_title=doc.document_title,
                status=doc.status.value,
                total_pages=doc.total_pages,
                updated_at=doc.updated_at.isoformat(),
                metrics_count=0,
                chunks_count=0
            ))

    return MetricsWithSourcesResponse(
        metrics=metrics_dict,
        conflicts=conflicts_list,
        source_documents=source_doc_infos
    )


# ========================================
# DOCUMENT COUNT & ANALYSIS STATUS
# ========================================

class DocumentCountResponse(BaseModel):
    company_id: str
    total_documents: int
    processed_documents: int
    last_scored_at: Optional[str] = None
    last_scored_doc_count: int = 0
    has_new_documents: bool = False


class AnalysisStatusResponse(BaseModel):
    company_id: str
    has_score: bool
    is_running: bool
    last_scored_at: Optional[str] = None
    document_count: int
    last_scored_doc_count: int
    has_new_documents: bool
    has_new_connector_data: bool = False  # New connector data synced since last scoring
    connector_count: int = 0  # Number of active connectors
    can_run_analysis: bool
    message: str


@router.get("/companies/{company_id}/document-count", response_model=DocumentCountResponse)
def get_company_document_count(
    company_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permission(Permissions.SCORING_READ)),
):
    """
    Get document count for a company to check if rerun is needed.
    Compares current document count with last scored document count.
    """
    logger.info(f"[API] Document count requested for company {company_id}")

    # Verify company access
    company = session.get(Company, company_id)
    if not company or company.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Company not found")

    # Get total documents
    total_docs = session.exec(
        select(func.count(Document.id)).where(
            Document.company_id == company_id
        )
    ).one()

    # Get processed documents
    processed_docs = session.exec(
        select(func.count(Document.id)).where(
            Document.company_id == company_id,
            Document.status == DocumentStatus.COMPLETED
        )
    ).one()

    # Get latest BDE score (by calculated_at - supports scoring_run_id)
    bde_score = session.exec(
        select(CompanyBDEScore).where(
            CompanyBDEScore.company_id == company_id
        ).order_by(CompanyBDEScore.calculated_at.desc())
    ).first()

    last_scored_at = bde_score.calculated_at.isoformat() if bde_score else None
    last_scored_datetime = bde_score.calculated_at if bde_score else None

    # Get document count from database (persisted in BDE score)
    last_scored_doc_count = bde_score.scored_doc_count if bde_score else 0

    # Detect document changes by count difference OR new documents created after last scoring
    has_new_documents = processed_docs != last_scored_doc_count
    if not has_new_documents and last_scored_datetime and processed_docs > 0:
        # Count differs catches additions/deletions, but same count could mean
        # a doc was deleted and a new one uploaded — check timestamps
        docs_after_scoring = session.exec(
            select(func.count(Document.id)).where(
                Document.company_id == company_id,
                Document.status == DocumentStatus.COMPLETED,
                Document.created_at > last_scored_datetime
            )
        ).one()
        has_new_documents = docs_after_scoring > 0

    return DocumentCountResponse(
        company_id=company_id,
        total_documents=total_docs,
        processed_documents=processed_docs,
        last_scored_at=last_scored_at,
        last_scored_doc_count=last_scored_doc_count,
        has_new_documents=has_new_documents
    )


@router.get("/companies/{company_id}/analysis-status", response_model=AnalysisStatusResponse)
def get_analysis_status(
    company_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permission(Permissions.SCORING_READ)),
):
    """
    Get analysis status for a company - whether it can run, has new documents or connector data.
    """
    logger.info(f"[API] Analysis status requested for company {company_id}")

    # Verify company access
    company = session.get(Company, company_id)
    if not company or company.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Company not found")

    # Get processed documents count
    processed_docs = session.exec(
        select(func.count(Document.id)).where(
            Document.company_id == company_id,
            Document.status == DocumentStatus.COMPLETED
        )
    ).one()

    # Get latest BDE score (by calculated_at, not is_current - supports scoring_run_id)
    bde_score = session.exec(
        select(CompanyBDEScore).where(
            CompanyBDEScore.company_id == company_id
        ).order_by(CompanyBDEScore.calculated_at.desc())
    ).first()

    has_score = bde_score is not None
    last_scored_at = bde_score.calculated_at.isoformat() if bde_score else None
    last_scored_datetime = bde_score.calculated_at if bde_score else None

    # Check if scoring is currently running (company registered in ws_manager)
    is_running = company_id in scoring_ws_manager._company_tenants

    # Get document count from database (persisted in BDE score)
    last_scored_doc_count = bde_score.scored_doc_count if bde_score else 0

    # Detect document changes by count difference OR new documents created after last scoring
    # This handles: new uploads, deletions, and delete+re-upload (same count but different docs)
    has_new_documents = processed_docs != last_scored_doc_count
    if not has_new_documents and last_scored_datetime and processed_docs > 0:
        docs_after_scoring = session.exec(
            select(func.count(Document.id)).where(
                Document.company_id == company_id,
                Document.status == DocumentStatus.COMPLETED,
                Document.created_at > last_scored_datetime
            )
        ).one()
        has_new_documents = docs_after_scoring > 0

    # Check for new connector data since last scoring
    has_new_connector_data = False
    connector_count = 0

    # Count connected connectors for this company
    from database.models.connector import ConnectorStatus as ConnStatus
    connector_count = session.exec(
        select(func.count(ConnectorConfig.id)).where(
            ConnectorConfig.company_id == company_id,
            ConnectorConfig.connector_status == ConnStatus.CONNECTED
        )
    ).one()

    # Check if any connector sync completed after last scoring
    if last_scored_datetime and connector_count > 0:
        new_sync_count = session.exec(
            select(func.count(ConnectorSyncLog.id)).where(
                ConnectorSyncLog.company_id == company_id,
                ConnectorSyncLog.sync_status == SyncStatus.COMPLETED,
                ConnectorSyncLog.completed_at > last_scored_datetime
            )
        ).one()
        has_new_connector_data = new_sync_count > 0
    elif connector_count > 0 and not has_score:
        # No score yet but connectors exist - check if any sync completed
        completed_sync_count = session.exec(
            select(func.count(ConnectorSyncLog.id)).where(
                ConnectorSyncLog.company_id == company_id,
                ConnectorSyncLog.sync_status == SyncStatus.COMPLETED
            )
        ).one()
        has_new_connector_data = completed_sync_count > 0

    # Determine if analysis can run
    can_run_analysis = False
    message = ""

    has_data = processed_docs > 0 or (connector_count > 0 and has_new_connector_data)

    if not has_data and processed_docs == 0 and connector_count == 0:
        message = "No data available. Upload documents or connect integrations to run analysis."
    elif is_running:
        message = "Analysis is currently running..."
    elif not has_score:
        if has_data:
            can_run_analysis = True
            message = "Ready to run initial analysis. This may take 5-10 minutes."
        else:
            message = "No data available. Upload documents or sync connectors first."
    elif has_new_documents and has_new_connector_data:
        can_run_analysis = True
        message = "Document changes and new connector data available. Click to re-run."
    elif has_new_documents:
        can_run_analysis = True
        message = "Document changes detected. Click to re-run analysis."
    elif has_new_connector_data:
        can_run_analysis = True
        message = "New connector data available. Click to re-run analysis."
    else:
        message = "Analysis is up to date."

    return AnalysisStatusResponse(
        company_id=company_id,
        has_score=has_score,
        is_running=is_running,
        last_scored_at=last_scored_at,
        document_count=processed_docs,
        last_scored_doc_count=last_scored_doc_count,
        has_new_documents=has_new_documents,
        has_new_connector_data=has_new_connector_data,
        connector_count=connector_count,
        can_run_analysis=can_run_analysis,
        message=message
    )


# ========================================
# WEBSOCKET ENDPOINT FOR SCORING PROGRESS
# ========================================

@router.websocket("/ws")
async def scoring_websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time scoring pipeline progress.
    Client sends tenant_id after connection to subscribe to updates.
    """
    tenant_id = None
    try:
        await websocket.accept()
        data = await websocket.receive_json()
        tenant_id = data.get("tenant_id")

        if not tenant_id:
            await websocket.close(code=4001, reason="tenant_id required")
            return

        # Register connection
        async with scoring_ws_manager._lock:
            if tenant_id not in scoring_ws_manager._connections:
                scoring_ws_manager._connections[tenant_id] = set()
            scoring_ws_manager._connections[tenant_id].add(websocket)
        logger.info(f"[ScoringWS] Connection established for tenant: {tenant_id}")

        # Keep connection alive with ping/pong
        while True:
            try:
                message = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=30.0
                )
                if message.get("type") == "pong":
                    continue
            except asyncio.TimeoutError:
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
    except WebSocketDisconnect:
        logger.info(f"[ScoringWS] Client disconnected: {tenant_id}")
    except Exception as e:
        logger.error(f"[ScoringWS] Error: {e}")
    finally:
        if tenant_id:
            await scoring_ws_manager.disconnect(websocket, tenant_id)
