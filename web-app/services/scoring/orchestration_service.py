"""
Scoring Orchestration Service
Coordinates all 5 stages of BDE scoring pipeline.
Broadcasts real-time progress via WebSocket.
"""
import asyncio
import uuid
from typing import Dict, Any
from sqlmodel import Session, select, func
from database.models.document import BDEPillar, Document, DocumentStatus
from database.models.scoring import CompanyPillarScore, CompanyFlag
from services.scoring.metric_extraction_service import MetricExtractionService
from services.scoring.pillar_aggregation_service import PillarAggregationService
from services.scoring.scoring_services import (
    PillarEvaluationService,
    ScoringEngineService,
    FlagDetectionService,
    BDECalculatorService
)
from api.scoring.websocket_manager import scoring_ws_manager, PILLAR_NAMES, BDE_PILLARS
from utils.logger import get_logger

logger = get_logger(__name__)


class ScoringOrchestrationService:
    """
    Orchestrates the full BDE scoring pipeline.

    Pipeline:
    Stage 1: Metric Extraction
    Stage 2: Pillar Aggregation (per pillar)
    Stage 3A: Pillar Evaluation (LLM, per pillar)
    Stage 3B: Pillar Scoring (Code, per pillar)
    Stage 4: Flag Detection (LLM)
    Stage 5: BDE Score + Recommendation (Math + LLM)
    """

    def __init__(self):
        self.metric_service = MetricExtractionService()
        self.aggregation_service = PillarAggregationService()
        self.evaluation_service = PillarEvaluationService()
        self.scoring_service = ScoringEngineService()
        self.flag_service = FlagDetectionService()
        self.bde_calculator = BDECalculatorService()
        logger.info("[ScoringOrchestrationService] Initialized")

    def _get_pillar_progress(self, completed_pillars: Dict[str, CompanyPillarScore], current_pillar: str = None, current_status: str = "pending") -> Dict[str, dict]:
        """Build pillar progress dict for WebSocket updates."""
        pillar_progress = {}
        for pillar in BDE_PILLARS:
            if pillar in completed_pillars:
                score_obj = completed_pillars[pillar]
                pillar_progress[pillar] = {
                    "name": PILLAR_NAMES[pillar],
                    "status": "completed",
                    "progress": 100,
                    "score": score_obj.score,
                    "health_status": score_obj.health_status.value,
                }
            elif pillar == current_pillar:
                pillar_progress[pillar] = {
                    "name": PILLAR_NAMES[pillar],
                    "status": current_status,
                    "progress": 50 if current_status == "processing" else 0,
                    "score": None,
                    "health_status": None,
                }
            else:
                pillar_progress[pillar] = {
                    "name": PILLAR_NAMES[pillar],
                    "status": "pending",
                    "progress": 0,
                    "score": None,
                    "health_status": None,
                }
        return pillar_progress

    async def _broadcast(self, company_id: str, stage: int, stage_name: str, progress: int,
                         status: str = "processing", current_pillar: str = None,
                         pillar_progress: dict = None, error_message: str = None, result: dict = None):
        """Helper to broadcast progress and handle any async issues."""
        try:
            await scoring_ws_manager.broadcast_progress(
                company_id=company_id,
                stage=stage,
                stage_name=stage_name,
                progress=progress,
                status=status,
                current_pillar=current_pillar,
                pillar_progress=pillar_progress,
                error_message=error_message,
                result=result
            )
        except Exception as e:
            logger.warning(f"[PIPELINE] Failed to broadcast progress: {e}")

    async def score_company(
        self,
        db: Session,
        company_id: str,
        tenant_id: str,
        recompute: bool = False
    ) -> Dict[str, Any]:
        """
        Run full scoring pipeline for a company.
        Broadcasts real-time progress via WebSocket.

        Args:
            db: Database session
            company_id: Company to score
            tenant_id: Tenant ID
            recompute: If True, re-extract metrics and re-score

        Returns:
            Dict with overall_score, pillar_scores, flags, recommendation
        """
        # Generate unique scoring run ID for this pipeline execution
        scoring_run_id = str(uuid.uuid4())

        logger.info("=" * 70)
        logger.info(f"[SCORING PIPELINE] Starting for company {company_id}")
        logger.info(f"[SCORING PIPELINE] Scoring Run ID: {scoring_run_id}")
        logger.info(f"[SCORING PIPELINE] Recompute: {recompute}")
        logger.info("=" * 70)

        pillar_scores = {}

        # Get document count at start of scoring (for rerun detection)
        scored_doc_count = db.exec(
            select(func.count(Document.id)).where(
                Document.company_id == company_id,
                Document.status == DocumentStatus.COMPLETED
            )
        ).one()
        logger.info(f"[SCORING PIPELINE] Processing {scored_doc_count} documents")

        try:
            # ========== STAGE 1: METRIC EXTRACTION ==========
            logger.info("[PIPELINE] Stage 1: Metric Extraction")
            await self._broadcast(
                company_id=company_id,
                stage=1,
                stage_name="Extracting Metrics",
                progress=5,
                pillar_progress=self._get_pillar_progress({})
            )

            extracted_metrics = await self.metric_service.extract_metrics_for_company(
                db=db,
                company_id=company_id,
                tenant_id=tenant_id,
                scoring_run_id=scoring_run_id
            )
            logger.info(f"[PIPELINE] Stage 1 Complete: Extracted metrics for {len(extracted_metrics)} pillars")

            await self._broadcast(
                company_id=company_id,
                stage=1,
                stage_name="Extracting Metrics",
                progress=20,
                pillar_progress=self._get_pillar_progress({})
            )

            # ========== STAGE 2: PILLAR AGGREGATION ==========
            logger.info("[PIPELINE] Stage 2: Pillar Aggregation")
            await self._broadcast(
                company_id=company_id,
                stage=2,
                stage_name="Aggregating Pillar Data",
                progress=22,
                pillar_progress=self._get_pillar_progress({})
            )

            pillar_data_cache = {}
            pillars_to_process = [p for p in BDEPillar if p != BDEPillar.GENERAL]
            total_pillars = len(pillars_to_process)

            for idx, pillar in enumerate(pillars_to_process):
                pillar_value = pillar.value
                logger.info(f"[PIPELINE] Aggregating data for {pillar_value}")

                pillar_data = await self.aggregation_service.aggregate_pillar_data(
                    db=db,
                    company_id=company_id,
                    pillar=pillar_value
                )
                pillar_data_cache[pillar_value] = pillar_data

            logger.info(f"[PIPELINE] Stage 2 Complete: Aggregated data for {len(pillar_data_cache)} pillars")

            await self._broadcast(
                company_id=company_id,
                stage=2,
                stage_name="Aggregating Pillar Data",
                progress=30,
                pillar_progress=self._get_pillar_progress({})
            )

            # ========== STAGE 3: EVALUATION & SCORING ==========
            logger.info("[PIPELINE] Stage 3: Pillar Evaluation & Scoring")

            for idx, (pillar_value, pillar_data) in enumerate(pillar_data_cache.items()):
                logger.info(f"[PIPELINE] Evaluating and scoring {pillar_value}")

                # Broadcast: starting this pillar
                progress = 30 + int((idx / total_pillars) * 40)  # Stage 3 is 30-70%
                await self._broadcast(
                    company_id=company_id,
                    stage=3,
                    stage_name="Evaluating & Scoring Pillars",
                    progress=progress,
                    current_pillar=pillar_value,
                    pillar_progress=self._get_pillar_progress(pillar_scores, pillar_value, "processing")
                )

                # Stage 3A: LLM Evaluation (no scoring)
                evaluation_id = await self.evaluation_service.evaluate_pillar(
                    db=db,
                    company_id=company_id,
                    tenant_id=tenant_id,
                    pillar=pillar_value,
                    pillar_data=pillar_data,
                    scoring_run_id=scoring_run_id
                )

                # Stage 3B: Deterministic Scoring
                score_id = await self.scoring_service.score_pillar(
                    db=db,
                    company_id=company_id,
                    tenant_id=tenant_id,
                    pillar=pillar_value,
                    evaluation_id=evaluation_id,
                    coverage=pillar_data["coverage"],
                    scoring_run_id=scoring_run_id
                )

                # Get the score object
                pillar_score = db.get(CompanyPillarScore, score_id)
                pillar_scores[pillar_value] = pillar_score

                # Broadcast: completed this pillar
                await self._broadcast(
                    company_id=company_id,
                    stage=3,
                    stage_name="Evaluating & Scoring Pillars",
                    progress=progress + 5,
                    current_pillar=pillar_value,
                    pillar_progress=self._get_pillar_progress(pillar_scores)
                )

            logger.info(f"[PIPELINE] Stage 3 Complete: Scored {len(pillar_scores)} pillars")

            # ========== STAGE 4: FLAG DETECTION ==========
            logger.info("[PIPELINE] Stage 4: Flag Detection")
            await self._broadcast(
                company_id=company_id,
                stage=4,
                stage_name="Detecting Flags",
                progress=72,
                pillar_progress=self._get_pillar_progress(pillar_scores)
            )

            flag_ids = await self.flag_service.detect_flags(
                db=db,
                company_id=company_id,
                tenant_id=tenant_id,
                pillar_data_all=pillar_data_cache,
                pillar_scores=pillar_scores,
                scoring_run_id=scoring_run_id
            )

            # Get flag objects
            flags = [db.get(CompanyFlag, flag_id) for flag_id in flag_ids]

            logger.info(f"[PIPELINE] Stage 4 Complete: Detected {len(flags)} flags")

            await self._broadcast(
                company_id=company_id,
                stage=4,
                stage_name="Detecting Flags",
                progress=85,
                pillar_progress=self._get_pillar_progress(pillar_scores)
            )

            # ========== STAGE 5: BDE SCORE & RECOMMENDATION ==========
            logger.info("[PIPELINE] Stage 5: BDE Score Calculation & Recommendation")
            await self._broadcast(
                company_id=company_id,
                stage=5,
                stage_name="Calculating BDE Score & Recommendation",
                progress=87,
                pillar_progress=self._get_pillar_progress(pillar_scores)
            )

            bde_score_id = await self.bde_calculator.calculate_bde_score(
                db=db,
                company_id=company_id,
                tenant_id=tenant_id,
                pillar_scores=pillar_scores,
                flags=flags,
                scored_doc_count=scored_doc_count,
                scoring_run_id=scoring_run_id
            )

            logger.info(f"[PIPELINE] Stage 5 Complete")

            # ========== BUILD RESPONSE ==========
            from database.models.scoring import CompanyBDEScore, AcquisitionRecommendation

            bde_score = db.get(CompanyBDEScore, bde_score_id)

            # Get recommendation
            statement = select(AcquisitionRecommendation).where(
                AcquisitionRecommendation.bde_score_id == bde_score_id,
                AcquisitionRecommendation.is_current == True
            )
            recommendation = db.exec(statement).first()

            result = {
                "success": True,
                "company_id": company_id,
                "overall_score": bde_score.overall_score,
                "weighted_raw_score": bde_score.weighted_raw_score,
                "valuation_range": bde_score.valuation_range,
                "confidence": bde_score.confidence,
                "pillar_scores": {
                    pillar: {
                        "score": score.score,
                        "health_status": score.health_status.value,
                        "confidence": score.confidence,
                        "data_coverage": score.data_coverage_percent
                    }
                    for pillar, score in pillar_scores.items()
                },
                "flags": {
                    "red": [f.flag_text for f in flags if f.flag_type.value == "red"],
                    "yellow": [f.flag_text for f in flags if f.flag_type.value == "yellow"],
                    "green": [f.flag_text for f in flags if f.flag_type.value == "green"]
                },
                "recommendation": {
                    "recommendation": recommendation.recommendation if recommendation else "N/A",
                    "confidence": recommendation.recommendation_confidence if recommendation else 0,
                    "rationale": recommendation.rationale if recommendation else "",
                    "value_drivers": recommendation.value_drivers if recommendation else [],
                    "key_risks": recommendation.key_risks if recommendation else [],
                    "100_day_plan": recommendation.day_100_plan if recommendation else []
                } if recommendation else None,
                "calculated_at": bde_score.calculated_at.isoformat()
            }

            logger.info("=" * 70)
            logger.info(f"[SCORING PIPELINE] COMPLETE")
            logger.info(f"[SCORING PIPELINE] Overall Score: {result['overall_score']}/100")
            logger.info(f"[SCORING PIPELINE] Valuation Range: {result['valuation_range']}")
            logger.info("=" * 70)

            # Broadcast completion
            await self._broadcast(
                company_id=company_id,
                stage=5,
                stage_name="Complete",
                progress=100,
                status="completed",
                pillar_progress=self._get_pillar_progress(pillar_scores),
                result=result
            )

            # Unregister company from progress tracking
            scoring_ws_manager.unregister_company(company_id)

            return result

        except Exception as e:
            logger.error(f"[SCORING PIPELINE] ERROR: {e}", exc_info=True)

            # Broadcast error
            await self._broadcast(
                company_id=company_id,
                stage=0,
                stage_name="Error",
                progress=0,
                status="failed",
                pillar_progress=self._get_pillar_progress(pillar_scores),
                error_message=str(e)
            )

            # Unregister company from progress tracking
            scoring_ws_manager.unregister_company(company_id)

            return {
                "success": False,
                "error": str(e),
                "company_id": company_id
            }
