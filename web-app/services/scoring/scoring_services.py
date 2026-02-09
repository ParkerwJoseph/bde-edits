"""
Stages 3A, 3B, 4, 5: Core scoring services
Combined into single file for efficiency.
"""
import json
from typing import List, Dict, Optional, Any
from datetime import datetime
from sqlmodel import Session, select
from database.models.scoring import (
    PillarEvaluationCriteria,
    CompanyPillarScore,
    CompanyBDEScore,
    CompanyFlag,
    AcquisitionRecommendation,
    HealthStatus,
    FlagType,
    FlagSource,
    CompanyMetric
)
from database.models.document import DocumentChunk
from database.models.prompt_template import PromptTemplate
from services.llm_client import get_llm_client
from utils.logger import get_logger

logger = get_logger(__name__)


# ==================================================================
# STAGE 3A: Pillar Evaluation Service (LLM - NO SCORING)
# ==================================================================

class PillarEvaluationService:
    """
    LLM evaluates criteria WITHOUT assigning numeric scores.
    Uses prompts from prompt_templates table.
    """

    # Pillar weights for BDE calculation
    PILLAR_WEIGHTS = {
        "financial_health": 0.20,
        "gtm_engine": 0.15,
        "customer_health": 0.15,
        "product_technical": 0.15,
        "operational_maturity": 0.10,
        "leadership_transition": 0.10,
        "ecosystem_dependency": 0.10,
        "service_software_ratio": 0.05
    }

    # Pillar-specific scoring criteria from BCP Pillar Scoring Rubric - EXACT THRESHOLDS
    PILLAR_SCORING_CRITERIA = {
        "financial_health": {
            "green": ">50% recurring revenue; EBITDA margin 15-25%; customer concentration <25% (top 3); AR days <45; pricing growth >5% annually; services <50% of revenue; strong cash conversion; clean books",
            "yellow": "Recurring revenue 20-50%; EBITDA margin 5-15%; customer concentration 25-40%; AR days 60-90; inconsistent pricing growth; services heavy but manageable; some cashflow friction",
            "red": "Recurring revenue <20%; EBITDA margin <5% or negative; customer concentration >40%; AR days >90; stagnant pricing; high customization burden; unprofitable; AR collection issues"
        },
        "gtm_engine": {
            "green": "Clearly defined ICP with repeatable wins; pipeline coverage 3-5x monthly quota; excellent CRM hygiene; forecast accuracy ±10-15%; multiple lead channels (partner + inbound + outbound); documented sales playbooks",
            "yellow": "Loosely defined ICP but correctable; inconsistent pipeline coverage; CRM partially used; forecast variance 20-40%; sporadic lead generation; founder still involved in sales",
            "red": "No ICP definition; pipeline mostly founder-generated; CRM not used or unreliable; forecast is guesswork; no demand generation capability; founder-only sales dependency"
        },
        "customer_health": {
            "green": "GRR >90%; NRR >110%; top 3 customer concentration <20%; high multi-module adoption; low predictable support burden; strong positive sentiment/reviews; clear expansion pathways",
            "yellow": "GRR 80-90%; NRR ~100%; top 3 concentration 20-35%; OK adoption but not deep; manageable support burden; mixed/neutral sentiment; expansion present but untapped",
            "red": "GRR <80%; NRR <95%; top 3 concentration >35-40%; low adoption; high support burden; negative sentiment; minimal expansion potential; churn accelerating"
        },
        "product_technical": {
            "green": "Modular modern architecture; good documentation; real REST/GraphQL APIs; strong performance; strong security hygiene (SOC2/ISO); realistic roadmap delivered on time; no bus-factor risk; high test coverage",
            "yellow": "Some legacy areas; partial documentation; limited API depth; moderate performance issues; basic security practices; roadmap mostly delivered; some bus-factor risk; moderate test coverage",
            "red": "Monolithic architecture; poor/missing documentation; screen scraping or custom integrations only; major performance failures; significant security gaps; roadmap misses 50%+; bus-factor of 1; minimal testing"
        },
        "operational_maturity": {
            "green": "SOPs documented and followed; strong cross-functional cadence; integrated systems with automation; clean data across CRM/support/finance; standardized predictable onboarding; low support backlog with structured CS; low founder dependency",
            "yellow": "Partial documentation; some cadence inconsistency; manual processes with limited automation; mostly reliable data; onboarding varies by customer; reactive but manageable support; key individual reliance",
            "red": "No documentation; no operating cadence; disconnected manual systems with data re-entry; unreliable data; unpredictable onboarding; overwhelmed support; founder extremely dependent on all decisions"
        },
        "leadership_transition": {
            "green": "Founder not required day-to-day; competent aligned leadership team; documented institutional knowledge; data-driven decision making; healthy culture minimal politics; relationships distributed across team; emotionally ready for transition",
            "yellow": "Founder actively delegating; uneven but functional team; partial documentation; mostly disciplined decisions; some cultural friction; relationships mostly team-held; open to transition coaching",
            "red": "Founder holds all decisions; no real leadership team; tribal knowledge only; reactive/emotional decisions; fear-based or toxic culture; all key relationships founder-dependent; founder not emotionally ready to exit"
        },
        "ecosystem_dependency": {
            "green": "Moderate/low ERP dependency; aligned with ERP roadmap; robust modern integrations; ERP won't internalize ISV's functionality; strong validated marketplace position; multi-ERP diversification optionality",
            "yellow": "High ERP dependency but strong relationships; unclear but not hostile roadmap alignment; periodic integration firefighting; internalization possible but not imminent; moderate marketplace reliance; diversification requires investment",
            "red": "Very high single-ERP dependency; misaligned or unclear ERP roadmap; fragile integrations that break frequently; ERP actively replacing ISV features; low marketplace visibility/ratings; diversification technically or financially impossible"
        },
        "service_software_ratio": {
            "green": "Software revenue 70-90%+; standardized templated implementations; minimal custom coding required; high margins with strong trajectory; clear productization pathway to modules/add-ons; scalable without adding headcount",
            "yellow": "Software revenue 40-60%; semi-standardized implementations; moderate customization burden; improving margin trajectory; productization possible with investment; scalable with moderate effort",
            "red": "Software revenue <40%; unpredictable implementations; high customization burden; low margins; minimal productization potential; requires hiring more people to scale; essentially a services company with software wrapper"
        }
    }

    def __init__(self):
        self.llm_client = get_llm_client()
        logger.info("[PillarEvaluationService] Initialized")

    async def evaluate_pillar(
        self,
        db: Session,
        company_id: str,
        tenant_id: str,
        pillar: str,
        pillar_data: Dict[str, Any],
        scoring_run_id: str = None
    ) -> str:
        """
        Evaluate pillar using LLM (returns evaluation_id).
        LLM assesses criteria, does NOT assign score.
        """
        logger.info(f"[Stage 3A] Evaluating pillar: {pillar} (run: {scoring_run_id})")

        # Get prompt template
        prompt_template = self._get_prompt_template(db, f"pillar_evaluation_{pillar}")

        # Build evaluation prompt
        prompt = self._build_evaluation_prompt(
            template=prompt_template,
            pillar=pillar,
            pillar_data=pillar_data
        )

        # LLM evaluation
        evaluation_result = await self._llm_evaluate_criteria(prompt)

        # Resolve chunk references from LLM to actual chunk IDs
        evidence_chunk_ids = self._resolve_evaluation_chunk_references(
            evaluation_result.get("evidence_chunk_ids", []),
            pillar_data.get("chunks", [])
        )

        # Store evaluation
        evaluation = PillarEvaluationCriteria(
            company_id=company_id,
            tenant_id=tenant_id,
            scoring_run_id=scoring_run_id,
            pillar=pillar,
            meets_green_criteria=evaluation_result.get("meets_green_criteria", False),
            green_criteria_strength=evaluation_result.get("green_criteria_strength"),
            green_criteria_evidence=evaluation_result.get("green_criteria_evidence", []),
            meets_yellow_criteria=evaluation_result.get("meets_yellow_criteria", False),
            yellow_criteria_strength=evaluation_result.get("yellow_criteria_strength"),
            yellow_criteria_evidence=evaluation_result.get("yellow_criteria_evidence", []),
            fails_red_criteria=evaluation_result.get("fails_red_criteria", False),
            red_criteria_evidence=evaluation_result.get("red_criteria_evidence", []),
            key_findings=evaluation_result.get("key_findings", []),
            risks=evaluation_result.get("risks", []),
            data_gaps=evaluation_result.get("data_gaps", []),
            evidence_chunk_ids=evidence_chunk_ids,
            llm_confidence=evaluation_result.get("confidence", 70),
            is_current=True,
            version=1
        )

        db.add(evaluation)
        db.commit()
        db.refresh(evaluation)

        logger.info(f"[Stage 3A] Evaluation complete for {pillar}, ID: {evaluation.id}")
        return evaluation.id

    def _get_prompt_template(self, db: Session, template_name: str) -> str:
        """Get prompt template from database or return default"""

        statement = select(PromptTemplate).where(
            PromptTemplate.name == template_name,
            PromptTemplate.is_active == True
        )
        template = db.exec(statement).first()

        if template:
            return template.template

        # Return default template if not found
        return self._get_default_evaluation_template()

    def _get_default_evaluation_template(self) -> str:
        """Default evaluation template - uses pillar-specific criteria"""
        return """You are evaluating a company for the **{pillar}** pillar in BDE (Business Due Diligence Evaluation) analysis.

## CONTEXT:
You are assessing an ERP-adjacent software company for PE acquisition. This is a CRITICAL due diligence system.
Your evaluation MUST be evidence-based. Do NOT assume scores without documented evidence.

## PILLAR-SPECIFIC SCORING CRITERIA FOR {pillar}:

### GREEN CRITERIA (Score 4-5, Top Quartile - requires STRONG evidence):
{green_criteria}

### YELLOW CRITERIA (Score 2.5-3.9, Middle 50% - requires MODERATE evidence):
{yellow_criteria}

### RED CRITERIA (Score below 2.5, Bottom Quartile - requires evidence of problems):
{red_criteria}

## AVAILABLE DATA:
### Extracted Metrics:
{metrics_summary}

### Data Coverage:
{coverage_summary}

### Document Evidence (ANALYZE THOROUGHLY):
{chunks_summary}

## EVALUATION RULES - EVIDENCE-BASED ONLY:
1. **Every assessment MUST cite specific evidence** from the documents
2. **meets_green_criteria = TRUE** only if documents show CLEAR evidence matching green criteria
3. **meets_yellow_criteria = TRUE** only if documents show evidence of partial/moderate achievement
4. **fails_red_criteria = TRUE** only if documents show EXPLICIT problems or red flags
5. **Strength values** (0.0-1.0) must reflect the AMOUNT and QUALITY of evidence
6. **No evidence = No assumption** - if data is missing, set that criteria to FALSE with low strength
7. **Document data_gaps** for missing information that would be needed for full assessment

## CONFIDENCE SCORING:
- 80-100: Multiple strong pieces of evidence
- 60-79: Clear evidence but limited data points
- 40-59: Some evidence but significant gaps
- 20-39: Minimal evidence available
- 0-19: Insufficient data to evaluate

## OUTPUT FORMAT (JSON only, no markdown):
{{
  "meets_green_criteria": true/false,
  "green_criteria_strength": 0.0-1.0,
  "green_criteria_evidence": ["Specific evidence from documents"],

  "meets_yellow_criteria": true/false,
  "yellow_criteria_strength": 0.0-1.0,
  "yellow_criteria_evidence": ["Specific evidence from documents"],

  "fails_red_criteria": true/false,
  "red_criteria_evidence": ["Specific problems documented"],

  "key_findings": ["Key finding with source"],
  "risks": ["Identified risk with source"],
  "data_gaps": ["Missing information needed"],
  "evidence_chunk_ids": ["chunk_1", "chunk_5", "chunk_8"],
  "confidence": 50
}}"""

    def _build_evaluation_prompt(
        self,
        template: str,
        pillar: str,
        pillar_data: Dict[str, Any]
    ) -> str:
        """Fill prompt template with pillar data"""

        # Format metrics
        metrics = pillar_data.get("metrics", {})
        metrics_summary = "\n".join([
            f"- {name}: {metric.metric_value_text} ({metric.confidence}% confidence)"
            for name, metric in metrics.items()
        ]) if metrics else "No metrics extracted"

        # Format coverage
        coverage = pillar_data.get("coverage", {})
        coverage_summary = f"""
- Coverage: {coverage.get('percent', 0)}%
- Present: {', '.join(coverage.get('present_points', [])[:10])}
- Missing: {', '.join(coverage.get('missing_points', [])[:5])}
- Critical Missing: {', '.join(coverage.get('critical_missing', []))}
"""

        # Format ALL chunks for comprehensive evaluation - this is critical due diligence
        all_chunks = pillar_data.get("chunks", [])
        total_chunks = len(all_chunks)

        # Separate connector and document chunks
        connector_chunks = []
        document_chunks = []
        for chunk in all_chunks:
            if hasattr(chunk, 'connector_type'):
                connector_chunks.append(chunk)
            else:
                document_chunks.append(chunk)

        # Build chunks summary with source type labeling
        chunks_parts = []

        # Add connector chunks first (authoritative data)
        if connector_chunks:
            chunks_parts.append("=" * 60)
            chunks_parts.append("## CONNECTOR DATA (Authoritative - from integrated systems)")
            chunks_parts.append("=" * 60)
            for i, chunk in enumerate(connector_chunks[:50]):
                connector_type = chunk.connector_type.value if chunk.connector_type else "connector"
                entity_type = chunk.entity_type or "data"
                chunks_parts.append(f"\n--- CHUNK {i+1} [Source: {connector_type.upper()}/{entity_type}, ID: chunk_{i}] ---")
                chunks_parts.append(chunk.content[:800])

        # Add document chunks
        if document_chunks:
            # Offset for chunk IDs (continue numbering from connector chunks)
            offset = len(connector_chunks[:50])
            chunks_parts.append("\n" + "=" * 60)
            chunks_parts.append("## DOCUMENT DATA (from uploaded documents)")
            chunks_parts.append("=" * 60)
            for i, chunk in enumerate(document_chunks[:50]):
                page_num = getattr(chunk, 'page_number', 0)
                chunks_parts.append(f"\n--- CHUNK {offset + i + 1} [Page {page_num}, ID: chunk_{offset + i}] ---")
                chunks_parts.append(chunk.content[:800])

        chunks_summary = "\n".join(chunks_parts) if chunks_parts else "No chunks available"

        # Add chunk count context
        if total_chunks > 0:
            header = f"=== EVIDENCE: {len(connector_chunks)} connector chunks + {len(document_chunks)} document chunks ({total_chunks} total) ===\n\n"
            chunks_summary = header + chunks_summary
            shown = min(50, len(connector_chunks)) + min(50, len(document_chunks))
            if total_chunks > shown:
                chunks_summary += f"\n\n[Note: {total_chunks - shown} additional chunks not shown]"

        # Get pillar-specific criteria
        pillar_criteria = self.PILLAR_SCORING_CRITERIA.get(pillar, {
            "green": "Best-in-class maturity; highly scalable; low risk",
            "yellow": "Mixed maturity; fixable with investment; some friction",
            "red": "Significant gaps; founder dependency; scalability limited"
        })

        # Fill template with pillar-specific criteria
        filled_prompt = template.format(
            pillar=pillar,
            green_criteria=pillar_criteria["green"],
            yellow_criteria=pillar_criteria["yellow"],
            red_criteria=pillar_criteria["red"],
            metrics_summary=metrics_summary,
            coverage_summary=coverage_summary,
            chunks_summary=chunks_summary
        )

        return filled_prompt

    async def _llm_evaluate_criteria(self, prompt: str) -> Dict[str, Any]:
        """Call LLM to evaluate criteria with comprehensive evidence analysis"""

        try:
            response_text, usage_stats = self.llm_client.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a PE due diligence expert evaluating companies for acquisition. Analyze ALL provided evidence thoroughly. Your evaluation must be evidence-based - cite specific documents. Respond with valid JSON only, no markdown."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=4000  # Increased for detailed analysis
            )

            # Clean markdown code blocks if present
            cleaned_response = response_text.strip()
            if cleaned_response.startswith("```"):
                lines = cleaned_response.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                cleaned_response = "\n".join(lines)

            # Find JSON start
            json_start = cleaned_response.find("{")
            if json_start >= 0:
                cleaned_response = cleaned_response[json_start:]

            result = json.loads(cleaned_response)
            return result

        except json.JSONDecodeError as e:
            logger.error(f"[Stage 3A] JSON parse error: {e}")
            # Return neutral - NO assumed score without evidence
            return {
                "meets_green_criteria": False,
                "green_criteria_strength": 0.0,
                "meets_yellow_criteria": False,
                "yellow_criteria_strength": 0.0,
                "fails_red_criteria": False,
                "key_findings": ["Evaluation failed - JSON parse error"],
                "risks": ["Unable to evaluate - requires manual review"],
                "data_gaps": ["Full evaluation pending"],
                "evidence_chunk_ids": [],
                "confidence": 0
            }
        except Exception as e:
            logger.error(f"[Stage 3A] Error in LLM evaluation: {e}")
            # Return neutral - NO assumed score without evidence
            return {
                "meets_green_criteria": False,
                "green_criteria_strength": 0.0,
                "meets_yellow_criteria": False,
                "yellow_criteria_strength": 0.0,
                "fails_red_criteria": False,
                "key_findings": ["Evaluation failed - system error"],
                "risks": ["Unable to evaluate - requires manual review"],
                "data_gaps": ["Full evaluation pending"],
                "evidence_chunk_ids": [],
                "confidence": 0
            }

    def _resolve_evaluation_chunk_references(
        self,
        chunk_refs: List[str],
        chunks: List
    ) -> List[str]:
        """
        Resolve LLM chunk references to actual chunk IDs for Stage 3 evaluation.
        Similar to Stage 1's resolution, but for pillar evaluation evidence.
        """
        if not chunk_refs or not chunks:
            return []

        resolved_chunks = []
        for ref in chunk_refs:
            if not ref:
                continue

            # Handle "chunk_N" format (e.g., "chunk_1", "chunk_0")
            if isinstance(ref, str) and ref.startswith("chunk_") and len(ref.split("_")) == 2:
                try:
                    idx = int(ref.split("_")[1])
                    if idx < len(chunks):
                        resolved_chunks.append(chunks[idx].id)
                    else:
                        logger.warning(f"[Stage 3A] Invalid chunk index in evaluation: {ref}")
                except (ValueError, IndexError):
                    logger.warning(f"[Stage 3A] Could not parse chunk reference: {ref}")

            # Handle actual UUID (already correct)
            elif isinstance(ref, str) and "-" in ref and len(ref) > 30:
                # Looks like a UUID, accept it
                resolved_chunks.append(ref)

            else:
                logger.warning(f"[Stage 3A] Unknown chunk reference format in evaluation: {ref}")

        return resolved_chunks


