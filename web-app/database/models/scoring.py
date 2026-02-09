"""Database models for BDE scoring system"""
import uuid
from datetime import datetime, date
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import Text, JSON, ARRAY, String, Boolean, Integer, Float, Date
from typing import Optional, List, Any
from enum import Enum


class HealthStatus(str, Enum):
    """Health status for pillar scores (renamed from RAG to avoid confusion with Retrieval-Augmented Generation)"""
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"


class FlagType(str, Enum):
    """Type of flag detected"""
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"


class FlagSource(str, Enum):
    """Source of flag detection"""
    RULE = "rule"  # Rule-based detection (more trusted)
    LLM = "llm"    # LLM-detected (qualitative)


class CompanyMetric(SQLModel, table=True):
    """
    Stores extracted metrics from documents.
    Metrics are INPUTS to scoring (Stage 1 output).
    """
    __tablename__ = "company_metrics"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    company_id: str = Field(foreign_key="companies.id", index=True)
    tenant_id: str = Field(foreign_key="tenants.id", index=True)
    scoring_run_id: Optional[str] = Field(default=None, index=True)  # Links to specific scoring run

    # Metric identification
    metric_name: str = Field(max_length=200, index=True)  # e.g., "ARR", "GRR", "NRR"
    metric_category: Optional[str] = Field(default=None, max_length=100)  # e.g., "revenue", "retention"

    # Metric values (typed storage for queryability)
    metric_value_numeric: Optional[float] = Field(default=None)  # For numeric metrics
    metric_value_text: Optional[str] = Field(default=None, max_length=500)  # For text representation
    metric_value_json: Optional[Any] = Field(default=None, sa_column=Column(JSON))  # For complex metrics (dict or list)

    metric_unit: Optional[str] = Field(default=None, max_length=50)  # "$", "%", "months", etc.

    # Temporal tracking (for conflict resolution)
    metric_period: Optional[str] = Field(default=None, max_length=100)  # "FY2024", "Q3 2025"
    metric_as_of_date: Optional[date] = Field(default=None, sa_column=Column(Date))  # Precise date

    # Pillar associations (metrics can be used by multiple pillars)
    pillars_used_by: Optional[List[str]] = Field(default=None, sa_column=Column(ARRAY(String)))  # e.g., ["financial_health", "gtm_engine"]
    primary_pillar: Optional[str] = Field(default=None, max_length=100)  # Main pillar owner

    # Traceability
    source_chunk_ids: Optional[List[str]] = Field(default=None, sa_column=Column(ARRAY(String)))
    confidence: Optional[int] = Field(default=None)  # 0-100%

    # Version control & conflict resolution
    is_current: bool = Field(default=True, index=True)  # Only one current value per metric
    superseded_by: Optional[str] = Field(default=None, foreign_key="company_metrics.id")  # Points to newer metric
    needs_analyst_review: bool = Field(default=False)  # Flag conflicts for human review

    # Audit
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    extraction_context: Optional[str] = Field(default=None, sa_column=Column(Text))  # Additional context


class PillarDataCoverageConfig(SQLModel, table=True):
    """
    Defines required data points per pillar (deterministic checklist).
    Used to calculate data coverage %.
    """
    __tablename__ = "pillar_data_coverage_config"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    pillar: str = Field(max_length=100, index=True)  # e.g., "financial_health"

    required_data_point: str = Field(max_length=200)  # e.g., "ARR", "GrossMargin"
    data_point_description: Optional[str] = Field(default=None, sa_column=Column(Text))

    is_critical: bool = Field(default=False)  # Must-have vs nice-to-have
    priority: int = Field(default=3)  # 1-5, higher = more important

    created_at: datetime = Field(default_factory=datetime.utcnow)


class PillarEvaluationCriteria(SQLModel, table=True):
    """
    Stores LLM's criteria assessment (Stage 3A output).
    LLM evaluates YES/NO questions, NOT numeric scores.
    """
    __tablename__ = "pillar_evaluation_criteria"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    company_id: str = Field(foreign_key="companies.id", index=True)
    tenant_id: str = Field(foreign_key="tenants.id", index=True)
    scoring_run_id: Optional[str] = Field(default=None, index=True)  # Links to specific scoring run
    pillar: str = Field(max_length=100, index=True)

    # Criteria evaluation (boolean)
    meets_green_criteria: bool = Field(default=False)
    green_criteria_strength: Optional[float] = Field(default=None)  # 0.0-1.0, for nuance
    green_criteria_evidence: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))

    meets_yellow_criteria: bool = Field(default=False)
    yellow_criteria_strength: Optional[float] = Field(default=None)  # 0.0-1.0
    yellow_criteria_evidence: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))

    fails_red_criteria: bool = Field(default=False)
    red_criteria_evidence: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))

    # Findings from LLM
    key_findings: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    risks: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    data_gaps: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))

    # Evidence
    evidence_chunk_ids: Optional[List[str]] = Field(default=None, sa_column=Column(ARRAY(String)))

    # LLM confidence
    llm_confidence: Optional[int] = Field(default=None)  # 0-100%

    # Version control
    is_current: bool = Field(default=True, index=True)
    version: int = Field(default=1)

    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


class CompanyPillarScore(SQLModel, table=True):
    """
    Stores deterministic scores calculated from evaluations (Stage 3B output).
    Scores are COMPUTED by code, NOT assigned by LLM.
    """
    __tablename__ = "company_pillar_scores"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    company_id: str = Field(foreign_key="companies.id", index=True)
    tenant_id: str = Field(foreign_key="tenants.id", index=True)
    scoring_run_id: Optional[str] = Field(default=None, index=True)  # Links to specific scoring run
    pillar: str = Field(max_length=100, index=True)

    # Score (0-5 scale)
    score: float = Field(default=0.0)  # 0.0 to 5.0
    health_status: HealthStatus = Field(default=HealthStatus.RED)

    # Justification (code-generated from evaluation)
    justification: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Data quality
    data_coverage_percent: Optional[int] = Field(default=None)  # 0-100%
    confidence: Optional[int] = Field(default=None)  # 0-100%
    insufficient_data_flag: bool = Field(default=False)  # True if coverage < 30% + critical_missing > 2

    # Link to evaluation
    evaluation_id: Optional[str] = Field(default=None, foreign_key="pillar_evaluation_criteria.id")

    # Version control
    is_current: bool = Field(default=True, index=True)
    version: int = Field(default=1)

    calculated_at: datetime = Field(default_factory=datetime.utcnow)


class CompanyBDEScore(SQLModel, table=True):
    """
    Stores overall weighted BDE score (Stage 5A output).
    Also serves as the primary record for a scoring run.
    """
    __tablename__ = "company_bde_scores"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    company_id: str = Field(foreign_key="companies.id", index=True)
    tenant_id: str = Field(foreign_key="tenants.id", index=True)
    scoring_run_id: str = Field(index=True)  # Unique ID for this scoring run (required)

    # Overall scores
    overall_score: int = Field(default=0)  # 0-100 scale (the "78" in dashboard)
    weighted_raw_score: float = Field(default=0.0)  # 0-5 scale (before converting to 100)

    # Valuation
    valuation_range: Optional[str] = Field(default=None, max_length=100)  # "5-7x ARR"

    # Confidence
    confidence: Optional[int] = Field(default=None)  # 0-100%, aggregated from pillars

    # Document tracking for rerun detection
    scored_doc_count: int = Field(default=0)  # Number of documents used in this scoring run

    # Version control
    is_current: bool = Field(default=True, index=True)
    version: int = Field(default=1)

    calculated_at: datetime = Field(default_factory=datetime.utcnow)


class AcquisitionRecommendation(SQLModel, table=True):
    """
    Stores LLM-generated acquisition recommendation (Stage 5B output).
    """
    __tablename__ = "acquisition_recommendations"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    company_id: str = Field(foreign_key="companies.id", index=True)
    tenant_id: str = Field(foreign_key="tenants.id", index=True)
    scoring_run_id: Optional[str] = Field(default=None, index=True)  # Links to specific scoring run
    bde_score_id: str = Field(foreign_key="company_bde_scores.id")

    # Recommendation
    recommendation: str = Field(sa_column=Column(Text))  # "STRONG BUY", "BUY WITH CONDITIONS", etc.
    recommendation_confidence: Optional[int] = Field(default=None)  # 0-100%

    # Rationale
    rationale: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Strategic insights
    value_drivers: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    key_risks: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))

    # 100-day plan
    day_100_plan: Optional[List[dict]] = Field(default=None, sa_column=Column(JSON))  # List of action items

    # Valuation guidance
    suggested_valuation_multiple: Optional[str] = Field(default=None, max_length=100)
    valuation_adjustments: Optional[List[dict]] = Field(default=None, sa_column=Column(JSON))

    # Version control
    is_current: bool = Field(default=True, index=True)
    version: int = Field(default=1)

    generated_at: datetime = Field(default_factory=datetime.utcnow)


class CompanyFlag(SQLModel, table=True):
    """
    Stores detected flags (Stage 4 output).
    Flags are independent of scores.
    """
    __tablename__ = "company_flags"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    company_id: str = Field(foreign_key="companies.id", index=True)
    tenant_id: str = Field(foreign_key="tenants.id", index=True)
    scoring_run_id: Optional[str] = Field(default=None, index=True)  # Links to specific scoring run

    # Flag details
    flag_type: FlagType = Field(default=FlagType.YELLOW)
    flag_source: FlagSource = Field(default=FlagSource.RULE)  # RULE or LLM
    flag_category: str = Field(max_length=200)  # e.g., "customer_concentration", "founder_burnout"
    flag_text: str = Field(sa_column=Column(Text))  # Human-readable description

    # Association
    pillar: Optional[str] = Field(default=None, max_length=100)  # Can be NULL for general flags

    # Severity
    severity: int = Field(default=3)  # 1-5

    # Evidence
    evidence_chunk_ids: Optional[List[str]] = Field(default=None, sa_column=Column(ARRAY(String)))
    rationale: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Status
    is_active: bool = Field(default=True)  # Can be dismissed by analysts
    dismissed_by: Optional[str] = Field(default=None, foreign_key="users.id")
    dismissal_reason: Optional[str] = Field(default=None, sa_column=Column(Text))

    detected_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