# ==================================================================
# STAGE 3B: Deterministic Scoring Engine (CODE - NOT LLM)
# ==================================================================

class ScoringEngineService:
    """
    Applies rubric rules to compute scores (100% deterministic).
    LLM is NOT involved in this stage.
    """

    def __init__(self):
        logger.info("[ScoringEngineService] Initialized")

    async def score_pillar(
        self,
        db: Session,
        company_id: str,
        tenant_id: str,
        pillar: str,
        evaluation_id: str,
        coverage: Dict[str, Any],
        scoring_run_id: str = None
    ) -> str:
        """
        Calculate pillar score deterministically.
        Returns score_id.
        """
        logger.info(f"[Stage 3B] Scoring pillar: {pillar} (run: {scoring_run_id})")

        # Get evaluation
        evaluation = db.get(PillarEvaluationCriteria, evaluation_id)
        if not evaluation:
            raise ValueError(f"Evaluation {evaluation_id} not found")

        # Calculate score (deterministic)
        score_result = self._calculate_pillar_score(evaluation, coverage)

        # Store score
        pillar_score = CompanyPillarScore(
            company_id=company_id,
            tenant_id=tenant_id,
            scoring_run_id=scoring_run_id,
            pillar=pillar,
            score=score_result["score"],
            health_status=score_result["health_status"],
            justification=score_result["justification"],
            data_coverage_percent=coverage.get("percent", 0),
            confidence=score_result["confidence"],
            insufficient_data_flag=score_result["insufficient_data_flag"],
            evaluation_id=evaluation_id,
            is_current=True,
            version=1
        )

        db.add(pillar_score)
        db.commit()
        db.refresh(pillar_score)

        logger.info(f"[Stage 3B] Scored {pillar}: {score_result['score']}/5.0 ({score_result['health_status']})")
        return pillar_score.id

    def _calculate_pillar_score(
        self,
        evaluation: PillarEvaluationCriteria,
        coverage: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Deterministic scoring logic based on BCP Pillar Scoring Rubric.
        EVIDENCE-BASED ONLY - no score assumptions without documented criteria matches.

        Score Range (0-5) - ALIGNED WITH SOURCE DOCUMENTS:
        - 5.0: Exceptional (Top 10%) - premium valuation - requires strong GREEN + high coverage
        - 4.0-4.75: Strong (Top 25%) - above-average valuation - GREEN criteria met
        - 3.0-3.9: Adequate (Middle 50%) - standard valuation - YELLOW criteria met
        - 2.0-2.9: Weak (Bottom 25%) - discounted valuation - partial evidence
        - 1.0-1.9: Fragile (Bottom 10%) - deep discount - RED flags or no evidence
        - 0.0: Deal-killing condition - severe documented issues only
        """

        coverage_pct = coverage.get("percent", 0)
        critical_missing = len(coverage.get("critical_missing", []))
        llm_confidence = evaluation.llm_confidence or 0

        # EDGE CASE: Very low confidence or no evaluation data = 1.0 (Fragile)
        if llm_confidence < 20:
            return {
                "score": 1.0,  # No confidence = Fragile, requires manual review
                "health_status": HealthStatus.RED,
                "justification": f"Insufficient evaluation confidence ({llm_confidence}%). Score set to 1.0 pending manual review.",
                "confidence": llm_confidence,
                "insufficient_data_flag": True
            }

        # Base score from LLM criteria evaluation - EVIDENCE BASED
        green_strength = evaluation.green_criteria_strength or 0.0
        yellow_strength = evaluation.yellow_criteria_strength or 0.0

        # Scoring logic based on BCP rubric - ALIGNED WITH SOURCE DOCUMENT RANGES
        if evaluation.fails_red_criteria:
            # RED flags documented - score 1.0-2.4 based on severity
            # Higher yellow mitigation = less severe red
            red_mitigation = yellow_strength * 0.4
            base_score = 1.0 + red_mitigation + (0.5 if evaluation.meets_yellow_criteria else 0)
            # Cap RED at 2.4 (below YELLOW threshold)
            base_score = min(2.4, base_score)
        elif evaluation.meets_green_criteria and green_strength >= 0.7:
            # Strong GREEN evidence - score 4.0-4.75 (can reach 5.0 with high coverage)
            base_score = 4.0 + (green_strength * 0.75)  # 4.0-4.75 range
        elif evaluation.meets_green_criteria and green_strength >= 0.4:
            # Moderate GREEN evidence - score 3.9-4.3
            base_score = 3.9 + (green_strength * 0.4)  # 3.9-4.3 range
        elif evaluation.meets_green_criteria:
            # Some GREEN evidence - score 3.5-3.9
            base_score = 3.5 + (green_strength * 0.4)  # 3.5-3.9 range
        elif evaluation.meets_yellow_criteria and yellow_strength >= 0.7:
            # Strong YELLOW evidence - score 3.4-3.9 (top of YELLOW range)
            base_score = 3.4 + (yellow_strength * 0.5)  # 3.4-3.9 range
        elif evaluation.meets_yellow_criteria and yellow_strength >= 0.4:
            # Moderate YELLOW evidence - score 2.9-3.4
            base_score = 2.9 + (yellow_strength * 0.5)  # 2.9-3.4 range
        elif evaluation.meets_yellow_criteria:
            # Some YELLOW evidence - score 2.5-2.9
            base_score = 2.5 + (yellow_strength * 0.4)  # 2.5-2.9 range
        else:
            # No criteria met - insufficient evidence = score 1.0 (Fragile)
            base_score = 1.0

        # Coverage adjustments (moderate impact)
        if coverage_pct < 30:
            base_score -= 0.3
        elif coverage_pct < 50:
            base_score -= 0.2
        elif coverage_pct < 70:
            base_score -= 0.1

        # Critical missing penalty (capped)
        base_score -= min(0.5, critical_missing * 0.1)

        # Floor at 1.0 (not 0.0) - only 0 for deal-killing conditions
        final_score = max(1.0, min(4.75, base_score))

        # Upgrade to 5.0 only if truly exceptional with high coverage
        if final_score >= 4.5 and not evaluation.fails_red_criteria and coverage_pct >= 80 and green_strength >= 0.8:
            final_score = 5.0

        final_score = round(final_score, 1)

        # Map to health status
        health_status = self._map_score_to_health_status(final_score)

        # Generate justification
        justification = self._generate_justification(
            evaluation, final_score, coverage, green_strength, yellow_strength
        )

        # Calculate confidence
        confidence = self._calculate_confidence(
            evaluation.llm_confidence or 70,
            coverage_pct,
            critical_missing
        )

        return {
            "score": final_score,
            "health_status": health_status,
            "justification": justification,
            "confidence": confidence,
            "insufficient_data_flag": False
        }

    def _map_score_to_health_status(self, score: float) -> HealthStatus:
        """
        Deterministic mapping: score → health status
        ALIGNED WITH SOURCE DOCUMENTS:
        - GREEN: Score 4.0-5.0 (Top 25% - Strong/Exceptional)
        - YELLOW: Score 2.5-3.9 (Middle 50% - Adequate)
        - RED: Score 1.0-2.4 (Bottom 25% - Weak/Fragile)
        """
        if score >= 4.0:
            return HealthStatus.GREEN
        elif score >= 2.5:
            return HealthStatus.YELLOW
        else:
            return HealthStatus.RED

    def _generate_justification(
        self,
        evaluation: PillarEvaluationCriteria,
        score: float,
        coverage: Dict,
        green_strength: float,
        yellow_strength: float
    ) -> str:
        """Generate human-readable justification"""

        parts = []

        # Score explanation
        if score >= 4.0:
            parts.append(f"Strong performance (Score: {score}/5.0).")
        elif score >= 3.0:
            parts.append(f"Adequate performance (Score: {score}/5.0).")
        else:
            parts.append(f"Below-market performance (Score: {score}/5.0).")

        # Criteria evidence
        if evaluation.meets_green_criteria:
            evidence_sample = evaluation.green_criteria_evidence[:2] if evaluation.green_criteria_evidence else []
            parts.append(f"Meets green criteria ({int(green_strength*100)}% strength). {' '.join(evidence_sample)}")
        elif evaluation.meets_yellow_criteria:
            evidence_sample = evaluation.yellow_criteria_evidence[:2] if evaluation.yellow_criteria_evidence else []
            parts.append(f"Meets yellow criteria ({int(yellow_strength*100)}% strength). {' '.join(evidence_sample)}")

        # Red flags
        if evaluation.fails_red_criteria and evaluation.red_criteria_evidence:
            parts.append(f"⚠️ Red flag: {evaluation.red_criteria_evidence[0]}")

        # Coverage
        if coverage.get("percent", 0) < 70:
            missing = coverage.get("critical_missing", [])[:3]
            parts.append(f"Data coverage is {coverage.get('percent', 0)}%. Missing: {', '.join(missing)}.")

        return " ".join(parts)

    def _calculate_confidence(
        self,
        llm_confidence: int,
        coverage_pct: int,
        critical_missing: int
    ) -> int:
        """Calculate overall confidence"""

        # Start with LLM confidence
        confidence = llm_confidence

        # Reduce for low coverage
        if coverage_pct < 50:
            confidence -= 20
        elif coverage_pct < 70:
            confidence -= 10

        # Reduce for missing critical data
        confidence -= (critical_missing * 5)

        return max(0, min(100, confidence))


# ==================================================================
# STAGE 4: LLM Flag Detection Service
# ==================================================================

class FlagDetectionService:
    """
    Detects flags using LLM with exposed prompts.
    Uses Stage 2 output (pillar data) for context.
    """

    def __init__(self):
        self.llm_client = get_llm_client()
        logger.info("[FlagDetectionService] Initialized")

    async def detect_flags(
        self,
        db: Session,
        company_id: str,
        tenant_id: str,
        pillar_data_all: Dict[str, Dict[str, Any]],
        pillar_scores: Dict[str, CompanyPillarScore],
        scoring_run_id: str = None
    ) -> List[str]:
        """
        Detect flags using LLM.
        Returns list of flag IDs.
        """
        logger.info(f"[Stage 4] Detecting flags for company {company_id} (run: {scoring_run_id})")

        # Get prompt template
        prompt_template = self._get_prompt_template(db, "flag_detection")

        # Build flag detection prompt
        prompt = self._build_flag_detection_prompt(
            template=prompt_template,
            pillar_data_all=pillar_data_all,
            pillar_scores=pillar_scores
        )

        # LLM flag detection
        flags_result = await self._llm_detect_flags(prompt)

        # Store flags
        flag_ids = []
        for flag_data in flags_result.get("red_flags", []) + flags_result.get("yellow_flags", []) + flags_result.get("green_accelerants", []):
            flag = CompanyFlag(
                company_id=company_id,
                tenant_id=tenant_id,
                scoring_run_id=scoring_run_id,
                flag_type=FlagType(flag_data.get("type", "yellow").lower()),
                flag_source=FlagSource.LLM,
                flag_category=flag_data.get("category", "general"),
                flag_text=flag_data.get("text", ""),
                pillar=flag_data.get("pillar"),
                severity=flag_data.get("severity", 3),
                evidence_chunk_ids=flag_data.get("evidence_chunk_ids", []),
                rationale=flag_data.get("rationale"),
                is_active=True
            )
            db.add(flag)
            db.commit()
            db.refresh(flag)
            flag_ids.append(flag.id)

        logger.info(f"[Stage 4] Detected {len(flag_ids)} flags")
        return flag_ids

    def _get_prompt_template(self, db: Session, template_name: str) -> str:
        """Get prompt template"""
        statement = select(PromptTemplate).where(
            PromptTemplate.name == template_name,
            PromptTemplate.is_active == True
        )
        template = db.exec(statement).first()

        if template:
            return template.template

        return self._get_default_flag_detection_template()

    def _get_default_flag_detection_template(self) -> str:
        """Default flag detection template"""
        return """You are analyzing a company for acquisition due diligence flags.

## PILLAR SCORES:
{pillar_scores_summary}

## DATA COVERAGE:
{coverage_summary}

## KEY METRICS:
{metrics_summary}

## EVALUATION FINDINGS:
{findings_summary}

## TASK:
Identify RED, YELLOW, and GREEN flags based on quantitative and qualitative patterns.

OUTPUT FORMAT (JSON):
{{
  "red_flags": [
    {{
      "type": "red",
      "category": "customer_concentration",
      "text": "Top 3 customers = 45% of ARR",
      "pillar": "financial_health",
      "severity": 4,
      "evidence_chunk_ids": ["chunk_123"],
      "rationale": "Exceeds 40% threshold"
    }}
  ],
  "yellow_flags": [...],
  "green_accelerants": [...]
}}"""

    def _build_flag_detection_prompt(
        self,
        template: str,
        pillar_data_all: Dict[str, Dict],
        pillar_scores: Dict[str, CompanyPillarScore]
    ) -> str:
        """Fill template with data"""

        # Summarize pillar scores
        scores_summary = "\n".join([
            f"- {pillar}: {score.score}/5.0 ({score.health_status.value.upper()})"
            for pillar, score in pillar_scores.items()
        ])

        # Summarize metrics
        all_metrics = []
        for pillar_data in pillar_data_all.values():
            all_metrics.extend(pillar_data.get("metrics", {}).values())

        metrics_summary = "\n".join([
            f"- {m.metric_name}: {m.metric_value_text}"
            for m in all_metrics[:20]
        ])

        # Summarize coverage
        coverage_summary = "\n".join([
            f"- {pillar}: {data.get('coverage', {}).get('percent', 0)}%"
            for pillar, data in pillar_data_all.items()
        ])

        findings_summary = "See pillar evaluations for detailed findings."

        filled = template.format(
            pillar_scores_summary=scores_summary,
            coverage_summary=coverage_summary,
            metrics_summary=metrics_summary,
            findings_summary=findings_summary
        )

        return filled

    async def _llm_detect_flags(self, prompt: str) -> Dict[str, Any]:
        """Call LLM"""
        try:
            response_text, usage_stats = self.llm_client.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a BDE flag detection expert. You must respond with valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=3000
            )
            return json.loads(response_text)
        except Exception as e:
            logger.error(f"[Stage 4] Error: {e}")
            return {"red_flags": [], "yellow_flags": [], "green_accelerants": []}


# ==================================================================
# STAGE 5: BDE Calculator & Recommendation Service
# ==================================================================

class BDECalculatorService:
    """
    Stage 5A: Calculate weighted BDE score (pure math)
    Stage 5B: Generate LLM recommendation
    """

    PILLAR_WEIGHTS = {
        "financial_health": 0.20,
        "gtm_engine": 0.15,
        "customer_health": 0.15,
        "product_technical": 0.15,
        "operational_maturity": 0.10,
        "leadership_transition": 0.10,
        "ecosystem_dependency": 0.10,
        "service_software_ratio": 0.05
    }

    # From BCP Pillar Scoring Rubric - Weighted Score Interpretation
    VALUATION_RANGES = {
        (4.25, 5.0): "6-10x ARR (Premium - Exceptional)",
        (3.75, 4.24): "5-7x ARR (Above-market - Strong)",
        (3.00, 3.74): "3-5x ARR (Standard - Solid but mixed)",
        (2.00, 2.99): "1.5-3x ARR (Discounted - Weak)",
        (1.00, 1.99): "Deep Discount (High Risk)",
        (0.0, 0.99): "Walk-away (Potentially Uninvestable)"
    }

    def __init__(self):
        self.llm_client = get_llm_client()
        logger.info("[BDECalculatorService] Initialized")

    async def calculate_bde_score(
        self,
        db: Session,
        company_id: str,
        tenant_id: str,
        pillar_scores: Dict[str, CompanyPillarScore],
        flags: List[CompanyFlag],
        scored_doc_count: int = 0,
        scoring_run_id: str = None
    ) -> str:
        """
        Calculate overall BDE score and generate recommendation.
        Returns bde_score_id.
        """
        logger.info(f"[Stage 5] Calculating BDE score for company {company_id} (run: {scoring_run_id})")

        # Stage 5A: Calculate weighted score (math)
        weighted_sum = 0.0
        for pillar, weight in self.PILLAR_WEIGHTS.items():
            score = pillar_scores.get(pillar)
            if score:
                weighted_sum += score.score * weight

        weighted_raw_score = weighted_sum  # 0-5 scale
        overall_score = int(weighted_raw_score * 20)  # 0-100 scale

        # Map to valuation range
        valuation_range = self._map_valuation_range(weighted_raw_score)

        # Aggregate confidence
        confidences = [s.confidence for s in pillar_scores.values() if s.confidence]
        avg_confidence = int(sum(confidences) / len(confidences)) if confidences else 50

        # Store BDE score
        bde_score = CompanyBDEScore(
            company_id=company_id,
            tenant_id=tenant_id,
            scoring_run_id=scoring_run_id,
            overall_score=overall_score,
            weighted_raw_score=weighted_raw_score,
            valuation_range=valuation_range,
            confidence=avg_confidence,
            scored_doc_count=scored_doc_count,
            is_current=True,
            version=1
        )

        db.add(bde_score)
        db.commit()
        db.refresh(bde_score)

        # Stage 5B: Generate recommendation (LLM)
        await self._generate_recommendation(
            db, company_id, tenant_id, bde_score.id, pillar_scores, flags, scoring_run_id
        )

        logger.info(f"[Stage 5] BDE Score: {overall_score}/100 ({valuation_range})")
        return bde_score.id

    def _map_valuation_range(self, score: float) -> str:
        """Deterministic mapping"""
        for (low, high), range_text in self.VALUATION_RANGES.items():
            if low <= score <= high:
                return range_text
        return "Unknown"

    async def _generate_recommendation(
        self,
        db: Session,
        company_id: str,
        tenant_id: str,
        bde_score_id: str,
        pillar_scores: Dict[str, CompanyPillarScore],
        flags: List[CompanyFlag],
        scoring_run_id: str = None
    ):
        """Generate LLM recommendation"""

        # Get prompt template
        prompt_template = self._get_prompt_template(db, "acquisition_recommendation")

        # Get BDE score
        bde_score = db.get(CompanyBDEScore, bde_score_id)

        # Build prompt
        prompt = self._build_recommendation_prompt(
            template=prompt_template,
            bde_score=bde_score,
            pillar_scores=pillar_scores,
            flags=flags
        )

        # LLM recommendation
        rec_result = await self._llm_generate_recommendation(prompt)

        # Store recommendation
        recommendation = AcquisitionRecommendation(
            company_id=company_id,
            tenant_id=tenant_id,
            scoring_run_id=scoring_run_id,
            bde_score_id=bde_score_id,
            recommendation=rec_result.get("recommendation", "HOLD"),
            recommendation_confidence=rec_result.get("confidence", 70),
            rationale=rec_result.get("rationale"),
            value_drivers=rec_result.get("value_drivers", []),
            key_risks=rec_result.get("key_risks", []),
            day_100_plan=rec_result.get("100_day_plan", []),
            suggested_valuation_multiple=rec_result.get("suggested_valuation_multiple"),
            valuation_adjustments=rec_result.get("valuation_adjustments", []),
            is_current=True,
            version=1
        )

        db.add(recommendation)
        db.commit()

        logger.info(f"[Stage 5] Recommendation: {recommendation.recommendation}")

    def _get_prompt_template(self, db: Session, template_name: str) -> str:
        """Get prompt template"""
        statement = select(PromptTemplate).where(
            PromptTemplate.name == template_name,
            PromptTemplate.is_active == True
        )
        template = db.exec(statement).first()

        if template:
            return template.template

        return """Generate acquisition recommendation based on BDE score: {overall_score}/100, valuation range: {valuation_range}.

Pillar scores:
{pillar_scores}

Flags:
{flags}

Provide: recommendation, rationale, value drivers, key risks, 100-day plan, valuation guidance."""

    def _build_recommendation_prompt(
        self,
        template: str,
        bde_score: CompanyBDEScore,
        pillar_scores: Dict,
        flags: List
    ) -> str:
        """Fill template"""

        pillar_scores_text = "\n".join([
            f"- {p}: {s.score}/5.0 ({s.health_status.value})"
            for p, s in pillar_scores.items()
        ])

        # Separate flags by type
        red_flags_text = "\n".join([
            f"- {f.flag_text}"
            for f in flags if f.flag_type.value == "red"
        ]) or "None"

        yellow_flags_text = "\n".join([
            f"- {f.flag_text}"
            for f in flags if f.flag_type.value == "yellow"
        ]) or "None"

        green_accelerants_text = "\n".join([
            f"- {f.flag_text}"
            for f in flags if f.flag_type.value == "green"
        ]) or "None"

        return template.format(
            overall_score=bde_score.overall_score,
            weighted_raw_score=bde_score.weighted_raw_score,
            valuation_range=bde_score.valuation_range,
            confidence=bde_score.confidence,
            pillar_scores=pillar_scores_text,
            red_flags=red_flags_text,
            yellow_flags=yellow_flags_text,
            green_accelerants=green_accelerants_text
        )

    async def _llm_generate_recommendation(self, prompt: str) -> Dict:
        """Call LLM"""
        try:
            response_text, usage_stats = self.llm_client.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a PE acquisition advisor. You must respond with valid JSON only, no markdown formatting."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=4000
            )

            # Clean markdown code blocks if present
            cleaned_response = response_text.strip()
            if cleaned_response.startswith("```"):
                lines = cleaned_response.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                cleaned_response = "\n".join(lines)

            # Find JSON start
            json_start = cleaned_response.find("{")
            if json_start >= 0:
                cleaned_response = cleaned_response[json_start:]

            return json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            logger.error(f"[Stage 5] JSON parse error: {e}")
            return {
                "recommendation": "HOLD",
                "confidence": 50,
                "rationale": "Unable to generate detailed recommendation due to parsing error.",
                "value_drivers": [],
                "key_risks": [],
                "100_day_plan": []
            }
        except Exception as e:
            logger.error(f"[Stage 5] Error: {e}")
            return {
                "recommendation": "HOLD",
                "confidence": 50,
                "rationale": "Unable to generate detailed recommendation.",
                "value_drivers": [],
                "key_risks": [],
                "100_day_plan": []
            }
